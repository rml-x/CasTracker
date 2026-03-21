#!/bin/bash
# Arquivo: firmware/setup_env.sh

VENV_DIR="venv"

echo "======================================================="
echo " CONFIGURANDO VENV DO FIRMWARE"
echo "======================================================="

cd "$(dirname "$0")" || exit

if [ ! -d "$VENV_DIR" ]; then
    echo "Criando pasta '$VENV_DIR' no firmware..."
    python3 -m venv $VENV_DIR
fi

source $VENV_DIR/bin/activate
pip install --upgrade pip

echo "Instalando dependências (ferramentas do ESP32)..."
pip install -r requirements.txt

echo "======================================================="
echo " Firmware configurado! Para ativar:"
echo " source firmware/venv/bin/activate"
echo "======================================================="