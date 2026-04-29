#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RL Agent pre GNU Radio — absolútne gain akcie.

Namiesto inkrementálnych (+0.1 / -0.1) agent PRIAMO nastaví gain
na jednu z 9 pevných hodnôt. Žiadny drift, žiadne katastrofálne zážitky.
"""

import zmq, json, time, random, os, sys, logging, threading
import numpy as np
from stable_baselines3 import DQN
from stable_baselines3.common.logger import configure as sb3_configure
from gymnasium import spaces
import gymnasium as gym

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
MODEL_PATH  = os.path.join(BASE_DIR, "saved_models")
LOG_PATH    = os.path.join(BASE_DIR, "debug.log")
RL_LOG_PATH = os.path.join(BASE_DIR, "rl_decisions.log")

# ── logging ──────────────────────────────────────────────────────────────────
def setup_logging(debug_cfg):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout),
        ]
    )
    rl = logging.getLogger("rl_decisions")
    rl.setLevel(logging.DEBUG)
    rl.propagate = False
    if debug_cfg.get("rl_decisions_log"):
        fh = logging.FileHandler(RL_LOG_PATH, mode='w', encoding='utf-8')
        fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        rl.addHandler(fh)
    return rl

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

# ── monitor ───────────────────────────────────────────────────────────────────
def build_monitor(monitor_cfg, metrics_address):
    """
    Vráti (fig, animate_fn) pre hlavné vlákno, alebo None ak GUI nedostupné.
    Agent beží v samostatnom vlákne, matplotlib v hlavnom.
    """
    try:
        import collections
        import matplotlib
        for backend in ('Qt5Agg', 'Qt6Agg', 'GTK4Agg', 'GTK3Agg', 'WXAgg'):
            try:
                matplotlib.use(backend)
                import matplotlib.pyplot as plt
                import matplotlib.animation as animation
                break
            except Exception:
                continue
        else:
            logging.warning("Monitor: žiadny GUI backend, vypínam")
            return None, None
    except ImportError as e:
        logging.warning(f"Monitor: chýba matplotlib ({e}), vypínam")
        return None, None

    import collections
    WINDOW   = monitor_cfg.get("window", 200)
    INTERVAL = monitor_cfg.get("update_interval_ms", 100)

    bufs = {k: collections.deque([0.0] * WINDOW, maxlen=WINDOW)
            for k in ("snr", "tput", "loss", "reward", "gain")}

    ctx = zmq.Context()
    sub = ctx.socket(zmq.SUB)
    sub.connect(metrics_address)
    sub.setsockopt(zmq.SUBSCRIBE, b'')
    sub.setsockopt(zmq.RCVTIMEO, 0)   # neblokuje

    def _calc_reward(snr, tput, loss, bler, gain):
        sat = max(0.0, gain - 1.8) ** 2 * 8.0
        low = max(0.0, 0.8 - gain) ** 2 * 20.0
        return 1.5*tput - 15.0*loss - 5.0*bler - sat - low

    fig, axes = plt.subplots(3, 2, figsize=(13, 8))
    fig.suptitle("RL Agent — Live Monitor", fontsize=14, fontweight='bold')
    fig.patch.set_facecolor('#1e1e1e')
    for ax in axes.flat:
        ax.set_facecolor('#2d2d2d')
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_edgecolor('#555')

    specs = [
        ("snr",    axes[0,0], '#00bcd4', 'SNR (dB)',    (0, 25),   20),
        ("tput",   axes[0,1], '#4caf50', 'Throughput',  (0, 12),   10),
        ("loss",   axes[1,0], '#f44336', 'Packet Loss', (0, 1.05), None),
        ("gain",   axes[1,1], '#ffeb3b', 'Gain',        (0, 3.5),  1.0),
        ("reward", axes[2,0], '#e040fb', 'Reward',      (-25, 15), 0),
    ]
    axes[2,1].set_visible(False)
    lines = {}
    xs = list(range(WINDOW))
    for key, ax, color, title, ylim, ref in specs:
        ax.set_xlim(0, WINDOW); ax.set_ylim(*ylim)
        ax.set_title(title, color='white', fontsize=10)
        ax.grid(True, color='#444', linewidth=0.5)
        lines[key], = ax.plot([], [], color=color, linewidth=1.5)
        if ref is not None:
            ax.axhline(ref, color='white', linewidth=0.8, linestyle='--', alpha=0.4)

    status = fig.text(0.01, 0.01, '', color='#aaa', fontsize=9)
    counter = [0]

    def update(_):
        msg = None
        try:
            while True:
                raw = sub.recv()
                try: msg = json.loads(raw.decode())
                except: pass
        except zmq.Again:
            pass
        if msg is None:
            return list(lines.values())

        counter[0] += 1
        snr  = msg.get('snr', 0.0);   tput = msg.get('throughput', 0.0)
        loss = msg.get('loss', 0.4);   bler = msg.get('bler', 0.25)
        pwr  = msg.get('power', 0.5)
        gain = msg.get('gain', float(np.clip(np.sqrt(max(pwr, 1e-6) / 0.5), 0.01, 5.0)))
        rew  = _calc_reward(snr, tput, loss, bler, gain)

        bufs["snr"].append(snr);    bufs["tput"].append(tput)
        bufs["loss"].append(loss);  bufs["gain"].append(gain)
        bufs["reward"].append(rew)
        for key, line in lines.items():
            line.set_data(xs, list(bufs[key]))
        status.set_text(
            f"#{counter[0]:5d} | SNR={snr:5.1f}dB | tput={tput:4.1f} | "
            f"loss={loss:.3f} | gain={gain:.2f} | R={rew:6.2f}"
        )
        return list(lines.values())

    ani = animation.FuncAnimation(fig, update, interval=INTERVAL,
                                  blit=False, cache_frame_data=False)
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    logging.info("Monitor pripravený")
    return fig, ani   # ani musí zostať nažive (garbage collector)

# ── environment ───────────────────────────────────────────────────────────────
class RadioEnvironment(gym.Env):
    """
    9 absolútnych gain akcií: agent povie 'chcem gain=X'.
    Agent pošle do GNU Radia delta=(target - current).
    Žiadny drift, žiadna kumulatívna chyba.

    Gain targets: [0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 1.8, 2.0]
    """
    GAIN_TARGETS = [0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]
    ACTION_NAMES = [f"gain={g:.1f}" for g in GAIN_TARGETS]

    def __init__(self, config):
        super().__init__()
        self.config = config
        # obs: [snr, power, cfo, throughput, rtt, loss, bler]
        self.observation_space = spaces.Box(
            low =np.array([0.0,  0.0, -0.01,  0.0,   0.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([30.0, 10.0,  0.01, 100.0, 1000.0, 1.0, 1.0], dtype=np.float32),
        )
        self.action_space = spaces.Discrete(len(self.GAIN_TARGETS))

        self._gain  = 3.0   # GNU Radio štartuje s gain=3.0 — musí sedieť
        self._phase = 0.0

        self.ctrl_sock    = None
        self.metrics_sock = None
        self._zmq_ctx     = None
        self.connected    = False

    # ── ZMQ ──
    def init_sockets(self):
        self._zmq_ctx = zmq.Context()

        self.ctrl_sock = self._zmq_ctx.socket(zmq.REQ)
        self.ctrl_sock.setsockopt(zmq.SNDTIMEO, 1000)
        self.ctrl_sock.setsockopt(zmq.RCVTIMEO, 1000)
        self.ctrl_sock.connect(self.config["communication"]["control_address"])

        self.metrics_sock = self._zmq_ctx.socket(zmq.SUB)
        self.metrics_sock.connect(self.config["communication"]["metrics_address"])
        self.metrics_sock.setsockopt(zmq.SUBSCRIBE, b'')
        self.metrics_sock.setsockopt(zmq.RCVTIMEO, 2000)

        time.sleep(0.5)
        self.connected = True
        logging.info(f"ZMQ OK — ctrl={self.config['communication']['control_address']}")

    def _reconnect_ctrl(self):
        try: self.ctrl_sock.close()
        except: pass
        self.ctrl_sock = self._zmq_ctx.socket(zmq.REQ)
        self.ctrl_sock.setsockopt(zmq.SNDTIMEO, 1000)
        self.ctrl_sock.setsockopt(zmq.RCVTIMEO, 1000)
        self.ctrl_sock.connect(self.config["communication"]["control_address"])

    # ── metriky ──
    def get_state(self):
        default = np.array([15.0, 0.5, 0.0, 10.0, 50.0, 0.01, 0.02], dtype=np.float32)
        if not self.connected:
            return default
        try:
            if self.metrics_sock.poll(300) == 0:
                logging.warning("Metriky: timeout, predvolené")
                return default
            raw = self.metrics_sock.recv()
            # vyčerpaj frontu — chceme najnovšiu správu
            while self.metrics_sock.poll(0) > 0:
                raw = self.metrics_sock.recv()
            msg = json.loads(raw.decode('utf-8'))
            return np.array([
                msg.get("snr",        15.0),
                msg.get("power",       0.5),
                msg.get("cfo",         0.0),
                msg.get("throughput", 10.0),
                msg.get("rtt",         0.0),
                msg.get("loss",       0.01),
                msg.get("bler",       0.02),
            ], dtype=np.float32)
        except zmq.Again:
            logging.warning("Metriky recv timeout")
            return default
        except Exception as e:
            logging.error(f"Metriky chyba: {e}")
            return default

    # ── akcia ──
    def send_action(self, action_idx):
        target = self.GAIN_TARGETS[action_idx]
        delta  = round(target - self._gain, 6)   # koľko treba pridať/ubrať

        if not self.connected:
            self._gain = target
            return True

        if abs(delta) < 1e-5:   # gain je už na cieľovej hodnote, nič neposielaj
            return True

        payload = json.dumps({"gain": delta, "phase": 0.0, "eq_mu": 0.0}).encode()
        try:
            self.ctrl_sock.send(payload)
            self.ctrl_sock.recv()
            self._gain = target   # aktualizuj až po potvrdení
            return True
        except Exception as e:
            logging.error(f"send_action zlyhalo: {e}")
            self._reconnect_ctrl()
            return False

    # ── reward ──
    def calculate_reward(self, state):
        tput = float(state[3])
        loss = float(state[5])
        bler = float(state[6])
        r = 1.5 * tput - 15.0 * loss - 5.0 * bler
        # Kvadratická gain penalizácia — rovnaká ako v monitore (sat+low).
        # Pri novom loss=0 aj pre gain=1.5 je toto hlavný gradient
        # medzi dobrými a suboptimálnymi gainmi.
        sat = max(0.0, self._gain - 1.8) ** 2 * 8.0
        low = max(0.0, 0.8 - self._gain) ** 2 * 20.0
        r -= sat + low
        return float(r)

    # ── gym ──
    def step(self, action_idx):
        ok = self.send_action(action_idx)
        if not ok:
            return self.get_state(), -5.0, False, False, {"send_failed": True}
        time.sleep(0.15)
        state  = self.get_state()
        reward = self.calculate_reward(state)
        return state, reward, False, False, {}

    def reset(self, seed=None, options=None):
        # Nezasahujeme do gainu — štartujeme v zlom stave (gain=3.0)
        # aby agent videl reálne zlepšenie
        time.sleep(0.3)
        return self.get_state(), {}

    def close(self):
        if self.ctrl_sock:    self.ctrl_sock.close()
        if self.metrics_sock: self.metrics_sock.close()
        if self._zmq_ctx:     self._zmq_ctx.term()


# ── agent ─────────────────────────────────────────────────────────────────────
class RLAgent:
    EPS_START = 0.9
    EPS_END   = 0.01    # takmer žiadna explorácia po konvergencii
    EPS_DECAY = 0.995   # rýchlejší decay

    def __init__(self):
        self.cfg    = load_config()
        self.debug  = self.cfg.get("debug", {})
        self.tcfg   = self.cfg.get("training", {})
        self.rl_log = setup_logging(self.debug)
        self.env    = RadioEnvironment(self.cfg)
        self.model  = None

    def _create_model(self):
        return DQN(
            "MlpPolicy", self.env, verbose=0,
            learning_rate          = self.tcfg.get("learning_rate", 3e-4),
            buffer_size            = self.tcfg.get("buffer_size",   10000),
            learning_starts        = self.tcfg.get("learning_starts", 100),
            batch_size             = self.tcfg.get("batch_size", 64),
            max_grad_norm          = 10.0,
            target_update_interval = 100,
            gamma                  = 0.95,
            exploration_fraction   = 0.3,
            exploration_final_eps  = self.EPS_END,
        )

    def setup(self):
        self.env.init_sockets()
        os.makedirs(MODEL_PATH, exist_ok=True)

        zips = sorted(
            [f for f in os.listdir(MODEL_PATH) if f.endswith(".zip")],
            key=lambda x: os.path.getmtime(os.path.join(MODEL_PATH, x))
        )
        if zips:
            path = os.path.join(MODEL_PATH, zips[-1])
            try:
                self.model = DQN.load(path)
                self.model.set_env(self.env)
                self.model.set_logger(sb3_configure(None, []))
                self.model.exploration_rate = 0.3
                logging.info(f"Model načítaný: {zips[-1]}")
            except Exception as e:
                logging.warning(f"Načítanie modelu zlyhalo ({e}), vytváram nový")
                self.model = self._create_model()
                self.model.set_logger(sb3_configure(None, []))
        else:
            self.model = self._create_model()
            self.model.set_logger(sb3_configure(None, []))
            logging.info("Nový model vytvorený")

    def _push(self, obs, next_obs, action, reward):
        self.model.replay_buffer.add(
            np.array(obs).reshape(1, -1),
            np.array(next_obs).reshape(1, -1),
            np.array([[action]]),
            np.array([[reward]]),
            np.array([[0.0]]),   # done = False vždy
            [{}]
        )
        self.model.num_timesteps += 1

    def _train(self):
        if self.model.replay_buffer.size() >= self.model.learning_starts:
            self.model.train(gradient_steps=1, batch_size=self.model.batch_size)
            try:
                return float(self.model.logger.name_to_value.get("train/loss", float("nan")))
            except:
                return float("nan")
        return float("nan")

    def _save(self, step):
        ts   = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(MODEL_PATH, f"rl_model_{ts}_step{step}.zip")
        self.model.save(path)
        logging.info(f"Model uložený: {os.path.basename(path)}")

    def run(self):
        LOG_EVERY   = self.tcfg.get("log_interval_steps", 20)
        SAVE_EVERY  = self.tcfg.get("save_interval_steps", 500)
        TRAIN_EVERY = 2   # train každé 2 kroky (absolútne akcie sú pomalšie na učenie)

        epsilon    = self.EPS_START
        step       = 0
        t0         = time.time()

        buf_r, buf_snr, buf_tput, buf_loss, buf_gl = [], [], [], [], []
        act_counts = [0] * self.env.action_space.n
        recent_rewards = []   # posledných 50 pre adaptívny epsilon

        obs, _ = self.env.reset()
        logging.info("=== Štart tréningu — absolútne gain akcie ===")
        logging.info(f"Gain targets: {self.env.GAIN_TARGETS}")
        logging.info(f"Akcie: {self.env.ACTION_NAMES}")

        try:
            while True:
                # Adaptívny epsilon: ak je reward stabilne vysoký, prestaň explorovať
                if len(recent_rewards) >= 50:
                    avg_r = np.mean(recent_rewards[-50:])
                    if avg_r > 8.0:       # blízko optima (max ~11)
                        epsilon = self.EPS_END
                    elif avg_r > 5.0:
                        epsilon = max(self.EPS_END, epsilon * 0.99)
                    else:
                        epsilon = max(self.EPS_END, epsilon * self.EPS_DECAY)
                else:
                    epsilon = max(self.EPS_END, epsilon * self.EPS_DECAY)

                # ε-greedy výber
                if random.random() < epsilon:
                    action = self.env.action_space.sample()
                    src = "rand"
                else:
                    action = int(self.model.predict(obs, deterministic=True)[0])
                    src = "model"

                next_obs, reward, _, _, info = self.env.step(action)
                step += 1

                self._push(obs, next_obs, action, reward)
                if step % TRAIN_EVERY == 0:
                    gl = self._train()
                    if not np.isnan(gl):
                        buf_gl.append(gl)

                # RL decisions log — každý krok
                if self.debug.get("rl_decisions_log"):
                    self.rl_log.debug(
                        f"k={step:5d} {src:5s} | akcia={self.env.ACTION_NAMES[action]:10s} | "
                        f"gain={self.env._gain:.2f} | "
                        f"SNR={next_obs[0]:5.1f}dB tput={next_obs[3]:5.1f} "
                        f"loss={next_obs[5]:.3f} | "
                        f"R={reward:7.2f} | eps={epsilon:.3f}"
                    )

                buf_r.append(reward); buf_snr.append(next_obs[0])
                buf_tput.append(next_obs[3]); buf_loss.append(next_obs[5])
                act_counts[action] += 1
                recent_rewards.append(reward)
                if len(recent_rewards) > 100:
                    recent_rewards.pop(0)

                if step % LOG_EVERY == 0:
                    gl_s    = f"{np.mean(buf_gl):.3f}" if buf_gl else "N/A"
                    dom     = int(np.argmax(act_counts))
                    total_acts = max(sum(act_counts), 1)
                    avg_gain = sum(
                        self.env.GAIN_TARGETS[i] * act_counts[i]
                        for i in range(self.env.action_space.n)
                    ) / total_acts
                    logging.info(
                        f"[{step:5d}] t={time.time()-t0:.0f}s | "
                        f"reward={np.mean(buf_r):6.2f} | "
                        f"SNR={np.mean(buf_snr):5.1f}dB | tput={np.mean(buf_tput):4.1f} | "
                        f"loss={np.mean(buf_loss):.3f} | "
                        f"gain={avg_gain:.2f} | "
                        f"eps={epsilon:.3f} buf={self.model.replay_buffer.size()} | "
                        f"grad_loss={gl_s} | "
                        f"dom={self.env.ACTION_NAMES[dom]} | counts={act_counts}"
                    )
                    buf_r.clear(); buf_snr.clear(); buf_tput.clear()
                    buf_loss.clear(); buf_gl.clear()
                    act_counts = [0] * self.env.action_space.n

                if step % SAVE_EVERY == 0:
                    self._save(step)

                obs = next_obs

        except KeyboardInterrupt:
            logging.info("Ukončovanie...")
        finally:
            self._save(step)
            self.env.close()
            logging.info(f"Hotovo — {step} krokov, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    agent = RLAgent()
    agent.setup()
    agent.run()
