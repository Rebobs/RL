#!/bin/bash
# Spúšťač pre RL Agent
# Použitie: ./run.sh [train|run|list]

cd /home/martin/Desktop/RL_Project

if [ "$1" == "train" ]; then
    echo "Spúšťam trénovanie..."
    python3 main.py train
elif [ "$1" == "run" ]; then
    echo "Spúšťam agenta..."
    python3 main.py run "$@"
elif [ "$1" == "list" ]; then
    echo "Zoznam modelov..."
    python3 main.py list
else
    echo "Použitie: ./run.sh [train|run|list]"
    echo ""
    echo "Možnosti:"
    echo "  train  - Natrénuje nový model"
    echo "  run    - Spustí agenta s existujúcim modelom"
    echo "  list   - Zoznam dostupných modelov"
fi
