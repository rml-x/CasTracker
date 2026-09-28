# CasTracker — Firmware

Sistema embarcado de monitoramento meteorológico baseado em ESP32-C3, desenvolvido como parte de projeto de Iniciação Científica Tecnológica (IFRS). O dispositivo lê sensores ambientais periodicamente e publica os dados via MQTT numa plataforma IoT em nuvem (ThingsBoard), com mecanismos de resiliência para operação autônoma e contínua em campo.

## Sumário

- [Hardware](#hardware)
- [Arquitetura do firmware](#arquitetura-do-firmware)
- [Fluxo de execução](#fluxo-de-execução)
- [Mecanismos de resiliência](#mecanismos-de-resiliência)
- [Configuração](#configuração)
- [Deploy](#deploy)
- [Limitações conhecidas e trabalhos futuros](#limitações-conhecidas-e-trabalhos-futuros)

## Hardware

| Componente | Função | Interface |
|---|---|---|
| ESP32-C3 Super Mini | Microcontrolador principal | — |
| DS18B20 | Sensor de temperatura | OneWire |
| DHT22 | Sensor de umidade relativa | GPIO digital |
| BMP180 | Sensor de pressão atmosférica (e temperatura, não utilizada) | I2C |
| Display LCD 20x4 (HD44780 via PCF8574) | Interface local de status | I2C |

Todos os componentes estão integrados numa PCB customizada (ver pasta `hardware/` no workspace).

## Arquitetura do firmware

O firmware roda em **MicroPython** e segue uma organização modular orientada a objetos, com cada responsabilidade isolada em seu próprio módulo dentro de `src/modulos/`:

| Módulo | Responsabilidade |
|---|---|
| `main.py` | Orquestração: inicialização, loop principal, montagem do payload |
| `conexao.py` | Conexão e reconexão WiFi, sincronização de hora via NTP |
| `interface.py` | Cliente MQTT (`cliente_mqtt`): conexão, reconexão e publicação no broker |
| `sensores.py` | Classe base `Sensor` e as subclasses de cada sensor físico |
| `ihc.py` | Controle do display LCD (`meu_lcd`), com renderização diferencial (só reescreve caracteres que mudaram) |
| `armazenamento.py` | Persistência da fila de leituras pendentes em flash (sobrevivência a reboots) |
| `lib/bmp180.py` | Driver de baixo nível do sensor BMP180 |
| `lib/lcd_api.py`, `lib/machine_i2c_lcd.py` | Driver de baixo nível do LCD via I2C (PCF8574) |

**Base para o diagrama de classes:** a hierarquia mais relevante é a de `Sensor` (classe abstrata) → `temperatura_ds18b20`, `umidade_dht22`, `pressao_bmp180`, `temperatura_bmp180`. A classe base centraliza tratamento de erro e validação de faixa (`ler_sensor()`); cada subclasse só implementa `_ler_bruto()` e declara seus limites físicos (`LIMITE_MIN`/`LIMITE_MAX`). As demais classes de infraestrutura (`cliente_mqtt`, `meu_lcd`) não têm relação de herança entre si — são componentes independentes, usados por composição a partir de `main.py`.

**Base para o diagrama de componentes:** `main.py` depende de todos os outros módulos; `conexao.py`, `interface.py`, `sensores.py`, `ihc.py` e `armazenamento.py` não dependem uns dos outros (são paralelos, sem acoplamento entre si), o que mantém o sistema desacoplado e cada módulo testável isoladamente.

## Fluxo de execução

**Base para o diagrama de sequência.**

### Boot (executa uma única vez)

1. Carrega `config.json` (credenciais WiFi, broker MQTT, mapeamento de pinos)
2. Recupera fila de leituras pendentes salva antes de um reboot anterior (`armazenamento.carregar_fila()`)
3. Inicializa barramento I2C e display LCD
4. Conecta cada sensor (BMP180, DHT22, DS18B20), com feedback visual no LCD por sensor
5. Conecta WiFi (`conexao.conectar_wifi()`)
6. Sincroniza hora via NTP (`conexao.ajustar_hora_ntp()`)
7. Conecta ao broker MQTT (`interface.cliente_mqtt`)
8. Inicia o watchdog timer (`WDT`, timeout de 300s)

Falha em qualquer uma das etapas 5–7 reinicia o dispositivo (`machine.reset()`).

### Loop principal (repete indefinidamente, ciclo de ~60s)

1. Alimenta o watchdog (`wdt.feed()`)
2. Verifica conectividade WiFi; se caiu, tenta reconectar (com backoff exponencial) e, em caso de sucesso, ressincroniza NTP e reconecta o MQTT
3. Se WiFi/MQTT ok, envia `ping()` e processa mensagens pendentes (`check_msg()`)
4. Lê os três sensores (cada leitura passa por validação de faixa física; falhas não interrompem o ciclo)
5. Se houve pelo menos uma leitura válida, monta o payload e adiciona à fila local
6. Tenta esvaziar a fila publicando no broker, do item mais antigo ao mais novo, em ordem
7. Persiste a fila em flash se ainda houver pendências; limpa o arquivo se a fila esvaziou
8. Coleta de lixo (`gc.collect()`) e aguarda o próximo ciclo

## Mecanismos de resiliência

Esta seção documenta as decisões de design tomadas para lidar com instabilidade de rede (o dispositivo opera com hotspot de celular como fonte de conectividade, que é significativamente menos estável que um roteador fixo).

### Backoff exponencial

Tanto a reconexão WiFi (`conexao.calcular_backoff()`) quanto a reconexão MQTT (`interface._calcular_backoff()`) usam espera crescente entre tentativas (ex: 3s, 6s, 12s, 24s... até um teto), em vez de intervalo fixo. Isso reduz o desgaste de tentativas repetidas contra uma rede persistentemente indisponível, mantendo resposta rápida a falhas passageiras.

### Fila local de leituras pendentes

Leituras que não puderam ser publicadas (WiFi ou MQTT indisponível) ficam numa fila em memória (`fila_pendente`), limitada a 50 itens (descarta o mais antigo se o limite for excedido). Quando a conectividade volta, a fila é esvaziada em ordem cronológica antes de retomar a publicação em tempo real — nenhuma leitura é perdida durante quedas de curta/média duração.

### Persistência da fila em flash

Para sobreviver a reboots inesperados (falha de energia, reset manual, watchdog), o conteúdo da fila é espelhado em disco (`fila_pendente.jsonl`) sempre que há pendências, e removido quando a fila esvazia — minimizando desgaste de escrita da flash em operação normal (quando não há pendências, não há escrita). A gravação usa arquivo temporário + `os.rename()` para atomicidade, evitando corrupção em caso de queda de energia no meio da escrita.

> **Limitação conhecida:** existe uma janela residual entre uma leitura ser adicionada à fila e a tentativa de publicação ser concluída, na qual o dado ainda não foi persistido nem confirmado como enviado. Uma perda de energia exatamente nesse intervalo (tipicamente < 2s) resultaria na perda daquela leitura específica.

### Validação de leituras (detecção de outliers)

Cada sensor declara uma faixa fisicamente plausível (`LIMITE_MIN`/`LIMITE_MAX`). Leituras fora da faixa, ou falhas de comunicação com o driver, são descartadas sem interromper a leitura dos demais sensores no mesmo ciclo. O DS18B20 recebeu adicionalmente um delay de conversão (750ms) entre a solicitação de leitura e a leitura do resultado, corrigindo uma condição de corrida que podia retornar valores obsoletos ou o valor de reset de fábrica do sensor (85°C).

## Configuração

Credenciais e parâmetros ficam em `config.json`, na raiz do sistema de arquivos do dispositivo:

```json
{
    "wifi": { "ssid": "...", "pswd": "..." },
    "mqtt": {
        "id_cliente": "...",
        "broker": "demo.thingsboard.io",
        "topico": "v1/devices/me/telemetry",
        "token": "..."
    },
    "pinos": { "dht": 3, "sda": 8, "scl": 9, "onewire": 4 }
}
```

## Deploy

O deploy é feito via `mpremote`, copiando os arquivos para a flash do ESP32-C3:

```powershell
.\venv\Scripts\Activate.ps1
.\run_esp.bat
```

O script copia `config.json`, `main.py` e todos os módulos em `src/modulos/`, reseta o dispositivo e abre o REPL para monitoramento.

## Limitações conhecidas e trabalhos futuros

Itens avaliados e conscientemente deixados de fora do escopo atual:

- **Deep sleep entre ciclos**: traria economia de energia relevante para operação em bateria, mas exigiria reestruturar todo o modelo de execução (reinicialização completa a cada ciclo de leitura, já que o deep sleep zera a RAM). Não implementado por ora porque o dispositivo ainda opera alimentado continuamente (USB); revisar se houver migração para bateria.
- **Comandos remotos via MQTT (subscribe/RPC)**: a infraestrutura básica já existe (`check_msg()` é chamado a cada ciclo), mas nenhum tópico de comando foi implementado. Permitiria, por exemplo, ajustar o intervalo de leitura ou forçar republicação remotamente.
- **Configuração via portal WiFi (captive portal)**: hoje a troca de rede exige editar `config.json` e regravar via `mpremote`. Um portal de configuração tornaria isso mais autônomo.
- **Calibração cruzada entre sensores**: DS18B20 e BMP180 medem temperatura de forma independente; comparar as duas leituras poderia servir tanto para calibração quanto para detecção de deriva de um dos sensores.
