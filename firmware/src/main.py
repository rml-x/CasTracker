import ntptime
from modulos.conexao import conectar_wifi, ajustar_hora_ntp, timestamp
from modulos.sensores import temperatura_ds18b20, pressao_bmp180, umidade_dht22
from modulos.interface import cliente_mqtt
from modulos.ihc import meu_lcd
from modulos.armazenamento import salvar_fila, carregar_fila, limpar_arquivo_fila
from machine import I2C, Pin, reset, WDT
from ujson import load, dumps
from time import sleep, time
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
    ajustar_hora_ntp()

    lcd.imprimir(f"\n{"ntp ok!"}",1)
    sleep(2)
except Exception as e:
    #lcd.imprimir(f"\n{e}",1)

    lcd.imprimir("erro ntp!",1)
    print(f"Erro NTP: {e}")
    sleep(3)
    reset()

try:
    lcd.imprimir('Conectando MQTT...')
    hora_sincronizada = True
    print("Instanciando cliente MQTT...")
    print(f"broker: {assets['mqtt']['broker']}")
    print(f"id_cliente: {assets['mqtt']['id_cliente']}")
    print(f"token: {assets['mqtt']['token']}")

    cliente = cliente_mqtt(
        broker = assets['mqtt']['broker'],
        id_cliente = assets['mqtt']['id_cliente'],
        token=assets['mqtt']['token']
    )
    lcd.imprimir('\nMQTT Conectado!',1)
    sleep(2)
except Exception as e:
    lcd.imprimir(f"\n{e}",1)
    print(f"Erro MQTT: {e}")
    sleep(3)
    reset()

lcd.imprimir('Medicoes: ')

mqtt_ok = True  
fila_pendente = carregar_fila()
if fila_pendente:
    print(f"Recuperadas {len(fila_pendente)} leitura(s) pendente(s) de antes do reboot.")
TAMANHO_MAX_FILA = 50  # limite pra não estourar a RAM do ESP32-C3
wdt = WDT(timeout = 300000)
ntptime.settime()
#ts = time.time() * 1000 

while True:
    try:
        
        wdt.feed()
        print(f"--- Ciclo | WiFi: {sta_if.isconnected()} | MQTT: {mqtt_ok} ---")

        # 1. Verifica WiFi e tenta reconectar se necessário
        if not sta_if.isconnected():
            print("WiFi caiu. Reconectando...")
            mqtt_ok = False
            hora_sincronizada = False

            try:
                conectar_wifi(ssid, pswd)

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

            except Exception as e:
                print(f"WiFi não reconectou neste ciclo: {e}")
                mqtt_ok = False
                # segue o fluxo (não faz 'continue') para que os sensores
                # sejam lidos e a leitura entre na fila mesmo sem rede

        elif mqtt_ok:
            try:
                cliente.cliente.ping()
                sleep(2)
                cliente.cliente.check_msg()

            except Exception as e:
                print(f"Broker sem resposta, reconectando: {e}")
                mqtt_ok = False
                try:
                    cliente.reconectar()
                    mqtt_ok = True
                    print("MQTT reconectado!")
                except Exception as e:
                    print(f"Falha ao reconectar MQTT: {e}")

        # 2. Lê sensores (independente do MQTT)
        '''json_pub = {
            'timestamp': timestamp(),
            'Medições': []
        }'''

        json_pub = {
            'ts': int(time() * 1000),  
            
        }

        output = []

        for i in range(len(sensor)):
            sensor[i].ler_sensor()
            #json_pub['Medições'].append(sensor[i].empacotar())
            json_pub[sensor[i].tipo] = sensor[i].leitura
            output.append(f'\n{sensor[i].tipo[0:4]}: {sensor[i].leitura:.1f}')

        for nro, linha in enumerate(output):
            lcd.imprimir(linha, nro + 1)

        # 3. Adiciona a leitura atual na fila de pendências
        fila_pendente.append(json_pub)
        if len(fila_pendente) > TAMANHO_MAX_FILA:
            descartada = fila_pendente.pop(0)
            print(f"Fila cheia! Descartando leitura mais antiga (ts={descartada['ts']})")

        # 4. Tenta esvaziar a fila publicando tudo que estiver pendente,
        #    do mais antigo para o mais novo. Para no primeiro erro,
        #    preservando o restante da fila para o próximo ciclo.
        if mqtt_ok:
            while fila_pendente:
                item = fila_pendente[0]
                try:
                    print(f"Publicando (fila: {len(fila_pendente)} pendente(s))...")
                    print(f"JSON: {dumps(item)}")
                    cliente.publicar(
                        mensagem=dumps(item),
                        topico=assets['mqtt']['topico']
                    )
                    fila_pendente.pop(0)
                    print("publicado com sucesso!")
                except Exception as e:
                    print(f"Erro ao publicar MQTT: {e}")
                    mqtt_ok = False
                    break
        else:
            print(f"MQTT indisponível. {len(fila_pendente)} leitura(s) na fila.")

        # 5. Persiste a fila em disco para sobreviver a um reboot inesperado
        #    (watchdog, queda de energia, reset manual). Só grava quando há
        #    pendências reais, evitando escrita desnecessária na flash.
        if fila_pendente:
            salvar_fila(fila_pendente)
        else:
            limpar_arquivo_fila()

    except Exception as e:
        print(f"Erro inesperado no loop: {e}")
        sleep(10)

    gc.collect()
    sleep(60)