#!/usr/bin/env python3
"""
FIG. 12 -- the delay element has to be INERTIAL.

This sheet exists because of a measurement, not a design intention. The zero-
delay reference in the gate-level study settled less often than the glitchy
designs it was supposed to be a reference for, which is impossible if the
schedule works. Realignment of commensurate delay values was ruled out first
(five delay pools, all 100%). The cause is the delay element's semantics.

An inertial delay CANCELS a pending transition whose cause has gone away. A
transport delay queues every transition and delivers all of them. With
continuous re-evaluation a node's target can revert before its commit fires, and
under transport semantics that stale commit still lands -- on a node whose
neighbours have since moved.

The figure matters for the claims in two ways. The inertial behaviour is a
requirement of the scheme rather than a hazard mitigation that can be added or
left off; and a phase-shifted clock cannot supply it, because a clocked node
SAMPLES its input at an edge and has no notion of a superseded transition.
"""
import json, os
import numpy as np
from figlib import *

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + "/out"
D = json.load(open(os.path.join(os.path.dirname(HERE), "phase10_glitch",
                                "results", "inertial_required.json")))

fig, ax = page("THE DELAY ELEMENT MUST BE INERTIAL")

# ---- (A) the two semantics, as waveforms --------------------------------
label(ax, 50, 122, "(A)  WHAT THE TWO DELAY SEMANTICS DO WITH A SUPERSEDED "
                   "TRANSITION", fs=7.8)
x0, x1 = 30, 86
tv = 0.30            # target asserts
tr = 0.46            # target reverts, before the commit would have fired
tc = 0.62            # commit instant = tv + d

for nm, y in (("node target", 110), ("INERTIAL output", 100),
              ("TRANSPORT output", 90)):
    label(ax, 27, y + 1.3, nm, fs=7, ha="right")
    ax.add_line(Line2D([x0, x1], [y - 1.4, y - 1.4], lw=TH, color="k",
                       linestyle=":"))
waveform(ax, x0, x1, 110, [(0, 0), (tv, 1), (tr, 0)])
waveform(ax, x0, x1, 100, [(0, 0)])                      # nothing propagates
waveform(ax, x0, x1, 90, [(0, 0), (tc, 1), (tc + (tr - tv), 0)])
for f, s_ in ((tv, "target\nasserts"), (tr, "target\nreverts"), (tc, "commit\ninstant")):
    ax.add_line(Line2D([x0 + (x1 - x0) * f] * 2, [88, 114], lw=TH, color="k",
                       linestyle=":"))
    label(ax, x0 + (x1 - x0) * f, 117, s_, fs=6.2)
label(ax, 58, 96, "nothing is committed — the cause has gone away", fs=6.4, it=True)
label(ax, 58, 86, "a stale value is committed, onto neighbours that have since moved",
      fs=6.4, it=True)
numeral(ax, 1202, 24, 100, 30, 100)
numeral(ax, 1204, 24, 90, 30, 90)
label(ax, 50, 82, "d  =  the node's delay value;  the two rows differ only in "
                  "what happens to a\ntransition whose cause disappears before "
                  "d has elapsed.", fs=6.8, it=True)

# ---- (B) measured -------------------------------------------------------
label(ax, 50, 78, "(B)  MEASURED CONSEQUENCE", fs=7.8)
xb, yb, yt = 26, 34, 66
arrow(ax, [(xb, yb), (xb, yt + 3)]); arrow(ax, [(xb, yb), (88, yb)])
label(ax, 14, (yb + yt) / 2, "initial states\nreaching a\nfixed point", fs=6.6)
for p in (0, 25, 50, 75, 100):
    yy = yb + (yt - yb) * p / 100
    ax.add_line(Line2D([xb - 1.2, xb], [yy, yy], lw=TH, color="k"))
    label(ax, xb - 3, yy, f"{p}%", fs=6, ha="right")
for k, r in enumerate(D):
    xx = xb + 10 + k * 15
    for v, h, off in ((r["inertial"], "", -3.2), (r["transport"], "///", 3.2)):
        ax.add_patch(Rectangle((xx + off - 2.8, yb), 5.6,
                               (yt - yb) * v, facecolor="white",
                               edgecolor="k", lw=LW, hatch=h))
        label(ax, xx + off, yb + (yt - yb) * v + 2.2, f"{100*v:.0f}", fs=5.8)
    label(ax, xx, yb - 2.8, f"N={r['N']}", fs=6.4)
box(ax, 30, 68, 26, 7)
ax.add_patch(Rectangle((32, 72.4), 4, 1.8, facecolor="white", edgecolor="k", lw=TH))
label(ax, 46, 73.3, "inertial", fs=6.2)
ax.add_patch(Rectangle((32, 69.4), 4, 1.8, facecolor="white", edgecolor="k",
                       lw=TH, hatch="///"))
label(ax, 46, 70.3, "transport", fs=6.2)
numeral(ax, 1206, 33, 30, 33, 34)
label(ax, 50, 28, "Identical networks, identical colourings, identical delay "
                  "values, identical\ninitial states. The only difference is "
                  "the delay element's semantics.", fs=6.8, it=True)

label(ax, 50, 20,
      "The inertial behaviour is therefore a requirement of the scheduling scheme,\n"
      "not an optional mitigation. It is also something a phase-shifted clock\n"
      "cannot supply: a clocked node samples its input at an edge, and a\n"
      "transition that appeared and disappeared between two edges is simply not\n"
      "seen — there is nothing for the node to cancel, and nothing to sequence.",
      fs=7.2, it=True)
label(ax, 50, 9, "Delays here are consecutive multiples of one scale factor. "
                 "Delay pools spanning\npowers of two, primes and an "
                 "incommensurate ratio were also measured and are\n"
                 "indistinguishable, so the values matter only in being distinct "
                 "— see FIG. 6.", fs=6.4, it=True)
finish(fig, ax, 12, OUT)
print("wrote fig12")
