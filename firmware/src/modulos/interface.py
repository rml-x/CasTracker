from umqtt.simple import MQTTClient
from time import sleep

class cliente_mqtt:
    def __init__(self, broker, id_cliente=''):
        self.broker = broker
        self.id_cliente = id_cliente
        self.cliente = MQTTClient(self.id_cliente, self.broker, keepalive= 60)
        self.cliente.connect()
        self.cliente.sock.settimeout(10)
        print(f"MQTT conectado | keepalive=60 | timeout=10s") 

    def reconectar(self, tentativas=5, espera=3):
        for i in range(tentativas):
            try:
                try:
                    self.cliente.disconnect()
                except:
                    pass
                self.cliente = MQTTClient(self.id_cliente, self.broker, keepalive= 60)
                self.cliente.connect()
                self.cliente.sock.settimeout(10)
                print(f"MQTT conectado | keepalive=60 | timeout=10s")
                return True
            except Exception as e:
                print(f"MQTT tentativa {i+1}/{tentativas} falhou: {e}")
                sleep(espera)
        raise Exception(f"MQTT falhou após {tentativas} tentativas")

    def publicar(self, mensagem, topico, tentativas=3, espera=2):
        for i in range(tentativas):
            try:
                self.cliente.publish(
                    topico.encode(),
                    mensagem.encode()
                )
                return True
            except Exception as e:
                print(f"Publish tentativa {i+1}/{tentativas} falhou: {e}")
                sleep(espera)
        raise Exception(f"Publish falhou após {tentativas} tentativas")