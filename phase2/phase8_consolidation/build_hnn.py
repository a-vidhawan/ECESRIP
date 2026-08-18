#!/usr/bin/env python3
"""
build_hnn.py -- parameters in, synthesisable SystemVerilog out.

Everything the flow needs already exists, but only inside experiment scripts:
scale_study makes the support, improve_capacity trains it, schedule_hnn colours
the coupling graph, gen_dc_pla writes the operating-region PLAs, verify_dc_recall
calls espresso, rtl_n256 emits the RTL. This is the same flow with a single
entry point and nothing reimplemented -- every stage is an import.

    python3 build_hnn.py --N 256 --M 32 --fanin 32 --radius 3 --out design/

Stages
  1. seeded random bipolar patterns
  2. regular support of the requested fan-in
  3. train_margin_auto  -- largest FEASIBLE margin, not a fixed kappa=1
  4. coupling graph + DSATUR colouring -> per-neuron scheduling delays
  5. per-neuron PLA over the operating region only (Hamming radius `radius`
     around each stored pattern), everything else a don't-care
  6. espresso two-level minimisation
  7. emit hopfield_lut.sv + hopfield_sched.sv (+ a no-parameter variant) and
     build_meta.json

Two schedule files are emitted on purpose. `emit_sched` writes
`hopfield_lut #(.N(N)) lut`, which is correct against the behavioural LUT but
breaks against a yosys-elaborated gate netlist -- elaboration removes the
parameter, so there is nothing left to override. `hopfield_sched_noparam.sv` is
the same file with the override stripped, matching what gate_level_hazard.py
does inline.

The suggested simulation timeout is reported in build_meta.json: the
behavioural figure follows rtl_n256 (256*max_delay + 200), the gate-level one
follows gate_level_hazard (4000*max_delay + 5000), because real gate
propagation adds time on top of the scheduling delays.

DESIGN RULE (phase 7b): the scheduling delays emitted here are in arbitrary
units. Whatever unit they are given in the final timing constraints, one unit
MUST exceed the worst-case combinational propagation delay through the SOP, or
the colouring stops sequencing commits at all.
"""

import argparse, json, os, subprocess, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CLOCKLESS = os.path.join(os.path.dirname(HERE), "clockless")
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, CLOCKLESS)

from scale_study import make_support                      # support / mask
from improve_capacity import train_margin_auto, n_fixed   # training
from schedule_hnn import graph_from_W, dsatur             # colouring
from gen_dc_pla import care_rows, write_pla               # care set + PLA
from verify_dc_recall import espresso_sop                 # espresso
from rtl_n256 import emit_lut, emit_sched                 # RTL

DEFAULT_ESPRESSO = ("/tmp/claude-0/-home-user-ECESRIP/"
                    "34c74a44-9001-565a-8629-44b3228b7c84/scratchpad/"
                    "espresso-logic/bin/espresso")


def build(N, M, fanin, radius, seed, out, verbose=True):
    os.makedirs(out, exist_ok=True)
    pla_dir = os.path.join(out, "pla")
    os.makedirs(pla_dir, exist_ok=True)
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)
    t0 = time.time()

    # --- 1/2: patterns and support -------------------------------------
    pats = np.random.default_rng(seed + M).choice([-1, 1],
                                                  size=(M, N)).astype(float)
    d = min(N - 1, fanin)
    mask = make_support(N, d, "regular", np.random.default_rng(seed))
    log(f"[1/6] {M} patterns of width {N}, regular support fan-in {d}")

    # --- 3: training at the largest feasible margin --------------------
    W, kappa = train_margin_auto(pats, mask, seed=seed)
    stored = n_fixed(W, pats)
    log(f"[2/6] train_margin_auto: kappa={kappa}, stored {stored}/{M}")
    if stored < M:
        log(f"      WARNING: {M - stored} pattern(s) are not fixed points; "
            f"fan-in {d} is too small for M={M}")

    # --- 4: coupling graph, DSATUR, delays ------------------------------
    n, edges = graph_from_W(W)
    colour = dsatur(n, edges)
    chi = max(colour.values()) + 1
    delays = [colour[i] + 1 for i in range(n)]
    log(f"[3/6] coupling graph {len(edges)} edges, chi={chi}, "
        f"delays 1..{max(delays)}")

    # --- 5/6: operating-region PLAs, minimised by espresso ---------------
    funcs, unconnected = [], 0
    for i in range(N):
        sup, dd, rows = care_rows(i, W, pats, radius)
        if sup is None or dd == 0:
            funcs.append((None, None)); unconnected += 1; continue
        p = os.path.join(pla_dir, f"n{i}.pla")
        write_pla(p, sup, dd, rows, dc=True)
        funcs.append((sup, espresso_sop(p)))
    log(f"[4/6] {N - unconnected} neurons minimised with espresso "
        f"(radius {radius} don't-cares)")

    # --- 7: RTL ----------------------------------------------------------
    lut_sv = os.path.join(out, "hopfield_lut.sv")
    sched_sv = os.path.join(out, "hopfield_sched.sv")
    sched_np = os.path.join(out, "hopfield_sched_noparam.sv")
    terms = emit_lut(N, funcs, lut_sv)
    emit_sched(N, delays, sched_sv)
    # yosys elaborates the parameter away, so a gate-level hopfield_lut has no
    # N to override -- strip the override for builds against a synthesised netlist
    open(sched_np, "w").write(
        open(sched_sv).read().replace("hopfield_lut #(.N(N)) lut",
                                      "hopfield_lut lut"))
    log(f"[5/6] emitted RTL: {terms:,} product terms "
        f"({terms / max(1, N - unconnected):.1f} per neuron)")

    max_delay = max(delays)
    meta = dict(
        N=N, M=M, fan_in=d, radius=radius, seed=seed,
        kappa=kappa, patterns_stored=stored, all_stored=bool(stored == M),
        chi=chi, coupling_edges=len(edges), delays=delays,
        max_delay=max_delay, unconnected_neurons=unconnected,
        product_terms=terms,
        product_terms_per_neuron=terms / max(1, N - unconnected),
        suggested_timeout_behavioural=256 * max_delay + 200,
        suggested_timeout_gate_level=4000 * max_delay + 5000,
        suggested_drain=max_delay * 40 + 200,
        files=dict(lut="hopfield_lut.sv", sched="hopfield_sched.sv",
                   sched_noparam="hopfield_sched_noparam.sv", pla="pla/"),
        build_seconds=round(time.time() - t0, 1),
    )
    meta_path = os.path.join(out, "build_meta.json")
    json.dump(meta, open(meta_path, "w"), indent=2)
    log(f"[6/6] wrote {meta_path}")
    return meta, [lut_sv, sched_sv, sched_np]


def check_compile(lut_sv, sched_sv, sched_np, out):
    """iverilog -g2012 on both schedule variants against the behavioural LUT."""
    ok = True
    for tag, sched in (("param", sched_sv), ("noparam", sched_np)):
        r = subprocess.run(
            ["iverilog", "-g2012", "-o", os.path.join(out, f"_check_{tag}.vvp"),
             lut_sv, sched],
            capture_output=True, text=True)
        status = "OK" if r.returncode == 0 else "FAILED"
        print(f"  iverilog -g2012 [{tag}]: {status}")
        if r.returncode != 0:
            ok = False
            print(r.stderr[-1500:])
    return ok


def main():
    ap = argparse.ArgumentParser(
        description="parameters -> synthesisable clockless Hopfield RTL")
    ap.add_argument("--N", type=int, required=True)
    ap.add_argument("--M", type=int, required=True)
    ap.add_argument("--fanin", type=int, required=True)
    ap.add_argument("--radius", type=int, default=3)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-check", action="store_true",
                    help="skip the iverilog compile check")
    args = ap.parse_args()

    if not os.environ.get("ESPRESSO") and os.path.exists(DEFAULT_ESPRESSO):
        os.environ["ESPRESSO"] = DEFAULT_ESPRESSO
    # gen_dc_pla binds ESPRESSO at import time, so patch the bound name too
    import gen_dc_pla
    gen_dc_pla.ESPRESSO = os.environ.get("ESPRESSO", "espresso")
    import verify_dc_recall
    verify_dc_recall.ESPRESSO = gen_dc_pla.ESPRESSO
    print(f"espresso: {gen_dc_pla.ESPRESSO}")

    meta, files = build(args.N, args.M, args.fanin, args.radius, args.seed,
                        args.out)
    print()
    print(f"N={meta['N']} M={meta['M']} fan-in={meta['fan_in']} "
          f"kappa={meta['kappa']} chi={meta['chi']} "
          f"stored={meta['patterns_stored']}/{meta['M']} "
          f"terms={meta['product_terms']:,} "
          f"timeout(behav)={meta['suggested_timeout_behavioural']}")
    for f in files:
        print(f"  {f}")
    print(f"  {os.path.join(args.out, 'build_meta.json')}")
    if not args.no_check:
        print()
        if not check_compile(*files, args.out):
            sys.exit(1)


if __name__ == "__main__":
    main()
