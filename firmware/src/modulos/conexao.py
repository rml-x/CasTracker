import network
from network import WLAN,STA_IF
from time import sleep, localtime, time
from machine import reset, RTC
from ntptime import settime
from umqtt.simple import MQTTClient
from modulos.ihc import meu_lcd

class ConnectionError(Exception):
    pass

STATUS_MESSAGES = {
    network.STAT_IDLE: 'STAT_IDLE (Ocioso)',
    network.STAT_CONNECTING: 'STAT_CONNECTING (Conectando...)',
    network.STAT_WRONG_PASSWORD: 'STAT_WRONG_PASSWORD (Senha incorreta)',
    network.STAT_NO_AP_FOUND: 'STAT_NO_AP_FOUND (Rede não encontrada)',
    network.STAT_CONNECT_FAIL: 'STAT_CONNECT_FAIL (Falha na conexão)',
    network.STAT_GOT_IP: 'STAT_GOT_IP (Conexão bem-sucedida!)'
}

def conectar_wifi(ssid, pswd, tentativas=5, espera=3):
    sta_if = WLAN(STA_IF)

    if sta_if.isconnected():
        return True

    sta_if.active(False)
    sleep(1)
    sta_if.active(True)
    sleep(1)

    print(f"Conectando a {ssid} ... ")
    sta_if.connect(ssid, pswd)

    for i in range(tentativas):
        if sta_if.isconnected():
            print("\nConectado com sucesso!")
            return True
        print(f"WiFi tentativa {i+1}/{tentativas}...")
        sleep(espera)

    sta_if.active(False)
    final_status = sta_if.status()
    error_message = STATUS_MESSAGES.get(final_status, f"Código de erro desconhecido: {final_status}")
    print(f"\nFalha: {error_message}")
    return False

def ajustar_hora_ntp(tentativas = 10, espera = 5):
    for i in range(tentativas):
        try:
            settime()
            agora_utc = time()
            fuso_horario_offset = -3 * 3600
            tm = localtime(agora_utc + fuso_horario_offset)
            RTC().datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))
            print("ntp ok!")
            return True
        except Exception as e:
            print(f"NTP tentativa {i+1}/{tentativas} falhou: {e}")
            sleep(espera)
    raise Exception(f"NTP falhou após {tentativas} tentativas")


def timestamp():
    tupla_data = RTC().datetime()
    return f"{tupla_data[0]}-{tupla_data[1]}-{tupla_data[2]} {tupla_data[4]}:{tupla_data[5]}:{tupla_data[6]}.{tupla_data[7]}"