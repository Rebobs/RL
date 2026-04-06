#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hlavný spúšťací skript pre RL Agent
Vyberie si medzi trénovaním a runtime spúšťaním
"""

import os
import sys
import argparse

# Pridaj Project path
sys.path.insert(0, '/home/martin/Desktop/RL_Project')

from train_agent import train_model
from rl_agent import RLAgent

# --- Konštanty ---
PROJECT_DIR = "/home/martin/Desktop/RL_Project"
MODEL_PATH = os.path.join(PROJECT_DIR, "saved_models")

def list_models():
    """Zoznam dostupných modelov"""
    if not os.path.exists(MODEL_PATH):
        print("Žiadne modely v", MODEL_PATH)
        return []
        
    files = [f for f in os.listdir(MODEL_PATH) if f.endswith(".zip")]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(MODEL_PATH, x)))
    
    for f in files:
        filepath = os.path.join(MODEL_PATH, f)
        size = os.path.getsize(filepath)
        mtime = os.path.getmtime(filepath)
        print(f"  {f} ({size/1024:.1f} KB) - {time.ctime(mtime)}")
        
    return files

def main():
    parser = argparse.ArgumentParser(description="RL Agent pre GNU Radio")
    parser.add_argument("mode", choices=["train", "run", "list"], 
                        help="Trénovať, Spustiť, alebo Zoznam modelov")
    parser.add_argument("--time", type=int, default=None,
                        help="Čas runu v sekundách (pre 'run' mode)")
    parser.add_argument("--model", type=str, default=None,
                        help="Špecifický model na spustenie")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("RL AGENT PRE GNU RADIO - Hlavný spúšťač")
    print("=" * 60)
    
    if args.mode == "list":
        print("\nDostupné modely:")
        list_models()
        return
        
    elif args.mode == "train":
        print("\nZačínam trénovanie...")
        model, path = train_model()
        
        print("\n" + "=" * 60)
        print("Trénovanie dokončené!")
        print(f"Model: {path}")
        print("=" * 60)
        
        # Ponúknuť spustenie
        answer = input("\nChceš teraz spustiť agenta? (y/n): ").strip().lower()
        if answer == "y":
            agent = RLAgent()
            if agent.setup():
                agent.run(duration_seconds=args.time)
                
    elif args.mode == "run":
        # Skontroluj, či existuje model
        if not os.path.exists(MODEL_PATH):
            print("\n[ERROR] Žiadne modely v", MODEL_PATH)
            print("Najprv spusti 'python train_agent.py train'")
            return
            
        files = list_models()
        if not files:
            print("\n[ERROR] Žiadne modely v", MODEL_PATH)
            return
            
        # Ak nie je model zadaný, vyber najnovší
        if not args.model:
            model_file = max(files, key=lambda x: os.path.getmtime(os.path.join(MODEL_PATH, x)))
            print(f"[INFO] Používam najnovší model: {model_file}")
        else:
            model_file = args.model
            print(f"[INFO] Používam model: {model_file}")
            
        # Spusti agenta
        agent = RLAgent()
        if agent.setup():
            print(f"\n[INFO] Spúšťam agenta na {args.time} sekúnd...")
            agent.run(duration_seconds=args.time)
            
    else:
        print(f"[ERROR] Neznámy mode: {args.mode}")
        return

if __name__ == "__main__":
    main()
