#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GNU Radio Control Server
Tento server prijíma akcie od RL agenta a posiela metriky späť.
Beží ako samostatný proces vedľa GNU Radio flowgraphu.
"""

import zmq
import threading
import json
import time
import sys
import os

# --- Nastavenie ---
CONTROL_PORT = 5555
METRICS_PORT = 5556
CONTROL_ADDR = f"tcp://127.0.0.1:{CONTROL_PORT}"
METRICS_ADDR = f"tcp://127.0.0.1:{METRICS_PORT}"
SAVE_INTERVAL = 300  # sekund

# --- Bezpečnostné limity ---
SAFE_GAIN = 1.0
SAFE_PHASE = 0.0
SAFE_EQ_MU = 0.001
MAX_LOSS = 0.8
MAX_RTT = 1000
MIN_THROUGHPUT = 0.001

# --- Interné parametre (toto by sa dalo prepojiť s reálnym GNU Radio) ---
class RadioParameters:
    def __init__(self):
        self.gain = 1.0
        self.phase = 0.0
        self.eq_mu = 0.001
        self.last_snr = 15.0
        self.last_power = 0.5
        self.last_cfo = 0.0
        self.last_throughput = 10.0
        self.last_rtt = 50.0
        self.last_loss = 0.01
        self.last_bler = 0.02
        self.detached = False

class RadioControlServer:
    def __init__(self, params):
        self.params = params
        self.ctx = zmq.Context()
        self.control_sock = None
        self.metrics_sock = None
        self.running = False
        self.save_counter = 0
        
    def init_control_socket(self):
        """Inicializuje kontrolný socket (REQ/REP)"""
        self.control_sock = self.ctx.socket(zmq.REP)
        self.control_sock.bind(CONTROL_ADDR)
        print(f"[INFO] Kontrolný server počúva na {CONTROL_ADDR}")
        
    def init_metrics_socket(self):
        """Inicializuje metrics socket (PUB/SUB)"""
        self.metrics_sock = self.ctx.socket(zmq.PUB)
        self.metrics_sock.bind(METRICS_ADDR)
        print(f"[INFO] Metrics server počúva na {METRICS_ADDR}")
        
    def receive_action(self):
        """Prijme akciu od RL agenta"""
        try:
            msg = self.control_sock.recv()
            action = json.loads(msg.decode('utf-8'))
            return action
        except Exception as e:
            print(f"[ERROR] Chyba pri prijímaní akcie: {e}")
            return None
            
    def send_response(self, ok=True):
        """Odošle odpoveď RL agentovi"""
        response = {"ok": ok, "timestamp": time.time()}
        self.control_sock.send_json(response)
        
    def get_metrics(self):
        """Vytvorí metrics objekt"""
        # ⚠️ V reálnom prípade tu načítaš hodnoty z GNU Radio flowgraphu
        return {
            "snr": self.params.last_snr,
            "power": self.params.last_power,
            "cfo": self.params.last_cfo,
            "throughput": self.params.last_throughput,
            "rtt": self.params.last_rtt,
            "loss": self.params.last_loss,
            "bler": self.params.last_bler,
            "detached": self.params.detached
        }
        
    def apply_action(self, action):
        """Aplikuje akciu na parametre"""
        if "gain" in action:
            self.params.gain = max(0.0, min(10.0, action["gain"]))
        if "phase" in action:
            self.params.phase = max(-0.02, min(0.02, action["phase"]))
        if "eq_mu" in action:
            self.params.eq_mu = max(0.0, min(0.01, action["eq_mu"]))
            
    def check_watchdog(self, metrics):
        """Watchdog - bezpečnostná poistka"""
        if metrics.get("detached", False):
            print("[ALERT] UE detach! Reset na bezpečné hodnoty.")
            self.apply_action({"gain": SAFE_GAIN, "phase": SAFE_PHASE, "eq_mu": SAFE_EQ_MU})
            return True
            
        if metrics.get("loss", 0) > MAX_LOSS:
            print(f"[ALERT] High packet loss: {metrics['loss']:.1%}. Reset.")
            self.apply_action({"gain": SAFE_GAIN, "phase": SAFE_PHASE, "eq_mu": SAFE_EQ_MU})
            return True
            
        if metrics.get("rtt", 0) > MAX_RTT:
            print(f"[ALERT] High RTT: {metrics['rtt']:.0f}ms. Reset.")
            self.apply_action({"gain": SAFE_GAIN, "phase": SAFE_PHASE, "eq_mu": SAFE_EQ_MU})
            return True
            
        if metrics.get("throughput", 1.0) < MIN_THROUGHPUT:
            print(f"[ALERT] Throughput near zero: {metrics['throughput']:.3f} Mbps. Reset.")
            self.apply_action({"gain": SAFE_GAIN, "phase": SAFE_PHASE, "eq_mu": SAFE_EQ_MU})
            return True
            
        return False
        
    def save_state(self, filepath="/home/martin/Desktop/RL_Project/saved_params.json"):
        """Uloží aktuálne parametre"""
        state = {
            "gain": self.params.gain,
            "phase": self.params.phase,
            "eq_mu": self.params.eq_mu,
            "timestamp": time.time()
        }
        try:
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=4)
            print(f"[INFO] Parametre uložené do {filepath}")
        except Exception as e:
            print(f"[ERROR] Chyba pri ukladaní: {e}")
            
    def simulate_metrics_update(self):
        """Simuluje aktualizáciu metrík (pre demo účely)"""
        # V reálnom prípade by si tu čítal hodnoty z GNU Radio
        import random
        self.params.last_snr = max(0.0, 15.0 + random.uniform(-5, 5))
        self.params.last_power = 0.5 + random.uniform(-0.1, 0.1)
        self.params.last_cfo = random.uniform(-0.01, 0.01)
        self.params.last_throughput = max(0.0, 10.0 + random.uniform(-3, 3))
        self.params.last_rtt = max(10.0, 50.0 + random.uniform(-20, 20))
        self.params.last_loss = max(0.0, 0.01 + random.uniform(-0.005, 0.02))
        self.params.last_bler = max(0.0, 0.02 + random.uniform(-0.01, 0.02))
        
    def control_thread(self):
        """Hlavná slučka kontrolného servera"""
        self.running = True
        self.init_control_socket()
        self.init_metrics_socket()
        
        print(f"[INFO] Kontrolný server spustený")
        print(f"[INFO] Kontrolný port: {CONTROL_ADDR}")
        print(f"[INFO] Metrics port: {METRICS_ADDR}")
        print(f"[INFO] Stlač CTRL+C pre ukončenie")
        
        while self.running:
            try:
                # 1. Prijmi akciu od RL agenta
                action = self.receive_action()
                
                if action:
                    # 2. Aplikuj akciu
                    self.apply_action(action)
                    
                    # 3. Skontroluj watchdog
                    metrics = self.get_metrics()
                    if self.check_watchdog(metrics):
                        print("[INFO] Watchdog aktivoval bezpečný reset")
                    
                    # 4. Odošli odpoveď
                    self.send_response(ok=True)
                else:
                    self.send_response(ok=False)
                    
            except zmq.ZMQError as e:
                if not self.running:
                    break
                print(f"[ERROR] ZMQ chyba: {e}")
            except KeyboardInterrupt:
                print("\n[INFO] Ukonečovanie servera...")
                self.running = False
            except Exception as e:
                print(f"[ERROR] Nečakaná chyba: {e}")
                
    def metrics_thread(self):
        """Pozadie thread pre posielaie metrík"""
        self.running = True
        
        while self.running:
            try:
                # Simuluj aktualizáciu metrík
                self.simulate_metrics_update()
                
                # Odošli metriky
                metrics = self.get_metrics()
                self.metrics_sock.send_json(metrics)
                
                # Ukladaj parametre pravidelne
                self.save_counter += 1
                if self.save_counter % 150 == 0:  # približne každých 15 sekúnd
                    self.save_state()
                    
                time.sleep(0.1)  # 100ms
                
            except zmq.ZMQError as e:
                if not self.running:
                    break
            except Exception as e:
                print(f"[ERROR] Metrics chyba: {e}")
                
    def start(self):
        """Spusti server"""
        control_thread = threading.Thread(target=self.control_thread, daemon=True)
        metrics_thread = threading.Thread(target=self.metrics_thread, daemon=True)
        
        control_thread.start()
        metrics_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[INFO] Ukončovanie...")
            self.running = False
            time.sleep(0.5)
            self.ctx.term()
            print("[INFO] Server ukončený")

if __name__ == "__main__":
    params = RadioParameters()
    server = RadioControlServer(params)
    server.start()
