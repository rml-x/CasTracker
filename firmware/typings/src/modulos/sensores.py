from ds18x20 import DS18X20
from onewire import OneWire
from dht import DHT22
from machine import Pin
from .lib.bmp180 import BMP180
from json import dumps


class Sensor:
    def __init__(self, pino, tipo, componente):
        self.pino = pino
        self.tipo = tipo
        self.componente = componente

    def empacotar(self):
        return {
            "tipo": self.tipo,
            "componente": self.componente,
            "leitura": self.leitura
        }

    def ler_sensor(self):
        pass

class temperatura_ds18b20(Sensor):
    def __init__(self, pino):
        super().__init__(pino = pino, tipo = "temperatura", componente = "ds18b20")
        self.onewire_bus = OneWire(Pin(self.pino,Pin.IN, Pin.PULL_DOWN))
        self.driver_ds = DS18X20(self.onewire_bus)
        self.dispositivo = self.onewire_bus.scan()

    def ler_sensor(self):
        self.driver_ds.convert_temp()
        self.leitura = self.driver_ds.read_temp(self.dispositivo[0])
        return self.leitura

class umidade_dht22(Sensor):
    def __init__(self,pino):
        super().__init__(pino = pino, tipo = "umidade", componente = "dht22")
        self.driver = DHT22(Pin(self.pino))

    def ler_sensor(self):
        self.driver.measure()
        self.leitura = self.driver.humidity()
        return self.leitura

class pressao_bmp180(Sensor):
    def __init__(self, i2c_bus):
        super().__init__(pino = None,tipo = "pressao", componente = "bmp180")
        self.i2c_bus = i2c_bus
        self.driver = BMP180(self.i2c_bus)

    def ler_sensor(self):
        self.leitura = self.driver.get_pressure()
        return self.leitura
    
