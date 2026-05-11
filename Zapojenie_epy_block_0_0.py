import numpy as np
from gnuradio import gr
import zmq
import json
import threading
import time
import collections
import gc

BER_WINDOW = 20

class blk(gr.sync_block):
    def __init__(self, example_param=None):
        gr.sync_block.__init__(self,
            name="ZMQ Bridge",
            in_sig=[np.int8, np.int8],
            out_sig=[np.int8])
        self._running       = False
        self._ctx           = None
        self._rep           = None
        self._pub           = None
        self._noise_sigma   = 0.0
        self._win_errors    = 0
        self._win_total     = 0
        self._ber_window    = collections.deque(maxlen=BER_WINDOW)
        self._lock          = threading.Lock()
        self._top_block     = None

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
                self._top_block.set_signal_gain(sigma)
                win = getattr(self._top_block, "_signal_gain_win", None)
                if win is not None:
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, lambda v=sigma: win.setValue(v))
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
        threading.Thread(target=self._ctrl_loop,    daemon=True).start()
        threading.Thread(target=self._metrics_loop, daemon=True).start()
        print("[GRC] Bridge ready — real BER (2-input sync)")

    def _ctrl_loop(self):
        while self._running:
            try:
                raw  = self._rep.recv()
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

    def _metrics_loop(self):
        time.sleep(1.0)
        while self._running:
            try:
                with self._lock:
                    bw    = list(self._ber_window)
                    sigma = self._noise_sigma
                if bw:
                    ber_avg = float(np.clip(np.mean(bw), 1e-7, 1.0))
                    snr_db  = float(-20.0 * np.log10(max(sigma, 1e-6))) if sigma > 1e-6 else 40.0
                    snr_db  = float(np.clip(snr_db, -10.0, 40.0))
                    self._pub.send_json({"snr": snr_db, "ber": ber_avg, "noise_sigma": sigma})
            except Exception as e:
                print(f"[GRC] metrics err: {e}")
            time.sleep(0.2)

    def work(self, input_items, output_items):
        if not self._running:
            self._start_zmq()

        tx = input_items[0]
        rx = input_items[1]
        n  = len(tx)

        xor    = np.bitwise_xor(tx, rx).astype(np.uint8)
        errors = int(np.unpackbits(xor).sum())

        with self._lock:
            self._win_errors += errors
            self._win_total  += n * 8
            if self._win_total >= 200000:
                ber = self._win_errors / self._win_total
                self._ber_window.append(max(ber, 1e-7))
                self._win_errors = 0
                self._win_total  = 0
            bw = list(self._ber_window)

        output_items[0][:] = rx
        return n

    def stop(self):
        self._running = False
        if self._rep: self._rep.close()
        if self._pub: self._pub.close()
        if self._ctx: self._ctx.term()
        return True
