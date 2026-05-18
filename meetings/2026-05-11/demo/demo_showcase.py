"""
Comprehensive Hopfield showcase — 9 scenarios, one animation.

3×3 grid. All panels run per-sweep in lockstep.
Scenarios cover: async-cyclic, async-random, sync, below/above capacity,
converge to target, converge to inverse, spurious attractor, 2-cycle.

Run:
    python demo_showcase.py
Saves: demo_showcase.gif
"""

import sys, argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import ListedColormap

sys.path.insert(0, str(Path(__file__).parents[3] / 'sim' / 'python'))
from hopfield_net import HopfieldNetwork, STORKEY, HEBBIAN, SYNC, ASYNC_CYCLIC, ASYNC_RANDOM

# ── 4×4 patterns (N=16) ───────────────────────────────────────────────────────
_RAW = {
    '0': [0,1,1,0, 1,0,0,1, 1,0,0,1, 0,1,1,0],
    '1': [0,1,1,0, 0,0,1,0, 0,0,1,0, 0,1,1,1],
    '7': [1,1,1,1, 0,0,0,1, 0,0,1,0, 0,1,0,0],
    'X': [1,0,0,1, 0,1,1,0, 0,1,1,0, 1,0,0,1],
    'L': [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,1,1,1],
}
def bipolar(bits): return np.array([1. if b else -1. for b in bits])

SIZE, N   = 4, 16
MAX_SWEEPS = 12   # run this many sweeps even after convergence (hold state)
INTERVAL_MS = 500

# ── helpers ───────────────────────────────────────────────────────────────────
def sync_step(W, s):
    s_new = np.sign(W @ s); s_new[s_new == 0] = s[s_new == 0]; return s_new

def is_2cycle(h):
    return (len(h) >= 3 and np.array_equal(h[-1], h[-3])
            and not np.array_equal(h[-1], h[-2]))

def find_2cycle_start(W, max_tries=5000, seed=0):
    rng = np.random.default_rng(seed)
    for _ in range(max_tries):
        s0 = rng.choice([-1., 1.], size=N).astype(float)
        hist = [s0.copy()]
        for _ in range(60):
            hist.append(sync_step(W, hist[-1]))
            if is_2cycle(hist): return s0, True
    return rng.choice([-1., 1.], size=N).astype(float), False

def run_scenario(rule, mode, keys, target_key, n_flips, seed,
                 random_start=False):
    pats   = np.array([bipolar(_RAW[k]) for k in keys])
    net    = HopfieldNetwork(N=N, rule=rule, update_mode=mode)
    net.train(pats)
    target = bipolar(_RAW[target_key])
    rng    = np.random.default_rng(seed)

    if random_start:
        s0, found = find_2cycle_start(net.W, seed=seed)
    else:
        s0 = target.copy()
        s0[rng.choice(N, size=min(n_flips, N), replace=False)] *= -1

    hist    = [s0.copy()]
    outcome = 'running'
    conv_sw = None
    s       = s0.copy()

    for sweep in range(MAX_SWEEPS):
        s_prev = s.copy()
        if mode == SYNC:
            s = sync_step(net.W, s)
        else:
            order = np.arange(N) if mode == ASYNC_CYCLIC else rng.permutation(N)
            for i in order:
                h = float(net.W[i] @ s)
                if h > 0: s[i] = 1.
                elif h < 0: s[i] = -1.
        hist.append(s.copy())

        if is_2cycle(hist) and outcome == 'running':
            outcome = '2-cycle'; conv_sw = sweep + 1
        if np.array_equal(s, s_prev) and outcome == 'running':
            ham    = int((s != target).sum())
            ham_i  = int((s != -target).sum())
            outcome = ('target ✓'  if ham == 0
                       else 'inverse ✓' if ham_i == 0
                       else f'spurious  Δ={ham}')
            conv_sw = sweep + 1

    # always run full MAX_SWEEPS (hold on last state for visual clarity)
    while len(hist) <= MAX_SWEEPS:
        hist.append(hist[-1])

    if outcome == 'running':
        ham    = int((hist[-1] != target).sum())
        ham_i  = int((hist[-1] != -target).sum())
        outcome = ('target ✓' if ham == 0 else
                   'inverse ✓' if ham_i == 0 else f'spurious  Δ={ham}')

    return dict(hist=hist, target=target, net=net,
                outcome=outcome, conv_sw=conv_sw, M=len(keys))

# ── 9 scenarios ───────────────────────────────────────────────────────────────
#  (title_top, title_bot, rule, mode, keys, target_key, n_flips, seed, random_start)
SCENARIOS = [
    # ── row 0: async-cyclic baseline ─────────────────────────────────────────
    ("Async-cyclic", "Below cap · low noise → target ✓",
     STORKEY, ASYNC_CYCLIC, ['0','1'], '0', 3, 10, False),

    ("Async-cyclic", "Below cap · 70% noise → inverse ✓",
     STORKEY, ASYNC_CYCLIC, ['0','1'], '0', 11, 21, False),

    ("Async-random", "Below cap · low noise → target ✓",
     STORKEY, ASYNC_RANDOM, ['0','1'], '0', 3, 30, False),

    # ── row 1: capacity effects ───────────────────────────────────────────────
    ("Hebbian", "Below cap · low noise → target ✓",
     HEBBIAN,  ASYNC_CYCLIC, ['0','1'], '0', 3, 40, False),

    ("Storkey", "Above cap (M=3) · spurious ✗",
     STORKEY, ASYNC_CYCLIC, ['0','1','7'], '0', 3, 50, False),

    ("Hebbian", "Above cap (M=4) · spurious ✗",
     HEBBIAN,  ASYNC_CYCLIC, ['0','1','7','X'], '0', 6, 1, False),

    # ── row 2: sync comparison ────────────────────────────────────────────────
    ("Sync", "Below cap · converges ✓",
     STORKEY, SYNC, ['0','1'], '0', 3, 70, False),

    ("Sync", "Above cap · spurious ✗",
     STORKEY, SYNC, ['0','1','7','X','L'], '0', 4, 80, False),

    ("Sync", "Above cap · random start → 2-cycle ✗",
     STORKEY, SYNC, ['0','1','7','X'], '0', 4, 90, True),   # random_start
]

print("Running scenarios…")
results = []
for (tt, tb, rule, mode, keys, tkey, nf, seed, rs) in SCENARIOS:
    r = run_scenario(rule, mode, keys, tkey, nf, seed, random_start=rs)
    r['tt'] = tt; r['tb'] = tb
    print(f"  {tt:14s} M={r['M']} nf={nf:2d} → {r['outcome']}")
    results.append(r)

n_frames = MAX_SWEEPS + 1   # frame 0 = initial, frames 1..MAX = sweeps

# ── colours ───────────────────────────────────────────────────────────────────
BG, AX_BG    = '#0d0d0d', '#111111'
CMAP         = ListedColormap([AX_BG, '#ffffff'])
COL_TARGET   = '#27ae60'
COL_INVERSE  = '#f39c12'
COL_SPURIOUS = '#e74c3c'
COL_CYCLE    = '#9b59b6'

def ocol(oc):
    if 'target'  in oc: return COL_TARGET
    if 'inverse' in oc: return COL_INVERSE
    if '2-cycle' in oc: return COL_CYCLE
    return COL_SPURIOUS

def img(s): return ((s+1)/2).reshape(SIZE, SIZE)

# ── figure ────────────────────────────────────────────────────────────────────
N_ROWS, N_COLS = 3, 3
fig = plt.figure(figsize=(12, 10.5), facecolor=BG)
fig.patch.set_facecolor(BG)
fig.suptitle(
    'Hopfield Network — Behaviour Across Configurations  (N=16, 4×4)',
    color='white', fontsize=13, fontweight='bold', y=0.985)

gs = gridspec.GridSpec(N_ROWS, N_COLS, figure=fig,
                       hspace=0.65, wspace=0.32,
                       top=0.94, bottom=0.08, left=0.06, right=0.97)

panels = []
for idx, res in enumerate(results):
    row, col = divmod(idx, N_COLS)
    ax = fig.add_subplot(gs[row, col])
    ax.set_facecolor(AX_BG)
    ax.set_xticks([]); ax.set_yticks([])

    col_now = ocol(res['outcome'])
    for sp in ax.spines.values():
        sp.set_color(col_now); sp.set_linewidth(2.5)

    im = ax.imshow(img(res['hist'][0]), cmap=CMAP, vmin=0, vmax=1,
                   interpolation='nearest', animated=True)

    load = res['M'] / N
    ax.set_title(f"{res['tt']}  ·  M={res['M']}, load={load:.2f}\n{res['tb']}",
                 fontsize=7.5, color='#cccccc', pad=4, linespacing=1.5)

    badge = ax.text(0.5, -0.04, res['outcome'],
                    transform=ax.transAxes, ha='center', va='top',
                    fontsize=8, color=col_now, fontweight='bold')

    sweep_lbl = ax.text(0.03, 0.97, 't=0',
                        transform=ax.transAxes, ha='left', va='top',
                        fontsize=7.5, color='#f39c12', fontweight='bold')

    panels.append(dict(ax=ax, im=im, badge=badge, sweep=sweep_lbl, res=res))

# legend
leg = [
    plt.Line2D([0],[0], color=COL_TARGET,   lw=3, label='Converged → target ✓'),
    plt.Line2D([0],[0], color=COL_INVERSE,  lw=3, label='Converged → inverse (−ξ) ✓'),
    plt.Line2D([0],[0], color=COL_SPURIOUS, lw=3, label='Spurious attractor ✗'),
    plt.Line2D([0],[0], color=COL_CYCLE,    lw=3, label='2-cycle oscillation ✗'),
]
fig.legend(handles=leg, loc='lower center', ncol=4, fontsize=8.5,
           frameon=True, facecolor='#1a1a1a', edgecolor='#555555',
           labelcolor='white', bbox_to_anchor=(0.5, 0.01))

# ── animation ─────────────────────────────────────────────────────────────────
def update(frame):
    artists = []
    for p in panels:
        t     = min(frame, len(p['res']['hist']) - 1)
        state = p['res']['hist'][t]
        p['im'].set_data(img(state))
        p['sweep'].set_text(f't={t}')

        # flash border on convergence sweep
        conv = p['res']['conv_sw']
        if conv is not None and t >= conv:
            c = ocol(p['res']['outcome'])
            for sp in p['ax'].spines.values():
                lw = 3.5 if (frame % 2 == 0 and t == conv) else 2.5
                sp.set_linewidth(lw)

        artists += [p['im'], p['badge'], p['sweep']]
    return artists

anim = FuncAnimation(fig, update, frames=n_frames,
                     interval=INTERVAL_MS, blit=False,
                     repeat=True, repeat_delay=1800)

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--nosave', action='store_true')
args, _ = parser.parse_known_args()

if not args.nosave:
    out = Path(__file__).parent / 'demo_showcase.gif'
    print(f"Saving {n_frames} frames → {out.name} …")
    anim.save(str(out), writer=PillowWriter(fps=1000 // INTERVAL_MS), dpi=120)
    print("  Done.")

plt.show()
