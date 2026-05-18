"""
Pseudo-inverse vs Storkey vs Hebbian — capacity comparison demo  (N=16, 4×4)

Two accuracy metrics vs M:
  • Exact fixed-point rate (0 noise) — the theoretical guarantee
  • Noisy recall rate (2-bit, ~12 % flip) — practical basin-of-attraction

Bottom panel: at M=DEMO_M, side-by-side recalled patterns for each rule.

Run:
    python demo_pseudoinverse.py
Saves: demo_pseudoinverse.png
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.gridspec import GridSpec

sys.path.insert(0, str(Path(__file__).parents[3] / 'sim' / 'python'))
from hopfield_net import (HopfieldNetwork,
                          HEBBIAN, STORKEY, PSEUDOINVERSE, ASYNC_CYCLIC)

# ── config ────────────────────────────────────────────────────────────────────
N         = 16
SIZE      = 4
N_FLIPS   = 2     # ~12% noise for noisy-recall curve
N_TRIALS  = 150   # pattern sets per (rule, M) point
DEMO_M    = 8     # M shown in the bottom visual
SEED      = 42

BG, AX_BG = '#0d0d0d', '#111111'
COL = {HEBBIAN: '#e74c3c', STORKEY: '#f39c12', PSEUDOINVERSE: '#27ae60'}
LABEL = {HEBBIAN:      'Hebbian      (cap ≈ 0.14N)',
         STORKEY:      'Storkey      (cap ≈ 0.22N)',
         PSEUDOINVERSE:'Pseudo-inv   (cap  =  N)'}
CMAP_PAT = ListedColormap([AX_BG, '#ffffff'])

_RAW = {
    '0': [0,1,1,0, 1,0,0,1, 1,0,0,1, 0,1,1,0],
    '1': [0,1,1,0, 0,0,1,0, 0,0,1,0, 0,1,1,1],
    '7': [1,1,1,1, 0,0,0,1, 0,0,1,0, 0,1,0,0],
    'X': [1,0,0,1, 0,1,1,0, 0,1,1,0, 1,0,0,1],
    'L': [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,1,1,1],
    'T': [1,1,1,1, 0,1,0,0, 0,1,0,0, 0,1,0,0],
    'H': [1,0,0,1, 1,1,1,1, 1,0,0,1, 1,0,0,1],
    'F': [1,1,1,1, 1,1,0,0, 1,1,0,0, 1,0,0,0],
}
DEMO_KEYS = ['0','1','7','X','L','T','H','F'][:DEMO_M]

def bipolar(bits): return np.array([1. if b else -1. for b in bits])
def img(s):        return ((s+1)/2).reshape(SIZE, SIZE)

rng = np.random.default_rng(SEED)
rules = [HEBBIAN, STORKEY, PSEUDOINVERSE]
Ms    = list(range(1, N))          # M = 1 … 15

# ── accuracy sweep ─────────────────────────────────────────────────────────────
print("Computing accuracy curves …")
fp_rate   = {r: [] for r in rules}   # fixed-point (0-noise) rate
noisy_rate = {r: [] for r in rules}  # noisy recall rate

for M in Ms:
    for rule in rules:
        fp_ok = noisy_ok = total = 0
        for _ in range(N_TRIALS):
            pats = rng.choice([-1., 1.], size=(M, N)).astype(float)
            net  = HopfieldNetwork(N=N, rule=rule, update_mode=ASYNC_CYCLIC)
            net.train(pats)
            for p in pats:
                total += 1
                # exact fixed-point test
                fp_ok += int(net.is_fixed_point(p))
                # noisy recall test
                s = p.copy()
                s[rng.choice(N, size=N_FLIPS, replace=False)] *= -1
                s_out, _, _ = net.run(s)
                noisy_ok += int(np.array_equal(s_out, p))
        fp_rate[rule].append(fp_ok / total)
        noisy_rate[rule].append(noisy_ok / total)
    print(f"  M={M:2d}  (fp) H={fp_rate[HEBBIAN][-1]:.2f} "
          f"S={fp_rate[STORKEY][-1]:.2f} PI={fp_rate[PSEUDOINVERSE][-1]:.2f}")

# ── demo patterns at DEMO_M ───────────────────────────────────────────────────
demo_pats = np.array([bipolar(_RAW[k]) for k in DEMO_KEYS])
demo_rng  = np.random.default_rng(7)
corrupted = []
for p in demo_pats:
    s = p.copy()
    s[demo_rng.choice(N, size=N_FLIPS, replace=False)] *= -1
    corrupted.append(s)

recalled = {}
for rule in rules:
    net = HopfieldNetwork(N=N, rule=rule, update_mode=ASYNC_CYCLIC)
    net.train(demo_pats)
    recalled[rule] = [net.run(s.copy())[0] for s in corrupted]

# ── figure ─────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 10.5), facecolor=BG)
fig.patch.set_facecolor(BG)

gs_outer = GridSpec(2, 1, figure=fig, hspace=0.44,
                    top=0.94, bottom=0.04, left=0.07, right=0.97,
                    height_ratios=[2.2, 1.5])

# ── TOP: two side-by-side accuracy plots ──────────────────────────────────────
gs_top = gs_outer[0].subgridspec(1, 2, wspace=0.28)

def style_ax(ax, title):
    ax.set_facecolor(AX_BG)
    for sp in ax.spines.values(): sp.set_color('#333333')
    ax.tick_params(colors='#777777', labelsize=8.5)
    ax.set_xlabel('M  (patterns stored)', color='#888888', fontsize=10)
    ax.set_xlim(0.5, N - 0.5)
    ax.set_ylim(-0.03, 1.10)
    ax.set_title(title, color='#cccccc', fontsize=10, pad=5)
    ax.grid(axis='y', color='#1e1e1e', lw=0.8)
    ax.axvline(DEMO_M, color='#555555', lw=1.2, ls=':', alpha=0.8)
    ax.text(DEMO_M + 0.12, 0.03, f'M={DEMO_M}', color='#666666', fontsize=7.5)

ax_fp = fig.add_subplot(gs_top[0])
style_ax(ax_fp, 'Exact fixed-point rate  (0-noise test)')
ax_fp.set_ylabel('Fraction of patterns that ARE\nexact fixed points', color='#888888', fontsize=9)
for rule in rules:
    ax_fp.plot(Ms, fp_rate[rule], '-o', color=COL[rule],
               lw=2.2, ms=5, label=LABEL[rule])
ax_fp.legend(fontsize=8.5, frameon=True, facecolor='#161616',
             edgecolor='#333333', labelcolor='white', loc='upper right')

ax_nr = fig.add_subplot(gs_top[1])
style_ax(ax_nr, f'Noisy recall rate  ({N_FLIPS}/{N} bits flipped, ~{100*N_FLIPS//N}% noise)')
ax_nr.set_ylabel('Fraction perfectly recalled', color='#888888', fontsize=9)
for rule in rules:
    ax_nr.plot(Ms, noisy_rate[rule], '-o', color=COL[rule],
               lw=2.2, ms=5, label=LABEL[rule])
# capacity markers
for rule, cap in [(HEBBIAN, 0.138*N), (STORKEY, 0.22*N)]:
    ax_nr.axvline(cap, color=COL[rule], lw=1.1, ls='--', alpha=0.4)
    ax_nr.text(cap + 0.1, 1.04, f'{cap:.1f}', color=COL[rule], fontsize=7)
ax_nr.legend(fontsize=8.5, frameon=True, facecolor='#161616',
             edgecolor='#333333', labelcolor='white', loc='upper right')

# ── BOTTOM: recalled pattern grids at DEMO_M ─────────────────────────────────
# Columns: Target | Corrupted | Hebbian | Storkey | Pseudo-inv
COLS = [
    ('Target',              '#888888', None),
    (f'Corrupted\n({N_FLIPS} flips)', '#888888', None),
    ('Hebbian',             COL[HEBBIAN],      HEBBIAN),
    ('Storkey',             COL[STORKEY],      STORKEY),
    ('Pseudo-inv',          COL[PSEUDOINVERSE], PSEUDOINVERSE),
]

gs_bot = gs_outer[1].subgridspec(1, len(COLS), wspace=0.07)

for ci, (col_label, cc, rule) in enumerate(COLS):
    gs_col = gs_bot[0, ci].subgridspec(DEMO_M, 1, hspace=0.06)
    for ri in range(DEMO_M):
        ax_c = fig.add_subplot(gs_col[ri])
        ax_c.set_facecolor(AX_BG)
        ax_c.set_xticks([]); ax_c.set_yticks([])

        if rule is None:
            state  = demo_pats[ri] if ci == 0 else corrupted[ri]
            border = '#444444'
        else:
            state  = recalled[rule][ri]
            ok     = np.array_equal(state, demo_pats[ri])
            border = COL[rule] if ok else '#cc1111'
            ax_c.text(0.96, 0.96, '✓' if ok else '✗',
                      transform=ax_c.transAxes, ha='right', va='top',
                      fontsize=7, color=COL[rule] if ok else '#ff4444',
                      fontweight='bold')

        ax_c.imshow(img(state), cmap=CMAP_PAT, vmin=0, vmax=1,
                    interpolation='nearest')
        for sp in ax_c.spines.values():
            sp.set_color(border); sp.set_linewidth(1.8)

        if ri == 0:
            ax_c.set_title(col_label, color=cc, fontsize=8.5,
                           fontweight='bold', pad=4, linespacing=1.4)
        if ci == 0:
            ax_c.set_ylabel(DEMO_KEYS[ri], color='#666666', fontsize=7.5,
                            rotation=0, labelpad=8, va='center')

# ── suptitle ──────────────────────────────────────────────────────────────────
fig.suptitle(
    f'Pseudo-inverse Learning Rule — Exact Fixed Points Guaranteed  (N={N})',
    color='white', fontsize=13.5, fontweight='bold', y=0.99)

out = Path(__file__).parent / 'demo_pseudoinverse.png'
print(f"\nSaving → {out.name} …")
plt.savefig(str(out), dpi=140, bbox_inches='tight', facecolor=BG)
print("  Done.")
plt.show()
