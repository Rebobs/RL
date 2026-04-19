# RL Agent pre GNU Radio

DQN agent ktorý sa pripojí na GNU Radio cez ZeroMQ, číta metriky signálu (SNR, throughput, loss, RTT, BLER) a automaticky nastavuje gain pre optimálny príjem.

## Požiadavky

- Python 3.14
- GNU Radio 3.10+ (systémová inštalácia, nie cez pip)
- GPU nie je nutná (ale ak je, PyTorch ju automaticky využije)

### Inštalácia GNU Radio (Arch Linux)

```bash
sudo pacman -S gnuradio
```

### Inštalácia GNU Radio (Ubuntu/Debian)

```bash
sudo apt install gnuradio
```

## Inštalácia

```bash
# Klonovanie projektu
git clone <repo> RL_Project
cd RL_Project

# Vytvorenie virtuálneho prostredia
python -m venv venv

# Aktivácia (Linux/macOS)
source venv/bin/activate

# Inštalácia závislostí
pip install stable-baselines3 gymnasium numpy pyzmq matplotlib PyQt5
```

> **Poznámka:** `venv/` priečinok nie je v repozitári. Každý si ho vytvorí lokálne podľa krokov vyššie.

## Spustenie

### 1. Spusti GNU Radio

Otvor `flowgraph.grc` v GNU Radio Companion (`gnuradio-companion flowgraph.grc`) a klikni **Run**. GNU Radio vygeneruje `options_0_epy_block_0.py` a otvorí ZMQ sockety na portoch 5555 a 5556.

> **Poznámka:** `options_0_epy_block_0.py` sa generuje automaticky z `.grc` súboru — nie je v repozitári.

### 2. Spusti agenta

```bash
source venv/bin/activate
python main.py
```

Agent sa automaticky pripojí na GNU Radio, začne zbierať metriky a trénovať.

### Príkazy

| Príkaz | Popis |
|--------|-------|
| `python main.py` | Spusti agenta (automaticky načíta posledný uložený model) |
| `python main.py list` | Zoznam uložených modelov |
| `Ctrl+C` | Zastaví agenta a uloží model |

## Konfigurácia (`config.json`)

```json
{
    "communication": {
        "control_address": "tcp://127.0.0.1:5555",
        "metrics_address":  "tcp://127.0.0.1:5556"
    },
    "debug": {
        "enabled": true,
        "rl_decisions_log": true,
        "metrics_log": true
    },
    "monitor": {
        "enabled": true,
        "window": 500,
        "update_interval_ms": 100
    },
    "training": {
        "learning_rate": 0.0003,
        "buffer_size": 10000,
        "learning_starts": 200,
        "batch_size": 64,
        "save_interval_steps": 500,
        "log_interval_steps": 20
    }
}
```

| Kľúč | Popis |
|------|-------|
| `monitor.enabled` | Zobrazí live graf (SNR, throughput, reward, gain...) |
| `monitor.window` | Počet krokov viditeľných v grafe |
| `debug.rl_decisions_log` | Každé rozhodnutie agenta zapíše do `rl_decisions.log` |
| `training.learning_starts` | Koľko krokov sa zbiera do replay bufferu pred prvým tréningom |
| `training.save_interval_steps` | Každých N krokov sa uloží model do `saved_models/` |

## Súbory

| Súbor | Popis |
|-------|-------|
| `main.py` | Vstupný bod — spúšťa agenta a monitor |
| `rl_agent.py` | DQN agent, prostredie, reward funkcia |
| `config.json` | Konfigurácia |
| `monitor.py` | Standalone monitor (alternatíva k `monitor.enabled`) |
| `saved_models/` | Automaticky ukladané modely (`.zip`) |
| `debug.log` | Súhrnné štatistiky každých 20 krokov |
| `rl_decisions.log` | Každé rozhodnutie agenta (ak `rl_decisions_log: true`) |
| `options_0_epy_block_0.py` | GNU Radio embedded Python blok (ZMQ bridge) |

## Live Monitor

Ak je `monitor.enabled: true` v `config.json`, po spustení `python main.py` sa otvorí okno s 6 grafmi:

- SNR (dB) — kvalita signálu
- Throughput (Mbps)
- Packet Loss
- RTT (ms)
- Reward — čo agent optimalizuje
- Gain — aktuálna hodnota nastavená agentom

## Ako to funguje

Agent má **11 diskrétnych akcií** — každá akcia nastaví gain priamo na pevnú hodnotu:

```
[0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]
```

GNU Radio štartuje s `gain=3.0` (degradovaný stav → SNR≈0 dB). Agent sa naučí, že optimum je `gain≈1.0` (SNR≈20 dB, throughput≈10 Mbps). Po ~200–500 krokoch konverguje.

**Reward funkcia:**
```
reward = 1.5 * throughput - 15.0 * loss - 0.05 * rtt - 5.0 * bler
```

## ZeroMQ komunikácia

| Socket | Port | Smer | Typ |
|--------|------|------|-----|
| Control | 5555 | Agent → GNU Radio | REQ/REP |
| Metrics | 5556 | GNU Radio → Agent | PUB/SUB |

Podrobnosti o JSON formáte: [`JSON_FORMAT.md`](JSON_FORMAT.md)
