# Rýchly sprievodca - Ako spustiť RL Agent

## Krok 1: Inštalácia závislostí

```bash
pip install stable-baselines3 gymnasium numpy pyzmq
```

## Krok 2: Trénovanie modelu (prvýkrát)

```bash
cd /home/martin/Desktop/RL_Project
./run.sh train
```

Toto natrénuje DQN model a uloží ho do `saved_models/`.

## Krok 3: Zoznam modelov

```bash
./run.sh list
```

## Krok 4: Spustenie agenta

```bash
./run.sh run
```

Agent bude behať a upravovať parametre GNU Radio podľa toho, čo sa naučil.

## Krok 5: Ukončenie

Stlač `CTRL+C` pre ukončenie agenta. Model sa automaticky uloží.

## Dôležité

1. **Najprv trénuj, potom spust** - bez tréningu agent nebude vedieť rozhodovať
2. **Modely sa ukladajú automaticky** - každých 300 sekúnd počas runtime
3. **Watchdog je zapnutý** - ak nastane chyba, parametre sa resetujú na bezpečné hodnoty
4. **ZeroMQ musí bežať** - GNU Radio kontrolný server musí byť spustený

## Príklad konzoly

```
============================================================
RL AGENT PRE GNU RADIO - Hlavný spúšťač
============================================================

[INFO] RL Agent pripojený k GNU Radio
[INFO] Control: tcp://127.0.0.1:5555
[INFO] Metrics: tcp://127.0.0.1:5556
[INFO] Model načítaný: rl_model_20240115_103045.zip

[10.5s] Step    1 | Akcia: gain+0.1, phase-0.001          | Odmena: -0.052 | SNR:  14.2dB | Throughput:  9.5Mbps | Loss: 0.02%
[10.7s] Step    2 | Akcia: gain+0.1, phase-0.001          | Odmena: -0.048 | SNR:  14.8dB | Throughput:  9.8Mbps | Loss: 0.01%
[10.9s] Step    3 | Akcia: gain-0.1, phase+0.001          | Odmena:  0.125 | SNR:  15.1dB | Throughput: 10.2Mbps | Loss: 0.01%

^C
[INFO] Ukonečovanie agenta...
[INFO] Model uložený: /home/martin/Desktop/RL_Project/saved_models/rl_model_20240115_104000.zip
[INFO] RL Agent ukončený
```

## Čo robiť ak niečo nefunguje?

1. **Chyba pri načítaní modelu:** Spusti `./run.sh train` najprv
2. **Chyba pri pripojení:** Skontroluj, či beží ZeroMQ server na portoch 5555/5556
3. **Žiadne metriky:** Skontroluj, či GNU Radio posiela metriky na port 5556
4. **Agent nereaguje:** Skontroluj, či sú nainštalované všetky závislosti

## Čítanie ďalšej dokumentácie

- `README.md` - Celá dokumentácia projektu
- `JSON_FORMAT.md` - Detailný popis JSON formátov
- `https://wiki.gnuradio.org/index.php/Understanding_ZMQ_Blocks` - GNU Radio ZMQ bloky
