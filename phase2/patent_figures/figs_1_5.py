#!/usr/bin/env python3
"""
FIGS. 1-5 -- corrected versions of the inventor's originals.

Reference numerals are preserved so the specification does not have to be
renumbered. What changed:

  FIG. 1  Signal lines no longer cross one another or pass through boxes. The
          control path is drawn as the closed loop it actually is (array ->
          activity -> convergence -> annealing control -> timing elements ->
          array) instead of four unrelated arrows. The node array now shows
          what the invention is: nodes partitioned into classes, each class
          driving a DIFFERENT delay value. The original drew five unlabelled
          nodes with arbitrary edges and no delay elements at all, which is the
          one thing a reader must take away from FIG. 1.
  FIG. 2  One relationship per curve. The original superimposed two unrelated
          curves and then drew an "annealing trajectory" arrow along a third
          path, which reads as three different claims about the same axes.
  FIG. 3  The tap outputs now go to the tap multiplexer. In the original they
          ran to the pulse filter while the multiplexer's output looped
          backwards into the filter from the right, which is not a circuit.
          Adds the waveform inset that makes "rejection window" mean something.
  FIG. 4  Same tap-routing correction, plus the sizing constraint that makes
          the block correct rather than merely present.
  FIG. 5  Proper flowchart shapes and an explicit decision node for the
          convergence test, so the restart edge has somewhere to come from.
"""
import os
from figlib import *

OUT = os.path.dirname(os.path.abspath(__file__)) + "/out"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- FIG. 1
fig, ax = page()
label(ax, 50, 126, "APPARATUS OVERVIEW  —  NO CLOCK SIGNAL IS PRESENT "
                   "ANYWHERE IN THE APPARATUS", fs=8.2)

box(ax, 6, 84, 50, 36)
label(ax, 31, 117, "THRESHOLD-LOGIC NODE ARRAY", fs=8)
label(ax, 31, 113.6, "(weights and thresholds encode the cost function)", fs=6.6, it=True)
numeral(ax, 102, 3.0, 122.5, 6, 120)

# node graph: 6 nodes, 3 classes by hatch, each with its own delay element
NODES = {0: (14, 105, ""), 1: (30, 108, "///"), 2: (46, 105, "..."),
         3: (14, 92, "..."), 4: (30, 89, ""), 5: (46, 92, "///")}
EDGES = [(0, 1), (1, 2), (0, 3), (1, 4), (2, 5), (3, 4), (4, 5), (0, 4), (2, 4)]
for a, b in EDGES:
    xa, ya, _ = NODES[a]; xb, yb, _ = NODES[b]
    ax.add_line(Line2D([xa, xb], [ya, yb], lw=TH, color="k", zorder=1))
CLS = {"": "I", "///": "II", "...": "III"}
for k, (x, y, h) in NODES.items():
    ax.add_patch(Rectangle((x - 3.4, y - 2.6), 6.8, 5.2, facecolor="white",
                           edgecolor="k", lw=LW, hatch=h, zorder=2))
    ax.text(x, y, CLS[h], fontsize=6.8, ha="center", va="center", zorder=3,
            bbox=dict(boxstyle="square,pad=0.32", fc="white", ec="none"))
numeral(ax, 104, 8.4, 99.5, 11.2, 103.2)
label(ax, 31, 85.6, "classes I, II, III  →  delay values d₁ < d₂ < d₃", fs=6.8, it=True)

box(ax, 64, 100, 32, 14, "TIMING ELEMENTS\n(one per node,\nprogrammable)", fs=8)
numeral(ax, 106, 98.6, 116, 96, 114)
box(ax, 64, 80, 32, 13, "ANNEALING CONTROL\n(margin schedule)", fs=8)
numeral(ax, 108, 98.6, 94.6, 96, 93)
box(ax, 64, 60, 32, 13, "CONVERGENCE\nDETECTION", fs=8)
numeral(ax, 112, 98.6, 74.6, 96, 73)
box(ax, 64, 40, 32, 13, "ACTIVITY MONITOR\n(transition rate)", fs=8)
numeral(ax, 110, 98.6, 54.6, 96, 53)
box(ax, 6, 44, 50, 13, "INITIALIZATION / READOUT", fs=8.4)
numeral(ax, 114, 3.0, 58.6, 6, 57)

arrow(ax, [(56, 84), (60, 84), (60, 46.5), (64, 46.5)])
label(ax, 61.4, 62, "node transitions", fs=6.6, ha="center",
      va="center", box_=True)
ax.texts[-1].set_rotation(90)
arrow(ax, [(80, 53), (80, 60)]); label(ax, 81.4, 56.5, "rate", fs=6.6, ha="left")
arrow(ax, [(80, 73), (80, 80)]); label(ax, 81.4, 76.5, "quiescent", fs=6.6, ha="left")
arrow(ax, [(80, 93), (80, 100)]); label(ax, 81.4, 96.5, "margin", fs=6.6, ha="left")
arrow(ax, [(64, 107), (56, 107)])
label(ax, 60, 108.8, "dᵢ", fs=6.8)
arrow(ax, [(20, 84), (20, 57)], both=True)
label(ax, 21.6, 70, "state in / out", fs=6.6, ha="left")
arrow(ax, [(1, 50.5), (6, 50.5)]); label(ax, 2.0, 52.4, "IN", fs=7, ha="left")
arrow(ax, [(31, 44), (31, 36)]); label(ax, 32.4, 39.5, "SOLUTION", fs=7, ha="left")

label(ax, 50, 28,
      "Every node evaluates continuously. Ordering is enforced only by the\n"
      "relative magnitudes of the per-node delay values — no clock, no\n"
      "sequencer, and no handshake between nodes of different classes.",
      fs=7.2, it=True)
finish(fig, ax, 1, OUT)

# ---------------------------------------------------------------- FIG. 2
fig, ax = page("TIMING MARGIN AS THE ANNEALING CONTROL VARIABLE")
import numpy as np
x0, x1, y0, y1 = 18, 84, 40, 100
arrow(ax, [(x0, y0), (x0, y1 + 4)])
arrow(ax, [(x0, y0), (x1 + 6, y0)])
label(ax, 11, (y0 + y1) / 2, "ESCAPING-TRANSITION\nRATE  (perturbation)", fs=7.4)
label(ax, (x0 + x1) / 2, y0 - 6.5, "PROGRAMMED TIMING MARGIN  →", fs=7.6)
t = np.linspace(0, 1, 240)
yy = y0 + 3 + (y1 - y0 - 3) * np.exp(-3.6 * t)
ax.add_line(Line2D(x0 + (x1 - x0) * t, yy, lw=1.5, color="k"))
numeral(ax, 202, 46, 78, 40, 71.5)
ax.add_line(Line2D([x1, x1], [y0, y1 + 2], lw=TH, color="k", linestyle=":"))
label(ax, x1, y1 + 4.6, "FULL\nMARGIN", fs=6.9)
ax.add_patch(Circle((x1, y0 + 3.6), 1.15, facecolor="k"))
numeral(ax, 206, 91, 50, x1 + 1.1, y0 + 3.6)
arrow(ax, [(x0 + 4, y0 - 13), (x1, y0 - 13)])
label(ax, (x0 + x1) / 2, y0 - 16.5, "ANNEALING SCHEDULE  (margin increases with time)", fs=7)
numeral(ax, 204, 89, y0 - 13, x1 - 2, y0 - 13)
for xa, xb, s in ((x0, x0 + 22, "UNDERSIZED MARGIN:\nhazard pulses and\npremature evaluations\npropagate"),
                  (x0 + 22, x0 + 46, "INTERMEDIATE:\nrate falls as margin\nis advanced"),
                  (x0 + 46, x1, "FULL MARGIN:\nsettled, deterministic\ndescent")):
    label(ax, (xa + xb) / 2, y1 - 4, s, fs=6.5, it=True)
label(ax, 50, 15,
      "The perturbation rate is also proportional to the number of nodes still\n"
      "switching, so it falls to zero of its own accord as the network\n"
      "approaches a fixed point. The schedule therefore self-quenches and no\n"
      "separate cooling of a noise source is required.", fs=7.2, it=True)
label(ax, 50, 8, "Relationship shown; axes are not to scale. Operation below full margin is\n"
                 "known in clocked colour-partitioned implementations, where it has been\n"
                 "reported to improve rather than degrade solution quality.", fs=6.4, it=True)
finish(fig, ax, 2, OUT)

# ---------------------------------------------------------------- FIG. 3
fig, ax = page("PROGRAMMABLE INERTIAL DELAY ELEMENT")
box(ax, 8, 74, 84, 44, dashed=True)
numeral(ax, 300, 95, 120, 92, 118)
arrow(ax, [(1, 108), (14, 108)])
label(ax, 1.5, 110.4, "NODE LOGIC OUT", fs=7, ha="left")
xs = [14, 28, 42, 56]
for k, x in enumerate(xs):
    box(ax, x, 103, 11, 10, "DLY", fs=7.6)
    if k < 3:
        arrow(ax, [(x + 11, 108), (x + 14, 108)])
numeral(ax, 302, 19.5, 99.5, 19.5, 103)
# taps go to the MULTIPLEXER. In the original they ran to the pulse filter and
# the multiplexer output looped backwards into it, which is not a circuit.
for x in xs:
    ax.add_line(Line2D([x + 5.5, x + 5.5], [103, 98], lw=TH, color="k"))
    ax.add_line(Line2D([x + 5.5, 74], [98, 98], lw=TH, color="k"))
arrow(ax, [(67, 108), (74, 108)])
box(ax, 74, 94, 13, 18, "TAP\nMUX", fs=7.6)
numeral(ax, 304, 90.5, 116, 87, 112)
arrow(ax, [(80.5, 94), (80.5, 90), (46, 90), (46, 87)])
box(ax, 30, 76, 32, 11, "PULSE FILTER\n(reject width < r)", fs=7.6)
numeral(ax, 306, 25, 81.5, 30, 81.5)

arrow(ax, [(46, 76), (46, 70), (96, 70)])
label(ax, 97, 70, "V(i)", fs=7.6, ha="left")
arrow(ax, [(46, 60), (46, 66)])
label(ax, 46, 57.5, "REJECTION WINDOW  r", fs=7.2)
numeral(ax, 308, 62, 57.5, 55, 57.5)
arrow(ax, [(80.5, 122), (80.5, 118), (80.5, 112)])
label(ax, 82, 122, "TAP SELECT", fs=7, ha="left")
numeral(ax, 310, 76, 122, 80.5, 122)
label(ax, 50, 52, "both controls driven by the annealing control (108)", fs=6.8, it=True)

# waveform inset -- what "rejection window" actually does
box(ax, 14, 20, 72, 26)
label(ax, 50, 43.5, "OPERATION OF THE REJECTION WINDOW", fs=7.2)
label(ax, 17, 38, "input", fs=6.8, ha="left")
waveform(ax, 30, 82, 36.5, [(0.0, 0), (0.14, 1), (0.20, 0), (0.46, 1),
                            (0.52, 0), (0.70, 1)], amp=3.2)
label(ax, 17, 27.5, "output", fs=6.8, ha="left")
waveform(ax, 30, 82, 26, [(0.0, 0), (0.70, 0), (0.76, 1)], amp=3.2)
for fx in (0.17, 0.49):
    ax.add_line(Line2D([30 + 52 * fx, 30 + 52 * fx], [26, 40], lw=TH,
                       color="k", linestyle=":"))
label(ax, 30 + 52 * 0.33, 32, "pulses narrower than r are rejected", fs=6.4, it=True)
label(ax, 30 + 52 * 0.84, 32, "width ≥ r  →  passed", fs=6.4, it=True)

label(ax, 50, 14,
      "A short rejection window lets hazard pulses through, and those pulses are\n"
      "the perturbation source. A full-width window admits at most one settled\n"
      "transition per evaluation. r is therefore the annealing control variable.",
      fs=7.2, it=True)
label(ax, 50, 6,
      "The rejection is not a refinement of this element — it is what makes the\n"
      "schedule work at all. A delay that propagates every transition instead of\n"
      "cancelling superseded ones reaches a fixed point from 1–16% of initial\n"
      "states under the same schedule. See FIG. 12.", fs=6.6, it=True)
finish(fig, ax, 3, OUT)

# ---------------------------------------------------------------- FIG. 4
fig, ax = page("PROGRAMMABLE MATCHED-DELAY COMPLETION GENERATOR")
arrow(ax, [(3, 104), (14, 104)])
label(ax, 3.5, 106.6, "EN_k", fs=7.4, ha="left")
xs = [14, 30, 46, 62]
for k, x in enumerate(xs):
    box(ax, x, 99, 13, 10, "MATCHED\nCELL DLY", fs=6.8)
    if k < 3:
        arrow(ax, [(x + 13, 104), (x + 16, 104)])
numeral(ax, 402, 20, 114, 20.5, 109)
for x in xs:
    ax.add_line(Line2D([x + 6.5, x + 6.5], [99, 92], lw=TH, color="k"))
    ax.add_line(Line2D([x + 6.5, 80], [92, 92], lw=TH, color="k"))
ax.add_line(Line2D([80, 80], [92, 99], lw=TH, color="k"))
box(ax, 80, 96, 14, 16, "TAP\nSELECT", fs=7.2)
numeral(ax, 404, 97, 116, 94, 112)
arrow(ax, [(94, 104), (99, 104)])
label(ax, 99.5, 104, "DONE_k", fs=7.4, ha="left")
arrow(ax, [(87, 84), (87, 96)])
label(ax, 87, 81, "MARGIN SELECT", fs=7.2)
numeral(ax, 406, 74, 81, 82, 81)

box(ax, 12, 54, 76, 17)
label(ax, 50, 68, "SIZING CONSTRAINT", fs=7.4)
label(ax, 50, 63.5,
      "selected delay   ≥   t  pd,max  ( class k )   +   guard band",
      fs=8)
label(ax, 50, 58.5,
      "A tap shorter than the worst-case combinational propagation delay through\n"
      "the class asserts DONE_k early, and the next class then evaluates on inputs\n"
      "that have not settled.", fs=6.8, it=True)

label(ax, 50, 40,
      "That premature evaluation is the perturbation the annealing schedule\n"
      "exploits: undersized taps early in the schedule, full-width taps at the end.\n\n"
      "The same constraint applied to the node delays of FIG. 6 is a correctness\n"
      "requirement rather than a control variable — a node delay shorter than the\n"
      "propagation delay through its own logic makes the class ordering\n"
      "inoperative, because commits then interleave in an order the delay values\n"
      "no longer determine.", fs=7.2, it=True)
finish(fig, ax, 4, OUT)

# ---------------------------------------------------------------- FIG. 5
fig, ax = page("METHOD OF OPERATION")
S = [(502, "Encode the cost function in the node\nweights and thresholds"),
     (504, "Partition the coupling graph by proper\nvertex colouring; assign a DISTINCT delay\nvalue to each class"),
     (506, "Initialize the network state"),
     (508, "Set the timing margin to its low value\n(high perturbation)"),
     (510, "Evaluate clocklessly; advance the margin\nper the schedule"),
     ]
y = 116
for num, txt in S:
    box(ax, 22, y - 9, 56, 9, txt, fs=7)
    numeral(ax, num, 17, y - 4.5, 22, y - 4.5)
    arrow(ax, [(50, y - 9), (50, y - 13)])
    y -= 13
diamond(ax, 50, y - 6, 40, 13, "margin at full value\nAND a full pass with\nno transition?", fs=6.6)
numeral(ax, 512, 26, y - 6, 30, y - 6)
label(ax, 52, y - 15.5, "yes", fs=6.8, ha="left")
arrow(ax, [(50, y - 12.5), (50, y - 19)])
box(ax, 22, y - 28, 56, 9, "Read the candidate solution and its cost", fs=7)
numeral(ax, 514, 17, y - 23.5, 22, y - 23.5)
# "no" branch: keep evaluating
arrow(ax, [(30, y - 6), (12, y - 6), (12, y + 8.5), (22, y + 8.5)])
label(ax, 28, y - 3.6, "no", fs=6.8, ha="right")
# restart branch
arrow(ax, [(78, y - 23.5), (90, y - 23.5), (90, y + 34.5), (78, y + 34.5)])
label(ax, 91.5, y + 5, "OPTIONAL RESTART:\nre-initialize, reheat,\nkeep the lowest-cost\ncandidate", fs=6.6, ha="left")
numeral(ax, 516, 86, y - 27, 90, y - 23.5)
label(ax, 50, 16,
      "Steps 502 and 504 are performed once at compile time. Nothing inside the\n"
      "evaluation loop reprograms the node logic, so the loop rate is set by the\n"
      "settling time of the array and not by any reconfiguration time.",
      fs=7.2, it=True)
finish(fig, ax, 5, OUT)
