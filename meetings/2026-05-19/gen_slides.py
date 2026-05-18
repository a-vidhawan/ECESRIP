"""
Generate 3 slide PNGs for supervisor meeting 2026-05-19.
White background edition — suitable for light-theme slide decks.

  slide_1_energy_landscape.png  — 3-D energy wells + stored patterns
  slide_2_connections.png       — excitatory / inhibitory weight diagram
  slide_3_similarity.png        — correlated patterns → crosstalk

Run: python gen_slides.py
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.gridspec import GridSpec
from mpl_toolkits.mplot3d import Axes3D          # noqa: F401
from pathlib import Path

OUT = Path(__file__).parent

# ── palette (white-background friendly) ──────────────────────────────────────
BG      = '#ffffff'
AX_BG   = '#f7f8fc'
T_DARK  = '#111111'   # main body text
T_MID   = '#444444'   # secondary text
T_LIGHT = '#777777'   # caption / minor

GREEN  = '#1a7a40'
RED    = '#c0392b'
BLUE   = '#1565c0'
AMBER  = '#b36a00'
PINK   = '#c2185b'
CYAN   = '#0077aa'

# ── shared patterns (4×4, N=16) ──────────────────────────────────────────────
_RAW = {
    '0': [0,1,1,0, 1,0,0,1, 1,0,0,1, 0,1,1,0],
    '1': [0,1,1,0, 0,0,1,0, 0,0,1,0, 0,1,1,1],
    '7': [1,1,1,1, 0,0,0,1, 0,0,1,0, 0,1,0,0],
}
def bipolar(key): return np.array([1. if b else -1. for b in _RAW[key]])
def pat_img(key): return ((bipolar(key)+1)/2).reshape(4,4)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Energy Landscape  (white bg, refined)
# ═══════════════════════════════════════════════════════════════════════════════
fig1 = plt.figure(figsize=(16, 9), facecolor=BG)
fig1.patch.set_facecolor(BG)

# 3-D axes — upper portion; leaves a strip below for pattern thumbnails
ax3d = fig1.add_axes([0.02, 0.17, 0.96, 0.72], projection='3d')
ax3d.set_facecolor(BG)

x = np.linspace(-3.6, 3.6, 300)
y = np.linspace(-2.6, 2.6, 300)
X, Y = np.meshgrid(x, y)

wells = [(-2.0, 0.25, 1.45), (0.0, 0.65, 1.1), (2.1, -0.15, 1.55)]
sigma = 0.72
Z     = np.zeros_like(X)
for wx, wy, wd in wells:
    Z -= wd * np.exp(-((X-wx)**2 + (Y-wy)**2) / (2*sigma**2))
Z_norm = (Z - Z.min()) / (Z.max() - Z.min())

# Colormap: deep crimson/gold at basins → indigo/slate at ridges
# (reads well on white background — warmer at bottoms, cooler at peaks)
cmap_e = LinearSegmentedColormap.from_list('energy',
    ['#cc2200', '#e85a00', '#c97a00', '#6655aa', '#3333bb', '#1a1a88'])

ax3d.plot_surface(X, Y, Z, facecolors=cmap_e(Z_norm),
                  linewidth=0, antialiased=True, alpha=0.90, shade=False)
# Thin dark wireframe for structure
ax3d.plot_wireframe(X, Y, Z, color='#111111', lw=0.10, alpha=0.18,
                    rstride=14, cstride=14)

ax3d.set_axis_off()
ax3d.view_init(elev=28, azim=-55)
ax3d.set_box_aspect([7, 5, 3.8])

# Black dot + stem at each well bottom
for wx, wy, wd in wells:
    zbot = -wd
    ax3d.scatter([wx],[wy],[zbot], color='#111111', s=70, zorder=10)
    ax3d.plot([wx,wx],[wy,wy],[zbot, zbot-0.40], color='#333333',
              lw=1.3, alpha=0.9)

# Pattern thumbnails — placed in figure coordinates below the 3-D axes
# x-positions tuned to match the projected well bottoms
thumb_xf = [0.200, 0.450, 0.720]
CMAP_P   = ListedColormap(['#111111', '#eeeeee'])   # dark pixels on near-white

for key, xf in zip(['0','1','7'], thumb_xf):
    ax_t = fig1.add_axes([xf - 0.043, 0.01, 0.086, 0.145])
    ax_t.imshow(pat_img(key), cmap=CMAP_P, vmin=0, vmax=1,
                interpolation='nearest', aspect='equal')
    ax_t.set_xticks([]); ax_t.set_yticks([])
    for sp in ax_t.spines.values():
        sp.set_color('#333333'); sp.set_linewidth(2)
    ax_t.set_title(f"ξ  '{key}'", color=T_DARK, fontsize=10, pad=3,
                   fontweight='bold')

# Titles
fig1.text(0.5, 0.965, 'The Energy Landscape',
          ha='center', fontsize=30, color=T_DARK,
          fontweight='bold', fontfamily='serif')
fig1.text(0.5, 0.925,
          'Training sculpts wells — each stored pattern  ξ  becomes a local energy minimum\n'
          'A noisy query rolls downhill and settles at the nearest attractor',
          ha='center', fontsize=13.5, color=T_MID, linespacing=1.7)

fig1.savefig(OUT/'slide_1_energy_landscape.png', dpi=150,
             bbox_inches='tight', facecolor=BG)
plt.close(fig1)
print("slide_1_energy_landscape.png  ✓")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Excitatory / Inhibitory Connections  (white bg)
# ═══════════════════════════════════════════════════════════════════════════════

def neuron(ax, x, y, val, bright=True, r=0.30):
    if bright and val > 0:
        fc, ec, tc = '#1565c0', '#0d47a1', 'white'
    elif bright and val < 0:
        fc, ec, tc = '#e8eaf6', '#7986cb', '#3949ab'
    else:
        fc, ec, tc = '#eeeeee', '#aaaaaa', '#aaaaaa'
    c = plt.Circle((x, y), r, fc=fc, ec=ec, lw=2.5, zorder=5)
    ax.add_patch(c)
    ax.text(x, y, ('+1' if val > 0 else '−1'), ha='center', va='center',
            fontsize=14, color=tc, fontweight='bold', zorder=6)

def edge(ax, x1, y1, x2, y2, w_pos=True, lw=4.5, alpha=1.0):
    ax.plot([x1,x2],[y1,y2], color=(GREEN if w_pos else RED),
            lw=lw, alpha=alpha, solid_capstyle='round', zorder=4)

def outcome(ax, x, y, ok, label):
    col = GREEN if ok else RED
    ax.text(x, y, ('✓  ' if ok else '✗  ') + label,
            ha='center', fontsize=12, color=col, fontweight='bold')

fig2 = plt.figure(figsize=(16, 9), facecolor=BG)
fig2.patch.set_facecolor(BG)

def make_half(fig, left_frac, rule_label, rule_color, w_pos):
    ax = fig.add_axes([left_frac, 0.06, 0.46, 0.84])
    ax.set_facecolor(BG); ax.set_xlim(0,4); ax.set_ylim(0,7)
    ax.set_aspect('equal'); ax.axis('off')

    sign_str = '> 0' if w_pos else '< 0'
    ax.text(2.0, 6.65, rf'$w_{{ij}} {sign_str}$  —  {rule_label}',
            ha='center', fontsize=19, color=rule_color, fontweight='bold')

    agree_str   = 'agree' if w_pos else 'disagree'
    ax.text(2.0, 6.22, f'Neurons prefer to {agree_str}',
            ha='center', fontsize=12.5, color=T_MID)

    if w_pos:
        pairs = [(+1,+1,True), (-1,-1,True), (+1,-1,False)]
    else:
        pairs = [(+1,-1,True), (-1,+1,True), (+1,+1,False)]

    ys      = [5.2, 3.6, 2.0]
    labels  = ['low energy', 'low energy', 'high energy  →  unstable']
    ok_list = [True, True, False]

    for (v1,v2,b), y, lbl, ok in zip(pairs, ys, labels, ok_list):
        alpha = 1.0 if ok else 0.35
        edge(ax, 0.85, y, 3.15, y, w_pos=w_pos, alpha=alpha)
        neuron(ax, 0.85, y, v1, bright=(ok or v1==pairs[0][0]))
        neuron(ax, 3.15, y, v2, bright=ok)
        outcome(ax, 2.0, y-0.48, ok, lbl)

    ax.text(2.0, 0.88, r'$\Delta E = -w_{ij}\,s_i s_j$',
            ha='center', fontsize=16, color=T_DARK)
    if w_pos:
        note = r'Same sign: $s_i s_j > 0$,  $w_{ij}>0$  →  $\Delta E < 0$  (stable)'
    else:
        note = r'Opp. sign: $s_i s_j < 0$,  $w_{ij}<0$  →  $\Delta E < 0$  (stable)'
    ax.text(2.0, 0.44, note, ha='center', fontsize=11, color=T_LIGHT)
    return ax

make_half(fig2, 0.03, 'Excitatory', GREEN, w_pos=True)
make_half(fig2, 0.52, 'Inhibitory',  RED,  w_pos=False)

# Divider
fig2.add_artist(plt.Line2D([0.505,0.505],[0.06,0.94],
                transform=fig2.transFigure, color='#cccccc', lw=1.5))

fig2.suptitle('Weight Signs Encode Pattern Co-activation',
              fontsize=27, color=T_DARK, fontweight='bold',
              fontfamily='serif', y=0.975)
fig2.text(0.5, 0.01,
          r'Hebbian rule: $w_{ij} = \frac{1}{N}\sum_\mu \xi_i^\mu \xi_j^\mu$'
          r'  —  co-active neurons build excitatory links; opposing neurons build inhibitory links',
          ha='center', fontsize=11.5, color=T_LIGHT)

fig2.savefig(OUT/'slide_2_connections.png', dpi=150,
             bbox_inches='tight', facecolor=BG)
plt.close(fig2)
print("slide_2_connections.png  ✓")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — Pattern Similarity & Crosstalk  (white bg)
# ═══════════════════════════════════════════════════════════════════════════════
p1 = bipolar('1'); p7 = bipolar('7')
overlap    = float(p1 @ p7) / 16
shared_pct = (1 - int((p1 != p7).sum())/16)*100

fig3 = plt.figure(figsize=(16, 9), facecolor=BG)
fig3.patch.set_facecolor(BG)

gs = GridSpec(2, 3, figure=fig3,
              left=0.06, right=0.94, top=0.80, bottom=0.07,
              hspace=0.52, wspace=0.18, width_ratios=[1, 0.75, 1])

CMAP_C = ListedColormap(['#f0f0f0', BLUE])

# ── top row ───────────────────────────────────────────────────────────────────
for ax, key in [(fig3.add_subplot(gs[0,0]),'1'),
                (fig3.add_subplot(gs[0,2]),'7')]:
    ax.imshow(pat_img(key), cmap=CMAP_C, vmin=0, vmax=1, interpolation='nearest')
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_color(BLUE); sp.set_linewidth(2.5)
    ax.set_title(f"Pattern  ξ  '{key}'", fontsize=14, color=BLUE,
                 fontweight='bold', pad=5)

ax_m = fig3.add_subplot(gs[0,1])
ax_m.set_facecolor(BG); ax_m.axis('off')
ax_m.set_xlim(0,1); ax_m.set_ylim(0,1)
ax_m.annotate('', xy=(0.92,0.5), xytext=(0.08,0.5),
              arrowprops=dict(arrowstyle='<->', color=PINK, lw=2.8, mutation_scale=18))
ax_m.text(0.5, 0.74, f'{shared_pct:.0f}% shared bits',
          ha='center', fontsize=13, color=PINK, fontweight='bold')
ax_m.text(0.5, 0.50, r'$\xi^1\!\cdot\!\xi^7/N$', ha='center',
          fontsize=13, color=PINK)
ax_m.text(0.5, 0.28, f'$= {overlap:+.3f}$', ha='center',
          fontsize=15, color=PINK, fontweight='bold')
ax_m.text(0.5, 0.09, r'$\neq 0$  →  not orthogonal', ha='center',
          fontsize=11, color=T_LIGHT)

# ── bottom row ────────────────────────────────────────────────────────────────
panel_kw = dict(facecolor='#f4f6fb')
border_cols = [AMBER, '#555555', GREEN]

ax_tr  = fig3.add_subplot(gs[1,0])
ax_bth = fig3.add_subplot(gs[1,1])
ax_in  = fig3.add_subplot(gs[1,2])

for ax, bc in zip([ax_tr, ax_bth, ax_in], border_cols):
    ax.set(**panel_kw); ax.set_xlim(0,1); ax.set_ylim(0,1)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_color(bc); sp.set_linewidth(1.8)

ax_tr.set_title('Training  (learning rule)', fontsize=13,
                color=AMBER, fontweight='bold', pad=4)
train_lines = [
    (r"$W \;+\!=\; \frac{1}{N}\xi^7(\xi^7)^T$",   T_DARK, 13),
    ('', '', 0),
    (r"Because  $\xi^1\!\cdot\!\xi^7 \neq 0$:", T_MID, 11),
    ("the new outer product has",                  T_MID, 11),
    (r"projection onto $\xi^1$ in $W$",           T_MID, 11),
    ('', '', 0),
    ("Earlier memories are partially",             T_LIGHT, 11),
    ("overwritten — capacity drops",               T_LIGHT, 11),
]
y = 0.88
for line, col, sz in train_lines:
    if sz: ax_tr.text(0.07, y, line, fontsize=sz, color=col, va='top')
    y -= 0.113

ax_bth.set_title('Root cause', fontsize=13, color=T_DARK, fontweight='bold', pad=4)
ax_bth.text(0.5, 0.64,
            'Crosstalk is baked\ninto W at training\ntime and surfaces\nat recall',
            ha='center', va='center', fontsize=11.5,
            color=T_DARK, linespacing=1.8)
ax_bth.annotate('', xy=(0.5,0.17), xytext=(0.5,0.38),
                arrowprops=dict(arrowstyle='->', color=T_MID, lw=2))
ax_bth.text(0.5, 0.10, 'capacity  ↓', ha='center',
            fontsize=13, color=RED, fontweight='bold')

ax_in.set_title('Inference  (recall)', fontsize=13,
                color=GREEN, fontweight='bold', pad=4)
infer_lines = [
    (r"Query  $s \approx \xi^1$:",                              T_DARK, 13),
    ('', '', 0),
    (r"$h_i = W[i]\cdot s$",                                   T_DARK, 13),
    (r"$\approx \xi^1_i + (\xi^1\!\cdot\!\xi^7/N)\,\xi^7_i + \ldots$", T_DARK, 12),
    (r"$\quad\quad\quad\uparrow\,crosstalk$",                   RED,    11),
    ('', '', 0),
    ("Crosstalk pulls the state",                               T_LIGHT, 11),
    ("toward the wrong memory",                                 T_LIGHT, 11),
]
y = 0.88
for line, col, sz in infer_lines:
    if sz: ax_in.text(0.06, y, line, fontsize=sz, color=col, va='top')
    y -= 0.113

fig3.suptitle("Correlated Patterns Compete for Storage",
              fontsize=28, color=T_DARK, fontweight='bold',
              fontfamily='serif', y=0.965)
fig3.text(0.5, 0.875,
          "Non-orthogonal patterns create crosstalk in  W  —"
          " degrading capacity during training and accuracy during recall",
          ha='center', fontsize=13, color=T_MID)

fig3.savefig(OUT/'slide_3_similarity.png', dpi=150,
             bbox_inches='tight', facecolor=BG)
plt.close(fig3)
print("slide_3_similarity.png  ✓")

print("\nAll 3 slides saved to", OUT)
