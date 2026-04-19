#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from rl_agent import RLAgent, build_monitor, load_config

MODEL_PATH = os.path.join(BASE_DIR, "saved_models")

def list_models():
    if not os.path.exists(MODEL_PATH):
        print("Žiadne modely v", MODEL_PATH)
        return
    files = sorted(
        [f for f in os.listdir(MODEL_PATH) if f.endswith(".zip")],
        key=lambda x: os.path.getmtime(os.path.join(MODEL_PATH, x))
    )
    if not files:
        print("  (žiadne uložené modely)")
        return
    for f in files:
        fp   = os.path.join(MODEL_PATH, f)
        size = os.path.getsize(fp) / 1024
        mt   = time.ctime(os.path.getmtime(fp))
        print(f"  {f}  ({size:.1f} KB)  {mt}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="RL Agent pre GNU Radio")
    parser.add_argument("mode", nargs="?", default="run",
                        choices=["run", "list"],
                        help="run = spusti agenta, list = zoznam modelov")
    args = parser.parse_args()

    print("=" * 60)
    print("RL AGENT PRE GNU RADIO")
    print("=" * 60)

    if args.mode == "list":
        list_models()
        return

    print("Logy:  debug.log       — súhrnné štatistiky každých 20 krokov")
    print("       rl_decisions.log — každé rozhodnutie agenta (ak debug=true)")
    print("Ukonči: CTRL+C")
    print("=" * 60)

    agent = RLAgent()
    agent.setup()

    cfg     = load_config()
    mon_cfg = cfg.get("monitor", {})
    fig, ani = None, None

    if mon_cfg.get("enabled", False):
        fig, ani = build_monitor(mon_cfg, cfg["communication"]["metrics_address"])

    # Agent beží v daemon vlákne; plt.show() blokuje hlavné vlákno
    t = threading.Thread(target=agent.run, daemon=True)
    t.start()

    if fig is not None:
        import matplotlib.pyplot as plt
        try:
            plt.show()
        except KeyboardInterrupt:
            pass
    else:
        # žiadny monitor — čakáme na agent vlákno
        try:
            while t.is_alive():
                t.join(timeout=1.0)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
