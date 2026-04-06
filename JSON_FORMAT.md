# JSON Formáty komunikácie pre RL Agent a GNU Radio

## 1. Kontrolná správa (RL Agent → GNU Radio)

RL Agent odošle túto správu cez ZeroMQ REQ socket na port 5555:

```json
{
  "gain": 0.1,
  "phase": -0.001,
  "eq_mu": 0.0005
}
```

### Polia:

| Pole | Typ | Rozsah | Popis |
|------|-----|--------|-------|
| gain | float | [0.0, 10.0] | Zmena gainu (multiplier) |
| phase | float | [-0.02, 0.02] | Fázová korekcia v radiánoch |
| eq_mu | float | [0.0, 0.01] | Adaptácia equalizera |

**Poznámka:** RL Agent odosiela iba *zmenu* parametrov, nie absolútne hodnoty.

## 2. Správa odpovede (GNU Radio → RL Agent)

GNU Radio odpovie potvrdenie cez ZeroMQ REP socket:

```json
{
  "ok": true,
  "timestamp": 1705329600.123
}
```

## 3. Metriky (GNU Radio → RL Agent)

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

### Polia:

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

## 4. Reward formula

Reward sa počíta podľa nasledujúceho vzorca:

```
reward = 1.5 * throughput - 15.0 * loss - 0.05 * rtt - 5.0 * bler
```