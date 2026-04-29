import numpy as np
from gnuradio import gr
import zmq
import time

PACKET_SIZE = 336
MAGIC = (0xDE, 0xAD)   # synchrónizačné bajty na začiatku každého paketu

class blk(gr.sync_block):
    """
    Zdroj štruktúrovaných paketov (336 B):
      [0xDE, 0xAD, seq_hi, seq_lo, ...332 náhodných bajtov...]
    Seq číslo (uint16) + timestamp posiela aj cez ZMQ PUSH → port 5557.
    """
    def __init__(self, example_param=None):
        gr.sync_block.__init__(self,
            name="Seq Source",
            in_sig=None,
            out_sig=[np.uint8])
        self._seq     = 0
        self._pos     = 0
        self._pkt     = self._make_packet()
        self._running = False
        self._ctx     = None
        self._push    = None

    def _make_packet(self):
        pkt    = np.random.randint(0, 256, PACKET_SIZE, dtype=np.uint8)
        pkt[0] = MAGIC[0]
        pkt[1] = MAGIC[1]
        pkt[2] = (self._seq >> 8) & 0xFF
        pkt[3] = self._seq & 0xFF
        return pkt

    def _start_zmq(self):
        self._running = True
        self._ctx  = zmq.Context()
        self._push = self._ctx.socket(zmq.PUSH)
        self._push.bind("tcp://127.0.0.1:5557")
        print("[GRC] Seq Source start")

    def work(self, input_items, output_items):
        if not self._running:
            self._start_zmq()
        out = output_items[0]
        n   = len(out)
        i   = 0
        while i < n:
            chunk = min(n - i, PACKET_SIZE - self._pos)
            out[i:i+chunk] = self._pkt[self._pos:self._pos+chunk]
            self._pos += chunk
            i += chunk
            if self._pos >= PACKET_SIZE:
                try:
                    self._push.send_json(
                        {"seq": self._seq, "ts": time.time()},
                        flags=zmq.NOBLOCK
                    )
                except Exception:
                    pass
                self._seq = (self._seq + 1) % 65536
                self._pos = 0
                self._pkt = self._make_packet()
        return n

    def stop(self):
        self._running = False
        if self._push: self._push.close()
        if self._ctx:  self._ctx.term()
        print("[GRC] Seq Source stop")
        return True
