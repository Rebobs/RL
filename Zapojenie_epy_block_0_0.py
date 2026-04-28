import numpy as np
from gnuradio import gr
import zmq
import json
import threading
import time
import math
import random
import collections

_gain  = 3.0
_phase = 0.0
_eq_mu = 0.001

BASE_SNR_DB  = 20.0
PACKET_BITS  = 336 * 8
PROBE_WINDOW = 60


def _per_from_gain(gain):
    snr_penalty = (gain - 1.0) ** 2 * 15.0
    snr_db      = max(0.0, BASE_SNR_DB - snr_penalty)
    snr_linear  = 10.0 ** (snr_db / 10.0)
    ber = 0.5 * math.erfc(math.sqrt(max(snr_linear / 2.0, 0.0)))
    per = 1.0 - (1.0 - ber) ** PACKET_BITS
    return float(np.clip(per, 0.0, 1.0)), float(snr_db)


class blk(gr.sync_block):
    def __init__(self, example_param=None):
        gr.sync_block.__init__(self,
            name="ZMQ Bridge",
            in_sig=[np.complex64],
            out_sig=[np.complex64])
        self._power    = 0.5
        self._running  = False
        self._ctx      = None
        self._rep      = None
        self._pub      = None
        self._ref_sock = None

        self._last_seq   = None
        self._rx_window  = collections.deque(maxlen=PROBE_WINDOW)
        self._rtt_window = collections.deque(maxlen=5)

    def _start_zmq(self):
        self._running = True
        self._ctx = zmq.Context()

        self._rep = self._ctx.socket(zmq.REP)
        self._rep.setsockopt(zmq.RCVTIMEO, 100)
        self._rep.bind("tcp://127.0.0.1:5555")

        self._pub = self._ctx.socket(zmq.PUB)
        self._pub.bind("tcp://127.0.0.1:5556")

        self._ref_sock = self._ctx.socket(zmq.PULL)
        self._ref_sock.connect("tcp://127.0.0.1:5557")
        self._ref_sock.setsockopt(zmq.RCVTIMEO, 0)

        threading.Thread(target=self._ctrl_loop,    daemon=True).start()
        threading.Thread(target=self._metrics_loop, daemon=True).start()
        print(f"[GRC] ZMQ Bridge start — gain={_gain}")

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
                self._process_probes()

                per, snr_db = _per_from_gain(_gain)
                snr  = float(snr_db + np.random.uniform(-0.3, 0.3))
                pwr  = float(self._power)
                bler = float(np.clip(per * 0.6 + np.random.uniform(-0.005, 0.005), 0.0, 1.0))
                tput = float(np.clip(snr * 0.5 + np.random.uniform(-0.3, 0.3), 0.0, 100.0))

                loss = self._real_loss()
                rtt  = self._real_rtt(loss)

                self._pub.send_json({
                    "snr":        snr,
                    "power":      float(np.clip(pwr, 0.0, 10.0)),
                    "cfo":        0.0,
                    "throughput": tput,
                    "rtt":        rtt,
                    "loss":       loss,
                    "bler":       bler,
                    "gain":       _gain,
                })
            except Exception as e:
                print(f"[GRC] metrics err: {e}")
            time.sleep(0.05)

    def _process_probes(self):
        per, _ = _per_from_gain(_gain)
        try:
            while True:
                raw   = self._ref_sock.recv()
                probe = json.loads(raw.decode())
                seq   = probe["seq"]
                ts    = probe["ts"]

                if self._last_seq is not None:
                    gap = seq - self._last_seq - 1
                    for _ in range(min(gap, 10)):
                        self._rx_window.append(False)
                self._last_seq = seq

                received = random.random() > per
                self._rx_window.append(received)

                loss_now   = self._real_loss()
                retx       = loss_now / max(1.0 - loss_now, 0.01)
                queuing_ms = retx * 30.0
                rtt_sample = float(np.clip(30.0 + queuing_ms, 20.0, 500.0))
                self._rtt_window.append(rtt_sample)

        except zmq.Again:
            pass
        except Exception as e:
            print(f"[GRC] probe recv err: {e}")

    def _real_loss(self):
        if not self._rx_window:
            return 0.4
        return float(1.0 - sum(self._rx_window) / len(self._rx_window))

    def _real_rtt(self, loss):
        if not self._rtt_window:
            retx = loss / max(1.0 - loss, 0.01)
            return float(np.clip(20.0 + retx * 30.0, 20.0, 500.0))
        return float(np.mean(self._rtt_window))

    def work(self, input_items, output_items):
        if not self._running:
            self._start_zmq()
        rot = np.exp(1j * _phase).astype(np.complex64)
        output_items[0][:] = input_items[0] * np.float32(_gain) * rot
        self._power = float(np.mean(np.abs(output_items[0]) ** 2))
        return len(output_items[0])

    def stop(self):
        self._running = False
        if self._rep:      self._rep.close()
        if self._pub:      self._pub.close()
        if self._ref_sock: self._ref_sock.close()
        if self._ctx:      self._ctx.term()
        print("[GRC] ZMQ Bridge stop")
        return True
