@echo off
echo =======================================================
echo  DEPLOY CAS-TRACKER (GRAVACAO NA FLASH)
echo =======================================================

:: Verifica a venv 
IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [ERRO] Ambiente virtual nao encontrado!
    pause
    exit /b
)

call venv\Scripts\activate.bat

echo [1/3] Limpando e Enviando arquivos atualizados...
mpremote connect COM6 fs cp src\config.json :config.json
mpremote connect COM6 fs cp src\main.py :main.py
mpremote connect COM6 fs cp src\modulos\conexao.py :modulos/conexao.py
mpremote connect COM6 fs cp src\modulos\interface.py :modulos/interface.py
mpremote connect COM6 fs cp src\modulos\sensores.py :modulos/sensores.py
mpremote connect COM6 fs cp src\modulos\ihc.py :modulos/ihc.py
mpremote connect COM6 fs cp src\modulos\armazenamento.py :modulos/armazenamento.py

echo [2/3] Resetando o hardware...
mpremote connect COM6 reset

echo [3/3] Abrindo REPL para monitoramento...
mpremote connect COM6

pause