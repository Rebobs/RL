# RL Agent pre GNU Radio

Tento projekt implementuje RL model (DQN) pre dynamické nastavovanie parametrov v GNU Radio/srsRAN systéme.

## Štruktúra projektu

```
/home/martin/Desktop/RL_Project/
├── config.json              # Konfigurácia a JSON formát komunikácie
├── radio_control_server.py  # GNU Radio kontrolný server (ZeroMQ)
├── rl_agent.py              # RL Agent (komunikuje s GR)
├── train_agent.py           # Trénovací skript
├── main.py                  # Hlavný spúšťač
├── saved_models/            # Uložené modely
└── README.md
```

## Inštalácia závislostí

```bash
pip install stable-baselines3 gymnasium numpy pyzmq
```

## Použitie

### 1. Trénovanie modelu

```bash
python main.py train
```

Trénuje DQN model na 50 000 krokov a uloží ho do `saved_models/`.

### 2. Zoznam dostupných modelov

```bash
python main.py list
```

### 3. Spustenie agenta s existujúcim modelom

```bash
python main.py run
```

Alebo s časovým limitom:

```bash
python main.py run --time 300
```

### 4. Spustenie s konkrétnym modelom

```bash
python main.py run --model rl_model_20240115_103045.zip
```

## Komunikácia medzi RL Agent a GNU Radio

### JSON Formát - Kontrolná správa (RL → GNU Radio)

```json
{
  "gain": 0.1,          // float, rozsah [0.0, 10.0]
  "phase": -0.001,      // float, rozsah [-0.02, 0.02]
  "eq_mu": 0.0005       // float, rozsah [0.0, 0.01]
}
```

### JSON Formát - Metriky (GNU Radio → RL)

```json
{
  "snr": 15.0,          // float, SNR v dB
  "power": 0.5,         // float, výkon signálu
  "cfo": 0.0,           // float, carrier frequency offset
  "throughput": 10.0,   // float, throughput v Mbps
  "rtt": 50.0,          // float, RTT v ms
  "loss": 0.01,         // float, packet loss (0-1)
  "bler": 0.02,         // float, BLER (0-1)
  "detached": false     // bool, či je UE odpojený
}
```

### ZeroMQ Sockets

| Typ | Port | Popis |
|-----|------|-------|
| REP | 5555 | RL agent odošle akciu (REQ) |
| PUB | 5556 | GNU Radio posiela metriky (SUB) |

## Reward Formula

```
reward = 1.5 * throughput - 15 * loss - 0.05 * rtt - 5.0 * bler
```

## Bezpečnostné mechanizmy (Watchdog)

Ak nastane ktorákolvek z týchto podmienok, parametre sa resetujú na bezpečné hodnoty:

- UE detach (`detached = true`)
- Packet loss > 80%
- RTT > 1000ms
- Throughput < 0.001 Mbps

Bezpečné hodnoty:
```json
{
  "gain": 1.0,
  "phase": 0.0,
  "eq_mu": 0.001
}
```

## Automatické ukladanie modelu

Počas runtime sa model ukladá každých 300 sekúnd (5 minút) do `saved_models/` s timestampom v názve súboru.

## Príklad outputu z konzoly

```
[INFO] RL Agent pripojený k GNU Radio
[INFO] Control: tcp://127.0.0.1:5555
[INFO] Metrics: tcp://127.0.0.1:5556
[INFO] Model načítaný: rl_model_20240115_103045.zip

[10.5s] Step    1 | Akcia: gain+0.1, phase-0.001          | Odmena: -0.052 | SNR:  14.2dB | Throughput:  9.5Mbps | Loss: 0.02%
[10.7s] Step    2 | Akcia: gain+0.1, phase-0.001          | Odmena: -0.048 | SNR:  14.8dB | Throughput:  9.8Mbps | Loss: 0.01%
[10.9s] Step    3 | Akcia: gain-0.1, phase+0.001          | Odmena:  0.125 | SNR:  15.1dB | Throughput: 10.2Mbps | Loss: 0.01%

[INFO] Model uložený: /home/martin/Desktop/RL_Project/saved_models/rl_model_20240115_103500.zip
```

## Architektúra

```
┌─────────────────────────────────────────────────────────────┐
│                   RL Agent (Python)                          │
│  - DQN model                                                 │
│  - ZeroMQ REQ (kontrola) + SUB (metriky)                     │
│  - Automatické ukladanie každých 300s                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
              ZeroMQ (127.0.0.1:5555/5556)
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              GNU Radio Control Server                        │
│  - ZeroMQ REP (kontrola) + PUB (metriky)                    │
│  - Watchdog bezpečnostné kontroly                            │
│  - Aplikuje zmeny parametrov                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
              ZeroMQ (127.0.0.1:5556)
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   GNU Radio Flowgraph                        │
│  - Channel Model → Compensation Blocks → srsRAN             │
│  - ZMQ Source/Sink bloky                                     │
│  - Metrics probes                                            │
└─────────────────────────────────────────────────────────────┘
```

## Dôležité poznámky

1. **localhost vs 127.0.0.1**: Vždy používať IP adresu `127.0.0.1`, nie `localhost`
2. **Bind vs Connect**: Sink bloky v GR `bind`, Source v RL `connect`
3. **SUB subscribe**: Always `setsockopt(SUBSCRIBE, b'')` pre prijatie všetkých správ
4. **Tréning**: Najprv trénuj offline, až potom spúšťaj na reálnom systéme
5. **Watchdog**: Vždy zapnutý počas runtime pre bezpečnosť

## Kontakt a ďalšie informácie

Tento projekt bol vytvorený pre školský tímový projekt s využitím RL v sieťovej komunikácii.
Pre viac informácií sa pozri na dokumentáciu GNU Radio ZMQ blokov:
https://wiki.gnuradio.org/index.php/Understanding_ZMQ_Blocks
