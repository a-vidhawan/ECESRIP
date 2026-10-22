#!/usr/bin/env python3
"""
Application 1 (self-timed network, clockless sequencing) -- FIGS. 1 and 2.

These are for Application 1, not the annealing set in figs_1_5.py; output goes
to app1/ so the two FIG. 1s cannot be confused.

  FIG. 1  Sequencing circuitry 106 is drawn where it actually is. In the
          delay-differentiated embodiment there is no central sequencer: 106
          is one inertial delay element 110 per node circuit, inside that
          node's own feedback path. A single central block suggests a
          controller, which is the handshake embodiment, not the delay one.
          The handshake form is shown separately in (B), where 106 really is a
          shared block.
  FIG. 2  Keeps the bipartite and odd-cycle cases, then adds the measured
          N = 16 coupling graph under a proper colouring and under index
          parity (19 of 43 coupled pairs in a shared class), and the class
          counts measured at N = 256 / 1024 / 4096.

The N = 16 graph is read live from the PLAs through
../clockless/analyze_coupling.py, and the counts on the sheet are asserted
against it rather than typed in.
"""
import os, sys
import numpy as np
from figlib import *

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + "/app1"
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(HERE, "..", "clockless"))
import analyze_coupling as ac

ROMAN = ["I", "II", "III", "IV", "V", "VI"]
HATCH = [None, "////", "....", "\\\\\\\\", "xxx", "----"]

# ---------------------------------------------------------------- FIG. 1
fig, ax = page("SELF-TIMED RECURRENT THRESHOLD-LOGIC NETWORK CIRCUIT")

label(ax, 50, 121, "(A)  DELAY-DIFFERENTIATED EMBODIMENT  (FIG. 4)", fs=7.8)
box(ax, 6.5, 55, 87, 63.5, lw=TH)
numeral(ax, 100, 3.5, 121, 6.5, 118.5)

# interconnection network 104
box(ax, 10, 106, 80, 7.5, "RECURRENT INTERCONNECTION NETWORK\n"
    "couplings W(i, j)  —  no registers, no clock", fs=6.9)
numeral(ax, 104, 97, 114.5, 90, 111)

# node slices: (x, index, class, delay value); the ellipsis stands for the rest
SLICES = [(11, "1", "I", "d₁"), (25, "2", "II", "d₂"), (39, "3", "I", "d₁"),
          (53, "4", "III", "d₃"), (75, "N", "II", "d₂")]
for sx, idx, cls, d in SLICES:
    arrow(ax, [(sx + 5, 106), (sx + 5, 100)])                # inputs from 104
    box(ax, sx, 91, 10, 9, f"NODE {idx}\nΣ W·V ≥ T", fs=6.2)
    label(ax, sx + 5, 88.6, f"class {cls}", fs=6.0, it=True)
    arrow(ax, [(sx + 5, 91), (sx + 5, 84.5)])                # into delay
    box(ax, sx + 1.5, 77.5, 7, 7, d, fs=7.2)
    # feedback path: delay output back up to 104, tapped to 108
    ax.add_line(Line2D([sx + 5, sx + 5, sx + 12], [77.5, 74, 74], lw=LW, color="k"))
    arrow(ax, [(sx + 12, 74), (sx + 12, 106)])
    arrow(ax, [(sx + 12, 74), (sx + 12, 67)])
    ax.add_patch(Circle((sx + 12, 74), 0.55, color="k"))
label(ax, 70, 95.5, "···", fs=10)
label(ax, 70, 81, "···", fs=10)

# 106 is the set of delay elements, not a block
ax.add_patch(Rectangle((9.5, 76), 81, 10, fill=False, lw=TH, ls=(0, (5, 3)),
                       edgecolor="k"))
numeral(ax, 102, 3.5, 97.5, 11, 96)
numeral(ax, 110, 3.5, 82.5, 12.5, 81)
numeral(ax, 106, 97, 88, 90.5, 84)

# convergence detection 108
box(ax, 10, 58, 80, 9, "CONVERGENCE DETECTION CIRCUITRY\n"
    "(activity monitor: quiescence longer than the slowest class delay)", fs=6.8)
numeral(ax, 108, 3.5, 64.5, 10, 63)
arrow(ax, [(80, 58), (80, 51)])
label(ax, 78.5, 52.2, "DONE", fs=6.6, ha="right")
numeral(ax, 112, 86.5, 52, 80, 53.5)

label(ax, 50, 48.6, "106  SEQUENCING CIRCUITRY (CLOCKLESS) IS DISTRIBUTED: one inertial "
      "delay element 110 per node circuit,", fs=6.5, it=True)
label(ax, 50, 46.2, "inside that node's own feedback path.  There is no central "
      "sequencer, clock or state machine.", fs=6.5, it=True)
label(ax, 50, 43.8, "Classes I, II, III are a proper colouring of the coupling graph "
      "(FIG. 2);  d₁, d₂, d₃ are pairwise different.", fs=6.5, it=True)

# (B) handshake embodiment: here 106 really is a shared block
label(ax, 50, 38.5, "(B)  HANDSHAKE EMBODIMENT  (FIG. 5)  —  HERE 106 IS A SHARED BLOCK",
      fs=7.8)
box(ax, 8, 25, 24, 9, "NODE CIRCUITS\nOF CLASS C(1)", fs=6.6)
box(ax, 68, 25, 24, 9, "NODE CIRCUITS\nOF CLASS C(2)", fs=6.6)
arrow(ax, [(32, 31.5), (68, 31.5)], both=True)
label(ax, 50, 33, "via 104", fs=6.2, it=True)

box(ax, 11, 11, 18, 7, "COMPLETION\nDETECT C(1)", fs=6.2)
box(ax, 71, 11, 18, 7, "COMPLETION\nDETECT C(2)", fs=6.2)
box(ax, 40, 10.5, 20, 8, "PHASE ELEMENT\n(gen. C-element)", fs=6.2)
arrow(ax, [(20, 25), (20, 18)])
arrow(ax, [(80, 25), (80, 18)])
arrow(ax, [(29, 14.5), (40, 14.5)]); label(ax, 34.5, 16, "R", fs=6.2)
arrow(ax, [(71, 14.5), (60, 14.5)]); label(ax, 65.5, 16, "S", fs=6.2)
arrow(ax, [(46, 18.5), (46, 27.5), (32, 27.5)])
label(ax, 39, 29, r"EN₁ = $\varphi$", fs=6.2)
arrow(ax, [(54, 18.5), (54, 27.5), (68, 27.5)])
label(ax, 61, 29, r"EN₂ = $\overline{\varphi}$", fs=6.2)
ax.add_patch(Rectangle((9, 8.5), 82, 11.5, fill=False, lw=TH, ls=(0, (5, 3)),
                       edgecolor="k"))
numeral(ax, 106, 97, 21, 91, 19)
numeral(ax, 114, 4.5, 14.5, 11, 14.5)
numeral(ax, 116, 50, 22, 50, 18.5)
finish(fig, ax, 1, OUT)


# ---------------------------------------------------------------- FIG. 2
def vertex(ax, x, y, c, r=2.0, fs=5.6):
    ax.add_patch(Circle((x, y), r, facecolor="white", edgecolor="k", lw=LW,
                        hatch=HATCH[c], zorder=3))
    ax.text(x, y, ROMAN[c], fontsize=fs, ha="center", va="center", zorder=4,
            bbox=dict(boxstyle="square,pad=0.14", fc="white", ec="none"))


def edge(ax, a, b, lw=TH, z=1):
    ax.add_line(Line2D([a[0], b[0]], [a[1], b[1]], lw=lw, color="k", zorder=z))


def wheel_layout(n, edges, hub, seed=0, tries=40000):
    """The measured graph is a hub adjacent to every other node of its
    component, plus a separate K4. Draw the hub at the centre and its
    neighbours on a rim, in the rim order with fewest chord crossings; draw
    the K4 planar (triangle round a centre). Unit coordinates, fixed seed."""
    adj = {i: set() for i in range(n)}
    for i, j in edges:
        adj[i].add(j); adj[j].add(i)
    rim = sorted(adj[hub])
    rest = [v for v in range(n) if v != hub and v not in adj[hub]]
    chords = [(i, j) for i, j in edges if hub not in (i, j) and i in rim and j in rim]
    rng = np.random.default_rng(seed)

    def crossings(order):
        pos = {v: k for k, v in enumerate(order)}
        c = 0
        for x, (a, b) in enumerate(chords):
            a, b = sorted((pos[a], pos[b]))
            for (c1, d1) in chords[x + 1:]:
                c1, d1 = sorted((pos[c1], pos[d1]))
                if len({a, b, c1, d1}) == 4 and (a < c1 < b) != (a < d1 < b):
                    c += 1
        return c

    best = min((list(rng.permutation(rim)) for _ in range(tries)), key=crossings)
    P = {hub: (0.0, 0.0)}
    for k, v in enumerate(best):
        t = np.pi / 2 + 2 * np.pi * k / len(best)
        P[v] = (np.cos(t), np.sin(t))
    assert len(rest) == 4 and all(len(adj[v] & set(rest)) == 3 for v in rest)
    P[rest[0]] = (0.0, 0.0)                                  # K4: centre ...
    for k, v in enumerate(rest[1:]):                         # ... and triangle
        t = np.pi / 2 + 2 * np.pi * k / 3
        P[v] = (np.cos(t), np.sin(t))
    return P, set(rest), crossings(best)


_, _, E16 = ac.build_graph()
N16 = ac.N
deg = {i: 0 for i in range(N16)}
for i, j in E16:
    deg[i] += 1; deg[j] += 1
COL = ac.greedy_colour(E16, sorted(range(N16), key=lambda v: -deg[v]))
PAR = {i: i % 2 for i in range(N16)}
K16 = max(COL.values()) + 1
assert len(E16) == 43 and K16 == 6
assert not ac.conflicts(E16, COL)
PC = ac.conflicts(E16, PAR)
assert len(PC) == 19
HUB = max(deg, key=deg.get)
HUB_SAME = sum(1 for e in PC if HUB in e)
assert (deg[HUB], HUB_SAME) == (11, 6)

fig, ax = page("INTERACTION GRAPHS PARTITIONED INTO UPDATE CLASSES")

# (A) bipartite: 2 classes
label(ax, 25, 121, "(A)  BIPARTITE — 2 CLASSES", fs=7.4)
A = [(13, 113), (13, 104), (13, 95), (37, 113), (37, 104), (37, 95)]
for i, j in [(0, 3), (0, 4), (1, 3), (1, 5), (2, 4), (2, 5), (1, 4)]:
    edge(ax, A[i], A[j])
for i, xy in enumerate(A):
    vertex(ax, *xy, 0 if i < 3 else 1, r=2.4, fs=6.2)
label(ax, 25, 89.5, "every edge joins I to II", fs=6.4, it=True)
numeral(ax, 202, 5, 117, 11.3, 114.6)
numeral(ax, 204, 25, 117.5, 25, 113.4)

# (B) odd cycle: 3 classes
label(ax, 75, 121, "(B)  ODD CYCLE — 3 CLASSES", fs=7.4)
ang = np.pi / 2 + np.arange(5) * 2 * np.pi / 5
B = [(75 + 10 * np.cos(a), 104 + 10 * np.sin(a)) for a in ang]
for i in range(5):
    edge(ax, B[i], B[(i + 1) % 5])
for i, c in enumerate([0, 1, 0, 1, 2]):
    vertex(ax, *B[i], c, r=2.4, fs=6.2)
label(ax, 75, 89.5, "a 5-cycle cannot be 2-coloured", fs=6.4, it=True)
numeral(ax, 206, 94, 113, B[4][0] + 1.8, B[4][1] + 1.2)

# (C) and (D): the measured N = 16 graph, same layout in both
WP, K4, _ = wheel_layout(N16, E16, HUB)


def place(x0, y0):
    """Wheel centred left in the panel, the separate K4 small at its right."""
    out = {}
    for v, (u, w) in WP.items():
        if v in K4:
            out[v] = (x0 + 39 + 6.2 * u, y0 + 31 + 6.2 * w)
        else:
            out[v] = (x0 + 15.5 + 14 * u, y0 + 20 + 14 * w)
    return out


label(ax, 25, 84.5, "(C)  MEASURED NETWORK, PROPER COLOURING", fs=7.2)
label(ax, 25, 81.6, f"N = 16, 43 couplings, {K16} classes", fs=6.4, it=True)
Q = place(3, 38)
for i, j in E16:
    edge(ax, Q[i], Q[j])
for i in range(N16):
    vertex(ax, *Q[i], COL[i])
label(ax, 25, 36, "0 of 43 coupled pairs share a class", fs=6.6, box_=True)

label(ax, 75, 84.5, "(D)  SAME NETWORK, PARTITIONED BY INDEX PARITY", fs=7.2)
label(ax, 75, 81.6, "2 classes (even / odd)  —  NOT a proper colouring", fs=6.4, it=True)
R = place(53, 38)
pcs = set(PC)
for i, j in E16:
    if (i, j) in pcs:
        edge(ax, R[i], R[j], lw=2.6, z=2)
    else:
        edge(ax, R[i], R[j])
for i in range(N16):
    vertex(ax, *R[i], PAR[i])
label(ax, 75, 36, "19 of 43 coupled pairs (44.2%) share a class  (bold, 208)",
      fs=6.6, box_=True)
hx, hy = R[HUB]
top = max((v for v in R if v not in K4 and v != HUB), key=lambda v: R[v][1])
assert tuple(sorted((HUB, top))) in pcs          # the vertical spoke is bold
numeral(ax, 208, hx + 6, hy + 21.5, hx + 0.3, hy + 7)
hx, hy = R[HUB]
t = np.radians(106)                      # between the first two rim nodes
numeral(ax, 210, hx + 21 * np.cos(t), hy + 21 * np.sin(t),
        hx + 2.2 * np.cos(t), hy + 2.2 * np.sin(t))
label(ax, 75, 33.2, "210  highest-degree node: 6 of its 11 neighbours in its own class",
      fs=6.0, it=True)

# measured class counts at scale
label(ax, 50, 28.4, "MEASURED — UPDATE CLASSES REQUIRED, SPARSIFIED AND RETRAINED NETWORKS (FIG. 7)",
      fs=6.8)
tx = [18, 34, 50, 66, 82]
box(ax, 10, 16, 80, 9, lw=TH)
ax.add_line(Line2D([10, 90], [20.5, 20.5], lw=TH, color="k"))
ax.add_line(Line2D([26, 26], [16, 25], lw=TH, color="k"))
for x in (42, 58, 74):
    ax.add_line(Line2D([x, x], [16, 25], lw=TH, color="k"))
label(ax, 18, 22.75, "nodes N", fs=6.6)
label(ax, 18, 18.25, "classes K", fs=6.6)
for x, n, k in [(34, "16 ¹", "6"), (50, "256", "4"), (66, "1 024", "5"), (82, "4 096", "6")]:
    label(ax, x, 22.75, n, fs=6.8)
    label(ax, x, 18.25, k, fs=6.8)
label(ax, 50, 12.6, "¹ the N = 16 network of (C)–(D) is dense (35.8%) and not of bounded "
      "degree; it is shown for the parity comparison.", fs=5.9, it=True)
label(ax, 50, 10.0, "For interaction graphs of bounded degree the number of classes does "
      "not grow appreciably with N.  The colouring need not be optimal.", fs=5.9, it=True)
finish(fig, ax, 2, OUT)
print("wrote", OUT)
