#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trénovací skript pre RL agenta
Natrénuje model a uloží ho do priečinka saved_models
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from stable_baselines3 import DQN
from stable_baselines3.common.env_checker import check_env
import os
import time
import json

# --- Import RL environment ---
sys.path.append('/home/martin/Desktop/RL_Project')
from rl_agent import RadioEnvironment

# --- Konfigurácia ---
CONFIG_PATH = "/home/martin/Desktop/RL_Project/config.json"
MODEL_PATH = "/home/martin/Desktop/RL_Project/saved_models"

# --- Trénovacie nastavenia ---
TRAINING_SETTINGS = {
    "total_timesteps": 50000,
    "buffer_size": 10000,
    "learning_starts": 500,
    "batch_size": 32,
    "learning_rate": 1e-3,
    "exploration_fraction": 0.4,
    "verbose": 1
}

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def train_model():
    """Trénuje RL model a uloží ho"""
    
    print("=" * 60)
    print("TRÉNOVANIE RL AGENTA PRE GNU RADIO")
    print("=" * 60)
    
    # Vytvor priečinok pre modely
    if not os.path.exists(MODEL_PATH):
        os.makedirs(MODEL_PATH)
        
    # Načítaj konfiguráciu
    config = load_config()
    
    # Vytvor environment
    print("\n[INFO] Vytváram environment...")
    env = RadioEnvironment(config, MODEL_PATH)
    
    # Kontrola environmentu
    print("[INFO] Kontrola environmentu...")
    check_env(env, warn=True)
    
    # Vytvor DQN model
    print("\n[INFO] Vytváram DQN model...")
    model = DQN(
        "MlpPolicy",
        env,
        verbose=TRAINING_SETTINGS["verbose"],
        learning_rate=TRAINING_SETTINGS["learning_rate"],
        buffer_size=TRAINING_SETTINGS["buffer_size"],
        learning_starts=TRAINING_SETTINGS["learning_starts"],
        batch_size=TRAINING_SETTINGS["batch_size"],
        exploration_fraction=TRAINING_SETTINGS["exploration_fraction"],
    )
    
    # Trénuj
    print("\n[INFO] Začínam trénovať...")
    start_time = time.time()
    
    model.learn(total_timesteps=TRAINING_SETTINGS["total_timesteps"])
    
    train_time = time.time() - start_time
    print(f"\n[INFO] Trénovanie dokončené. Čas: {train_time:.1f}s")
    
    # Ulož model
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    model_file = f"rl_model_{timestamp}.zip"
    save_path = os.path.join(MODEL_PATH, model_file)
    
    model.save(save_path)
    print(f"\n[INFO] Model uložený: {save_path}")
    
    # Zoznam súborov v priečinku
    files = os.listdir(MODEL_PATH)
    print(f"\n[INFO] Modely v priečinku {MODEL_PATH}:")
    for f in sorted(files):
        filepath = os.path.join(MODEL_PATH, f)
        size = os.path.getsize(filepath)
        print(f"  - {f} ({size / 1024:.1f} KB)")
    
    return model, save_path

def test_model(model):
    """Testuje nacenený model"""
    
    print("\n" + "=" * 60)
    print("TESTOVANIE MODEL")
    print("=" * 60)
    
    config = load_config()
    env = RadioEnvironment(config, MODEL_PATH)
    env.init_sockets()  # Iniciuje sockety pre test
    
    # Simulované testovanie (bez reálnej komunikácie)
    obs = env.reset()
    print(f"\nPočiatočný stav: SNR={obs[0]:.1f}dB | Throughput={obs[3]:.1f}Mbps")
    
    for i in range(10):
        action, _ = model.predict(obs, deterministic=True)
        next_state, reward, done = env.step(int(action))
        
        print(f"  Krok {i+1}: "
              f"Akcia {int(action)} | "
              f"Odmena {reward:.3f} | "
              f"SNR {next_state[0]:.1f}dB | "
              f"Throughput {next_state[3]:.1f}Mbps")
        
        obs = next_state
        if done:
            break
    
    env.close()
    print("\n[INFO] Test dokončený")

if __name__ == "__main__":
    import sys
    sys.path.append('/home/martin/Desktop/RL_Project')
    
    try:
        model, save_path = train_model()
        
        # Otázka na testovanie
        answer = input("\nChceš testovať model? (y/n): ").strip().lower()
        if answer == "y":
            test_model(model)
            
        print("\n" + "=" * 60)
        print("TRÉN DOKONČENÝ")
        print(f"Model uložený: {save_path}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Chyba počas trénovania: {e}")
        import traceback
        traceback.print_exc()
