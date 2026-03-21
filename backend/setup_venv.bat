@echo off
echo =======================================================
echo  CONFIGURANDO AMBIENTE VIRTUAL (BACKEND)
echo =======================================================

:: 1. Cria a Venv se não existir
IF NOT EXIST "venv" (
    echo [1/4] Criando pasta 'venv'...
    python -m venv venv
) ELSE (
    echo [1/4] Pasta 'venv' ja existe.
)

:: 2. Ativa a Venv
echo [2/4] Ambiente ativado. Atualizando pip...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip

:: 3. Garante que requirements.txt exista
IF NOT EXIST "requirements.txt" (
    echo       -^> Populando requirements.txt com bibliotecas padrao...
    echo paho-mqtt>> requirements.txt
    echo sqlalchemy>> requirements.txt
    echo psycopg2>> requirements.txt
    echo python-dotenv>> requirements.txt
)

:: 4. Instala as dependências
echo [3/4] Instalando dependencias do BACKEND...
pip install -r requirements.txt

echo =======================================================
echo  SUCESSO! Ambiente configurado.
echo =======================================================
echo  Para ativar a venv no seu terminal, rode:
echo  venv\Scripts\activate
echo =======================================================
pause
