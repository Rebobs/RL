# JSON Formáty komunikácie — RL Agent ↔ GNU Radio

Komunikácia prebieha cez ZeroMQ. GNU Radio blok (`options_0_epy_block_0.py`) otvára oba sockety.

---

## 1. Kontrolná správa — Agent → GNU Radio

**Socket:** ZMQ REQ na porte `5555`

Agent posiela **deltu** (zmenu) gainu, nie absolútnu hodnotu. GNU Radio ju prirátava k aktuálnemu gainu a orezáva na rozsah `[0.01, 5.0]`.

```json
{
  "gain":   0.1,
  "phase":  0.0,
  "eq_mu":  0.0
}
```

| Pole | Typ | Rozsah | Popis |
|------|-----|--------|-------|
| `gain` | float | delta, GNU Radio clips výsledok na [0.01, 5.0] | Zmena zosilnenia |
| `phase` | float | delta, výsledok clips na [-3.14, 3.14] | Fázová korekcia (rad) |
| `eq_mu` | float | delta, výsledok clips na [0.0001, 0.1] | Krok adaptácie equalizera |

GNU Radio odpovie `b'ok'` po prijatí. Agent čaká na túto odpoveď pred každým ďalším krokom.

---

## 2. Metriky — GNU Radio → Agent

**Socket:** ZMQ PUB na porte `5556`

GNU Radio posiela metriky každých ~50 ms. Agent drénuje frontu a berie vždy najnovšiu správu.

```json
{
  "snr":        20.0,
  "power":       0.5,
  "cfo":         0.0,
  "throughput": 10.0,
  "rtt":        50.0,
  "loss":        0.01,
  "bler":        0.02
}
```

| Pole | Typ | Typický rozsah | Popis |
|------|-----|----------------|-------|
| `snr` | float | 0 – 25 dB | SNR signálu (optimum ~20 dB pri gain=1.0) |
| `power` | float | 0 – 10 | Výkon výstupného signálu (gain² × 0.5) |
| `cfo` | float | 0.0 | Carrier frequency offset (momentálne fixný) |
| `throughput` | float | 0 – 12 Mbps | Prenosová rýchlosť |
| `rtt` | float | 20 – 500 ms | Round-trip time |
| `loss` | float | 0.0 – 1.0 | Packet loss |
| `bler` | float | 0.0 – 1.0 | Block Error Rate |

---

## 3. Fyzikálny model (GNU Radio simulácia)

SNR závisí kvadraticky od gainu — optimum je `gain = 1.0`:

```
snr_penalty = (gain - 1.0)² × 15.0
snr = clip(20.0 - snr_penalty + noise, 0, 25)   # noise ≈ ±0.3 dB
```

Príklady:

| gain | SNR |
|------|-----|
| 0.3 | ~11 dB |
| 0.5 | ~16 dB |
| 1.0 | ~20 dB ✓ optimum |
| 1.5 | ~16 dB |
| 2.0 | ~5 dB |
| 3.0 | ~0 dB (štart) |

---

## 4. Reward funkcia

```
reward = 1.5 × throughput
       - 15.0 × loss
       -  0.05 × rtt
       -  5.0 × bler
       - sat_penalty    # max(0, gain - 1.8)² × 8.0
       - low_penalty    # max(0, 0.8 - gain)² × 20.0
```

| Komponent | Váha | Popis |
|-----------|------|-------|
| throughput | +1.5 | Maximalizuj prenosovú rýchlosť |
| loss | -15.0 | Penalizuj straty paketov |
| rtt | -0.05 | Penalizuj latenciu |
| bler | -5.0 | Penalizuj chybovosť blokov |
| sat_penalty | -8.0× | Penalizuj príliš vysoký gain (>1.8) |
| low_penalty | -20.0× | Penalizuj príliš nízky gain (<0.8) |

Teoretické maximum pri `gain=1.0`: reward ≈ **+11**

---

## 5. Akcie agenta

Agent vyberá z 11 absolútnych gain hodnôt:

```
[0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]
```

Do GNU Radia sa posiela **delta** = `target_gain - current_gain`, nie priamo target. Takto sa predchádza driftom.
