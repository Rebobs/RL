# RL Agent pre GNU Radio

DQN agent ktorý sa pripojí na GNU Radio cez ZeroMQ, číta BER (Bit Error Rate) a automaticky nastavuje zosilnenie signálu (signal_gain) na Multiply Const bloku s cieľom minimalizovať BER.

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

Otvor `Zapojenie.grc` v GNU Radio Companion a klikni **Run**. Flowgraph vygeneruje `Zapojenie_epy_block_0_0.py` (ZMQ bridge) a otvorí sockety na portoch 5555 a 5556.

> **Poznámka:** `Zapojenie.py` sa generuje automaticky príkazom `grcc Zapojenie.grc` — nie je potrebné ho upravovať ručne.

### 2. Spusti agenta

```bash
source venv/bin/activate
python main.py
```

Agent sa automaticky pripojí na GNU Radio, začne zbierať BER metriky a trénovať.

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
        "window": 1000,
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
| `monitor.enabled` | Zobrazí live graf (Signal Gain, BER, Reward) |
| `monitor.window` | Počet meraní viditeľných v grafe |
| `debug.rl_decisions_log` | Každé rozhodnutie agenta zapíše do `rl_decisions.log` |
| `training.learning_starts` | Koľko krokov sa zbiera do replay bufferu pred prvým tréningom |
| `training.save_interval_steps` | Každých N krokov sa uloží model do `saved_models/` |

## Súbory

| Súbor | Popis |
|-------|-------|
| `main.py` | Vstupný bod — spúšťa agenta a monitor |
| `rl_agent.py` | DQN agent, prostredie, reward funkcia |
| `config.json` | Konfigurácia |
| `Zapojenie.grc` | GNU Radio flowgraph (QPSK TX/RX + ZMQ bridge) |
| `Zapojenie_epy_block_0_0.py` | ZMQ bridge — meria BER, prijíma príkazy od agenta |
| `saved_models/` | Automaticky ukladané modely (`.zip`) |
| `debug.log` | Súhrnné štatistiky každých 20 krokov |
| `rl_decisions.log` | Každé rozhodnutie agenta (ak `rl_decisions_log: true`) |

## Live Monitor

Ak je `monitor.enabled: true` v `config.json`, po spustení `python main.py` sa otvorí okno s 3 grafmi:

- **Signal Gain** — aktuálna hodnota zosilnenia nastavená agentom (referencia = 1.0)
- **BER (log)** — nameraný Bit Error Rate v logaritmickej škále
- **Reward** — hodnota odmeny (`-log10(BER)`)

## Ako to funguje

Agent má **10 diskrétnych akcií** — každá akcia nastaví signal_gain priamo na pevnú hodnotu:

```
[0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
```

BER sa meria priamo v GNU Rádiu porovnaním TX a RX bitov (XOR → unpackbits). Vyššie zosilnenie → lepší SNR → nižší BER → vyšší reward.

**Reward funkcia:**
```
reward = -log10(BER)
```
Príklady: BER=0.5 → reward≈0.3 | BER=0.01 → reward=2.0 | BER=1e-4 → reward=4.0

## ZeroMQ komunikácia

| Socket | Port | Smer | Typ |
|--------|------|------|-----|
| Control | 5555 | Agent → GNU Radio | REQ/REP |
| Metrics | 5556 | GNU Radio → Agent | PUB/SUB |

**Správa od agenta (Control):**
```json
{"noise_sigma": 2.0}
```

**Správa od GNU Rádia (Metrics):**
```json
{"ber": 0.0012, "noise_sigma": 2.0}
```
