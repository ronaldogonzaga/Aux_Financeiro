from __future__ import annotations
import re
import shutil
import unicodedata
import zipfile
from pathlib import Path
from typing import Any, Optional

def normalize_name(text: str) -> str:
    if not text:
        return ''
    nfkd = unicodedata.normalize('NFKD', text)
    sem_acento = ''.join((c for c in nfkd if not unicodedata.combining(c)))
    limpo = re.sub('[^a-zA-Z0-9\\s]', ' ', sem_acento.lower())
    return re.sub('\\s+', ' ', limpo).strip()

def extract_periodo_from_path(pasta_medico: str | Path) -> Optional[str]:
    nome = Path(pasta_medico).name
    match = re.search('pagamento\\s+(.+)$', nome, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    if re.search('\\d{1,2}-\\d{1,2}-\\d{2,4}', nome):
        return nome
    return None

def extract_mes_ano_from_periodo(periodo: str) -> tuple[Optional[str], Optional[str]]:
    match = re.search('(\\d{1,2})-(\\d{1,2})-(\\d{2,4})', periodo)
    if not match:
        return (None, None)
    mes = match.group(2).zfill(2)
    ano = match.group(3)
    if len(ano) == 2:
        ano_completo = f'20{ano}'
    else:
        ano_completo = ano
    return (mes, ano_completo)

def find_pdf_medico(pasta_medico: Path, nome_medico: str) -> Optional[Path]:
    if not pasta_medico.exists() or not pasta_medico.is_dir():
        return None
    alvo = normalize_name(nome_medico)
    if not alvo:
        return None
    candidatos: list[tuple[int, Path]] = []
    for pdf in pasta_medico.glob('*.pdf'):
        nome_arquivo = normalize_name(pdf.stem)
        if alvo in nome_arquivo or nome_arquivo.endswith(alvo):
            score = abs(len(nome_arquivo) - len(alvo))
            candidatos.append((score, pdf))
    if not candidatos:
        palavras = alvo.split()
        for pdf in pasta_medico.glob('*.pdf'):
            nome_arquivo = normalize_name(pdf.stem)
            if all((p in nome_arquivo for p in palavras)):
                score = abs(len(nome_arquivo) - len(alvo))
                candidatos.append((score, pdf))
    if not candidatos:
        return None
    candidatos.sort(key=lambda x: x[0])
    return candidatos[0][1]

def find_pasta_medico_convenio(pasta_convenio: Path, nome_medico: str) -> Optional[Path]:
    if not pasta_convenio.exists() or not pasta_convenio.is_dir():
        return None
    alvo = normalize_name(nome_medico)
    if not alvo:
        return None
    melhores: list[tuple[int, Path]] = []
    for item in pasta_convenio.iterdir():
        if not item.is_dir():
            continue
        nome_pasta = normalize_name(item.name)
        if nome_pasta == alvo or alvo in nome_pasta or nome_pasta in alvo:
            score = abs(len(nome_pasta) - len(alvo))
            melhores.append((score, item))
        else:
            palavras = alvo.split()
            if palavras and all((p in nome_pasta for p in palavras)):
                score = abs(len(nome_pasta) - len(alvo)) + 10
                melhores.append((score, item))
    if not melhores:
        return None
    melhores.sort(key=lambda x: x[0])
    return melhores[0][1]

def find_pasta_pagamento(pasta_medico_convenio: Path, periodo: str) -> Optional[Path]:
    if not pasta_medico_convenio.exists():
        return None
    periodo_norm = normalize_name(periodo)
    periodo_raw = periodo.strip().lower()
    for item in pasta_medico_convenio.iterdir():
        if not item.is_dir():
            continue
        nome = item.name.lower()
        nome_norm = normalize_name(item.name)
        if periodo_raw in nome or periodo_norm in nome_norm:
            return item
        if f'pagamento {periodo_raw}' in nome:
            return item
    mes, ano = extract_mes_ano_from_periodo(periodo)
    if mes and ano:
        ano_curto = ano[-2:]
        padroes = [f'{mes}-{ano}', f'{mes}-{ano_curto}', f'{ano}-{mes}', f'{ano_curto}-{mes}']
        for item in pasta_medico_convenio.iterdir():
            if not item.is_dir():
                continue
            nome = item.name.lower()
            if any((p in nome for p in padroes)) and 'pagamento' in nome:
                return item
    return None

def zip_folder(pasta: Path, destino_zip: Path) -> Path:
    destino_zip.parent.mkdir(parents=True, exist_ok=True)
    if destino_zip.exists():
        destino_zip.unlink()
    with zipfile.ZipFile(destino_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for arquivo in pasta.rglob('*'):
            if arquivo.is_file():
                arcname = arquivo.relative_to(pasta)
                zf.write(arquivo, arcname)
    return destino_zip

def safe_filename(name: str) -> str:
    limpo = re.sub('[<>:"/\\\\|?*]', '_', name)
    return limpo.strip() or 'anexo'

def montar_anexos_prestador(nome: str, pasta_medico: Path, pasta_convenio: Path, periodo: str, temp_dir: Path) -> dict[str, Any]:
    anexos: list[dict[str, str]] = []
    avisos: list[str] = []
    pdf = find_pdf_medico(pasta_medico, nome)
    if pdf:
        anexos.append({'tipo': 'pdf_medico', 'nome': pdf.name, 'caminho': str(pdf.resolve())})
    else:
        avisos.append('PDF do relatório médico não encontrado.')
    if pasta_convenio.exists():
        pasta_med = find_pasta_medico_convenio(pasta_convenio, nome)
        if pasta_med:
            pasta_pag = find_pasta_pagamento(pasta_med, periodo)
            if pasta_pag:
                zip_name = f'{safe_filename(nome)} - Pagamento {safe_filename(periodo)}.zip'
                zip_path = temp_dir / zip_name
                try:
                    zip_folder(pasta_pag, zip_path)
                    anexos.append({'tipo': 'zip_convenio', 'nome': zip_name, 'caminho': str(zip_path.resolve()), 'origem': str(pasta_pag.resolve())})
                except OSError as exc:
                    avisos.append(f'Falha ao compactar pasta de convênio: {exc}')
            else:
                avisos.append(f"Subpasta de pagamento '{periodo}' não encontrada em '{pasta_med.name}'.")
        else:
            avisos.append('Pasta do médico em Relatório de Convênios não encontrada.')
    else:
        avisos.append('Pasta de Relatório de Convênios inexistente ou não informada.')
    return {'anexos': anexos, 'qtd_anexos': len(anexos), 'avisos': avisos, 'tem_anexos': len(anexos) > 0}

def limpar_temp_zips(temp_dir: Path) -> None:
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

def limpar_anexos_temporarios(anexos: list[dict[str, Any]], temp_dir: Path | None=None) -> None:
    temp_resolved = temp_dir.resolve() if temp_dir else None
    for anexo in anexos or []:
        if anexo.get('tipo') != 'zip_convenio':
            continue
        caminho = anexo.get('caminho') or ''
        if not caminho:
            continue
        path = Path(caminho)
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if not resolved.is_file():
            continue
        if temp_resolved is not None:
            try:
                resolved.relative_to(temp_resolved)
            except ValueError:
                continue
        elif 'temp_zips' not in resolved.parts:
            continue
        try:
            resolved.unlink(missing_ok=True)
        except OSError:
            pass

def preview_todos(prestadores: list[dict[str, Any]], pasta_medico: str, pasta_convenio: str, temp_dir: Path) -> dict[str, Any]:
    pm = Path(pasta_medico)
    pc = Path(pasta_convenio) if pasta_convenio else Path('')
    periodo = extract_periodo_from_path(pm)
    if not pasta_medico or not pm.exists():
        return {'ok': False, 'erro': 'Pasta de Relatório Médico inválida ou inexistente.', 'periodo': periodo, 'itens': []}
    if not periodo:
        return {'ok': False, 'erro': "Não foi possível identificar o período de pagamento no nome da pasta. Use algo como 'Pagamento 15-09-26'.", 'periodo': None, 'itens': []}
    limpar_temp_zips(temp_dir)
    itens = []
    for p in prestadores:
        resultado = montar_anexos_prestador(nome=p['nome'], pasta_medico=pm, pasta_convenio=pc, periodo=periodo, temp_dir=temp_dir)
        itens.append({'prestador_id': p['id'], 'nome': p['nome'], 'email': p['email'], 'anexos': resultado['anexos'], 'qtd_anexos': resultado['qtd_anexos'], 'avisos': resultado['avisos'], 'tem_anexos': resultado['tem_anexos'], 'selecionado': resultado['tem_anexos']})
    com_anexo = sum((1 for i in itens if i['tem_anexos']))
    sem_anexo = len(itens) - com_anexo
    return {'ok': True, 'periodo': periodo, 'pasta_medico': str(pm), 'pasta_convenio': str(pc) if pasta_convenio else '', 'total': len(itens), 'com_anexo': com_anexo, 'sem_anexo': sem_anexo, 'itens': itens}
