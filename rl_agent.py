#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RL Agent - komunikuje s GNU Radio a vykonáva rozhodnutia
Načíta tréningový model a aplikuje ho počas runtime.
"""

import zmq
import json
import time
import numpy as np
from stable_baselines3 import DQN
from stable_baselines3.common.env_checker import check_env
import os
import sys
import threading

# --- Konfigurácia ---
CONFIG_PATH = "/home/martin/Desktop/RL_Project/config.json"
MODEL_PATH = "/home/martin/Desktop/RL_Project/saved_models"

# --- Načítanie konfigurácie ---
def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

class RadioEnvironment:
    """
    Gym-like prostredie pre RL agenta
    Simuluje komunikáciu s GNU Radio
    """
    def __init__(self, config, model_path):
        self.config = config
        self.model_path = model_path
        
        # State: [snr, power, cfo, throughput, rtt, loss, bler]
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, -0.01, 0.0, 0.0, 0.0, 0.0]),
            high=np.array([30.0, 1.0, 0.01, 100.0, 1000.0, 1.0, 1.0]),
            dtype=np.float32
        )
        
        # Action: gain, phase, eq_mu (discrete pre DQN)
        self.action_space = spaces.Discrete(6)
        self.action_names = [
            "gain+0.1, phase+0.001",
            "gain+0.1, phase-0.001",
            "gain-0.1, phase+0.001",
            "gain-0.1, phase-0.001",
            "gain+0.05, eq_mu+0.0005",
            "gain-0.05, eq_mu-0.0005"
        ]
        
        self.ctrl_sock = None
        self.metrics_sock = None
        self.running = False
        self.model = None
        
    def init_sockets(self):
        """Inicializuje ZMQ sockety"""
        ctx = zmq.Context()
        
        # Control (REQ) - odošle akciu
        self.ctrl_sock = ctx.socket(zmq.REQ)
        self.ctrl_sock.connect(self.config["communication"]["control_address"])
        
        # Metrics (SUB) - príjme metriky
        self.metrics_sock = ctx.socket(zmq.SUB)
        self.metrics_sock.connect(self.config["communication"]["metrics_address"])
        self.metrics_sock.setsockopt(zmq.SUBSCRIBE, b'')
        
        print(f"[INFO] RL Agent pripojený k GNU Radio")
        print(f"[INFO] Control: {self.config['communication']['control_address']}")
        print(f"[INFO] Metrics: {self.config['communication']['metrics_address']}")
        
    def get_state(self):
        """Načíta aktuálny state z metrík"""
        try:
            if self.metrics_sock.poll(1000) > 0:
                msg = self.metrics_sock.recv_json()
                state = np.array([
                    msg.get("snr", 15.0),
                    msg.get("power", 0.5),
                    msg.get("cfo", 0.0),
                    msg.get("throughput", 10.0),
                    msg.get("rtt", 50.0),
                    msg.get("loss", 0.01),
                    msg.get("bler", 0.02)
                ], dtype=np.float32)
                return state
            else:
                print("[WARNING] Žiadne metriky, použijem predvolené")
                return np.array([15.0, 0.5, 0.0, 10.0, 50.0, 0.01, 0.02], dtype=np.float32)
        except Exception as e:
            print(f"[ERROR] Chyba pri čítaní metrík: {e}")
            return np.array([15.0, 0.5, 0.0, 10.0, 50.0, 0.01, 0.02], dtype=np.float32)
            
    def send_action(self, action_idx):
        """Odošle akciu do GNU Radio"""
        try:
            # Map index na reálne hodnoty
            gains = [0.1, 0.1, -0.1, -0.1, 0.05, -0.05]
            phases = [0.001, -0.001, 0.001, -0.001, 0.0, 0.0]
            eq_mus = [0.0, 0.0, 0.0, 0.0, 0.0005, -0.0005]
            
            action = {
                "gain": gains[action_idx],
                "phase": phases[action_idx],
                "eq_mu": eq_mus[action_idx]
            }
            
            self.ctrl_sock.send_json(action)
            response = self.ctrl_sock.recv_json()
            
            if response.get("ok", False):
                print(f"[INFO] Akcia {action_idx} odoslaná: {self.action_names[action_idx]}")
                return True
            else:
                print(f"[ERROR] Akcia {action_idx} bola odmietnutá")
                return False
                
        except Exception as e:
            print(f"[ERROR] Chyba pri posielaní akcie: {e}")
            return False
            
    def compute_reward(self, state):
        """Vypočíta odmenu podľa vzorca z config"""
        throughput = state[3]
        loss = state[5]
        rtt = state[4]
        bler = state[6]
        
        reward = (
            1.5 * throughput -
            15.0 * loss -
            0.05 * rtt -
            5.0 * bler
        )
        
        return reward
        
    def step(self, action_idx):
        """Jeden krok environmentu"""
        # 1. Odošli akciu
        success = self.send_action(action_idx)
        
        # 2. Počkaj na zmenu
        time.sleep(0.2)  # 200ms
        
        # 3. Načítaj nový state
        next_state = self.get_state()
        
        # 4. Vypočítaj odmenu
        reward = self.compute_reward(next_state)
        
        # 5. Kontrola ukončenia
        done = next_state[5] > 0.8 or next_state[3] < 0.001  # loss > 80% alebo throughput = 0
        
        return next_state, reward, done
        
    def reset(self):
        """Reset environmentu"""
        print("[INFO] Reset environmentu...")
        
        # Bezpečný reset
        safe_action = {"gain": 1.0, "phase": 0.0, "eq_mu": 0.001}
        self.ctrl_sock.send_json(safe_action)
        self.ctrl_sock.recv_json()
        
        time.sleep(1.0)
        
        return self.get_state()
        
    def close(self):
        """Uzavrie sockety"""
        if self.ctrl_sock:
            self.ctrl_sock.close()
        if self.metrics_sock:
            self.metrics_sock.close()
        print("[INFO] RL Agent sockety uzatvorené")
        
    def load_model(self):
        """Načíta tréningový model"""
        model_files = [f for f in os.listdir(self.model_path) if f.endswith(".zip")]
        
        if not model_files:
            print("[ERROR] Nenašiel som žiadny model v", self.model_path)
            return False
            
        model_file = max(model_files, key=lambda x: os.path.getmtime(os.path.join(self.model_path, x)))
        model_path = os.path.join(self.model_path, model_file)
        
        try:
            self.model = DQN.load(model_path)
            print(f"[INFO] Model načítaný: {model_file}")
            return True
        except Exception as e:
            print(f"[ERROR] Chyba pri načítaní modelu: {e}")
            return False
            
    def save_model(self, model):
        """Uloží aktuálny model"""
        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
            
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(self.model_path, f"rl_model_{timestamp}.zip")
        
        try:
            model.save(save_path)
            print(f"[INFO] Model uložený: {save_path}")
        except Exception as e:
            print(f"[ERROR] Chyba pri ukladaní modelu: {e}")

class RLAgent:
    """
    Hlavný RL agent s automatickým ukladaním
    """
    def __init__(self):
        config = load_config()
        self.config = config
        self.env = RadioEnvironment(config, MODEL_PATH)
        self.model = None
        
    def setup(self):
        """Naštartuje agenta"""
        # Inicializuj sockety
        self.env.init_sockets()
        
        # Načítaj model
        if not self.env.load_model():
            print("[ERROR] Nemôžem spustiť agenta bez modelu")
            return False
        
        self.model = self.env.model
        
        # Kontrola environmentu
        check_env(self.env, warn=True)
        
        print("[INFO] RL Agent pripravený")
        print("[INFO] Stlač CTRL+C pre ukončenie")
        
        return True
        
    def run(self, duration_seconds=None):
        """Spusti agenta"""
        self.env.running = True
        
        start_time = time.time()
        step_count = 0
        save_counter = 0
        
        try:
            obs = self.env.reset()
            
            while self.env.running:
                # Kontrola času
                if duration_seconds and (time.time() - start_time) > duration_seconds:
                    print("\n[INFO] Dĺžka runu dosiahnutá")
                    break
                    
                # 1. Predict action
                action, _ = self.model.predict(obs, deterministic=True)
                action_idx = int(action)
                
                # 2. Step environment
                next_state, reward, done = self.env.step(action_idx)
                step_count += 1
                
                # 3. Output
                print(f"[{time.time() - start_time:.1f}s] "
                      f"Step {step_count:4d} | "
                      f"Akcia: {self.env.action_names[action_idx]:30s} | "
                      f"Odmena: {reward:8.3f} | "
                      f"SNR: {next_state[0]:5.1f}dB | "
                      f"Throughput: {next_state[3]:6.1f}Mbps | "
                      f"Loss: {next_state[5]:5.2%}")
                
                # 4. Kontrola ukončenia
                if done:
                    print("\n[INFO] Environment ukončený (detached alebo low throughput)")
                    obs = self.env.reset()
                    continue
                    
                obs = next_state
                
                # 5. Pravidelné ukladanie modelu
                save_counter += 1
                if save_counter % 100 == 0:  # každých ~20 sekúnd
                    self.env.save_model(self.model)
                    
        except KeyboardInterrupt:
            print("\n[INFO] Ukonečovanie agenta...")
            self.env.running = False
            
        finally:
            # Finalné uloženie
            self.env.save_model(self.model)
            self.env.close()
            print("[INFO] RL Agent ukončený")

if __name__ == "__main__":
    import gymnasium as gym
    import numpy as np
    from gymnasium import spaces
    
    agent = RLAgent()
    
    if agent.setup():
        agent.run(duration_seconds=None)  # None = beží dovtedy, kým sa nezastaví
    else:
        print("[ERROR] Nemôžem spustiť agenta")
