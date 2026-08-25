#!/usr/bin/env python3
"""
FIGS. 6-11 -- figures the original set does not have.

The originals draw the annealing embodiment in detail and the sequencing
mechanism not at all, which is backwards: the sequencing mechanism is what the
independent claims recite. FIG. 6 and FIG. 7 supply it. FIG. 8 gives the node
circuit and the delay design rule. FIG. 9 gives the delay-insensitive
alternative embodiment. FIGS. 10-11 give the don't-care synthesis, which the
prior-art review found is described nowhere in the claims despite being the
result least anticipated by the cited art.

FIG. 7 and FIG. 11 carry measured values. They are marked as measured and the
conditions are stated on the sheet, so nothing here reads as a prophetic
example dressed up as data.
"""
import os, json
import numpy as np
from figlib import *

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + "/out"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- FIG. 6
fig, ax = page("DERIVATION OF THE NODE DELAY VALUES FROM THE COUPLING GRAPH")
V = {0: (16, 0), 1: (30, 8), 2: (44, 2), 3: (17, -10), 4: (33, -7), 5: (46, -12)}
E = [(0, 1), (1, 2), (0, 3), (1, 4), (2, 5), (3, 4), (4, 5), (0, 4)]
COL = {0: 0, 1: 1, 2: 2, 3: 2, 4: 0, 5: 1}
HAT = ["", "///", "..."]
ROM = ["I", "II", "III"]


def graph(ax, ox, oy, coloured):
    for a, b in E:
        ax.add_line(Line2D([ox + V[a][0], ox + V[b][0]],
                           [oy + V[a][1], oy + V[b][1]], lw=TH, color="k", zorder=1))
    for k, (x, y) in V.items():
        h = HAT[COL[k]] if coloured else ""
        ax.add_patch(Circle((ox + x, oy + y), 3.1, facecolor="white",
                            edgecolor="k", lw=LW, hatch=h, zorder=2))
        ax.text(ox + x, oy + y, ROM[COL[k]] if coloured else str(k + 1),
                fontsize=6.4, ha="center", va="center", zorder=3,
                bbox=dict(boxstyle="square,pad=0.3", fc="white", ec="none"))


label(ax, 22, 118, "(A)  COUPLING GRAPH", fs=7.8)
label(ax, 22, 114.2, "vertex per node; edge wherever  W(i,j) ≠ 0", fs=6.6, it=True)
graph(ax, 6, 100, False)
numeral(ax, 602, 8, 112, 22, 106)

label(ax, 74, 118, "(B)  PROPER VERTEX COLOURING", fs=7.8)
label(ax, 74, 114.2, "no edge joins two vertices of one class", fs=6.6, it=True)
graph(ax, 48, 100, True)
numeral(ax, 604, 97, 112, 91, 106)

label(ax, 50, 84, "(C)  ASSIGNMENT OF DELAY VALUES", fs=7.8)
box(ax, 24, 62, 52, 18)
for k, (r, d) in enumerate((("I", "d₁"), ("II", "d₂"), ("III", "d₃"))):
    yy = 76 - k * 4.6
    ax.add_patch(Rectangle((28, yy - 1.7), 5, 3.4, facecolor="white",
                           edgecolor="k", lw=LW, hatch=HAT[k]))
    label(ax, 40, yy, f"class {r}", fs=7, ha="center")
    label(ax, 52, yy, "→", fs=7)
    label(ax, 62, yy, f"delay value  {d}", fs=7)
label(ax, 50, 64.4, "d₁ , d₂ , d₃  pairwise DIFFERENT", fs=7, it=True)
numeral(ax, 606, 20, 71, 24, 71)

box(ax, 12, 44, 76, 13)
label(ax, 50, 53.4, "THE CONSTRAINT THAT MUST HOLD", fs=7.4)
label(ax, 50, 49.4,
      "for every edge (i, j) of the coupling graph :   d(i)  ≠  d(j)", fs=8.4)
label(ax, 50, 46, "the colouring is a means of satisfying it, not the constraint itself",
      fs=6.6, it=True)

label(ax, 50, 34,
      "The constraint is on the DELAY VALUES, not on the class labels. A proper\n"
      "colouring whose classes are all assigned the same delay value satisfies\n"
      "every graph-theoretic requirement and does not work — see FIG. 7. The\n"
      "particular values are otherwise immaterial; only their distinctness on\n"
      "each edge is required.", fs=7.2, it=True)
label(ax, 50, 22,
      "Because the coupling graph is sparse, the number of distinct values needed\n"
      "is small and does not grow appreciably with the number of nodes.",
      fs=7.2, it=True)
finish(fig, ax, 6, OUT)

# ---------------------------------------------------------------- FIG. 7
fig, ax = page("WHY THE DELAY VALUES MUST DIFFER  —  COUPLED PAIR (i, j)")
for panel, (yb, tag, sub) in enumerate((
        (86, "(A)  EQUAL DELAY VALUES     d(i) = d(j)",
         "both nodes commit at the same instant, each on the other's stale value"),
        (44, "(B)  DIFFERENT DELAY VALUES     d(i) < d(j)",
         "node j re-evaluates on the committed value of node i"))):
    label(ax, 50, yb + 30, tag, fs=8)
    label(ax, 50, yb + 26.5, sub, fs=6.8, it=True)
    x0, x1 = 26, 84
    for r, (nm, y) in enumerate((("V(i)", yb + 18), ("V(j)", yb + 10))):
        label(ax, 22, y + 1.3, nm, fs=7.4, ha="right")
        ax.add_line(Line2D([x0, x1], [y - 1.2, y - 1.2], lw=TH, color="k",
                           linestyle=":"))
    if panel == 0:
        waveform(ax, x0, x1, yb + 18, [(0, 1), (0.25, 0), (0.55, 1), (0.85, 0)])
        waveform(ax, x0, x1, yb + 10, [(0, 0), (0.25, 1), (0.55, 0), (0.85, 1)])
        for f in (0.25, 0.55, 0.85):
            ax.add_line(Line2D([x0 + (x1 - x0) * f] * 2, [yb + 8, yb + 22],
                               lw=TH, color="k", linestyle=":"))
        label(ax, 55, yb + 4, "state alternates without end — a limit cycle,\n"
                              "never a fixed point", fs=7, it=True)
    else:
        waveform(ax, x0, x1, yb + 18, [(0, 1), (0.25, 0)])
        waveform(ax, x0, x1, yb + 10, [(0, 0), (0.45, 1)])
        for f, s_ in ((0.25, "d(i)"), (0.45, "d(j)")):
            ax.add_line(Line2D([x0 + (x1 - x0) * f] * 2, [yb + 8, yb + 22],
                               lw=TH, color="k", linestyle=":"))
            label(ax, x0 + (x1 - x0) * f, yb + 23, s_, fs=6.8)
        label(ax, 55, yb + 4, "both nodes quiescent — a fixed point is reached", fs=7, it=True)
numeral(ax, 702, 91, 108, 84, 104)
numeral(ax, 704, 91, 66, 84, 62)

box(ax, 14, 16, 72, 22)
label(ax, 50, 35, "MEASURED", fs=7.6)
cw = [30, 20, 20]
hx = [26, 54, 74]
label(ax, hx[1], 31, "distinct\ndelay values", fs=6.8)
label(ax, hx[2], 31, "identical\ndelay values", fs=6.8)
for k, (rl, a, b) in enumerate((("proper colouring", "100 %", "0 %"),
                                ("no colouring (parity)", "0 %", "—"))):
    yy = 25.5 - k * 4.6
    label(ax, hx[0], yy, rl, fs=6.9, ha="center")
    label(ax, hx[1], yy, a, fs=7.6)
    label(ax, hx[2], yy, b, fs=7.6)
ax.add_line(Line2D([18, 82], [28.6, 28.6], lw=TH, color="k"))
label(ax, 50, 18.5, "fraction of initial states reaching a fixed point,  N = 16,  "
                    "register-transfer simulation", fs=6.4, it=True)
label(ax, 50, 11,
      "The upper-right cell is the reason the constraint is stated on delay values.\n"
      "That configuration is a valid proper colouring of the coupling graph and it\n"
      "settles in none of the trials.", fs=7.2, it=True)
finish(fig, ax, 7, OUT)

# ---------------------------------------------------------------- FIG. 8
fig, ax = page("NODE CIRCUIT  AND  THE DELAY SIZING RULE")
label(ax, 50, 122, "one node i of the array (102)", fs=6.8, it=True)
for k, y in enumerate((112, 107, 102, 94)):
    if k == 3:
        label(ax, 12, y + 2.5, "⋮", fs=9)
        continue
    arrow(ax, [(6, y), (22, y)])
    label(ax, 5, y, f"V(j{k+1})", fs=6.8, ha="right")
arrow(ax, [(6, 90), (22, 90)])
label(ax, 5, 90, "V(jd)", fs=6.8, ha="right")
label(ax, 13, 84, "inputs from the d nodes\ncoupled to node i", fs=6.4, it=True)

box(ax, 22, 86, 20, 30, "AND\nPLANE", fs=7.4)
box(ax, 46, 86, 20, 30, "OR\nPLANE", fs=7.4)
for y in (112, 107, 102, 90):
    arrow(ax, [(42, y), (46, y)])
numeral(ax, 802, 32, 120, 32, 116)
label(ax, 44, 82, "two-level logic realising the node's update function\n"
                  "(synthesised as in FIG. 10)", fs=6.4, it=True)
arrow(ax, [(66, 101), (74, 101)])
box(ax, 74, 94, 18, 14, "INERTIAL\nDELAY  d(i)", fs=7.2)
label(ax, 83, 91, "cancels superseded\ntransitions (FIG. 12)", fs=6.0, it=True)
numeral(ax, 300, 95, 112, 92, 108)
label(ax, 50, 74, "V(i) becomes an input to every node coupled to i, and to no other\n"
                  "node. Node i does not receive its own output.", fs=6.6, it=True)
arrow(ax, [(92, 101), (98, 101)])
label(ax, 98.5, 101, "V(i)", fs=7.2, ha="left")

box(ax, 10, 46, 80, 18)
label(ax, 50, 61, "SIZING RULE FOR THE NODE DELAY", fs=7.6)
label(ax, 50, 56,
      "d(i)   >   t  pd,max  ( node i )      and      d(i) ≠ d(j) for every coupled j",
      fs=8.2)
label(ax, 50, 50.5,
      "The first inequality is what makes the second one mean anything. If the node\n"
      "delay is shorter than the worst-case propagation delay through that node's own\n"
      "logic, commits interleave in an order the delay values no longer determine and\n"
      "the class ordering is inoperative — the array still runs, and still settles, but\n"
      "not under the schedule that was designed.", fs=6.8, it=True)

label(ax, 50, 36,
      "The two inequalities are independent. Satisfying only the second gives a\n"
      "circuit that violates its own schedule; satisfying only the first gives a\n"
      "correctly-timed circuit with no ordering at all.", fs=7.2, it=True)
label(ax, 50, 22,
      "The delay element is the same element as FIG. 3. When its rejection window\n"
      "is programmable, one element performs both functions: it sequences the node\n"
      "and it sets how much hazard activity is admitted.", fs=7.2, it=True)
finish(fig, ax, 8, OUT)

# ---------------------------------------------------------------- FIG. 9
fig, ax = page("ALTERNATIVE EMBODIMENT  —  DELAY-INSENSITIVE NODE")
label(ax, 50, 122, "each signal carried on two wires:  NULL = both low,  "
                   "DATA = exactly one high", fs=7, it=True)
for k, (nm, y) in enumerate((("r.t (j)", 110), ("r.f (j)", 105))):
    arrow(ax, [(6, y), (20, y)])
    label(ax, 5, y, nm, fs=6.8, ha="right")
box(ax, 20, 96, 24, 20, "ON-SET\nAND / OR PLANE", fs=7)
box(ax, 20, 74, 24, 18, "DUAL PLANE\n(De Morgan on\nthe same cover)", fs=7)
arrow(ax, [(6, 84), (20, 84)]); label(ax, 5, 84, "r.f / r.t", fs=6.8, ha="right")
numeral(ax, 902, 16, 120, 26, 116)
arrow(ax, [(44, 106), (56, 106)]); label(ax, 50, 108, "f.t", fs=6.8)
arrow(ax, [(44, 83), (56, 83)]); label(ax, 50, 85, "f.f", fs=6.8)
box(ax, 56, 78, 12, 32, "OR", fs=7.4)
arrow(ax, [(68, 94), (76, 94)])
box(ax, 76, 86, 18, 16, "C-ELEMENT\nTREE", fs=7)
numeral(ax, 904, 97, 106, 94, 102)
arrow(ax, [(85, 86), (85, 78), (96, 78)])
label(ax, 96.5, 78, "COMPLETE", fs=7, ha="left")
label(ax, 74, 71, "asserts only when every node is DATA;\n"
                  "de-asserts only when every node is NULL", fs=6.4, it=True)
label(ax, 30, 68, "no inverter anywhere in the datapath", fs=6.6, it=True)

box(ax, 8, 34, 84, 30)
label(ax, 50, 61, "WHY THIS IS HAZARD-FREE WITHOUT ANY TIMING ASSUMPTION", fs=7.4)
label(ax, 50, 54,
      "Out of NULL every rail rises and none falls, so every product term is a\n"
      "monotone function of the rails and every internal node can only go 0 → 1.\n"
      "A node that never falls cannot glitch. Correctness therefore does not depend\n"
      "on the sizing rule of FIG. 8.", fs=7, it=True)
label(ax, 50, 43,
      "The false rail is obtained from the true rail's cover by De Morgan, not by a\n"
      "second independent minimisation. Two covers minimised against the same\n"
      "don't-care set leave inputs covered by neither, both rails then stay low, and\n"
      "completion detection waits for a DATA that never arrives.", fs=6.6, it=True)

label(ax, 50, 26,
      "This embodiment does NOT replace the partitioning. A C-element prevents a\n"
      "node from acting on inputs that have not settled; it does nothing about two\n"
      "coupled nodes acting on the same stale state. The same dual-rail array with\n"
      "the partitioning removed does not converge.", fs=7.2, it=True)
label(ax, 50, 15,
      "It costs roughly twice the logic of FIG. 8 and one NULL phase per evaluation.",
      fs=7.2, it=True)
finish(fig, ax, 9, OUT)

# ---------------------------------------------------------------- FIG. 10
fig, ax = page("SYNTHESIS OF THE NODE LOGIC USING OPERATING-REGION DON'T-CARES")
S = [(1002, "Stored patterns / problem instance\n(M target states)"),
     (1004, "Operating region:  all states within Hamming\nradius h of a target state"),
     (1006, "Project the operating region onto the support\nof node i  (its d coupled inputs)"),
     (1008, "CARE SET for node i\n"
            "size   M · Σ  C(d, k)   for k = 0 … h"),
     (1010, "Two-level minimisation with every input\noutside the care set left unspecified"),
     (1012, "AND / OR planes of FIG. 8")]
y = 116
for num, txt in S:
    box(ax, 20, y - 10, 60, 10, txt, fs=7)
    numeral(ax, num, 15, y - 5, 20, y - 5)
    if num != 1012:
        arrow(ax, [(50, y - 10), (50, y - 14)])
    y -= 14

box(ax, 8, 22, 84, 20)
label(ax, 50, 39, "WHY THE CARE SET IS SMALL", fs=7.6)
label(ax, 50, 33.5,
      "full table :   2 ^ d   rows                     care set :   M · Σ  C(d, k)  rows",
      fs=8)
label(ax, 50, 28,
      "exponential in the fan-in                        polynomial in the fan-in, of\n"
      "                                                              degree h", fs=6.6, it=True)
numeral(ax, 1014, 5, 32, 8, 32)

label(ax, 50, 14,
      "The care set is derived in closed form from the operating region. It is not\n"
      "obtained by sampling which inputs a trained network happens to visit, and it\n"
      "carries a guarantee over a stated radius rather than an observed frequency.\n"
      "Because the network is recurrent, an unspecified input that is later realised\n"
      "may create a fixed point that the target function does not have — a failure\n"
      "mode with no counterpart in a feed-forward network.", fs=7.1, it=True)
finish(fig, ax, 10, OUT)

# ---------------------------------------------------------------- FIG. 11
fig, ax = page("MEASURED  —  CARE SET AND PRODUCT-TERM COUNT VERSUS FAN-IN")
D = json.load(open(os.path.join(os.path.dirname(HERE), "paper", "data",
                                "dc_terms.json")))
runs = D["runs"]

# (A) rows that must be specified
x0, x1, yb, yt = 22, 88, 78, 116
arrow(ax, [(x0, yb), (x0, yt + 3)]); arrow(ax, [(x0, yb), (x1 + 4, yb)])
label(ax, 50, 121, "(A)  INPUT COMBINATIONS THAT MUST BE SPECIFIED", fs=7.8)
label(ax, 12, (yb + yt) / 2, "rows\n(logarithmic)", fs=6.8)
label(ax, 50, yb - 5, "fan-in  d", fs=7.2)
lo, hi = 3.0, 10.0                        # log10 limits


def ly(v):
    return yb + (yt - yb) * (np.log10(v) - lo) / (hi - lo)


for k in range(3, 11):
    ax.add_line(Line2D([x0 - 1.2, x0], [ly(10 ** k)] * 2, lw=TH, color="k"))
    sup = "".join("⁰¹²³⁴⁵⁶⁷⁸⁹"[int(c)] for c in str(k))
    label(ax, x0 - 3.2, ly(10 ** k), f"10{sup}", fs=6, ha="right")
for k, r in enumerate(runs):
    xx = x0 + (x1 - x0) * (k + 0.5) / 3
    for v, h, nm in ((r["full_table_rows"], "", "full table  2^d"),
                     (r["care_rows"], "///", "care set")):
        off = -5 if h == "" else 5
        ax.add_patch(Rectangle((xx + off - 4.4, yb), 8.8, ly(v) - yb,
                               facecolor="white", edgecolor="k", lw=LW, hatch=h))
        label(ax, xx + off, ly(v) + 2.4, f"{v:,}", fs=5.6)
    label(ax, xx, yb - 2.6, f"{r['fan_in']}", fs=7)
box(ax, 26, 100, 26, 7)
ax.add_patch(Rectangle((28, 104.4), 4, 1.8, facecolor="white", edgecolor="k", lw=TH))
label(ax, 42, 105.3, "full table", fs=6.2)
ax.add_patch(Rectangle((28, 101.4), 4, 1.8, facecolor="white", edgecolor="k",
                       lw=TH, hatch="///"))
label(ax, 42, 102.3, "care set", fs=6.2)
numeral(ax, 1102, 33, 95, 28, 88)

# (B) resulting product terms, where the full table is small enough to minimise
r0 = runs[0]
label(ax, 50, 68, "(B)  PRODUCT TERMS AFTER MINIMISATION,  fan-in 16", fs=7.8)
x0b, ybb, ytb = 26, 30, 60
arrow(ax, [(x0b, ybb), (x0b, ytb + 3)]); arrow(ax, [(x0b, ybb), (86, ybb)])
label(ax, 15, (ybb + ytb) / 2, "product\nterms", fs=6.8)
mx = max(r0["full_terms"])
for k, (fu, dc) in enumerate(zip(r0["full_terms"], r0["dc_terms"])):
    xx = x0b + 9 + k * 9.4
    for v, h, off in ((fu, "", -2.1), (dc, "///", 2.1)):
        ax.add_patch(Rectangle((xx + off - 2.0, ybb), 4.0,
                               (ytb - ybb) * v / mx,
                               facecolor="white", edgecolor="k", lw=TH, hatch=h))
    label(ax, xx, ybb - 2.6, f"n{k+1}", fs=6)
label(ax, 56, ybb - 6.4, "individual nodes", fs=6.6, it=True)
label(ax, 62, 49, "the don't-care bars are present but too short to\n"
                  "resolve at this scale", fs=6.2, it=True)
label(ax, 62, 55,
      f"fully specified :  {min(r0['full_terms']):,} – {max(r0['full_terms']):,} terms\n"
      f"don't-care      :  {min(r0['dc_terms'])} – {max(r0['dc_terms'])} terms",
      fs=6.8)
numeral(ax, 1104, 30, 52, 33.5, 56)

label(ax, 50, 18,
      f"Conditions: {r0['N']} nodes, M = {r0['M']} target states, radius h = "
      f"{r0['radius']}, two-level minimisation\nby the Berkeley espresso program. "
      "At fan-in 24 and above the fully-specified table\ncannot be enumerated at all, "
      "so no comparison column exists there.", fs=6.9, it=True)
label(ax, 50, 11,
      "The saving is in what has to be SPECIFIED, and only then in the term count\n"
      "that follows from it.", fs=7.2, it=True)
finish(fig, ax, 11, OUT)
