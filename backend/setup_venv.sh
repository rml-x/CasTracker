#!/bin/bash

VENV_DIR="venv"

echo "======================================================="
echo " CONFIGURANDO VENV DO BACKEND"
echo "======================================================="

cd "$(dirname "$0")" || exit

if [ ! -d "$VENV_DIR" ]; then
    echo "Criando pasta '$VENV_DIR' no backend..."
    python3 -m venv $VENV_DIR
fi

source $VENV_DIR/bin/activate
pip install --upgrade pip

echo "Instalando dependências do backend..."
pip install -r requirements.txt

echo "======================================================="
echo " Backend configurado! Para ativar:"
echo " source backend/venv/bin/activate"
echo "======================================================="