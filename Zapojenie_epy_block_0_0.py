import numpy as np
from gnuradio import gr
import zmq
import json
import threading
import time

_gain  = 3.0    # štart s degradovaným stavom — agent to musí opraviť
_phase = 0.0
_eq_mu = 0.001

BASE_SNR_DB = 20.0   # maximálne dosiahnuteľné SNR pri gain=1.0

class blk(gr.sync_block):
    def __init__(self, example_param=None):
        gr.sync_block.__init__(self,
            name="ZMQ Bridge",
            in_sig=[np.complex64],
            out_sig=[np.complex64])
        self._power   = 0.5
        self._running = False
        self._ctx     = None
        self._rep     = None
        self._pub     = None

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
        print(f"[GRC] ZMQ Bridge štart — počiatočný gain={_gain}")

    def _ctrl_loop(self):
        global _gain, _phase, _eq_mu
        while self._running:
            try:
                raw  = self._rep.recv()
                data = json.loads(raw.decode('utf-8'))
                _gain  = float(np.clip(_gain  + data.get('gain',  0.0), 0.01, 5.0))
                _phase = float(np.clip(_phase + data.get('phase', 0.0), -3.14, 3.14))
                _eq_mu = float(np.clip(_eq_mu + data.get('eq_mu', 0.0), 0.0001, 0.1))
                print(f"[GRC] gain={_gain:.3f} phase={_phase:.4f}")
                self._rep.send(b'ok')
            except zmq.Again:
                pass
            except Exception as e:
                print(f"[GRC] ctrl err: {e}")
                try:    self._rep.send(b'err')
                except: pass

    def _metrics_loop(self):
        time.sleep(1.0)
        while self._running:
            try:
                # Jasná kvadratická SNR krivka centrovaná na gain=1.0
                # gain=1.0 → SNR=20dB (optimum)
                # gain=1.5 → SNR=16dB
                # gain=2.0 → SNR= 5dB
                # gain=3.0 → SNR= 0dB (štartovný stav — veľmi zlý)
                # gain=0.5 → SNR=16dB
                # gain=0.3 → SNR=11dB
                snr_penalty = (_gain - 1.0) ** 2 * 15.0
                snr = float(np.clip(
                    BASE_SNR_DB - snr_penalty + np.random.uniform(-0.3, 0.3),
                    0.0, 25.0
                ))

                pwr  = float(self._power)
                rtt  = float(np.clip(50.0 + (20.0 - snr) * 8 + np.random.uniform(-2, 2), 20.0, 500.0))
                loss = float(np.clip(0.4 - snr * 0.018 + np.random.uniform(-0.005, 0.005), 0.0, 1.0))
                bler = float(np.clip(0.25 - snr * 0.009 + np.random.uniform(-0.003, 0.003), 0.0, 1.0))
                tput = float(np.clip(snr * 0.5 + np.random.uniform(-0.3, 0.3), 0.0, 100.0))

                self._pub.send_json({
                    "snr":        snr,
                    "power":      float(np.clip(pwr, 0.0, 10.0)),
                    "cfo":        0.0,
                    "throughput": tput,
                    "rtt":        rtt,
                    "loss":       loss,
                    "bler":       bler,
                    "gain":       _gain
                })
            except Exception as e:
                print(f"[GRC] metrics err: {e}")
            time.sleep(0.05)

    def work(self, input_items, output_items):
        if not self._running:
            self._start_zmq()
        rot = np.exp(1j * _phase).astype(np.complex64)
        output_items[0][:] = (input_items[0] * np.float32(_gain) * rot)
        self._power = float(np.mean(np.abs(output_items[0]) ** 2))
        return len(output_items[0])

    def stop(self):
        self._running = False
        if self._rep: self._rep.close()
        if self._pub: self._pub.close()
        if self._ctx: self._ctx.term()
        print("[GRC] ZMQ Bridge stop")
        return True
