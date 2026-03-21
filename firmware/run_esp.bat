@echo off
echo =======================================================
echo  CONFIGURANDO AMBIENTE VIRTUAL (FIRMWARE)
echo =======================================================

IF NOT EXIST "venv" (
    echo [1/4] Criando pasta 'venv'...
    python -m venv venv
) ELSE (
    echo [1/4] Pasta 'venv' ja existe.
)

echo [2/4] Ambiente ativado. Atualizando pip...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip

IF NOT EXIST "requirements.txt" (
    echo       -^> Populando requirements.txt com ferramentas ESP...
    echo esptool>> requirements.txt
    echo mpremote>> requirements.txt
    echo adafruit-ampy>> requirements.txt
)

echo [3/4] Instalando ferramentas do FIRMWARE...
pip install -r requirements.txt

echo =======================================================
echo  SUCESSO! Ambiente configurado.
echo =======================================================
echo  Para ativar a venv no seu terminal, rode:
echo  venv\Scripts\activate
echo =======================================================
pause