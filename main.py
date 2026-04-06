#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from rl_agent import RLAgent

MODEL_PATH = os.path.join(BASE_DIR, "saved_models")

def list_models():
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
    parser = argparse.ArgumentParser(description="RL Agent pre GNU Radio",
                                     epilog="Príklady: python main.py | python main.py run | python main.py list")
    parser.add_argument("mode", nargs="?", default="run", choices=["run", "list"], 
                        help="Režim: run (spustiť agenta) alebo list (zoznam modelov). Default: run")
    parser.add_argument("--time", type=int, default=None,
                        help="Čas runu v sekundách (len pre 'run' mode)")
    parser.add_argument("--model", type=str, default=None,
                        help="Špecifický model na spustenie (len pre 'run' mode)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("RL AGENT PRE GNU RADIO - Hlavný spúšťač")
    print("=" * 60)
    
    if args.mode == "list":
        print("\nDostupné modely:")
        list_models()
        return
        
    elif args.mode == "run":
        if not os.path.exists(MODEL_PATH):
            os.makedirs(MODEL_PATH)
            print(f"[INFO] Vytvorený priečinok: {MODEL_PATH}")
        
        model_files = [f for f in os.listdir(MODEL_PATH) if f.endswith(".zip")]
        
        if not model_files:
            print("\n[INFO] Žiadny existujúci model")
            print("[INFO] Agent začne s novým modelom a bude sa učiť ONLINE")
            print("[INFO] Počas behu sa model bude trénovať a ukladať")
        else:
            if not args.model:
                model_file = max(model_files, key=lambda x: os.path.getmtime(os.path.join(MODEL_PATH, x)))
                print(f"[INFO] Používam najnovší model: {model_file}")
            else:
                model_file = args.model
                print(f"[INFO] Používam model: {model_file}")
            
            print("\nDostupné modely:")
            list_models()
        
        print("\n" + "=" * 60)
        print("SPÚŠŤANIE AGENTA S ONLINE TRÉNINGOM")
        print("=" * 60)
        print("[INFO] Agent sa bude učiť počas behu")
        print("[INFO] Model sa bude ukladať každých 300 krokov")
        print("[INFO] Stlač CTRL+C pre ukončenie")
        print("=" * 60)
        
        agent = RLAgent()
        if agent.setup():
            print(f"\n[INFO] Spúšťam agenta na {args.time} sekúnd...")
            agent.run(duration_seconds=args.time)
        else:
            print("[ERROR] Nemôžem spustiť agenta")
            
    else:
        print(f"[ERROR] Neznámy mode: {args.mode}")
        return

if __name__ == "__main__":
    main()
