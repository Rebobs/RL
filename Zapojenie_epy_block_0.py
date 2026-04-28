import numpy as np
from gnuradio import gr
import zmq
import threading
import time

class blk(gr.sync_block):
    def __init__(self, example_param=None):
        gr.sync_block.__init__(self,
            name="ZMQ TX Reference",
            in_sig=[np.complex64],
            out_sig=[np.complex64])
        self._power   = 0.5
        self._running = False
        self._ctx     = None
        self._push    = None
        self._seq     = 0

    def _start_zmq(self):
        self._running = True
        self._ctx  = zmq.Context()
        self._push = self._ctx.socket(zmq.PUSH)
        self._push.bind("tcp://127.0.0.1:5557")
        threading.Thread(target=self._probe_loop, daemon=True).start()
        print("[GRC] ZMQ TX Reference start")

    def _probe_loop(self):
        time.sleep(1.0)
        while self._running:
            try:
                self._push.send_json({
                    "seq":      self._seq,
                    "ts":       time.time(),
                    "tx_power": float(self._power),
                })
                self._seq += 1
            except Exception as e:
                print(f"[GRC] tx ref err: {e}")
            time.sleep(0.05)

    def work(self, input_items, output_items):
        if not self._running:
            self._start_zmq()
        output_items[0][:] = input_items[0]
        self._power = float(np.mean(np.abs(input_items[0]) ** 2))
        return len(output_items[0])

    def stop(self):
        self._running = False
        if self._push: self._push.close()
        if self._ctx:  self._ctx.term()
        print("[GRC] ZMQ TX Reference stop")
        return True
