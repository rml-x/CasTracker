from modulos.conexao import conectar_wifi, ajustar_hora_ntp, timestamp
from modulos.sensores import temperatura_ds18b20, pressao_bmp180, umidade_dht22
from modulos.interface import cliente_mqtt
from modulos.ihc import meu_lcd
from machine import I2C, Pin, reset
from ujson import load, dumps
from time import sleep
import gc
from network import WLAN, STA_IF

sta_if = WLAN(STA_IF)


with open('config.json','r') as arquivo:
    assets = load(arquivo)


ssid = assets['wifi']['ssid']
pswd = assets['wifi']['pswd']

sensor = []

try:
    print("Gerando bus...")
    bus_i2c = I2C(
        0,
        sda = Pin(assets['pinos']['sda']),
        scl = Pin(assets['pinos']['scl']),
        freq = 100000
    )
    enderecos_dispositivos = bus_i2c.scan()
except Exception as e:
    print(f"Deu erro no I2C: {e}")

try:
    print("Ligando LCD")
    lcd = meu_lcd(
        bus_i2c, 
        enderecos_dispositivos[0],
        4, 
        20
    )
    lcd.imprimir("LCD e I2C Ok!", 1)
except Exception as e:
    print(f"Deu erro no LCD: {e}")

lcd.imprimir("Conectando Sensores...")
lcd.imprimir("Pres: ...", 1)
lcd.imprimir("Umid: ...", 2)
lcd.imprimir("Temp: ...", 3)
sleep(5)

try:
    lcd.imprimir("Pres: Conectando...", 1)
    sensor.append(
        pressao_bmp180(
            i2c_bus = bus_i2c
        )
    )
    lcd.imprimir("Pres: Conectado!", 1)
    sleep(1)
except Exception as e:
    lcd.imprimir(lcd.imprimir("Pres: erro!!!", 1))
    print('Erro ao conectar sensor de Pressão!',e)

try:
    lcd.imprimir("Umid: ...", 2)
    sensor.append(
        umidade_dht22(
            pino = assets['pinos']['dht']
        )
    )
    lcd.imprimir("Umid: Conectado!", 2)
    sleep(1)
except Exception as e:
    lcd.imprimir(lcd.imprimir("Umid: erro!!!", 2))
    print('Erro ao conectar sensor de Umidade!',e)


try:
    lcd.imprimir("Temp: Conectando...", 3)
    sensor.append(
        temperatura_ds18b20(
            pino = assets['pinos']['onewire']
        )
    )
    lcd.imprimir("Temp: Conectado", 3)
    sleep(1)
except Exception as e:
    lcd.imprimir(lcd.imprimir("Temp: erro!!!", 2))
    print('Erro ao conectar sensor de Temperatura!',e)


try:
    lcd.imprimir("Conectando WiFi...")

    print(assets['wifi']['ssid'],assets['wifi']['pswd'])
    lcd.imprimir(f"\n{conectar_wifi(assets['wifi']['ssid'],assets['wifi']['pswd'])}",1)
    lcd.imprimir(f"IP: {sta_if.ifconfig()[0]}", 1)
    print(f"Conectado! IP do dispositivo: {sta_if.ifconfig()[0]}")
    sleep(5)
except Exception as e:
    lcd.imprimir(f"\n{e}",1)
    print('Erro ao carregar Wifi!',e)
    sleep(3)
    reset()

try:
    lcd.imprimir("Sincronizando hora...")
    sleep(5)
    lcd.imprimir(f"\n{ajustar_hora_ntp()}",1)
    sleep(2)
except Exception as e:
    #lcd.imprimir(f"\n{e}",1)

    lcd.imprimir("erro ntp!",1)
    sleep(3)
    reset()

try:
    lcd.imprimir('Conectando MQTT...')
    hora_sincronizada = True
    cliente = cliente_mqtt(
        broker = assets['mqtt']['broker'],
        id_cliente = assets['mqtt']['id_cliente']
    )
    lcd.imprimir('\nMQTT Conectado!',1)
    sleep(2)
except Exception as e:
    lcd.imprimir(f"\n{e}",1)
    sleep(3)
    reset()

lcd.imprimir('Medicoes: ')

mqtt_ok = True  # coloca essa flag ANTES do while True

while True:
    try:
        # 1. Verifica WiFi e tenta reconectar se necessário
        if not sta_if.isconnected():
            print("WiFi caiu. Reconectando...")
            mqtt_ok = False
            hora_sincronizada = False

            if not conectar_wifi(ssid, pswd):
                print("Sem sinal. Aguardando próximo ciclo...")
                sleep(10)
                continue

            # WiFi voltou — estabiliza antes de subir os serviços
            print("WiFi recuperado! Estabilizando...")
            sleep(5)

            try:
                print("Sincronizando NTP...")
                ajustar_hora_ntp()
                hora_sincronizada = True

                print("Reconectando MQTT...")
                cliente.reconectar()
                mqtt_ok = True
                print("MQTT pronto!")

            except Exception as e:
                print(f"Rede instável, MQTT adiado: {e}")
                mqtt_ok = False

        # 2. Lê sensores (independente do MQTT)
        json_pub = {
            'timestamp': timestamp(),
            'Medições': []
        }
        output = []

        for i in range(len(sensor)):
            sensor[i].ler_sensor()
            json_pub['Medições'].append(sensor[i].empacotar())
            output.append(f'\n{sensor[i].tipo[0:4]}: {sensor[i].leitura:.1f}')

        for nro, linha in enumerate(output):
            lcd.imprimir(linha, nro + 1)

        # 3. Publica MQTT só se a conexão estiver confirmada
        if mqtt_ok:
            try:
                cliente.publicar(
                    mensagem=dumps(json_pub),
                    topico=assets['mqtt']['topico']
                )
            except Exception as e:
                print(f"Erro ao publicar MQTT: {e}")
                mqtt_ok = False

    except Exception as e:
        print(f"Erro inesperado no loop: {e}")
        sleep(10)

    gc.collect()
    sleep(60)