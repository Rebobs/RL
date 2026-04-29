#!/usr/bin/env python3
"""
Live monitor — číta metriky z GNU Radio (ZMQ PUB port 5556)
a zobrazuje real-time graf SNR, Throughput a Reward.

Spusti v samostatnom terminály:  python monitor.py
"""

import zmq
import json
import time
import collections
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

WINDOW = 200   # koľko posledných bodov zobraziť

# Kruhovýbuffer pre každú metriku
snr_buf   = collections.deque([0.0] * WINDOW, maxlen=WINDOW)
tput_buf  = collections.deque([0.0] * WINDOW, maxlen=WINDOW)
loss_buf  = collections.deque([0.0] * WINDOW, maxlen=WINDOW)
reward_buf= collections.deque([0.0] * WINDOW, maxlen=WINDOW)
gain_buf  = collections.deque([1.0] * WINDOW, maxlen=WINDOW)

last_gain  = [3.0]   # sledujeme gain z debug logu (odhadujeme z power)
last_reward = [0.0]

def calc_reward(snr, tput, loss, rtt, bler, gain):
    sat  = max(0.0, gain - 1.8) ** 2 * 8.0
    low  = max(0.0, 0.8 - gain) ** 2 * 20.0
    return 1.5*tput - 15.0*loss - 0.05*rtt - 5.0*bler - sat - low

ctx  = zmq.Context()
sub  = ctx.socket(zmq.SUB)
sub.connect("tcp://127.0.0.1:5556")
sub.setsockopt(zmq.SUBSCRIBE, b'')
sub.setsockopt(zmq.RCVTIMEO, 200)

# --- figure setup ---
fig, axes = plt.subplots(3, 2, figsize=(13, 8))
fig.suptitle("RL Agent — Live Monitor", fontsize=14, fontweight='bold')
fig.patch.set_facecolor('#1e1e1e')
for ax in axes.flat:
    ax.set_facecolor('#2d2d2d')
    ax.tick_params(colors='white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.title.set_color('white')
    for spine in ax.spines.values():
        spine.set_edgecolor('#555')

ax_snr, ax_tput, ax_loss, ax_rtt, ax_reward, ax_gain = axes.flat
ax_rtt.set_visible(False)

def make_line(ax, color, ylabel, title, ylim=None):
    line, = ax.plot([], [], color=color, linewidth=1.5)
    ax.set_xlim(0, WINDOW)
    if ylim:
        ax.set_ylim(*ylim)
    ax.set_ylabel(ylabel, color='white')
    ax.set_title(title, color='white', fontsize=10)
    ax.grid(True, color='#444', linewidth=0.5)
    return line

ln_snr    = make_line(ax_snr,    '#00bcd4', 'dB',   'SNR',        (0, 25))
ln_tput   = make_line(ax_tput,   '#4caf50', 'Mbps', 'Throughput', (0, 12))
ln_loss   = make_line(ax_loss,   '#f44336', '',     'Packet Loss',(0, 0.45))
ln_reward = make_line(ax_reward, '#e040fb', '',     'Reward',     (-25, 15))
ln_gain   = make_line(ax_gain,   '#ffeb3b', '',     'Gain (agent)',(0, 3.5))

# Referenčné čiary
for ax, val in [(ax_snr, 20), (ax_tput, 10)]:
    ax.axhline(val, color='white', linewidth=0.8, linestyle='--', alpha=0.4)
ax_gain.axhline(1.0, color='white', linewidth=0.8, linestyle='--', alpha=0.4)
ax_reward.axhline(0, color='white', linewidth=0.8, linestyle='--', alpha=0.4)

xs = list(range(WINDOW))
status_text = fig.text(0.01, 0.01, '', color='#aaa', fontsize=9)

step_counter = [0]

def update(_frame):
    # Vyčerpaj všetky dostupné správy, vezmi poslednú
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
        return ln_snr, ln_tput, ln_loss, ln_reward, ln_gain

    step_counter[0] += 1
    snr  = msg.get('snr',        0.0)
    tput = msg.get('throughput', 0.0)
    loss = msg.get('loss',       0.4)
    rtt  = msg.get('rtt',       500.0)
    bler = msg.get('bler',       0.25)
    pwr  = msg.get('power',      0.5)

    # Odhadni gain z power (power = gain^2 * 0.5 pre cos sigál s amp=1)
    gain_est = float(np.sqrt(max(pwr, 1e-6) / 0.5))
    gain_est = float(np.clip(gain_est, 0.01, 5.0))
    last_gain[0] = gain_est

    reward = calc_reward(snr, tput, loss, rtt, bler, gain_est)
    last_reward[0] = reward

    snr_buf.append(snr)
    tput_buf.append(tput)
    loss_buf.append(loss)
    reward_buf.append(reward)
    gain_buf.append(gain_est)

    ln_snr.set_data(xs, list(snr_buf))
    ln_tput.set_data(xs, list(tput_buf))
    ln_loss.set_data(xs, list(loss_buf))
    ln_reward.set_data(xs, list(reward_buf))
    ln_gain.set_data(xs, list(gain_buf))

    status_text.set_text(
        f"Metriky #{step_counter[0]:5d} | "
        f"SNR={snr:5.1f}dB | tput={tput:4.1f} | loss={loss:.3f} | "
        f"gain≈{gain_est:.2f} | reward={reward:6.2f}"
    )

    return ln_snr, ln_tput, ln_loss, ln_reward, ln_gain

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
