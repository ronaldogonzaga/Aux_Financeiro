@echo off
chcp 65001 >nul
title Aux_Financeiro - Envio de Relatorios
cd /d "%~dp0"

echo ============================================
echo   Aux_Financeiro - Envio de Relatorios Medicos
echo ============================================
echo.

if not exist "venv\" (
    echo [1/3] Criando ambiente virtual...
    python -m venv venv
    if errorlevel 1 (
        echo ERRO: Python nao encontrado. Instale Python 3.10+ e tente novamente.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Ambiente virtual ja existe.
)

echo [2/3] Ativando venv e instalando dependencias...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo ERRO ao instalar dependencias.
    pause
    exit /b 1
)

echo [3/3] Iniciando aplicacao...
echo.
echo   Abrindo o navegador em http://127.0.0.1:5000
echo   Pressione Ctrl+C para encerrar.
echo.

start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:5000"

python run.py

pause
