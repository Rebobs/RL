# RL Agent pre GNU Radio - ONLINE TRÉNING

Tento projekt implementuje RL model (DQN) pre dynamické nastavovanie parametrov v GNU Radio/srsRAN systéme.

## Inštalácia

```bash
pip install stable-baselines3 gymnasium numpy pyzmq
```

## Použitie

```bash
python main.py
```

**Agent sa bude učiť počas behu a model sa bude ukladať automaticky.**

## Online tréning - ako to funguje

| Krok | Čo sa deje |
|------|-----------|
| 1-49 | Agent experimentuje a zbiera skúsenosti |
| 50 | Tréning: `model.learn(1000 timesteps)` |
| 51-299 | Agent pokračuje v behu |
| 300 | Model sa uloží do `saved_models/rl_model_TIMESTAMP.zip` |
| 301-349 | Agent pokračuje v behu |
| 350 | Tréning: `model.learn(1000 timesteps)` |
| ... | Opakuje sa |

### Nastavenia online tréningu

Sú definované v `rl_agent.py`:

```python
ONLINE_TRAINING = {
    "learn_interval_steps": 50,
    "learn_timesteps_per_iteration": 1000,
    "exploration_fraction": 0.3,
    "exploration_final": 0.05,
    "save_interval_steps": 300,
}
```

## Komunikácia medzi RL Agent a GNU Radio

### JSON Formát - Kontrolná správa (RL Agent → GNU Radio)

RL Agent odošle túto správu cez ZeroMQ REQ socket na port 5555:

```json
{
  "gain": 0.1,
  "phase": -0.001,
  "eq_mu": 0.0005
}
```

**Polia:**

| Pole | Typ | Rozsah | Popis |
|------|-----|--------|-------|
| gain | float | [0.0, 10.0] | Zmena gainu (multiplier) |
| phase | float | [-0.02, 0.02] | Fázová korekcia v radiánoch |
| eq_mu | float | [0.0, 0.01] | Adaptácia equalizera |

### JSON Formát - Metriky (GNU Radio → RL Agent)

GNU Radio posiela metriky cez ZeroMQ PUB socket na port 5556:

```json
{
  "snr": 15.0,
  "power": 0.5,
  "cfo": 0.001,
  "throughput": 10.5,
  "rtt": 48.2,
  "loss": 0.008,
  "bler": 0.015,
  "detached": false
}
```

**Polia:**

| Pole | Typ | Popis |
|------|-----|-------|
| snr | float | SNR v decibeloch |
| power | float | Výkon signálu |
| cfo | float | Carrier frequency offset |
| throughput | float | Throughput v Mbps |
| rtt | float | Round-trip time v ms |
| loss | float | Packet loss (0.0 - 1.0) |
| bler | float | Block Error Rate (0.0 - 1.0) |
| detached | bool | Stav UE (true = odpojený) |

### ZeroMQ Sockets

| Typ | Port | Popis |
|-----|------|-------|
| REP | 5555 | RL agent odošle akciu (REQ) |
| PUB | 5556 | GNU Radio posiela metriky (SUB) |

## Reward Formula

```
reward = 1.5 * throughput - 15 * loss - 0.05 * rtt - 5.0 * bler
```

## Automatické ukladanie modelu

Počas runtime sa model ukladá každých 300 sekúnd do `saved_models/` s timestampom v názve súboru.