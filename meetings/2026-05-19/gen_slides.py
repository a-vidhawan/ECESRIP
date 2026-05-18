"""
Generate 3 slide PNGs for supervisor meeting 2026-05-19.

  slide_1_energy_landscape.png  — 3-D energy wells + stored patterns
  slide_2_connections.png       — excitatory / inhibitory weight diagram
  slide_3_similarity.png        — correlated patterns → crosstalk (training & inference)

Run: python gen_slides.py
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.gridspec import GridSpec
from mpl_toolkits.mplot3d import Axes3D          # noqa: F401
from pathlib import Path

OUT = Path(__file__).parent
BG  = '#08080f'

# ── shared patterns (4×4, N=16) ──────────────────────────────────────────────
_RAW = {
    '0': [0,1,1,0, 1,0,0,1, 1,0,0,1, 0,1,1,0],
    '1': [0,1,1,0, 0,0,1,0, 0,0,1,0, 0,1,1,1],
    '7': [1,1,1,1, 0,0,0,1, 0,0,1,0, 0,1,0,0],
}
def bipolar(key): return np.array([1. if b else -1. for b in _RAW[key]])
def pat_img(key): return ((bipolar(key)+1)/2).reshape(4,4)

GOLD   = '#FFD700'
GREEN  = '#27ae60'
RED    = '#e74c3c'
CYAN   = '#00d4e8'
PINK   = '#ff2d78'

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Energy Landscape
# ═══════════════════════════════════════════════════════════════════════════════
fig1 = plt.figure(figsize=(16, 9), facecolor=BG)
fig1.patch.set_facecolor(BG)

# 3-D axes occupies upper 80% of the figure
ax3d = fig1.add_axes([0.0, 0.15, 1.0, 0.78], projection='3d')
ax3d.set_facecolor(BG)

x = np.linspace(-3.6, 3.6, 280)
y = np.linspace(-2.6, 2.6, 280)
X, Y = np.meshgrid(x, y)

# Three energy wells at these (wx, wy) positions, each with a depth
wells    = [(-2.0, 0.25, 1.45), (0.0, 0.65, 1.1), (2.1, -0.15, 1.55)]
sigma    = 0.72
Z        = np.zeros_like(X)
for wx, wy, wd in wells:
    Z -= wd * np.exp(-((X-wx)**2 + (Y-wy)**2) / (2*sigma**2))

Z_norm = (Z - Z.min()) / (Z.max() - Z.min())

# Warm-to-cool colormap: orange/red at basins → indigo at ridges
cmap_e = LinearSegmentedColormap.from_list('energy',
    ['#ff8c00', '#cc2200', '#991166', '#5500bb', '#2200cc'])

ax3d.plot_surface(X, Y, Z, facecolors=cmap_e(Z_norm),
                  linewidth=0, antialiased=True, alpha=0.87, shade=False)
ax3d.plot_wireframe(X, Y, Z, color='#ffffff', lw=0.11, alpha=0.14,
                   rstride=14, cstride=14)
ax3d.set_axis_off()
ax3d.view_init(elev=28, azim=-55)
ax3d.set_box_aspect([7, 5, 3.8])

# White dot + short stem at each well bottom
for wx, wy, wd in wells:
    zbot = -wd
    ax3d.scatter([wx],[wy],[zbot], color='white', s=70, zorder=10)
    ax3d.plot([wx,wx],[wy,wy],[zbot, zbot-0.38], 'w-', lw=1.3, alpha=0.85)

# Pattern thumbnails placed in figure coordinates below the 3-D axes.
# x positions manually tuned to match the projected well locations.
thumb_xf = [0.215, 0.455, 0.720]
thumb_wh  = (0.085, 0.13)
CMAP_P   = ListedColormap([BG, GOLD])

for key, xf in zip(['0','1','7'], thumb_xf):
    ax_t = fig1.add_axes([xf - thumb_wh[0]/2, 0.01, thumb_wh[0], thumb_wh[1]])
    ax_t.imshow(pat_img(key), cmap=CMAP_P, vmin=0, vmax=1,
                interpolation='nearest', aspect='equal')
    ax_t.set_xticks([]); ax_t.set_yticks([])
    for sp in ax_t.spines.values():
        sp.set_color(GOLD); sp.set_linewidth(2)
    ax_t.set_title(f"ξ'{key}'", color=GOLD, fontsize=10, pad=2, fontweight='bold')

# Titles
fig1.text(0.5, 0.965, 'The Energy Landscape',
          ha='center', fontsize=31, color='white',
          fontweight='bold', fontfamily='serif')
fig1.text(0.5, 0.925,
          'Training sculpts wells — each stored pattern ξ becomes a local energy minimum\n'
          'A noisy query follows the gradient downhill and lands at the nearest attractor',
          ha='center', fontsize=13.5, color='#bbbbbb', linespacing=1.7)

fig1.savefig(OUT/'slide_1_energy_landscape.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.close(fig1)
print("slide_1_energy_landscape.png  ✓")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Excitatory / Inhibitory Connections
# ═══════════════════════════════════════════════════════════════════════════════

def neuron(ax, x, y, val, bright=True, r=0.30):
    if bright and val > 0:
        fc, ec, tc = '#00d4e8', '#66ffff', 'white'
    elif bright and val < 0:
        fc, ec, tc = '#1c2f55', '#3a5a99', '#88aadd'
    else:  # faded mismatch
        fc, ec, tc = '#1a1a2e', '#333355', '#556688'
    c = plt.Circle((x, y), r, fc=fc, ec=ec, lw=2.5, zorder=5)
    ax.add_patch(c)
    ax.text(x, y, ('+1' if val > 0 else '−1'), ha='center', va='center',
            fontsize=14, color=tc, fontweight='bold', zorder=6)

def edge(ax, x1, y1, x2, y2, w_pos=True, lw=4.5, alpha=1.0):
    ax.plot([x1,x2],[y1,y2], color=(GREEN if w_pos else RED),
            lw=lw, alpha=alpha, solid_capstyle='round', zorder=4)

def outcome(ax, x, y, ok, label):
    sym  = '✓' if ok else '✗'
    col  = GREEN if ok else RED
    txt  = f'{sym}  {label}'
    ax.text(x, y, txt, ha='center', fontsize=12, color=col)

fig2 = plt.figure(figsize=(16, 9), facecolor=BG)
fig2.patch.set_facecolor(BG)

# Left panel: excitatory (w > 0)
axL = fig2.add_axes([0.03, 0.06, 0.46, 0.84])
axL.set_facecolor(BG); axL.set_xlim(0,4); axL.set_ylim(0,7)
axL.set_aspect('equal'); axL.axis('off')

axL.text(2.0, 6.65, r'$w_{ij} > 0$  —  Excitatory', ha='center', fontsize=19,
         color='#00e676', fontweight='bold')
axL.text(2.0, 6.22, 'Neurons prefer to agree', ha='center',
         fontsize=12.5, color='#888888')

# +1, +1  happy
edge(axL, 0.85, 5.2, 3.15, 5.2, w_pos=True)
neuron(axL, 0.85, 5.2, +1, bright=True)
neuron(axL, 3.15, 5.2, +1, bright=True)
outcome(axL, 2.0, 4.72, True, 'aligned — low energy')

# -1, -1  happy
edge(axL, 0.85, 3.6, 3.15, 3.6, w_pos=True)
neuron(axL, 0.85, 3.6, -1, bright=True)
neuron(axL, 3.15, 3.6, -1, bright=True)
outcome(axL, 2.0, 3.12, True, 'aligned — low energy')

# +1, -1  unhappy
edge(axL, 0.85, 2.0, 3.15, 2.0, w_pos=True, alpha=0.35)
neuron(axL, 0.85, 2.0, +1, bright=True)
neuron(axL, 3.15, 2.0, -1, bright=False)
outcome(axL, 2.0, 1.52, False, 'misaligned — high energy → unstable')

# Energy formula
axL.text(2.0, 0.85, r'$\Delta E = -w_{ij}\,s_i s_j$', ha='center',
         fontsize=16, color='#dddddd')
axL.text(2.0, 0.42, r'Same sign: $s_i s_j > 0$,  $w_{ij}>0$  $\Rightarrow$  $\Delta E < 0$  (stable)',
         ha='center', fontsize=11, color='#777777')

# Divider
fig2.add_artist(plt.Line2D([0.505, 0.505],[0.06, 0.94],
                transform=fig2.transFigure, color='#2a2a44', lw=1.8))

# Right panel: inhibitory (w < 0)
axR = fig2.add_axes([0.52, 0.06, 0.46, 0.84])
axR.set_facecolor(BG); axR.set_xlim(0,4); axR.set_ylim(0,7)
axR.set_aspect('equal'); axR.axis('off')

axR.text(2.0, 6.65, r'$w_{ij} < 0$  —  Inhibitory', ha='center', fontsize=19,
         color='#ff5252', fontweight='bold')
axR.text(2.0, 6.22, 'Neurons prefer to disagree', ha='center',
         fontsize=12.5, color='#888888')

# +1, -1  happy
edge(axR, 0.85, 5.2, 3.15, 5.2, w_pos=False)
neuron(axR, 0.85, 5.2, +1, bright=True)
neuron(axR, 3.15, 5.2, -1, bright=True)
outcome(axR, 2.0, 4.72, True, 'anti-aligned — low energy')

# -1, +1  happy
edge(axR, 0.85, 3.6, 3.15, 3.6, w_pos=False)
neuron(axR, 0.85, 3.6, -1, bright=True)
neuron(axR, 3.15, 3.6, +1, bright=True)
outcome(axR, 2.0, 3.12, True, 'anti-aligned — low energy')

# +1, +1  unhappy
edge(axR, 0.85, 2.0, 3.15, 2.0, w_pos=False, alpha=0.35)
neuron(axR, 0.85, 2.0, +1, bright=True)
neuron(axR, 3.15, 2.0, +1, bright=False)
outcome(axR, 2.0, 1.52, False, 'aligned — high energy → unstable')

axR.text(2.0, 0.85, r'$\Delta E = -w_{ij}\,s_i s_j$', ha='center',
         fontsize=16, color='#dddddd')
axR.text(2.0, 0.42, r'Opposite sign: $s_i s_j < 0$,  $w_{ij}<0$  $\Rightarrow$  $\Delta E < 0$  (stable)',
         ha='center', fontsize=11, color='#777777')

# Main title + Hebbian footnote
fig2.suptitle('Weight Signs Encode Pattern Co-activation',
              fontsize=27, color='white', fontweight='bold',
              fontfamily='serif', y=0.975)
fig2.text(0.5, 0.01,
          r'Hebbian rule: $w_{ij} = \frac{1}{N}\sum_\mu \xi_i^\mu \xi_j^\mu$  '
          r'— neurons that fire together wire together; opposite neurons build inhibitory links',
          ha='center', fontsize=11.5, color='#666666')

fig2.savefig(OUT/'slide_2_connections.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.close(fig2)
print("slide_2_connections.png  ✓")


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — Pattern Similarity & Crosstalk
# ═══════════════════════════════════════════════════════════════════════════════
p1 = bipolar('1'); p7 = bipolar('7')
overlap = float(p1 @ p7) / 16   # ξ¹·ξ⁷ / N

fig3 = plt.figure(figsize=(16, 9), facecolor=BG)
fig3.patch.set_facecolor(BG)

gs = GridSpec(2, 3, figure=fig3,
              left=0.06, right=0.94, top=0.80, bottom=0.07,
              hspace=0.52, wspace=0.18,
              width_ratios=[1, 0.75, 1])

CMAP_C = ListedColormap([BG, CYAN])

# ── top row: pattern '1' | overlap bar | pattern '7' ─────────────────────────
ax1 = fig3.add_subplot(gs[0, 0])
ax1.imshow(pat_img('1'), cmap=CMAP_C, vmin=0, vmax=1, interpolation='nearest')
ax1.set_xticks([]); ax1.set_yticks([])
for sp in ax1.spines.values(): sp.set_color(CYAN); sp.set_linewidth(2.5)
ax1.set_title("Pattern  ξ¹  ('1')", fontsize=14, color=CYAN,
              fontweight='bold', pad=5)

ax7 = fig3.add_subplot(gs[0, 2])
ax7.imshow(pat_img('7'), cmap=CMAP_C, vmin=0, vmax=1, interpolation='nearest')
ax7.set_xticks([]); ax7.set_yticks([])
for sp in ax7.spines.values(): sp.set_color(CYAN); sp.set_linewidth(2.5)
ax7.set_title("Pattern  ξ⁷  ('7')", fontsize=14, color=CYAN,
              fontweight='bold', pad=5)

# Middle: similarity annotation
ax_m = fig3.add_subplot(gs[0, 1])
ax_m.set_facecolor(BG); ax_m.axis('off')
ax_m.set_xlim(0,1); ax_m.set_ylim(0,1)
ax_m.annotate('', xy=(0.92, 0.5), xytext=(0.08, 0.5),
              arrowprops=dict(arrowstyle='<->', color=PINK,
                              lw=2.8, mutation_scale=18))
shared_pct = (1 - int((p1 != p7).sum())/16)*100
ax_m.text(0.5, 0.73, f'{shared_pct:.0f}% shared bits', ha='center',
          fontsize=13, color=PINK, fontweight='bold')
ax_m.text(0.5, 0.50, r'$\xi^1\!\cdot\!\xi^7/N$', ha='center',
          fontsize=13, color='#ffaacc')
ax_m.text(0.5, 0.30, f'$= {overlap:+.3f}$', ha='center',
          fontsize=15, color=PINK, fontweight='bold')
ax_m.text(0.5, 0.10, '≠ 0  →  not orthogonal', ha='center',
          fontsize=11, color='#bb8899')

# ── bottom row: training | both | inference ───────────────────────────────────
panel_style = dict(facecolor='#0c0c1e')

ax_tr = fig3.add_subplot(gs[1, 0])
ax_tr.set(**panel_style); ax_tr.set_xlim(0,1); ax_tr.set_ylim(0,1)
ax_tr.set_xticks([]); ax_tr.set_yticks([])
for sp in ax_tr.spines.values(): sp.set_color('#f39c12'); sp.set_linewidth(1.8)
ax_tr.set_title('Training  (learning rule)', fontsize=13,
                color='#f39c12', fontweight='bold', pad=4)

train_txt = [
    (r"$W \;+\!=\; \frac{1}{N}\xi^7(\xi^7)^T$", '#dddddd', 13),
    ('', '', 0),
    (r"Because  $\xi^1\!\cdot\!\xi^7 \neq 0$:", '#aaaaaa', 11),
    (r"the outer product of $\xi^7$ has", '#aaaaaa', 11),
    (r"non-zero projection onto $\xi^1$", '#aaaaaa', 11),
    ('', '', 0),
    ('Earlier memories are partially', '#888888', 11),
    ('overwritten — capacity drops', '#888888', 11),
]
y = 0.88
for line, col, sz in train_txt:
    if sz: ax_tr.text(0.07, y, line, fontsize=sz, color=col, va='top')
    y -= 0.115

ax_bth = fig3.add_subplot(gs[1, 1])
ax_bth.set(**panel_style); ax_bth.set_xlim(0,1); ax_bth.set_ylim(0,1)
ax_bth.set_xticks([]); ax_bth.set_yticks([])
for sp in ax_bth.spines.values(): sp.set_color('#555577'); sp.set_linewidth(1.2)
ax_bth.set_title('Root cause', fontsize=13,
                 color='#ffffff', fontweight='bold', pad=4)
ax_bth.text(0.5, 0.64,
            'Crosstalk is baked\ninto W at training\ntime and surfaces\nat recall',
            ha='center', va='center', fontsize=11.5,
            color='#ccccdd', linespacing=1.8)
ax_bth.annotate('', xy=(0.5, 0.18), xytext=(0.5, 0.38),
                arrowprops=dict(arrowstyle='->', color='#888899', lw=2))
ax_bth.text(0.5, 0.11, 'capacity  ↓', ha='center',
            fontsize=13, color=RED, fontweight='bold')

ax_in = fig3.add_subplot(gs[1, 2])
ax_in.set(**panel_style); ax_in.set_xlim(0,1); ax_in.set_ylim(0,1)
ax_in.set_xticks([]); ax_in.set_yticks([])
for sp in ax_in.spines.values(): sp.set_color('#2ecc71'); sp.set_linewidth(1.8)
ax_in.set_title('Inference  (recall)', fontsize=13,
                color='#2ecc71', fontweight='bold', pad=4)

infer_txt = [
    (r"Query  $s \approx \xi^1$:", '#dddddd', 13),
    ('', '', 0),
    (r"$h_i = W[i]\cdot s$", '#dddddd', 13),
    (r"$\approx \xi^1_i + \,(\xi^1\!\cdot\!\xi^7/N)\,\xi^7_i + \ldots$",
     '#dddddd', 12),
    (r"$\quad\quad\quad\uparrow\,\mathrm{crosstalk}$", '#ff8888', 11),
    ('', '', 0),
    ('Crosstalk term pulls the', '#888888', 11),
    ("state toward  ξ⁷  instead", '#888888', 11),
    ('of the correct attractor', '#888888', 11),
]
y = 0.88
for line, col, sz in infer_txt:
    if sz: ax_in.text(0.06, y, line, fontsize=sz, color=col, va='top')
    y -= 0.115

# Main title + subtitle
fig3.suptitle('Correlated Patterns Compete for Storage',
              fontsize=28, color='white', fontweight='bold',
              fontfamily='serif', y=0.965)
fig3.text(0.5, 0.875,
          'Non-orthogonal patterns create crosstalk in W — degrading capacity at training '
          'and pulling recall toward the wrong memory at inference',
          ha='center', fontsize=13, color='#999999')

fig3.savefig(OUT/'slide_3_similarity.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.close(fig3)
print("slide_3_similarity.png  ✓")

print("\nAll 3 slides saved to", OUT)
