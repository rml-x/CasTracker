from ds18x20 import DS18X20
from onewire import OneWire
from dht import DHT22
from machine import Pin
from .lib.bmp180 import BMP180
from json import dumps
from time import sleep_ms


class Sensor:
    # Subclasses definem seus próprios limites físicos plausíveis.
    # None desativa a checagem naquele extremo.
    LIMITE_MIN = None
    LIMITE_MAX = None

    def __init__(self, pino, tipo, componente):
        self.pino = pino
        self.tipo = tipo
        self.componente = componente
        self.leitura = None
        self.falhas_consecutivas = 0

    def empacotar(self):
        return {
            "tipo": self.tipo,
            "componente": self.componente,
            "leitura": self.leitura
        }

    def _ler_bruto(self):
        """Cada subclasse implementa a leitura real do driver aqui."""
        raise NotImplementedError

    def _valor_plausivel(self, valor):
        if valor is None:
            return False
        if self.LIMITE_MIN is not None and valor < self.LIMITE_MIN:
            return False
        if self.LIMITE_MAX is not None and valor > self.LIMITE_MAX:
            return False
        return True

    def ler_sensor(self):
        """Lê o sensor com tratamento de erro e validação de faixa física.
        Retorna a leitura válida, ou None se a leitura falhou ou veio
        fora da faixa plausível — nunca lança exceção, para não derrubar
        o ciclo inteiro por causa de um único sensor com falha pontual.
        """
        try:
            valor = self._ler_bruto()
        except Exception as e:
            self.falhas_consecutivas += 1
            print(f"Erro ao ler sensor ou sensor não implementado corretamente {self.componente} ({self.tipo}): {e}")
            self.leitura = None
            return None

        if not self._valor_plausivel(valor):
            self.falhas_consecutivas += 1
            print(f"Leitura descartada (fora da faixa plausível) - {self.componente} ({self.tipo}): {valor}")
            self.leitura = None
            return None

        self.falhas_consecutivas = 0
        self.leitura = valor
        return valor


class temperatura_ds18b20(Sensor):
    # Faixa plausível para monitoramento meteorológico externo.
    LIMITE_MIN = -20
    LIMITE_MAX = 60

    def __init__(self, pino):
        super().__init__(pino = pino, tipo = "temperatura", componente = "ds18b20")
        self.onewire_bus = OneWire(Pin(self.pino,Pin.IN, Pin.PULL_DOWN))
        self.driver_ds = DS18X20(self.onewire_bus)
        self.dispositivo = self.onewire_bus.scan()

    def _ler_bruto(self):
        self.driver_ds.convert_temp()
        # Tempo mínimo de conversão do DS18B20 em resolução padrão (12 bits).
        # Sem essa espera, read_temp() pode retornar a leitura anterior ou
        # o valor de reset de fábrica (85.0°C).
        sleep_ms(750)
        return self.driver_ds.read_temp(self.dispositivo[0])


class umidade_dht22(Sensor):
    LIMITE_MIN = 0
    LIMITE_MAX = 100

    def __init__(self,pino):
        super().__init__(pino = pino, tipo = "umidade", componente = "dht22")
        self.driver = DHT22(Pin(self.pino))

    def _ler_bruto(self):
        self.driver.measure()
        return self.driver.humidity()


class pressao_bmp180(Sensor):
    # Faixa de operação do BMP180: ~300 hPa a ~1100 hPa (valor em Pa).
    LIMITE_MIN = 30000
    LIMITE_MAX = 110000

    def __init__(self, i2c_bus):
        super().__init__(pino = None,tipo = "pressao", componente = "bmp180")
        self.i2c_bus = i2c_bus
        self.driver = BMP180(self.i2c_bus)

    def _ler_bruto(self):
        return self.driver.get_pressure()


class temperatura_bmp180(Sensor):
    LIMITE_MIN = -20
    LIMITE_MAX = 60

    def __init__(self, i2c_bus):
        super().__init__(pino = None, tipo = "temperatura", componente = "bmp180")
        self.i2c_bus = i2c_bus
        self.driver = BMP180(self.i2c_bus)

    def _ler_bruto(self):
        return self.driver.get_temperature()