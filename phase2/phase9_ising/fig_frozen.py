#!/usr/bin/env python3
"""Figure for phase 9b: quality-per-reprogramming-event, and the dwell.

Two panels because the argument has two halves -- the frozen scheme is NOT
dynamically broken (left), it is bottlenecked on how often the noise can be
changed (right).
"""
import os, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frozen_noise import run
from maxcut import random_graph

HERE = os.path.dirname(os.path.abspath(__file__))
ROUNDS = [1, 2, 3, 5, 8, 12, 20]
INST, N, P, STEPS, SEED = 8, 60, 0.3, 60, 17

q = {m: [] for m in ("fresh", "frozen", "frozen_r", "chaotic")}
rd = {m: [] for m in q}
dwell = []
for R in ROUNDS:
    per = {m: [] for m in q}; perrd = {m: [] for m in q}
    for i in range(INST):
        A = random_graph(N, P, np.random.default_rng(SEED + i))
        res = {}
        for m in q:
            cut, r, dw = run(A, m, STEPS, R, np.random.default_rng(SEED+1000+i),
                             track_dwell=(m == "frozen" and R == 20))
            res[m] = cut; perrd[m].append(r); dwell += dw
        best = max(res.values()) or 1.0
        for m in q: per[m].append(res[m] / best)
    for m in q:
        q[m].append(np.mean(per[m])); rd[m].append(np.mean(perrd[m]))

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
STY = dict(fresh=("o-", "#1f77b4", "fresh noise every round"),
           frozen=("s-", "#d62728", "frozen per temperature step"),
           frozen_r=("^-", "#ff7f0e", "frozen + restart per step"),
           chaotic=("d-", "#2ca02c", "state-hash noise (no redraw)"))
for m, (mk, c, lab) in STY.items():
    x = [max(v, 0.5) for v in rd[m]]      # chaotic never redraws; park it at 0.5
    ax[0].plot(x, q[m], mk, color=c, label=lab, ms=5)
ax[0].set_xscale("log")
ax[0].set_xlabel("noise redraws  =  FPGA reprogramming events per anneal")
ax[0].set_ylabel("cut / best found on that instance")
ax[0].set_title("Quality per reprogramming event")
ax[0].legend(fontsize=8, loc="lower right"); ax[0].grid(alpha=.3)

d = np.array(dwell, dtype=float)
ax[1].hist(d, bins=np.arange(0.5, 22.5, 1), color="#d62728", alpha=.8)
ax[1].axvline(np.median(d), color="k", ls="--",
              label=f"median {np.median(d):.0f} rounds")
ax[1].set_xlabel("rounds before the state stops moving, within one frozen step")
ax[1].set_ylabel("temperature steps")
ax[1].set_title(f"Frozen noise stops doing work after ~{np.median(d):.0f} rounds\n"
                f"(budget was 20 -> {100*(1-np.mean(np.minimum(d,20))/20):.0f}% of "
                f"rounds wasted)")
ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
fig.tight_layout()
dest = os.path.join(HERE, "results", "fig_frozen_noise.png")
fig.savefig(dest, dpi=160)
print("wrote", dest)
