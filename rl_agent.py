#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import zmq
import json
import time
import numpy as np
from stable_baselines3 import DQN
from stable_baselines3.common.env_checker import check_env
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from gymnasium import spaces
import gymnasium as gym

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
MODEL_PATH = os.path.join(BASE_DIR, "saved_models")

ONLINE_TRAINING = {
    "learn_interval_steps": 50,
    "learn_timesteps_per_iteration": 1000,
    "exploration_fraction": 0.3,
    "exploration_final": 0.05,
    "save_interval_steps": 300,
}

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

class RadioEnvironment(gym.Env):
    def __init__(self, config, model_path):
        super().__init__()
        self.config = config
        self.model_path = model_path
        
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, -0.01, 0.0, 0.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([30.0, 1.0, 0.01, 100.0, 1000.0, 1.0, 1.0], dtype=np.float32),
            dtype=np.float32
        )
        
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
        self.step_count = 0
        self.learn_counter = 0
        self.connected = False
        
    def init_sockets(self):
        ctx = zmq.Context()
        
        try:
            self.ctrl_sock = ctx.socket(zmq.REQ)
            self.ctrl_sock.connect(self.config["communication"]["control_address"])
            self.ctrl_sock.setsockopt(zmq.RCVTIMEO, 5000)
            
            self.metrics_sock = ctx.socket(zmq.SUB)
            self.metrics_sock.connect(self.config["communication"]["metrics_address"])
            self.metrics_sock.setsockopt(zmq.SUBSCRIBE, b'')
            self.metrics_sock.setsockopt(zmq.RCVTIMEO, 2000)
            
            self.connected = True
            print("[INFO] RL Agent pripojený k GNU Radio")
            print(f"[INFO] Control: {self.config['communication']['control_address']}")
            print(f"[INFO] Metrics: {self.config['communication']['metrics_address']}")
        except Exception as e:
            self.connected = False
            print(f"[WARNING] Nemôžem sa pripojiť k GNU Radio: {e}")
            print("[WARNING] Budem používať simulované metriky")
            self.ctrl_sock = None
            self.metrics_sock = None
        
    def get_state(self):
        if not self.connected:
            print("[WARNING] Používam simulované metriky")
            return np.array([
                15.0 + np.random.uniform(-3, 3),
                0.5 + np.random.uniform(-0.1, 0.1),
                0.0 + np.random.uniform(-0.01, 0.01),
                10.0 + np.random.uniform(-2, 2),
                50.0 + np.random.uniform(-15, 15),
                0.01 + np.random.uniform(-0.005, 0.02),
                0.02 + np.random.uniform(-0.01, 0.01)
            ], dtype=np.float32)
        
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
        except zmq.Again:
            print("[WARNING] Timeout pri čítaní metrík")
            return np.array([15.0, 0.5, 0.0, 10.0, 50.0, 0.01, 0.02], dtype=np.float32)
        except Exception as e:
            print(f"[ERROR] Chyba pri čítaní metrík: {e}")
            return np.array([15.0, 0.5, 0.0, 10.0, 50.0, 0.01, 0.02], dtype=np.float32)
            
    def send_action(self, action_idx):
        if not self.connected:
            print(f"[INFO] Simulovaná akcia {action_idx}: {self.action_names[action_idx]}")
            return True
        
        try:
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
                
        except zmq.Again:
            print("[ERROR] Timeout pri odoberaní odpovede od GNU Radio")
            return False
        except Exception as e:
            print(f"[ERROR] Chyba pri posielaní akcie: {e}")
            return False
            
    def calculate_reward(self, state):
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
        success = self.send_action(action_idx)
        
        if not success:
            return None, -10.0, True, False, {}
        
        time.sleep(0.2)
        
        next_state = self.get_state()
        reward = self.calculate_reward(next_state)
        done = next_state[5] > 0.8 or next_state[3] < 0.001
        
        self.step_count += 1
        
        return next_state, reward, done, False, {}
        
    def reset(self, seed=None, options=None):
        print("[INFO] Reset environmentu...")
        
        if self.connected:
            try:
                safe_action = {"gain": 1.0, "phase": 0.0, "eq_mu": 0.001}
                self.ctrl_sock.send_json(safe_action)
                self.ctrl_sock.recv_json()
            except Exception as e:
                print(f"[WARNING] Chyba pri resete: {e}")
        else:
            print("[INFO] Simulovaný reset (GNU Radio nie je pripojený)")
        
        time.sleep(1.0)
        
        obs = self.get_state()
        
        return obs, {}
        
    def close(self):
        if self.ctrl_sock:
            self.ctrl_sock.close()
        if self.metrics_sock:
            self.metrics_sock.close()
        print("[INFO] RL Agent sockety uzatvorené")
        
    def load_or_create_model(self):
        model_files = [f for f in os.listdir(self.model_path) if f.endswith(".zip")]
        
        if not model_files:
            print("[INFO] Žiadny existujúci model, vytváram nový pre online tréning")
            self.model = DQN(
                "MlpPolicy",
                self,
                verbose=0,
                learning_rate=1e-3,
                buffer_size=10000,
                learning_starts=100,
                batch_size=32,
                exploration_fraction=ONLINE_TRAINING["exploration_fraction"],
                exploration_final_eps=ONLINE_TRAINING["exploration_final"],
            )
            return True
            
        model_file = max(model_files, key=lambda x: os.path.getmtime(os.path.join(self.model_path, x)))
        model_path_full = os.path.join(self.model_path, model_file)
        
        try:
            self.model = DQN.load(model_path_full)
            print(f"[INFO] Model načítaný: {model_file}")
            return True
        except Exception as e:
            print(f"[ERROR] Chyba pri načítaní modelu, vytváram nový: {e}")
            self.model = DQN(
                "MlpPolicy",
                self,
                verbose=0,
                learning_rate=1e-3,
                buffer_size=10000,
                learning_starts=100,
                batch_size=32,
                exploration_fraction=ONLINE_TRAINING["exploration_fraction"],
                exploration_final_eps=ONLINE_TRAINING["exploration_final"],
            )
            return False
            
    def save_model(self, model):
        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
            
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(self.model_path, f"rl_model_{timestamp}.zip")
        
        try:
            model.save(save_path)
            print(f"[INFO] Model uložený: {save_path}")
        except Exception as e:
            print(f"[ERROR] Chyba pri ukladaní modelu: {e}")
            
    def online_train(self):
        try:
            self.model.learn(total_timesteps=ONLINE_TRAINING["learn_timesteps_per_iteration"])
            print(f"[INFO] Online tréning: {ONLINE_TRAINING['learn_timesteps_per_iteration']} timesteps")
        except Exception as e:
            print(f"[ERROR] Chyba pri online tréningu: {e}")

class RLAgent:
    def __init__(self):
        config = load_config()
        self.config = config
        self.env = RadioEnvironment(config, MODEL_PATH)
        self.model = None
        
    def setup(self):
        self.env.init_sockets()
        
        if not self.env.load_or_create_model():
            print("[ERROR] Nemôžem spustiť agenta bez modelu")
            return False
        
        self.model = self.env.model
        
        print("[INFO] Kontrola environmentu...")
        # check_env(self.env, warn=True)
        
        print("[INFO] RL Agent pripravený")
        if self.env.connected:
            print("[INFO] Pripojený k GNU Radio cez ZMQ")
        else:
            print("[WARNING] Nie je pripojený k GNU Radio (simulácia)")
        print("[INFO] Stlač CTRL+C pre ukončenie")
        
        return True
        
    def run(self, duration_seconds=None):
        self.env.running = True
        
        start_time = time.time()
        step_count = 0
        train_counter = 0
        save_counter = 0
        
        try:
            obs, _ = self.env.reset()
            
            while self.env.running:
                if duration_seconds and (time.time() - start_time) > duration_seconds:
                    print("\n[INFO] Dĺžka runu dosiahnutá")
                    break
                    
                action, _ = self.model.predict(obs, deterministic=False)
                action_idx = int(action)
                
                next_state, reward, done, truncated, info = self.env.step(action_idx)
                step_count += 1
                
                if next_state is None:
                    print("[ERROR] Akcia zlyhala, resetujem environment")
                    obs, _ = self.env.reset()
                    continue
                    
                print(f"[{time.time() - start_time:.1f}s] "
                      f"Step {step_count:4d} | "
                      f"Akcia: {self.env.action_names[action_idx]:30s} | "
                      f"Odmena: {reward:8.3f} | "
                      f"SNR: {next_state[0]:5.1f}dB | "
                      f"Throughput: {next_state[3]:6.1f}Mbps | "
                      f"Loss: {next_state[5]:5.2%}")
                
                if done or truncated:
                    print("\n[INFO] Environment ukončený (detached alebo low throughput)")
                    obs, _ = self.env.reset()
                    continue
                    
                obs = next_state
                
                train_counter += 1
                if train_counter >= ONLINE_TRAINING["learn_interval_steps"]:
                    self.env.online_train()
                    train_counter = 0
                
                save_counter += 1
                if save_counter >= ONLINE_TRAINING["save_interval_steps"]:
                    self.env.save_model(self.model)
                    save_counter = 0
                    
        except KeyboardInterrupt:
            print("\n[INFO] Ukonečovanie agenta...")
            self.env.running = False
            
        finally:
            print("[INFO] Finalné uloženie modelu...")
            self.env.save_model(self.model)
            self.env.close()
            print("[INFO] RL Agent ukončený")

if __name__ == "__main__":
    agent = RLAgent()
    
    if agent.setup():
        agent.run(duration_seconds=None)
    else:
        print("[ERROR] Nemôžem spustiť agenta")
