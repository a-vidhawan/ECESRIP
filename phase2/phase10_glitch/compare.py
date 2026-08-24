#!/usr/bin/env python3
"""
PHASE 10 -- the two textbook cures for logic hazards, built and measured.

Phase 7b established that real glitches change the settled state: synthesise the
neuron logic to primitive gates with unequal per-type delays and the network no
longer agrees with its own zero-delay model. This builds the two standard fixes
and runs them against the same instances.

  A. INERTIAL DELAY -- a bundled-data fix. Put a delay element in the feedback
     path whose pulse-rejection width exceeds the widest glitch. Cheap: one
     buffer per neuron, no change to the logic. Correct only under a TIMING
     ASSUMPTION, which is a thing that has to be met at every corner.

  B. MULLER C-ELEMENTS / dual-rail NCL -- a delay-insensitive fix. Encode each
     signal on two wires, compute the ON-set and OFF-set separately, and insert
     a NULL phase so every evaluation is monotone. Nothing glitches, so nothing
     needs filtering, and there is no timing assumption to meet. Expensive.

An important correction falls out of writing these down. The current design uses
`s_settle[i] <= #(d_i) s_next[i]`, and a non-blocking assignment with an
intra-assignment delay is TRANSPORT delay -- it queues every event and replays
it later. So the design has never actually had inertial delay, despite the
phase-4 Python model being called an inertial-delay simulator. Approach A is
therefore not only a mitigation, it is a bug fix.

Reference for all comparisons is the zero-delay behavioural model on the same
network: any disagreement with it is caused by glitches, because the designs are
logically equivalent by construction.
"""

import argparse, json, os, subprocess, sys, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CLK = os.path.join(os.path.dirname(HERE), "clockless")
sys.path.insert(0, ROOT); sys.path.insert(0, CLK); sys.path.insert(0, HERE)

from gen_dc_pla import care_rows, write_pla
from verify_dc_recall import espresso_sop, sop_eval
from improve_capacity import train_margin_auto, n_fixed
from scale_study import make_support
from schedule_hnn import graph_from_W, dsatur
from rtl_n256 import emit_lut, emit_sched

import netlist, schemes


def build(N, M, radius, seed, out, degree=0):
    """Train, then minimise every neuron with operating-region don't-cares.

    Only the ON-set is minimised. An earlier version also ran espresso on the
    flipped output column to get an independent OFF-set cover for the dual-rail
    build. That is twice the work AND wrong: two covers minimised against the
    same don't-care set leave points covered by neither, which deadlocks
    completion detection. The false rail is derived structurally instead.
    """
    pats = np.random.default_rng(seed + M).choice([-1, 1], size=(M, N)).astype(float)
    d = degree or min(N - 1, max(16, 4 * M))
    mask = make_support(N, min(N - 1, d), "regular",
                        np.random.default_rng(seed))
    W, kappa = train_margin_auto(pats, mask, seed=seed)
    on = []
    for i in range(N):
        sup, d, rows = care_rows(i, W, pats, radius)
        if sup is None or d == 0:
            on.append((None, None)); continue
        p = os.path.join(out, f"n{i}.pla")
        write_pla(p, sup, d, rows, dc=True)
        on.append((sup, espresso_sop(p)))
    return pats, W, kappa, on


def emit_tb(N, inits, budget, hold, tb, vec):
    nib = (N + 3) // 4
    open(vec, "w").write("".join(
        format(int(s), f"0{nib}x") + "\n" for s in inits))
    open(tb, "w").write(f"""`timescale 1ns/1ps
module tb;
  localparam int NTESTS = {len(inits)};
  localparam int TIMEOUT = {budget};
  localparam int DRAIN = {max(200, budget // 20)};
  // Quiescence must PERSIST. `s === s_next` is a combinational comparison, so
  // in a gate-level design it is transiently true while the logic is still
  // propagating -- the tell was the zero-delay reference reporting a LOWER
  // settled rate than the glitchy designs it is the reference for. Requiring
  // the comparison to hold continuously for longer than the worst-case
  // scheduling delay removes that false positive.
  localparam int HOLD = {hold};
  logic init_en = 1;
  logic [{N-1}:0] init_val = '0;
  wire  [{N-1}:0] s;
  wire  stable;
  hopfield_top dut (.init_en(init_en), .init_val(init_val),
                    .s(s), .stable(stable));
  logic [{N-1}:0] vectors [0:NTESTS-1];
  integer t, hold; time t0; reg done;
  initial begin
    $readmemh("{vec}", vectors);
    for (t = 0; t < NTESTS; t = t + 1) begin
      init_en = 1; init_val = vectors[t]; #(DRAIN);
      init_en = 0; t0 = $time; done = 0;
      hold = 0;
      begin : settle
        forever begin
          #1;
          if (stable) hold = hold + 1; else hold = 0;
          if (hold >= HOLD) begin done = 1; disable settle; end
          if ($time - t0 > TIMEOUT) disable settle;
        end
      end
      $display("TEST %0d result=%0h settled=%0d lat=%0d",
               t, s, done, $time - t0);
      init_en = 1; init_val = '0; #(DRAIN);
    end
    $display("ALLDONE"); $finish;
  end
endmodule
""")


def run(files, out, tag):
    vvp = os.path.join(out, f"{tag}.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-o", vvp] + files,
                       capture_output=True, text=True)
    if c.returncode != 0:
        return None, "compile: " + c.stderr[-700:]
    try:
        r = subprocess.run(["vvp", vvp], capture_output=True, text=True,
                           timeout=10800)
    except subprocess.TimeoutExpired:
        return None, "simulation wall-clock timeout"
    res = {}
    for ln in r.stdout.splitlines():
        if ln.startswith("TEST"):
            f = ln.split()
            res[int(f[1])] = (f[2].split("=")[1], int(f[3].split("=")[1]),
                              int(f[4].split("=")[1]))
    if not res:
        return None, (r.stdout or r.stderr)[-700:]
    return res, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=32)
    ap.add_argument("--M", type=int, default=8)
    ap.add_argument("--radius", type=int, default=3)
    ap.add_argument("--degree", type=int, default=0,
                    help="coupling fan-in. Left at 0 this scales with M, which\n                         at N>=32 puts the care set past 40k rows and espresso\n                         past its half-hour timeout on a single neuron.")
    ap.add_argument("--hd", type=int, default=0)
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--tau", type=int, nargs="+", default=[0, 4, 8, 16, 32],
                    help="pulse-rejection widths to sweep for the inertial fix")
    ap.add_argument("--delay-scale", type=int, default=40,
                    help="scheduling delays, in units of colour index. Must "
                         "exceed worst-case combinational propagation or the "
                         "colouring is inoperative -- that is a design-rule "
                         "violation, not a hazard, and phase 7b confused the "
                         "two once already.")
    ap.add_argument("--keep", default=None)
    args = ap.parse_args()

    N, M = args.N, args.M
    hd = args.hd or max(3, N // 10)
    out = args.keep or tempfile.mkdtemp()
    os.makedirs(out, exist_ok=True)
    print(f"N={N} M={M} radius={args.radius} HD={hd} trials={args.trials}")

    pats, W, kappa, on = build(N, M, args.radius, args.seed, out, args.degree)
    print(f"  kappa={kappa}, stored {n_fixed(W, pats)}/{M}")

    n, edges = graph_from_W(W)
    col = dsatur(n, edges)
    chi = max(col.values()) + 1
    classes = [[i for i in range(N) if col[i] == c] for c in range(chi)]
    delays = [(col[i] + 1) * args.delay_scale for i in range(N)]
    print(f"  chi={chi}, {len(edges)} coupling edges, "
          f"max scheduling delay={max(delays)}")

    # ---- logic ----------------------------------------------------------
    beh = os.path.join(out, "lut_beh.sv")
    terms = emit_lut(N, on, beh)
    sr = os.path.join(out, "lut_sr.v")
    n_sr = netlist.emit_single_rail(N, on, sr)
    dr = os.path.join(out, "lut_dr.v")
    n_dr = netlist.emit_dual_rail(N, on, dr)
    cells = os.path.join(out, "cells.v")
    open(cells, "w").write(netlist.CELLS)
    print(f"  {terms:,} product terms | single-rail {n_sr:,} gates | "
          f"dual-rail {n_dr:,} gates ({n_dr/max(n_sr,1):.2f}x)")

    # ---- vectors --------------------------------------------------------
    P01 = ((pats + 1) // 2).astype(np.int8)
    rng = np.random.default_rng(args.seed + 21)
    cases = []
    for _ in range(args.trials):
        m = int(rng.integers(M))
        v = P01[m].copy()
        v[rng.choice(N, size=hd, replace=False)] ^= 1
        cases.append((v, m))
    inits = [int("".join(str(b) for b in v[::-1]), 2) for v, _ in cases]
    budget = 600 * max(delays) + 40000
    tb = os.path.join(out, "tb.sv"); vec = os.path.join(out, "vec.hex")
    hold = max(delays) + 200
    emit_tb(N, inits, budget, hold, tb, vec)

    # ---- configurations --------------------------------------------------
    cfgs = []
    ref_sched = os.path.join(out, "sched_ref.sv")
    schemes.emit_transport(N, delays, ref_sched, lut="lut_beh")
    # the behavioural LUT module is named hopfield_lut by emit_lut; alias it
    open(beh, "a").write(f"\nmodule lut_beh (input wire [{N-1}:0] s, "
                         f"output wire [{N-1}:0] s_next);\n"
                         f"  hopfield_lut #(.N({N})) u (.s(s), .s_next(s_next));\n"
                         f"endmodule\n")
    cfgs.append(("reference (zero-delay logic)", [beh, ref_sched, tb], None))

    base = os.path.join(out, "sched_base.sv")
    schemes.emit_transport(N, delays, base)
    cfgs.append(("baseline: transport delay", [sr, cells, base, tb], n_sr))

    for tau in args.tau:
        p = os.path.join(out, f"sched_in{tau}.sv")
        schemes.emit_inertial(N, delays, tau, p)
        cfgs.append((f"A. inertial delay, tau={tau}", [sr, cells, p, tb],
                     n_sr + 2 * N))

    for lab, colour in (("colour-scheduled", True), ("NO colouring", False)):
        p = os.path.join(out, f"sched_ncl_{int(colour)}.sv")
        schemes.emit_ncl(N, classes, p, colour=colour)
        cfgs.append((f"B. C-element NCL, {lab}", [dr, cells, p, tb], n_dr))

    # ---- run -------------------------------------------------------------
    print("\n  simulating...", flush=True)
    ref, rows = None, []
    for label, files, gates in cfgs:
        res, err = run(files, out, label.split(":")[0].replace(" ", "_")
                       .replace(".", "").replace(",", ""))
        if res is None:
            print(f"    {label}: FAILED -- {err}")
            rows.append(dict(config=label, failed=err)); continue
        if ref is None:
            ref = res
        ok = agree = settled = fixed = 0
        lat = []
        for i, (v, m) in enumerate(cases):
            if i not in res:
                continue
            r_, st, lt = res[i]
            settled += st
            got = np.array([(int(r_, 16) >> b) & 1 for b in range(N)], dtype=np.int8)
            ok += st and np.array_equal(got, P01[m])
            agree += (i in ref and r_.lower() == ref[i][0].lower())
            # schedule-independent correctness: is the state the hardware
            # stopped on actually a fixed point of the logic it implements?
            # `agree` compares against ONE valid schedule and so penalises a
            # different-but-equally-valid one; this does not.
            fixed += st and all(sop_eval(on, k, got) == got[k] for k in range(N))
            if st:
                lat.append(lt)
        t = len(cases)
        rows.append(dict(config=label, gates=gates, settled=settled / t,
                         recall=ok / t, agreement=agree / t, fixpoint=fixed / t,
                         latency=float(np.mean(lat)) if lat else None))
        print(f"    {label:<34} settled {100*settled/t:>3.0f}%  "
              f"fixpt {100*fixed/t:>3.0f}%  recall {100*ok/t:>3.0f}%  "
              f"agree {100*agree/t:>3.0f}%", flush=True)

    print()
    hdr = (f"{'configuration':<34}{'gates':>8}{'settled':>9}{'fixpt':>7}"
           f"{'recall':>8}{'agree':>7}{'latency':>9}")
    print(hdr); print("-" * len(hdr))
    for r in rows:
        if r.get("failed"):
            print(f"{r['config']:<34}{'  FAILED: ' + r['failed'][:40]}"); continue
        g = f"{r['gates']:,}" if r["gates"] else "-"
        lt = f"{r['latency']:.0f}" if r["latency"] else "-"
        print(f"{r['config']:<34}{g:>8}{100*r['settled']:>8.0f}%"
              f"{100*r['fixpoint']:>6.0f}%{100*r['recall']:>7.0f}%"
              f"{100*r['agreement']:>6.0f}%{lt:>9}")
    print("-" * len(hdr))
    print("fixpt  = the settled state really is a fixed point of the logic.")
    print("agree  = identical to the zero-delay reference. Meaningful for the")
    print("         single-rail rows, which run the same schedule; the NCL rows")
    print("         run a different but equally valid order, so read fixpt there.")

    dest = os.path.join(HERE, "results", f"glitch_N{N}_M{M}.json")
    json.dump(dict(N=N, M=M, hd=hd, chi=chi, kappa=kappa, terms=terms,
                   gates_single_rail=n_sr, gates_dual_rail=n_dr,
                   delay_scale=args.delay_scale, trials=len(cases), rows=rows),
              open(dest, "w"), indent=2)
    print(f"\nwrote {dest}")
    if args.keep:
        print(f"netlists in {out}")


if __name__ == "__main__":
    main()
