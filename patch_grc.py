#!/usr/bin/env python3
"""
Patches Zapojenie.grc:
  1. Adds noise_amp variable (controls real GRC noise source)
  2. Sets analog_noise_source_x_0.amp = noise_amp
  3. Inserts epy_block_0 (TX Reference) directly on the random_source → char_to_float path
  4. Inserts epy_block_0_0 (Bridge) directly on the decoder → char_to_float path
  5. Both epy blocks now work with int8 bytes instead of complex64
  6. Bridge compares real TX vs RX bytes for actual BER
  7. Bridge controls GRC noise source via gc top-block reference
"""
import yaml, sys, os

GRC = os.path.join(os.path.dirname(__file__), "Zapojenie.grc")

EPY_BLOCK_0_CODE = """\
import numpy as np
from gnuradio import gr
import zmq

class blk(gr.sync_block):
    def __init__(self, example_param=None):
        gr.sync_block.__init__(self,
            name="ZMQ TX Reference",
            in_sig=[np.int8],
            out_sig=[np.int8])
        self._ctx = zmq.Context()
        self._push = self._ctx.socket(zmq.PUSH)
        self._push.setsockopt(zmq.SNDHWM, 100)
        self._push.bind("tcp://127.0.0.1:5557")

    def work(self, input_items, output_items):
        data = bytes(input_items[0].tobytes())
        try:
            self._push.send(data, zmq.NOBLOCK)
        except zmq.Again:
            pass
        output_items[0][:] = input_items[0]
        return len(input_items[0])

    def stop(self):
        self._push.close()
        self._ctx.term()
        return True
"""

EPY_BLOCK_0_0_CODE = """\
import numpy as np
from gnuradio import gr
import zmq
import json
import threading
import time
import collections
import gc

BER_WINDOW = 50

class blk(gr.sync_block):
    def __init__(self, example_param=None):
        gr.sync_block.__init__(self,
            name="ZMQ Bridge",
            in_sig=[np.int8],
            out_sig=[np.int8])
        self._running = False
        self._ctx = None
        self._rep = None
        self._pub = None
        self._pull = None
        self._noise_sigma = 0.0
        self._tx_buf = collections.deque(maxlen=500000)
        self._rx_buf = collections.deque(maxlen=500000)
        self._ber_window = collections.deque(maxlen=BER_WINDOW)
        self._lock = threading.Lock()
        self._top_block = None

    def _find_top_block(self):
        for obj in gc.get_objects():
            if type(obj).__name__ == 'Zapojenie':
                return obj
        return None

    def _set_noise_amp(self, sigma):
        if self._top_block is None:
            self._top_block = self._find_top_block()
        if self._top_block is not None:
            try:
                self._top_block.set_noise_amp(sigma)
            except Exception as e:
                print(f"[GRC] noise err: {e}")

    def _start_zmq(self):
        self._running = True
        self._ctx = zmq.Context()
        self._rep = self._ctx.socket(zmq.REP)
        self._rep.setsockopt(zmq.RCVTIMEO, 100)
        self._rep.bind("tcp://127.0.0.1:5555")
        self._pub = self._ctx.socket(zmq.PUB)
        self._pub.bind("tcp://127.0.0.1:5556")
        self._pull = self._ctx.socket(zmq.PULL)
        self._pull.setsockopt(zmq.RCVTIMEO, 10)
        self._pull.connect("tcp://127.0.0.1:5557")
        threading.Thread(target=self._ctrl_loop, daemon=True).start()
        threading.Thread(target=self._pull_loop, daemon=True).start()
        threading.Thread(target=self._metrics_loop, daemon=True).start()
        print("[GRC] Bridge ready — real BER mode")

    def _ctrl_loop(self):
        while self._running:
            try:
                raw = self._rep.recv()
                data = json.loads(raw.decode())
                new_sigma = float(np.clip(float(data.get("noise_sigma", self._noise_sigma)), 0.0, 5.0))
                with self._lock:
                    self._noise_sigma = new_sigma
                self._set_noise_amp(new_sigma)
                self._rep.send(b"ok")
            except zmq.Again:
                pass
            except Exception as e:
                print(f"[GRC] ctrl err: {e}")
                try: self._rep.send(b"err")
                except: pass

    def _pull_loop(self):
        while self._running:
            try:
                data = self._pull.recv()
                bits = np.frombuffer(data, dtype=np.int8)
                with self._lock:
                    self._tx_buf.extend(bits.tolist())
            except zmq.Again:
                pass
            except Exception as e:
                print(f"[GRC] pull err: {e}")

    def _metrics_loop(self):
        time.sleep(2.0)
        while self._running:
            try:
                N = 4000
                with self._lock:
                    tx_len = len(self._tx_buf)
                    rx_len = len(self._rx_buf)
                    sigma = self._noise_sigma

                if tx_len >= N and rx_len >= N:
                    with self._lock:
                        tx_arr = np.array([self._tx_buf.popleft() for _ in range(N)], dtype=np.int8)
                        rx_arr = np.array([self._rx_buf.popleft() for _ in range(N)], dtype=np.int8)
                    ber = float(np.mean(tx_arr != rx_arr))
                    ber = float(np.clip(ber, 1e-7, 1.0))
                    with self._lock:
                        self._ber_window.append(ber)

                with self._lock:
                    bw = list(self._ber_window)
                if bw:
                    ber_avg = float(np.clip(np.mean(bw), 1e-7, 1.0))
                    snr_db = float(-20.0 * np.log10(max(sigma, 1e-6))) if sigma > 1e-6 else 40.0
                    snr_db = float(np.clip(snr_db, -10.0, 40.0))
                    self._pub.send_json({"snr": snr_db, "ber": ber_avg, "noise_sigma": sigma})
            except Exception as e:
                print(f"[GRC] metrics err: {e}")
            time.sleep(0.2)

    def work(self, input_items, output_items):
        if not self._running:
            self._start_zmq()
        rx_bits = input_items[0].copy()
        output_items[0][:] = rx_bits
        with self._lock:
            self._rx_buf.extend(rx_bits.tolist())
        return len(input_items[0])

    def stop(self):
        self._running = False
        if self._pull: self._pull.close()
        if self._rep:  self._rep.close()
        if self._pub:  self._pub.close()
        if self._ctx:  self._ctx.term()
        return True
"""

# ── load ──────────────────────────────────────────────────────────────────────
with open(GRC) as f:
    doc = yaml.safe_load(f)

blocks = doc["blocks"]

# ── 1. add noise_amp variable (skip if already present) ───────────────────────
if not any(b["name"] == "noise_amp" for b in blocks):
    noise_amp_block = {
        "name": "noise_amp",
        "id": "variable",
        "parameters": {"comment": "", "value": "0.0"},
        "states": {
            "bus_sink": False,
            "bus_source": False,
            "bus_structure": None,
            "coordinate": [832, 228],
            "rotation": 0,
            "state": "enabled",
        },
    }
    # insert right after samp_rate
    idx = next(i for i, b in enumerate(blocks) if b["name"] == "samp_rate")
    blocks.insert(idx + 1, noise_amp_block)
    print("+ added noise_amp variable")
else:
    print("  noise_amp already present")

# ── 2. set noise source amp to noise_amp ──────────────────────────────────────
for b in blocks:
    if b["name"] == "analog_noise_source_x_0":
        b["parameters"]["amp"] = "noise_amp"
        print("+ analog_noise_source_x_0.amp = noise_amp")

# ── 3. update epy_block_0 source + io_cache ───────────────────────────────────
for b in blocks:
    if b["name"] == "epy_block_0":
        b["parameters"]["_source_code"] = EPY_BLOCK_0_CODE
        b["states"]["_io_cache"] = (
            "('ZMQ TX Reference', 'blk', [('example_param', 'None')], "
            "[('0', 'byte', 1)], [('0', 'byte', 1)], '', [])"
        )
        print("+ epy_block_0 source updated (int8, real TX bytes)")

# ── 4. update epy_block_0_0 source + io_cache ────────────────────────────────
for b in blocks:
    if b["name"] == "epy_block_0_0":
        b["parameters"]["_source_code"] = EPY_BLOCK_0_0_CODE
        b["states"]["_io_cache"] = (
            "('ZMQ Bridge', 'blk', [('example_param', 'None')], "
            "[('0', 'byte', 1)], [('0', 'byte', 1)], '', [])"
        )
        print("+ epy_block_0_0 source updated (int8, real BER)")

# ── 5. rewire connections ─────────────────────────────────────────────────────
old_conns = doc["connections"]

REMOVE = {
    # TX path: remove random_source→char_to_float_0 and float_to_complex_0→epy_block_0
    ("analog_random_source_x_0", "0", "blocks_char_to_float_0",         "0"),
    ("blocks_float_to_complex_0", "0", "epy_block_0",                   "0"),
    # RX path: remove decoder→char_to_float_1 and float_to_complex_1→epy_block_0_0
    ("digital_constellation_decoder_cb_0", "0", "blocks_char_to_float_1", "0"),
    ("blocks_float_to_complex_1", "0", "epy_block_0_0",                  "0"),
}

ADD = [
    # TX path: random_source→epy_block_0→char_to_float_0
    ["analog_random_source_x_0", "0", "epy_block_0",          "0"],
    ["epy_block_0",              "0", "blocks_char_to_float_0","0"],
    # RX path: decoder→epy_block_0_0→char_to_float_1
    ["digital_constellation_decoder_cb_0", "0", "epy_block_0_0",          "0"],
    ["epy_block_0_0",                      "0", "blocks_char_to_float_1", "0"],
]

new_conns = [c for c in old_conns if tuple(c) not in REMOVE]
removed = len(old_conns) - len(new_conns)
new_conns.extend(ADD)
print(f"+ connections: removed {removed}, added {len(ADD)}")

doc["connections"] = new_conns

# ── write ─────────────────────────────────────────────────────────────────────
with open(GRC, "w") as f:
    yaml.dump(doc, f, allow_unicode=True, sort_keys=False, width=120)

print("\nDone — Zapojenie.grc patched. Otvor v GRC a spusti.")
