from __future__ import annotations
import threading
from pathlib import Path
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from app import models
from app.services.email_service import processar_envio
from app.services.file_matcher import preview_todos
from app.services.import_service import parse_planilha
bp = Blueprint('main', __name__)
_envio_estado: dict = {'em_andamento': False, 'envio_id': None, 'progresso': None, 'resultado': None}
_envio_lock = threading.Lock()

def _db() -> Path:
    return Path(current_app.config['DATABASE'])

def _temp() -> Path:
    return Path(current_app.config['TEMP_ZIPS'])

@bp.route('/')
def index():
    from app.services.file_matcher import extract_periodo_from_path
    dash = models.get_dashboard_stats(_db())
    periodo = None
    pasta = dash['caminhos'].get('pasta_medico') or ''
    if pasta:
        periodo = extract_periodo_from_path(pasta)
    return render_template('index.html', dash=dash, periodo=periodo, envio_estado=_envio_estado)

@bp.route('/envio')
def pagina_envio():
    caminhos = models.get_caminhos(_db())
    prestadores = models.list_prestadores(_db(), apenas_ativos=True)
    return render_template('envio.html', caminhos=caminhos, total_prestadores=len(prestadores), envio_estado=_envio_estado)

@bp.route('/configuracao')
def pagina_configuracao():
    return render_template('configuracao.html', config=models.get_configuracao(_db()))

@bp.route('/template')
def pagina_template():
    return render_template('template.html', template=models.get_template(_db()))

@bp.route('/prestadores')
def pagina_prestadores():
    return render_template('prestadores.html', prestadores=models.list_prestadores(_db()))

@bp.route('/historico')
def pagina_historico():
    return render_template('historico.html', envios=models.list_envios(_db()))

@bp.route('/historico/<int:envio_id>')
def pagina_historico_detalhe(envio_id: int):
    envio = models.get_envio(_db(), envio_id)
    if not envio:
        flash('Envio não encontrado.', 'erro')
        return redirect(url_for('main.pagina_historico'))
    return render_template('historico_detalhe.html', envio=envio)

@bp.route('/api/configuracao', methods=['GET', 'POST'])
def api_configuracao():
    if request.method == 'GET':
        return jsonify(models.get_configuracao(_db()))
    data = request.get_json(silent=True) or request.form.to_dict()
    atual = models.get_configuracao(_db())
    if not data.get('smtp_password'):
        data['smtp_password'] = atual.get('smtp_password', '')
    data['usar_tls'] = str(data.get('usar_tls', '1')) in ('1', 'true', 'True', 'on')
    salvo = models.save_configuracao(_db(), data)
    salvo = dict(salvo)
    salvo['smtp_password'] = '********' if salvo.get('smtp_password') else ''
    return jsonify({'ok': True, 'config': salvo})

@bp.route('/api/template', methods=['GET', 'POST'])
def api_template():
    if request.method == 'GET':
        return jsonify(models.get_template(_db()))
    data = request.get_json(silent=True) or request.form.to_dict()
    data['enviar_copia'] = str(data.get('enviar_copia', '0')) in ('1', 'true', 'True', 'on')
    salvo = models.save_template(_db(), data)
    return jsonify({'ok': True, 'template': salvo})

@bp.route('/api/caminhos', methods=['GET', 'POST'])
def api_caminhos():
    if request.method == 'GET':
        return jsonify(models.get_caminhos(_db()))
    data = request.get_json(silent=True) or request.form.to_dict()
    salvo = models.save_caminhos(_db(), data)
    return jsonify({'ok': True, 'caminhos': salvo})

@bp.route('/api/selecionar-pasta', methods=['POST'])
def api_selecionar_pasta():
    data = request.get_json(silent=True) or {}
    titulo = (data.get('titulo') or 'Selecionar pasta').strip()
    inicial = (data.get('inicial') or '').strip()
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return (jsonify({'ok': False, 'erro': 'Seletor de pastas indisponível neste ambiente (tkinter).'}), 500)
    initial_dir = inicial if inicial and Path(inicial).exists() else None
    if initial_dir and Path(initial_dir).is_file():
        initial_dir = str(Path(initial_dir).parent)
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    try:
        pasta = filedialog.askdirectory(parent=root, title=titulo, initialdir=initial_dir or None, mustexist=True)
    finally:
        root.destroy()
    if not pasta:
        return jsonify({'ok': False, 'cancelado': True})
    caminho = str(Path(pasta).resolve())
    return jsonify({'ok': True, 'pasta': caminho, 'nome': Path(caminho).name})

@bp.route('/api/prestadores', methods=['GET', 'POST'])
def api_prestadores():
    if request.method == 'GET':
        return jsonify(models.list_prestadores(_db()))
    data = request.get_json(silent=True) or {}
    nome = (data.get('nome') or '').strip()
    email = (data.get('email') or '').strip()
    if not nome or not email:
        return (jsonify({'ok': False, 'erro': 'Nome e e-mail são obrigatórios.'}), 400)
    try:
        p = models.create_prestador(_db(), nome, email, bool(data.get('ativo', True)))
        return jsonify({'ok': True, 'prestador': p})
    except Exception as exc:
        return (jsonify({'ok': False, 'erro': str(exc)}), 400)

@bp.route('/api/prestadores/<int:pid>', methods=['PUT', 'DELETE'])
def api_prestador_item(pid: int):
    if request.method == 'DELETE':
        ok = models.delete_prestador(_db(), pid)
        return jsonify({'ok': ok})
    data = request.get_json(silent=True) or {}
    nome = (data.get('nome') or '').strip()
    email = (data.get('email') or '').strip()
    if not nome or not email:
        return (jsonify({'ok': False, 'erro': 'Nome e e-mail são obrigatórios.'}), 400)
    try:
        p = models.update_prestador(_db(), pid, nome, email, bool(data.get('ativo', True)))
        if not p:
            return (jsonify({'ok': False, 'erro': 'Prestador não encontrado.'}), 404)
        return jsonify({'ok': True, 'prestador': p})
    except Exception as exc:
        return (jsonify({'ok': False, 'erro': str(exc)}), 400)

@bp.route('/api/prestadores/importar', methods=['POST'])
def api_importar_prestadores():
    arquivo = request.files.get('arquivo')
    if not arquivo or not arquivo.filename:
        return (jsonify({'ok': False, 'erro': 'Nenhum arquivo enviado.'}), 400)
    try:
        conteudo = arquivo.read()
        itens = parse_planilha(arquivo.filename, conteudo)
        if not itens:
            return (jsonify({'ok': False, 'erro': 'Nenhum registro válido encontrado.'}), 400)
        resultado = models.upsert_prestadores(_db(), itens)
        return jsonify({'ok': True, **resultado, 'total_lidos': len(itens)})
    except Exception as exc:
        return (jsonify({'ok': False, 'erro': str(exc)}), 400)

@bp.route('/api/preview', methods=['POST'])
def api_preview():
    data = request.get_json(silent=True) or {}
    pasta_medico = (data.get('pasta_relatorio_medico') or '').strip()
    pasta_convenio = (data.get('pasta_relatorio_convenio') or '').strip()
    models.save_caminhos(_db(), {'pasta_relatorio_medico': pasta_medico, 'pasta_relatorio_convenio': pasta_convenio})
    prestadores = models.list_prestadores(_db(), apenas_ativos=True)
    if not prestadores:
        return (jsonify({'ok': False, 'erro': 'Nenhum prestador ativo cadastrado.'}), 400)
    resultado = preview_todos(prestadores=prestadores, pasta_medico=pasta_medico, pasta_convenio=pasta_convenio, temp_dir=_temp())
    return jsonify(resultado)

@bp.route('/api/enviar', methods=['POST'])
def api_enviar():
    with _envio_lock:
        if _envio_estado['em_andamento']:
            return (jsonify({'ok': False, 'erro': 'Já existe um envio em andamento.'}), 409)
    data = request.get_json(silent=True) or {}
    itens = data.get('itens') or []
    selecionados = [i for i in itens if i.get('selecionado') and i.get('tem_anexos') and i.get('anexos')]
    if not selecionados:
        return (jsonify({'ok': False, 'erro': 'Nenhum destinatário válido selecionado.'}), 400)
    caminhos = models.get_caminhos(_db())
    periodo = data.get('periodo') or ''
    envio_id = models.create_envio(_db(), pasta_medico=caminhos.get('pasta_relatorio_medico', ''), pasta_convenio=caminhos.get('pasta_relatorio_convenio', ''), periodo=periodo, itens=selecionados)
    db_path = _db()
    temp_dir = _temp()

    def _worker():
        with _envio_lock:
            _envio_estado['em_andamento'] = True
            _envio_estado['envio_id'] = envio_id
            _envio_estado['progresso'] = {'enviados': 0, 'falhas': 0, 'total': len(selecionados)}
            _envio_estado['resultado'] = None

        def on_progress(info):
            with _envio_lock:
                _envio_estado['progresso'] = info
        try:
            resultado = processar_envio(db_path, envio_id, progress_callback=on_progress, temp_dir=temp_dir)
            with _envio_lock:
                _envio_estado['resultado'] = resultado
        finally:
            with _envio_lock:
                _envio_estado['em_andamento'] = False
    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return jsonify({'ok': True, 'envio_id': envio_id, 'total': len(selecionados)})

@bp.route('/api/envio/status')
def api_envio_status():
    with _envio_lock:
        return jsonify(dict(_envio_estado))

@bp.route('/api/historico')
def api_historico():
    return jsonify(models.list_envios(_db()))

@bp.route('/api/historico/<int:envio_id>')
def api_historico_detalhe(envio_id: int):
    envio = models.get_envio(_db(), envio_id)
    if not envio:
        return (jsonify({'ok': False, 'erro': 'Não encontrado.'}), 404)
    return jsonify(envio)
