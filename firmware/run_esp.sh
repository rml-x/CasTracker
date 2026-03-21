#!/bin/bash

echo "======================================================="
echo " EXECUTANDO ESP32 VIA MPREMOTE (LINUX/MAC)"
echo "======================================================="

# Verifica se o ambiente virtual existe
if [ ! -f "venv/bin/activate" ]; then
    echo "[ERRO] Ambiente virtual não encontrado!"
    echo "Rode o script de setup primeiro para criar a venv."
    exit 1
fi

# Ativa o ambiente para ter acesso ao mpremote
source venv/bin/activate

echo "Conectando ao ESP32..."
# Executa o arquivo main.py que está na pasta src diretamente no microcontrolador
mpremote run src/main.py

# Se preferir apenas abrir o terminal interativo (REPL), comente a linha acima
# e descomente a linha abaixo:
# mpremote repl