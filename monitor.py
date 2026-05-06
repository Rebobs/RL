#!/usr/bin/env python3
"""
Live monitor — číta metriky z GNU Radio (ZMQ PUB port 5556)
a zobrazuje real-time BER krivku v logaritmickej mierke.

Spusti v samostatnom terminály:  python monitor.py
"""

import zmq
import json
import collections
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

WINDOW = 1000

snr_buf   = collections.deque([0.0] * WINDOW, maxlen=WINDOW)
ber_buf   = collections.deque([0.5] * WINDOW, maxlen=WINDOW)
reward_buf= collections.deque([0.0] * WINDOW, maxlen=WINDOW)

ctx = zmq.Context()
sub = ctx.socket(zmq.SUB)
sub.connect("tcp://127.0.0.1:5556")
sub.setsockopt(zmq.SUBSCRIBE, b'')
sub.setsockopt(zmq.RCVTIMEO, 200)

fig, axes = plt.subplots(3, 1, figsize=(9, 10))
fig.suptitle("RL Agent — BER Monitor", fontsize=14, fontweight='bold')
fig.patch.set_facecolor('#1e1e1e')
for ax in axes:
    ax.set_facecolor('#2d2d2d')
    ax.tick_params(colors='white')
    ax.title.set_color('white')
    for spine in ax.spines.values():
        spine.set_edgecolor('#555')

ax_snr, ax_ber, ax_rew = axes

def _make(ax, color, title, ylim, ref=None, logy=False):
    ax.set_xlim(0, WINDOW)
    if logy:
        ax.set_yscale('log')
        ax.set_ylim(ylim)
    else:
        ax.set_ylim(*ylim)
    ax.set_title(title, color='white', fontsize=10)
    ax.grid(True, color='#444', linewidth=0.5)
    line, = ax.plot([], [], color=color, linewidth=1.5)
    if ref is not None:
        ax.axhline(ref, color='white', linewidth=0.8, linestyle='--', alpha=0.4)
    return line

ln_snr = _make(ax_snr, '#00bcd4', 'SNR (dB)',  (-10, 42), ref=20)
ln_ber = _make(ax_ber, '#f44336', 'BER (log)', (1e-7, 1), logy=True)
ln_rew = _make(ax_rew, '#e040fb', 'Reward',    (-1, 7),   ref=0)

xs = list(range(WINDOW))
status_text = fig.text(0.01, 0.01, '', color='#aaa', fontsize=9)
step_counter = [0]

def update(_frame):
    msg = None
    try:
        while True:
            raw = sub.recv()
            try:
                msg = json.loads(raw.decode())
            except Exception:
                pass
    except zmq.Again:
        pass

    if msg is None:
        return ln_snr, ln_ber, ln_rew, ln_noise

    step_counter[0] += 1
    snr   = msg.get('snr',          20.0)
    ber   = msg.get('ber',           0.5)
    sigma = msg.get('noise_sigma',   0.5)
    ber   = max(ber, 1e-7)
    rew   = float(-np.log10(ber))

    snr_buf.append(snr)
    ber_buf.append(ber)
    reward_buf.append(rew)

    ln_snr.set_data(xs, list(snr_buf))
    ln_ber.set_data(xs, list(ber_buf))
    ln_rew.set_data(xs, list(reward_buf))

    status_text.set_text(
        f"Metriky #{step_counter[0]:5d} | "
        f"SNR={snr:5.1f}dB | BER={ber:.2e} | reward={rew:.2f}"
    )

    return ln_snr, ln_ber, ln_rew

ani = animation.FuncAnimation(fig, update, interval=100, blit=False, cache_frame_data=False)

plt.tight_layout(rect=[0, 0.03, 1, 0.96])
print("Monitor spustený — čakám na dáta z GNU Radia (port 5556)...")
print("Zavrieť: zatvor okno alebo Ctrl+C")
try:
    plt.show()
except KeyboardInterrupt:
    pass
finally:
    sub.close()
    ctx.term()
