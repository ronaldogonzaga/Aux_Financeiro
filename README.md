# Aux_Financeiro

Aplicação web local para **envio automatizado de relatórios médicos e documentos de convênio** por e-mail aos prestadores (médicos).

O sistema associa, pelo nome do prestador, os PDFs da pasta de relatório médico e os arquivos da pasta de convênios, monta os anexos e dispara os e-mails via SMTP, com acompanhamento de progresso e histórico de envios.

---

## Objetivo

Facilitar o processo financeiro de pagamento a prestadores, permitindo:

- Cadastrar e importar prestadores (nome + e-mail)
- Configurar a conta SMTP de envio
- Personalizar o modelo de e-mail (assunto e corpo)
- Selecionar as pastas de **Relatório Médico** e **Relatório de Convênios**
- Pré-visualizar quais arquivos serão anexados a cada destinatário
- Enviar os e-mails em lote, com controle de taxa e registro de sucesso/falha
- Consultar o histórico de lotes enviados

---

## Tecnologias utilizadas

| Tecnologia | Uso |
|---|---|
| **Python 3.10+** | Linguagem principal |
| **Flask 3** | Framework web |
| **SQLite** | Banco de dados local (`data/aux_financeiro.db`) |
| **openpyxl** | Importação de planilhas Excel (`.xlsx`) |
| **odfpy** | Importação de planilhas LibreOffice (`.ods`) |
| **Werkzeug** | Utilitários do Flask (upload, etc.) |
| **smtplib** (stdlib) | Envio de e-mails via SMTP |
| **HTML / CSS / JavaScript** | Interface web |

---

## Pré-requisitos

- [Python 3.10 ou superior](https://www.python.org/downloads/) instalado
- No Windows, marque a opção **“Add Python to PATH”** durante a instalação
- Acesso a uma conta de e-mail com SMTP (ex.: Gmail com senha de app)

---

## Instalação das dependências

### Opção 1 — Script automático (Windows)

Na raiz do projeto, execute o arquivo:

```bat
iniciar.bat
```

Ele cria o ambiente virtual (`venv`), instala as dependências e inicia a aplicação.

### Opção 2 — Manual

1. Abra um terminal na pasta do projeto.

2. Crie e ative o ambiente virtual:

```bash
# Windows (PowerShell / CMD)
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

---

## Como executar a aplicação

Com o ambiente virtual ativo:

```bash
python run.py
```

A aplicação ficará disponível em:

**http://127.0.0.1:5000**

No Windows, o `iniciar.bat` também abre o navegador automaticamente nesse endereço.

Para encerrar, pressione `Ctrl+C` no terminal.

---

## Primeiros passos na interface

1. **Conta de e-mail** — Configure host SMTP, porta, usuário, senha e remetente.
2. **Modelo de e-mail** — Defina assunto e corpo (use `{{nome}}` para o nome do prestador).
3. **Prestadores** — Cadastre manualmente ou importe uma planilha (`.xlsx`, `.ods` ou `.csv`) com colunas de nome e e-mail.
4. **Enviar** — Informe as pastas de relatório médico e de convênios, gere a prévia, selecione os destinatários e dispare o lote.
5. **Histórico** — Consulte lotes anteriores e o detalhe de cada envio.

O painel inicial mostra um checklist de prontidão e estatísticas dos envios.

---

## Estrutura do projeto

```
Financeiro/
├── app/
│   ├── __init__.py          # Factory da aplicação Flask
│   ├── models.py            # Persistência SQLite
│   ├── routes.py            # Rotas de páginas e API
│   ├── services/
│   │   ├── email_service.py # Envio SMTP e processamento do lote
│   │   ├── file_matcher.py  # Associação de arquivos por nome
│   │   └── import_service.py# Parse de planilhas de prestadores
│   ├── static/              # CSS, JS e favicon
│   └── templates/           # Templates HTML (Jinja2)
├── data/                    # Banco SQLite (criado automaticamente)
├── temp_zips/               # Anexos temporários (ZIPs de convênio)
├── iniciar.bat              # Atalho de instalação + execução (Windows)
├── requirements.txt
├── run.py                   # Ponto de entrada
└── README.md
```

---

## Observações

- A aplicação é **local** (roda em `127.0.0.1`); os dados ficam no SQLite em `data/`.
- Pastas `venv/`, `data/*.db`, `temp_zips/` e arquivos `.zip` estão no `.gitignore`.
- O seletor de pastas na interface usa **tkinter** (incluído na instalação padrão do Python no Windows).
- O envio respeita um intervalo entre mensagens e um limite por hora para reduzir bloqueios do provedor SMTP.
