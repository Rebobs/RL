#!/usr/bin/env python3
import numpy as np
from gnuradio import gr, analog, blocks
import zmq
import json
import threading
import time

class ZMQBridge(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(self,
            name="ZMQ Bridge",
            in_sig=[np.complex64],
            out_sig=[np.complex64])
        self._power   = 0.5
        self._running = True
        ctx = zmq.Context()
        self._rep = ctx.socket(zmq.REP)
        self._rep.bind("tcp://127.0.0.1:5555")
        self._rep.setsockopt(zmq.RCVTIMEO, 100)
        self._pub = ctx.socket(zmq.PUB)
        self._pub.bind("tcp://127.0.0.1:5556")
        threading.Thread(target=self._ctrl_loop,    daemon=True).start()
        threading.Thread(target=self._metrics_loop, daemon=True).start()
        print("[GRC] ZMQ Bridge štart — ctrl=5555 metrics=5556")

    def _ctrl_loop(self):
        while self._running:
            try:
                data = json.loads(self._rep.recv().decode())
                print(f"[GRC] akcia: {data}")
                self._rep.send(b'ok')
            except zmq.Again:
                pass
            except Exception as e:
                print(f"[GRC] ctrl err: {e}")
                try: self._rep.send(b'err')
                except: pass

    def _metrics_loop(self):
        time.sleep(1.0)
        while self._running:
            try:
                pwr  = float(self._power)
                snr  = float(np.clip(10 * np.log10(pwr + 1e-9) + 25, 0.0, 30.0))
                self._pub.send_json({
                    "snr":        snr,
                    "power":      float(np.clip(pwr, 0.0, 1.0)),
                    "cfo":        0.0,
                    "throughput": float(np.clip(snr * 0.5,         0.0, 100.0)),
                    "rtt":        50.0,
                    "loss":       float(np.clip(0.5 - snr * 0.018, 0.0, 1.0)),
                    "bler":       float(np.clip(0.3 - snr * 0.009, 0.0, 1.0))
                })
            except Exception as e:
                print(f"[GRC] metrics err: {e}")
            time.sleep(0.05)

    def work(self, input_items, output_items):
        self._power        = float(np.mean(np.abs(input_items[0]) ** 2))
        output_items[0][:] = input_items[0]
        return len(output_items[0])

    def stop(self):
        self._running = False
        return True


class FlowGraph(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self)

        samp_rate = 32000

        sig   = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 1000, 1.0)
        noise = analog.noise_source_c(analog.GR_GAUSSIAN, 0.1)
        add   = blocks.add_cc()
        thr   = blocks.throttle(gr.sizeof_gr_complex, samp_rate)
        self.bridge = ZMQBridge()
        sink  = blocks.null_sink(gr.sizeof_gr_complex)

        self.connect(sig,   (add, 0))
        self.connect(noise, (add, 1))
        self.connect(add,   thr)
        self.connect(thr,   self.bridge)
        self.connect(self.bridge, sink)


if __name__ == "__main__":
    print("[GRC] Spúšťam flowgraph...")
    fg = FlowGraph()
    fg.start()
    print("[GRC] Beží. Ctrl+C pre zastavenie.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    fg.stop()
    fg.wait()
    print("[GRC] Zastavený.")