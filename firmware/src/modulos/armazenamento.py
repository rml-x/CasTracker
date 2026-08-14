import os
from ujson import dumps, loads

ARQUIVO_FILA = 'fila_pendente.jsonl'


def salvar_fila(fila):
    """Persiste a fila de leituras pendentes na flash (formato JSON Lines,
    uma leitura por linha), para sobreviver a um reboot inesperado.

    Escreve num arquivo temporário e só substitui o definitivo com
    os.rename() ao final — isso evita corromper a fila caso o dispositivo
    perca energia bem no meio da gravação.
    """
    temporario = ARQUIVO_FILA + '.tmp'
    try:
        with open(temporario, 'w') as arquivo:
            for item in fila:
                arquivo.write(dumps(item) + '\n')
        os.rename(temporario, ARQUIVO_FILA)
    except Exception as e:
        print(f"Erro ao salvar fila em disco: {e}")


def carregar_fila():
    """Recupera leituras pendentes salvas antes do último reboot.
    Retorna lista vazia se o arquivo não existir (primeira execução,
    ou última sessão terminou sem pendências).
    """
    fila = []
    try:
        with open(ARQUIVO_FILA, 'r') as arquivo:
            for linha in arquivo:
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    fila.append(loads(linha))
                except Exception:
                    print("Linha corrompida na fila salva, ignorando.")
    except OSError:
        pass  # arquivo não existe ainda
    return fila


def limpar_arquivo_fila():
    """Remove o arquivo de fila quando não há mais pendências."""
    try:
        os.remove(ARQUIVO_FILA)
    except OSError:
        pass  # já não existe, nada a fazer