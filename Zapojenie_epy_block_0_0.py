import numpy as np
from gnuradio import gr
import zmq
import json
import threading
import time
import collections

_gain  = 3.0
_phase = 0.0
_eq_mu = 0.001

BASE_SNR_DB  = 20.0
PACKET_SIZE  = 336
EVAL_DELAY   = 2.0
LOSS_WINDOW  = 80
MAGIC        = (0xDE, 0xAD)


def _snr_from_gain(gain):
    snr_db = max(0.0, BASE_SNR_DB - (gain - 1.0) ** 2 * 15.0)
    return float(snr_db)


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

        # Sync state machine for magic-byte packet alignment.
        # States: 0=searching 0xDE, 1=found 0xDE waiting 0xAD, 2=reading body
        self._sync_state = 0
        self._sym_buf    = np.zeros(4, dtype=np.int32)
        self._sym_pos    = 0
        self._byte_buf   = np.zeros(PACKET_SIZE, dtype=np.int32)
        self._byte_pos   = 0

        self._pending_tx  = {}
        self._rx_seqs     = set()
        self._loss_window = collections.deque(maxlen=LOSS_WINDOW)
        self._real_loss   = 0.4

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
                print(f"[GRC] gain={_gain:.3f}")
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
                self._read_tx_seqs()
                self._evaluate_loss()

                snr_db = _snr_from_gain(_gain)
                snr  = float(snr_db + np.random.uniform(-0.3, 0.3))
                pwr  = float(self._power)
                tput = float(np.clip(snr * 0.5 + np.random.uniform(-0.3, 0.3), 0.0, 100.0))
                bler = float(np.clip(self._real_loss * 0.6, 0.0, 1.0))

                self._pub.send_json({
                    "snr":        snr,
                    "power":      float(np.clip(pwr, 0.0, 10.0)),
                    "cfo":        0.0,
                    "throughput": tput,
                    "rtt":        0.0,
                    "loss":       self._real_loss,
                    "bler":       bler,
                    "gain":       _gain,
                })
            except Exception as e:
                print(f"[GRC] metrics err: {e}")
            time.sleep(0.05)

    def _read_tx_seqs(self):
        try:
            while True:
                msg = self._ref_sock.recv_json()
                self._pending_tx[msg["seq"]] = msg["ts"]
        except zmq.Again:
            pass
        except Exception as e:
            print(f"[GRC] tx seq err: {e}")

    def _evaluate_loss(self):
        now     = time.time()
        expired = [seq for seq, ts in self._pending_tx.items()
                   if now - ts > EVAL_DELAY]
        for seq in expired:
            self._pending_tx.pop(seq)
            received = seq in self._rx_seqs
            self._loss_window.append(received)
            self._rx_seqs.discard(seq)

        if self._loss_window:
            self._real_loss = float(1.0 - sum(self._loss_window) / len(self._loss_window))

    def _process_byte(self, byte_val):
        if self._sync_state == 0:
            if byte_val == MAGIC[0]:
                self._sync_state = 1
        elif self._sync_state == 1:
            if byte_val == MAGIC[1]:
                self._byte_buf[0] = MAGIC[0]
                self._byte_buf[1] = MAGIC[1]
                self._byte_pos    = 2
                self._sync_state  = 2
            else:
                self._sync_state = 0
                if byte_val == MAGIC[0]:
                    self._sync_state = 1
        else:
            self._byte_buf[self._byte_pos] = byte_val
            self._byte_pos += 1
            if self._byte_pos == PACKET_SIZE:
                rx_seq = (int(self._byte_buf[2]) << 8) | int(self._byte_buf[3])
                self._rx_seqs.add(rx_seq)
                self._byte_pos   = 0
                self._sync_state = 0

    def work(self, input_items, output_items):
        if not self._running:
            self._start_zmq()

        rot = np.exp(1j * _phase).astype(np.complex64)
        output_items[0][:] = input_items[0] * np.float32(_gain) * rot
        self._power = float(np.mean(np.abs(output_items[0]) ** 2))

        syms = np.round(input_items[0].real).astype(np.int32) & 0x3
        for sym in syms:
            self._sym_buf[self._sym_pos] = sym
            self._sym_pos += 1
            if self._sym_pos == 4:
                byte_val = (int(self._sym_buf[0]) << 6 |
                            int(self._sym_buf[1]) << 4 |
                            int(self._sym_buf[2]) << 2 |
                            int(self._sym_buf[3])) & 0xFF
                self._sym_pos = 0
                self._process_byte(byte_val)

        return len(output_items[0])

    def stop(self):
        self._running = False
        if self._rep:      self._rep.close()
        if self._pub:      self._pub.close()
        if self._ref_sock: self._ref_sock.close()
        if self._ctx:      self._ctx.term()
        print("[GRC] ZMQ Bridge stop")
        return True
