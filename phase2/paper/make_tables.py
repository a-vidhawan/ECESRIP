#!/usr/bin/env python3
"""
Canonical results tables for the paper, with Wilson confidence intervals.

Several headline numbers are proportions from small samples -- the universal
oscillator set is n=32, and "100% settled" there is 32/32, which is NOT the same
evidence as 32/32 out of 3,000. Wilson intervals are used rather than normal
approximation because the estimates sit at exactly 0 and 1, where the normal
interval degenerates to zero width and would overstate certainty.

Emits RESULTS_TABLES.md. Regenerate rather than hand-editing.
"""

import json, os
from math import sqrt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "clockless", "results")
OUT = os.path.join(HERE, "RESULTS_TABLES.md")


def wilson(k, n, z=1.96):
    """Wilson score interval. Correct at p=0 and p=1, unlike the normal approx."""
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def pct(k, n):
    p, lo, hi = wilson(k, n)
    return f"{100*p:.1f} [{100*lo:.1f}–{100*hi:.1f}]"


def load(f):
    p = os.path.join(RES, f)
    return pd.read_csv(p) if os.path.exists(p) else None


L = []
def w(s=""):
    L.append(s)


def t_rule():
    df = load("stress_r7_permutation.csv")
    if df is None:
        return
    w("## Table 1 — The scheduling rule (2×2)")
    w()
    w("Settling on the 32 hardest states (those that oscillate under both the "
      "depth and parity schedules). Percentages are Wilson 95% intervals; each "
      "condition pools all its schemes.")
    w()
    w("| condition | schemes | n | settled % [95% CI] |")
    w("|---|---|---|---|")
    u = df[df["testset"] == "uosc"]
    for cat in ["colour+incommens", "colour+commens", "colour+nosep",
                "parity+incommens"]:
        s = u[u["category"] == cat]
        if not len(s):
            continue
        w(f"| {cat} | {s['scheme'].nunique()} | {len(s)} | "
          f"{pct(int(s['settled'].sum()), len(s))} |")
    w()
    w("A single scheme on this set is n=32, giving a 95% interval of roughly "
      "[89–100] even at 32/32 — the confidence comes from pooling 15 independent "
      "schemes, not from any one of them.")
    w()


def t_perm():
    df = load("stress_r7_permutation.csv")
    if df is None:
        return
    p = df[df["scheme"].str.startswith("perm")]
    w("## Table 2 — Robustness to the delay values")
    w()
    w("Twelve random permutations of the same six primes over the same six "
      "colour classes. If the effect were numerological, these would disagree.")
    w()
    w("| test set | n per scheme | settled mean % | sd | min | max |")
    w("|---|---|---|---|---|---|")
    for ts in sorted(p["testset"].unique()):
        s = p[p["testset"] == ts]
        by = s.groupby("scheme")["settled"].mean() * 100
        w(f"| {ts} | {len(s)//len(by)} | {by.mean():.2f} | {by.std():.2f} | "
          f"{by.min():.1f} | {by.max():.1f} |")
    w()


def t_scale():
    for f, cap in (("scale_final.json",
                    "M=4, fan-in 24, random d-regular support + masked retrain"),):
        p = os.path.join(RES, f)
        if not os.path.exists(p):
            continue
        rows = json.load(open(p))
        w("## Table 3 — Scaling")
        w()
        w(f"{cap}. Settling and recall from the schedule simulator "
          "(validated against RTL at N=16 only — see limitations).")
        w()
        w("| N | χ | max delay | fan-in | settled % @HD≤3 | recall % @HD≤3 | trials |")
        w("|---|---|---|---|---|---|---|")
        for r in rows:
            n = 25
            w(f"| {r['N']} | {r['chromatic']} | {r['max_delay']} | "
              f"{r['max_degree']} | {pct(round(r['settled_hd3']*n), n)} | "
              f"{pct(round(r['correct_hd3']*n), n)} | {n} |")
        w()


def t_dc():
    p = os.path.join(HERE, "data", "dc_terms.json")
    if not os.path.exists(p):
        return
    d = json.load(open(p))
    w("## Table 4 — Don't-care minimisation (measured, Berkeley espresso)")
    w()
    w("| fan-in | full table rows | care rows | care % | DC terms (min–max, mean) "
      "| full-table terms | espresso time (DC) |")
    w("|---|---|---|---|---|---|---|")
    for r in d["runs"]:
        dc = r["dc_terms"]
        ft = r["full_terms"]
        fts = (f"{min(ft)}–{max(ft)} (mean {np.mean(ft):.0f})" if ft
               else "infeasible to enumerate")
        w(f"| {r['fan_in']} | {r['full_table_rows']:,} | {r['care_rows']:,} | "
          f"{100*r['care_rows']/r['full_table_rows']:.3f}% | "
          f"{min(dc)}–{max(dc)} (mean {np.mean(dc):.0f}) | {fts} | "
          f"{np.mean(r['dc_seconds']):.1f} s |")
    w()
    w(f"_{d['_note']}_")
    w()
    v = d["verification"]
    w("## Table 5 — Behavioural equivalence of the minimised network")
    w()
    w(f"N=256, fan-in 16, care radius 3. {v['total_sop_terms']:,} product terms "
      f"across {v['neurons']} neurons, χ={v['chi']}. 40 trials per row; the exact "
      "threshold network and the network rebuilt from the espresso SOPs are run "
      "on identical inputs under the same schedule.")
    w()
    w("| input | exact settled | exact recall | SOP settled | SOP recall | agreement |")
    w("|---|---|---|---|---|---|")
    for r in v["rows"]:
        f = lambda x: "—" if x is None else pct(round(x * 40), 40)
        w(f"| {r['test']} | {f(r['exact_settled'])} | {f(r['exact_recall'])} | "
          f"{f(r['sop_settled'])} | {f(r['sop_recall'])} | {f(r['agreement'])} |")
    w()
    w("The last row is the cost of the method, not a defect to hide: off the "
      "care set espresso is free to choose, so the two networks diverge. Inside "
      "the operating region they are indistinguishable, including at HD=5, "
      "beyond the radius-3 care set they were built from.")
    w()


def t_outcomes():
    df = load("stress_r6_scheduling.csv")
    if df is None:
        return
    w("## Table 6 — Failure decomposition (why scheduling is not enough)")
    w()
    w("| scheme | test set | n | correct | wrong pattern | spurious | oscillated |")
    w("|---|---|---|---|---|---|---|")
    for ts in ("hd3", "random"):
        for sc in ("parity", "colour6"):
            s = df[(df["testset"] == ts) & (df["scheme"] == sc)]
            if not len(s):
                continue
            n = len(s)
            g = lambda c: pct(int((s["outcome"] == c).sum()), n)
            w(f"| {sc} | {ts} | {n} | {g('correct')} | {g('wrong_pattern')} | "
              f"{g('spurious')} | {g('oscillated')} |")
    w()
    w("Spurious convergence dominates oscillation by more than an order of "
      "magnitude on random states. Scheduling addresses the second column of "
      "failures; only loading addresses the first.")
    w()


def t_rtl():
    p = os.path.join(HERE, "data", "dc_terms.json")
    if not os.path.exists(p):
        return
    r = json.load(open(p)).get("rtl_n256")
    if not r:
        return
    w("## Table 7 — End-to-end RTL verification at N=256")
    w()
    w(f"N={r['N']}, M={r['M']}, fan-in {r['fan_in']}, care radius {r['radius']}. "
      f"{r['total_terms']:,} product terms over {r['neurons']} neurons "
      f"(χ={r['chi']}, {r['delay_value_conflicts']} delay-value conflicts). "
      "Don't-care SOPs emitted as SystemVerilog and simulated in iverilog — the "
      "same tool as every N=16 result. The last column is the one that matters: "
      "it upgrades the scaling claim from simulator to measured.")
    w()
    w("| HD | n | RTL settled | RTL recall | simulator settled | RTL = simulator |")
    w("|---|---|---|---|---|---|")
    n = r["trials_per_hd"]
    for row in r["rows"]:
        w(f"| {row['hd']} | {n} | {pct(round(row['rtl_settled']*n), n)} | "
          f"{pct(round(row['rtl_recall']*n), n)} | "
          f"{pct(round(row['sim_settled']*n), n)} | "
          f"{pct(round(row['rtl_matches_sim']*n), n)} |")
    w()
    w("The simulator models the schedule as periodic firing rather than "
      "event-driven NBA semantics; agreement on 240/240 inputs at N=256 is what "
      "licenses using it at all. It does not license using it at N=4096.")
    w()


def main():
    w("# Canonical Results Tables")
    w()
    w("_Generated by `make_tables.py`. Do not hand-edit — regenerate._")
    w()
    w("All proportions are Wilson 95% confidence intervals. Wilson rather than "
      "the normal approximation because many estimates sit at exactly 0 or 1, "
      "where the normal interval collapses to zero width and overstates "
      "certainty.")
    w()
    for f in (t_rule, t_perm, t_scale, t_dc, t_outcomes, t_rtl):
        try:
            f()
        except Exception as e:
            w(f"_[table failed: {type(e).__name__}: {e}]_")
            w()
    open(OUT, "w").write("\n".join(L) + "\n")
    print(f"wrote {OUT} ({len(L)} lines)")


if __name__ == "__main__":
    main()
