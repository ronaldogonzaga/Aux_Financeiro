from __future__ import annotations
import smtplib
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Any, Callable, Optional
from app import models
from app.services.file_matcher import limpar_anexos_temporarios
MAX_EMAILS_POR_HORA = 80
INTERVALO_ENTRE_ENVIOS = 3

def render_template(texto: str, nome: str, **extra: str) -> str:
    resultado = texto.replace('{{nome}}', nome)
    for chave, valor in extra.items():
        resultado = resultado.replace(f'{ {{chave}}} ', valor)
    return resultado

def _anexar_arquivo(msg: MIMEMultipart, caminho: str, nome: Optional[str]=None) -> None:
    path = Path(caminho)
    if not path.exists():
        raise FileNotFoundError(f'Anexo não encontrado: {caminho}')
    with open(path, 'rb') as f:
        parte = MIMEApplication(f.read(), Name=nome or path.name)
    parte['Content-Disposition'] = f'attachment; filename="{nome or path.name}"'
    msg.attach(parte)

def enviar_email_unico(config: dict[str, Any], template: dict[str, Any], destinatario_nome: str, destinatario_email: str, anexos: list[dict[str, str]]) -> None:
    assunto = render_template(template.get('assunto') or '', destinatario_nome)
    corpo = render_template(template.get('corpo') or '', destinatario_nome)
    remetente_email = config.get('remetente_email') or config.get('smtp_user')
    remetente_nome = config.get('remetente_nome') or ''
    msg = MIMEMultipart()
    msg['From'] = formataddr((remetente_nome, remetente_email))
    msg['To'] = destinatario_email
    msg['Subject'] = assunto
    if template.get('enviar_copia'):
        msg['Bcc'] = remetente_email
    msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
    for anexo in anexos:
        _anexar_arquivo(msg, anexo['caminho'], anexo.get('nome'))
    host = config.get('smtp_host') or 'smtp.gmail.com'
    port = int(config.get('smtp_port') or 587)
    user = config.get('smtp_user') or ''
    password = config.get('smtp_password') or ''
    usar_tls = bool(config.get('usar_tls', 1))
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=60) as server:
            if user and password:
                server.login(user, password)
            destinatarios = [destinatario_email]
            if template.get('enviar_copia') and remetente_email:
                destinatarios.append(remetente_email)
            server.sendmail(remetente_email, destinatarios, msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=60) as server:
            if usar_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            destinatarios = [destinatario_email]
            if template.get('enviar_copia') and remetente_email:
                destinatarios.append(remetente_email)
            server.sendmail(remetente_email, destinatarios, msg.as_string())

def processar_envio(db_path: Path, envio_id: int, progress_callback: Optional[Callable[[dict[str, Any]], None]]=None, temp_dir: Optional[Path]=None) -> dict[str, Any]:
    config = models.get_configuracao(db_path)
    template = models.get_template(db_path)
    if not (config.get('remetente_email') or config.get('smtp_user')):
        models.finalize_envio(db_path, envio_id, 'erro', 'Remetente de e-mail não configurado.')
        return {'ok': False, 'erro': 'Remetente de e-mail não configurado.'}
    itens = models.get_envio_itens_pendentes(db_path, envio_id)
    enviados_na_hora = 0
    inicio_janela = time.monotonic()
    total = len(itens)
    enviados = 0
    falhas = 0
    for idx, item in enumerate(itens):
        decorrido = time.monotonic() - inicio_janela
        if enviados_na_hora >= MAX_EMAILS_POR_HORA:
            espera = max(0, 3600 - decorrido)
            if progress_callback:
                progress_callback({'tipo': 'pausa', 'mensagem': f'Limite de {MAX_EMAILS_POR_HORA} e-mails/hora atingido. Aguardando {int(espera)}s...', 'enviados': enviados, 'falhas': falhas, 'total': total, 'atual': idx})
            if espera > 0:
                time.sleep(espera)
            enviados_na_hora = 0
            inicio_janela = time.monotonic()
        anexos = item.get('anexos') or []
        try:
            enviar_email_unico(config=config, template=template, destinatario_nome=item['prestador_nome'], destinatario_email=item['prestador_email'], anexos=anexos)
            models.update_envio_item(db_path, item['id'], 'enviado')
            limpar_anexos_temporarios(anexos, temp_dir)
            enviados += 1
            enviados_na_hora += 1
            if progress_callback:
                progress_callback({'tipo': 'ok', 'nome': item['prestador_nome'], 'email': item['prestador_email'], 'enviados': enviados, 'falhas': falhas, 'total': total, 'atual': idx + 1})
        except Exception as exc:
            models.update_envio_item(db_path, item['id'], 'erro', str(exc))
            falhas += 1
            if progress_callback:
                progress_callback({'tipo': 'erro', 'nome': item['prestador_nome'], 'email': item['prestador_email'], 'erro': str(exc), 'enviados': enviados, 'falhas': falhas, 'total': total, 'atual': idx + 1})
        if idx < total - 1:
            time.sleep(INTERVALO_ENTRE_ENVIOS)
    models.finalize_envio(db_path, envio_id, 'concluido')
    return {'ok': True, 'envio_id': envio_id, 'enviados': enviados, 'falhas': falhas, 'total': total}
