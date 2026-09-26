from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Generator, Iterable, Optional

def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

@contextmanager
def get_db(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    conn = _connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_db(db_path) as conn:
        conn.executescript("\n            CREATE TABLE IF NOT EXISTS configuracao (\n                id INTEGER PRIMARY KEY CHECK (id = 1),\n                smtp_host TEXT NOT NULL DEFAULT 'smtp.gmail.com',\n                smtp_port INTEGER NOT NULL DEFAULT 587,\n                smtp_user TEXT NOT NULL DEFAULT '',\n                smtp_password TEXT NOT NULL DEFAULT '',\n                remetente_nome TEXT NOT NULL DEFAULT '',\n                remetente_email TEXT NOT NULL DEFAULT '',\n                usar_tls INTEGER NOT NULL DEFAULT 1,\n                atualizado_em TEXT\n            );\n\n            CREATE TABLE IF NOT EXISTS email_template (\n                id INTEGER PRIMARY KEY CHECK (id = 1),\n                assunto TEXT NOT NULL DEFAULT 'Relatório de Pagamento - {{nome}}',\n                corpo TEXT NOT NULL DEFAULT 'Prezado(a) Dr(a). {{nome}},\n\nSegue em anexo o relatório médico e os documentos de convênio referentes ao período.\n\nAtenciosamente.',\n                enviar_copia INTEGER NOT NULL DEFAULT 0,\n                atualizado_em TEXT\n            );\n\n            CREATE TABLE IF NOT EXISTS caminhos (\n                id INTEGER PRIMARY KEY CHECK (id = 1),\n                pasta_relatorio_medico TEXT NOT NULL DEFAULT '',\n                pasta_relatorio_convenio TEXT NOT NULL DEFAULT '',\n                atualizado_em TEXT\n            );\n\n            CREATE TABLE IF NOT EXISTS prestadores (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                nome TEXT NOT NULL,\n                email TEXT NOT NULL,\n                ativo INTEGER NOT NULL DEFAULT 1,\n                criado_em TEXT NOT NULL,\n                atualizado_em TEXT NOT NULL,\n                UNIQUE(email)\n            );\n\n            CREATE TABLE IF NOT EXISTS envios (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                iniciado_em TEXT NOT NULL,\n                finalizado_em TEXT,\n                pasta_medico TEXT,\n                pasta_convenio TEXT,\n                periodo_pagamento TEXT,\n                total_destinatarios INTEGER NOT NULL DEFAULT 0,\n                total_enviados INTEGER NOT NULL DEFAULT 0,\n                total_falhas INTEGER NOT NULL DEFAULT 0,\n                status TEXT NOT NULL DEFAULT 'em_andamento',\n                observacao TEXT\n            );\n\n            CREATE TABLE IF NOT EXISTS envio_itens (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                envio_id INTEGER NOT NULL,\n                prestador_id INTEGER,\n                prestador_nome TEXT NOT NULL,\n                prestador_email TEXT NOT NULL,\n                anexos_json TEXT NOT NULL DEFAULT '[]',\n                qtd_anexos INTEGER NOT NULL DEFAULT 0,\n                status TEXT NOT NULL DEFAULT 'pendente',\n                erro TEXT,\n                enviado_em TEXT,\n                FOREIGN KEY (envio_id) REFERENCES envios(id) ON DELETE CASCADE\n            );\n\n            INSERT OR IGNORE INTO configuracao (id, atualizado_em)\n            VALUES (1, datetime('now'));\n\n            INSERT OR IGNORE INTO email_template (id, atualizado_em)\n            VALUES (1, datetime('now'));\n\n            INSERT OR IGNORE INTO caminhos (id, atualizado_em)\n            VALUES (1, datetime('now'));\n            ")

def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')

def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    return dict(row)

def get_configuracao(db_path: Path) -> dict[str, Any]:
    with get_db(db_path) as conn:
        row = conn.execute('SELECT * FROM configuracao WHERE id = 1').fetchone()
        return dict(row)

def save_configuracao(db_path: Path, data: dict[str, Any]) -> dict[str, Any]:
    with get_db(db_path) as conn:
        conn.execute('\n            UPDATE configuracao SET\n                smtp_host = ?,\n                smtp_port = ?,\n                smtp_user = ?,\n                smtp_password = ?,\n                remetente_nome = ?,\n                remetente_email = ?,\n                usar_tls = ?,\n                atualizado_em = ?\n            WHERE id = 1\n            ', (data.get('smtp_host', 'smtp.gmail.com'), int(data.get('smtp_port', 587)), data.get('smtp_user', ''), data.get('smtp_password', ''), data.get('remetente_nome', ''), data.get('remetente_email', ''), 1 if data.get('usar_tls', True) else 0, _now()))
    return get_configuracao(db_path)

def get_template(db_path: Path) -> dict[str, Any]:
    with get_db(db_path) as conn:
        return dict(conn.execute('SELECT * FROM email_template WHERE id = 1').fetchone())

def save_template(db_path: Path, data: dict[str, Any]) -> dict[str, Any]:
    with get_db(db_path) as conn:
        conn.execute('\n            UPDATE email_template SET\n                assunto = ?,\n                corpo = ?,\n                enviar_copia = ?,\n                atualizado_em = ?\n            WHERE id = 1\n            ', (data.get('assunto', ''), data.get('corpo', ''), 1 if data.get('enviar_copia') else 0, _now()))
    return get_template(db_path)

def get_caminhos(db_path: Path) -> dict[str, Any]:
    with get_db(db_path) as conn:
        return dict(conn.execute('SELECT * FROM caminhos WHERE id = 1').fetchone())

def save_caminhos(db_path: Path, data: dict[str, Any]) -> dict[str, Any]:
    with get_db(db_path) as conn:
        conn.execute('\n            UPDATE caminhos SET\n                pasta_relatorio_medico = ?,\n                pasta_relatorio_convenio = ?,\n                atualizado_em = ?\n            WHERE id = 1\n            ', (data.get('pasta_relatorio_medico', ''), data.get('pasta_relatorio_convenio', ''), _now()))
    return get_caminhos(db_path)

def list_prestadores(db_path: Path, apenas_ativos: bool=False) -> list[dict[str, Any]]:
    sql = 'SELECT * FROM prestadores'
    if apenas_ativos:
        sql += ' WHERE ativo = 1'
    sql += ' ORDER BY nome COLLATE NOCASE'
    with get_db(db_path) as conn:
        return [dict(r) for r in conn.execute(sql).fetchall()]

def get_prestador(db_path: Path, prestador_id: int) -> Optional[dict[str, Any]]:
    with get_db(db_path) as conn:
        row = conn.execute('SELECT * FROM prestadores WHERE id = ?', (prestador_id,)).fetchone()
        return row_to_dict(row)

def create_prestador(db_path: Path, nome: str, email: str, ativo: bool=True) -> dict[str, Any]:
    agora = _now()
    with get_db(db_path) as conn:
        cur = conn.execute('\n            INSERT INTO prestadores (nome, email, ativo, criado_em, atualizado_em)\n            VALUES (?, ?, ?, ?, ?)\n            ', (nome.strip(), email.strip().lower(), 1 if ativo else 0, agora, agora))
        pid = cur.lastrowid
    return get_prestador(db_path, pid)

def update_prestador(db_path: Path, prestador_id: int, nome: str, email: str, ativo: bool=True) -> Optional[dict[str, Any]]:
    with get_db(db_path) as conn:
        conn.execute('\n            UPDATE prestadores SET\n                nome = ?, email = ?, ativo = ?, atualizado_em = ?\n            WHERE id = ?\n            ', (nome.strip(), email.strip().lower(), 1 if ativo else 0, _now(), prestador_id))
    return get_prestador(db_path, prestador_id)

def delete_prestador(db_path: Path, prestador_id: int) -> bool:
    with get_db(db_path) as conn:
        cur = conn.execute('DELETE FROM prestadores WHERE id = ?', (prestador_id,))
        return cur.rowcount > 0

def upsert_prestadores(db_path: Path, itens: Iterable[dict[str, str]]) -> dict[str, int]:
    inseridos = 0
    atualizados = 0
    agora = _now()
    with get_db(db_path) as conn:
        for item in itens:
            nome = (item.get('nome') or '').strip()
            email = (item.get('email') or '').strip().lower()
            if not nome or not email:
                continue
            existente = conn.execute('SELECT id FROM prestadores WHERE email = ?', (email,)).fetchone()
            if existente:
                conn.execute('\n                    UPDATE prestadores SET nome = ?, ativo = 1, atualizado_em = ?\n                    WHERE id = ?\n                    ', (nome, agora, existente['id']))
                atualizados += 1
            else:
                conn.execute('\n                    INSERT INTO prestadores (nome, email, ativo, criado_em, atualizado_em)\n                    VALUES (?, ?, 1, ?, ?)\n                    ', (nome, email, agora, agora))
                inseridos += 1
    return {'inseridos': inseridos, 'atualizados': atualizados}

def create_envio(db_path: Path, pasta_medico: str, pasta_convenio: str, periodo: str, itens: list[dict[str, Any]]) -> int:
    with get_db(db_path) as conn:
        cur = conn.execute("\n            INSERT INTO envios (\n                iniciado_em, pasta_medico, pasta_convenio, periodo_pagamento,\n                total_destinatarios, status\n            ) VALUES (?, ?, ?, ?, ?, 'em_andamento')\n            ", (_now(), pasta_medico, pasta_convenio, periodo, len(itens)))
        envio_id = cur.lastrowid
        for item in itens:
            conn.execute("\n                INSERT INTO envio_itens (\n                    envio_id, prestador_id, prestador_nome, prestador_email,\n                    anexos_json, qtd_anexos, status\n                ) VALUES (?, ?, ?, ?, ?, ?, 'pendente')\n                ", (envio_id, item.get('prestador_id'), item['nome'], item['email'], json.dumps(item.get('anexos', []), ensure_ascii=False), item.get('qtd_anexos', 0)))
        return int(envio_id)

def update_envio_item(db_path: Path, item_id: int, status: str, erro: Optional[str]=None) -> None:
    with get_db(db_path) as conn:
        conn.execute('\n            UPDATE envio_itens SET\n                status = ?, erro = ?, enviado_em = ?\n            WHERE id = ?\n            ', (status, erro, _now() if status == 'enviado' else None, item_id))

def finalize_envio(db_path: Path, envio_id: int, status: str='concluido', observacao: str='') -> None:
    with get_db(db_path) as conn:
        stats = conn.execute("\n            SELECT\n                SUM(CASE WHEN status = 'enviado' THEN 1 ELSE 0 END) AS enviados,\n                SUM(CASE WHEN status = 'erro' THEN 1 ELSE 0 END) AS falhas\n            FROM envio_itens WHERE envio_id = ?\n            ", (envio_id,)).fetchone()
        conn.execute('\n            UPDATE envios SET\n                finalizado_em = ?,\n                total_enviados = ?,\n                total_falhas = ?,\n                status = ?,\n                observacao = ?\n            WHERE id = ?\n            ', (_now(), stats['enviados'] or 0, stats['falhas'] or 0, status, observacao, envio_id))

def list_envios(db_path: Path, limit: int=50) -> list[dict[str, Any]]:
    with get_db(db_path) as conn:
        rows = conn.execute('\n            SELECT * FROM envios\n            ORDER BY id DESC\n            LIMIT ?\n            ', (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_envio(db_path: Path, envio_id: int) -> Optional[dict[str, Any]]:
    with get_db(db_path) as conn:
        envio = conn.execute('SELECT * FROM envios WHERE id = ?', (envio_id,)).fetchone()
        if not envio:
            return None
        itens = conn.execute('\n            SELECT * FROM envio_itens\n            WHERE envio_id = ?\n            ORDER BY prestador_nome COLLATE NOCASE\n            ', (envio_id,)).fetchall()
        result = dict(envio)
        parsed = []
        for item in itens:
            d = dict(item)
            try:
                d['anexos'] = json.loads(d.get('anexos_json') or '[]')
            except json.JSONDecodeError:
                d['anexos'] = []
            parsed.append(d)
        result['itens'] = parsed
        return result

def get_envio_itens_pendentes(db_path: Path, envio_id: int) -> list[dict[str, Any]]:
    with get_db(db_path) as conn:
        rows = conn.execute("\n            SELECT * FROM envio_itens\n            WHERE envio_id = ? AND status = 'pendente'\n            ORDER BY id\n            ", (envio_id,)).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d['anexos'] = json.loads(d.get('anexos_json') or '[]')
            except json.JSONDecodeError:
                d['anexos'] = []
            result.append(d)
        return result

def get_dashboard_stats(db_path: Path) -> dict[str, Any]:
    with get_db(db_path) as conn:
        prest = conn.execute('\n            SELECT\n                COUNT(*) AS total,\n                SUM(CASE WHEN ativo = 1 THEN 1 ELSE 0 END) AS ativos,\n                SUM(CASE WHEN ativo = 0 THEN 1 ELSE 0 END) AS inativos\n            FROM prestadores\n            ').fetchone()
        envio_totais = conn.execute('\n            SELECT\n                COUNT(*) AS total_lotes,\n                COALESCE(SUM(total_enviados), 0) AS emails_enviados,\n                COALESCE(SUM(total_falhas), 0) AS emails_falha,\n                COALESCE(SUM(total_destinatarios), 0) AS emails_tentados\n            FROM envios\n            ').fetchone()
        desde = (datetime.now() - timedelta(days=30)).isoformat(timespec='seconds')
        mes = conn.execute('\n            SELECT\n                COUNT(*) AS lotes,\n                COALESCE(SUM(total_enviados), 0) AS enviados,\n                COALESCE(SUM(total_falhas), 0) AS falhas\n            FROM envios\n            WHERE iniciado_em >= ?\n            ', (desde,)).fetchone()
        ultimo = conn.execute('\n            SELECT * FROM envios\n            ORDER BY id DESC\n            LIMIT 1\n            ').fetchone()
        recentes = conn.execute('\n            SELECT id, iniciado_em, periodo_pagamento, total_destinatarios,\n                   total_enviados, total_falhas, status\n            FROM envios\n            ORDER BY id DESC\n            LIMIT 5\n            ').fetchall()
        falhas_recentes = conn.execute("\n            SELECT ei.prestador_nome, ei.prestador_email, ei.erro, ei.enviado_em, e.id AS envio_id\n            FROM envio_itens ei\n            JOIN envios e ON e.id = ei.envio_id\n            WHERE ei.status = 'erro'\n            ORDER BY ei.id DESC\n            LIMIT 5\n            ").fetchall()
        config = dict(conn.execute('SELECT * FROM configuracao WHERE id = 1').fetchone())
        template = dict(conn.execute('SELECT * FROM email_template WHERE id = 1').fetchone())
        caminhos = dict(conn.execute('SELECT * FROM caminhos WHERE id = 1').fetchone())
    smtp_ok = bool((config.get('remetente_email') or config.get('smtp_user')) and config.get('smtp_host') and config.get('smtp_password'))
    template_ok = bool((template.get('assunto') or '').strip() and (template.get('corpo') or '').strip())
    pasta_medico = (caminhos.get('pasta_relatorio_medico') or '').strip()
    pasta_convenio = (caminhos.get('pasta_relatorio_convenio') or '').strip()
    pasta_medico_ok = bool(pasta_medico and Path(pasta_medico).exists())
    pasta_convenio_ok = bool(pasta_convenio and Path(pasta_convenio).exists())
    prestadores_ok = int(prest['ativos'] or 0) > 0
    checklist = [{'id': 'smtp', 'label': 'Remetente SMTP configurado', 'ok': smtp_ok, 'href': 'configuracao'}, {'id': 'template', 'label': 'Template de e-mail definido', 'ok': template_ok, 'href': 'template'}, {'id': 'prestadores', 'label': 'Prestadores ativos cadastrados', 'ok': prestadores_ok, 'href': 'prestadores'}, {'id': 'medico', 'label': 'Pasta Relatório Médico acessível', 'ok': pasta_medico_ok, 'href': 'envio'}, {'id': 'convenio', 'label': 'Pasta Relatório de Convênios acessível', 'ok': pasta_convenio_ok, 'href': 'envio'}]
    prontos = sum((1 for c in checklist if c['ok']))
    enviados = int(envio_totais['emails_enviados'] or 0)
    falhas = int(envio_totais['emails_falha'] or 0)
    tentados = enviados + falhas
    taxa_sucesso = round(enviados / tentados * 100, 1) if tentados else None
    return {'prestadores_total': int(prest['total'] or 0), 'prestadores_ativos': int(prest['ativos'] or 0), 'prestadores_inativos': int(prest['inativos'] or 0), 'lotes_total': int(envio_totais['total_lotes'] or 0), 'emails_enviados': enviados, 'emails_falha': falhas, 'taxa_sucesso': taxa_sucesso, 'lotes_30d': int(mes['lotes'] or 0), 'enviados_30d': int(mes['enviados'] or 0), 'falhas_30d': int(mes['falhas'] or 0), 'ultimo_envio': dict(ultimo) if ultimo else None, 'envios_recentes': [dict(r) for r in recentes], 'falhas_recentes': [dict(r) for r in falhas_recentes], 'checklist': checklist, 'prontidao': {'ok': prontos, 'total': len(checklist), 'completo': prontos == len(checklist)}, 'config': {'remetente': config.get('remetente_nome') or config.get('remetente_email') or '', 'email': config.get('remetente_email') or '', 'smtp_host': config.get('smtp_host') or '', 'smtp_ok': smtp_ok}, 'caminhos': {'pasta_medico': pasta_medico, 'pasta_convenio': pasta_convenio, 'pasta_medico_ok': pasta_medico_ok, 'pasta_convenio_ok': pasta_convenio_ok}, 'template_assunto': (template.get('assunto') or '')[:80], 'enviar_copia': bool(template.get('enviar_copia'))}
