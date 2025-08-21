@echo off
echo ========================================
echo    Dashboard Logístico - Mesorregioes
echo ========================================
echo.
echo Iniciando aplicacao...
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    echo Por favor, instale Python 3.8+ e tente novamente.
    pause
    exit /b 1
)

REM Verificar se o ambiente virtual existe
if not exist "venv" (
    echo Criando ambiente virtual...
    python -m venv venv
    if errorlevel 1 (
        echo ERRO: Falha ao criar ambiente virtual!
        pause
        exit /b 1
    )
)

REM Ativar ambiente virtual
echo Ativando ambiente virtual...
call venv\Scripts\activate.bat

REM Instalar dependências
echo Instalando dependencias...
pip install -r requirements.txt

REM Executar aplicação
echo.
echo Iniciando servidor...
echo Acesse: http://localhost:5000
echo.
echo Pressione Ctrl+C para parar o servidor
echo.
python app.py

pause
