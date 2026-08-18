#!/usr/bin/env python3
"""
PHASE 7b -- gate-level hazard test: do REAL glitches change the settled state?

The injection study (phase 7) showed the network tolerates spurious commits, but
it invents the glitches. This produces them: the neuron logic is synthesised down
to primitive gates, each gate type is given a different propagation delay so path
lengths through the SOP are genuinely unequal, and the network is simulated in
iverilog. Glitches then arise from the circuit rather than from a random number
generator.

Method
  1. build the network, minimise each neuron with operating-region don't-cares
  2. yosys: techmap + abc -g simple  ->  primitive gate netlist
  3. supply a cell library where each gate type has its own delay, so the AND/OR
     planes have unequal arrival times (this is what creates hazards)
  4. instantiate that netlist inside the same clockless wrapper
  5. run identical vectors through the ZERO-DELAY behavioural model and the
     gate-level model and compare the settled states

Any difference is hazard-induced, because the two designs are logically
equivalent by construction.
"""

import argparse, json, os, subprocess, sys, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

from gen_dc_pla import care_rows, write_pla
from verify_dc_recall import espresso_sop
from improve_capacity import train_margin_auto, n_fixed
from scale_study import make_support
from schedule_hnn import graph_from_W, dsatur
from rtl_n256 import emit_lut, emit_sched

# Distinct delay per gate type. Equal delays would balance every path and hide
# the hazards we are trying to observe, so the point is that these differ.
CELL_LIB = r"""
`timescale 1ns/1ps
module \$_NOT_ (input A, output Y); assign #1 Y = ~A; endmodule
module \$_AND_ (input A, B, output Y); assign #3 Y = A & B;   endmodule
module \$_NAND_ (input A, B, output Y); assign #2 Y = ~(A & B);endmodule
module \$_OR_ (input A, B, output Y); assign #4 Y = A | B;   endmodule
module \$_NOR_ (input A, B, output Y); assign #2 Y = ~(A | B);endmodule
module \$_XOR_ (input A, B, output Y); assign #5 Y = A ^ B;   endmodule
module \$_XNOR_ (input A, B, output Y); assign #5 Y = ~(A ^ B);endmodule
module \$_ANDNOT_ (input A, B, output Y); assign #3 Y = A & ~B;endmodule
module \$_ORNOT_ (input A, B, output Y); assign #3 Y = A | ~B;endmodule
module \$_MUX_ (input A, B, S, output Y); assign #3 Y = S ? B : A; endmodule
module \$_AOI3_ (input A, B, C, output Y); assign #3 Y = ~((A&B)|C); endmodule
module \$_OAI3_ (input A, B, C, output Y); assign #3 Y = ~((A|B)&C); endmodule
module \$_AOI4_ (input A, B, C, D, output Y); assign #4 Y = ~((A&B)|(C&D)); endmodule
module \$_OAI4_ (input A, B, C, D, output Y); assign #4 Y = ~((A|B)&(C|D)); endmodule
"""


def build(N, M, radius, seed, out):
    pats = np.random.default_rng(seed + M).choice([-1, 1], size=(M, N)).astype(float)
    mask = make_support(N, min(N - 1, max(16, 4 * M)), "regular",
                        np.random.default_rng(seed))
    W, kappa = train_margin_auto(pats, mask, seed=seed)
    funcs = []
    for i in range(N):
        sup, d, rows = care_rows(i, W, pats, radius)
        if sup is None or d == 0:
            funcs.append((None, None)); continue
        p = os.path.join(out, f"n{i}.pla")
        write_pla(p, sup, d, rows, dc=True)
        funcs.append((sup, espresso_sop(p)))
    terms = emit_lut(N, funcs, os.path.join(out, "lut_behav.sv"))
    return pats, W, kappa, terms


def synth_gates(out):
    """Map the behavioural LUT to primitive gates."""
    src = os.path.join(out, "lut_behav.sv")
    dst = os.path.join(out, "lut_gates.v")
    script = (f"read_verilog -sv {src}; hierarchy -top hopfield_lut; "
              f"proc; opt; techmap; opt; abc -g simple; opt_clean; "
              f"write_verilog -noexpr -noattr {dst}")
    r = subprocess.run(["yosys", "-p", script], capture_output=True, text=True,
                       timeout=7200)
    if r.returncode != 0:
        return None, r.stderr[-800:]
    n = sum(1 for ln in open(dst) if "\\$_" in ln and "(" in ln)
    return dst, n


def emit_tb(N, inits, max_delay, tb, vec):
    nib = (N + 3) // 4
    with open(vec, "w") as f:
        for s in inits:
            f.write(format(int(s), f"0{nib}x") + "\n")
    # generous timeout: gate delays add real propagation time on top of the
    # scheduling delays, so the behavioural budget is not enough here
    timeout = 4000 * max_delay + 5000
    open(tb, "w").write(f"""`timescale 1ns/1ps
module tb;
  parameter int N = {N};
  localparam int NTESTS = {len(inits)};
  localparam int TIMEOUT = {timeout};
  localparam int DRAIN = {max_delay * 40 + 200};
  logic         init_en = 1;
  logic [N-1:0] init_val = '0;
  wire  [N-1:0] s, s_next;
  wire          stable;
  hopfield_clockless #(.N(N)) dut (.init_en(init_en), .init_val(init_val),
                                   .s(s), .s_next(s_next), .stable(stable));
  logic [N-1:0] vectors [0:NTESTS-1];
  integer t; time t0; reg done;
  initial begin
    $readmemh("{vec}", vectors);
    for (t = 0; t < NTESTS; t = t + 1) begin
      init_en = 1; init_val = vectors[t]; #(DRAIN);
      init_en = 0; t0 = $time; done = 0;
      begin : settle
        forever begin
          #1;
          if (stable) begin done = 1; disable settle; end
          if ($time - t0 > TIMEOUT) disable settle;
        end
      end
      $display("TEST %0d init=%0h result=%0h settled=%0d", t, vectors[t], s, done);
      init_en = 1; init_val = '0; #(DRAIN);
    end
    $display("ALLDONE"); $finish;
  end
endmodule
""")


def run_sim(files, out, tag):
    vvp = os.path.join(out, f"{tag}.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-o", vvp] + files,
                       capture_output=True, text=True)
    if c.returncode != 0:
        return None, c.stderr[-800:]
    r = subprocess.run(["vvp", vvp], capture_output=True, text=True, timeout=7200)
    res = {}
    for ln in r.stdout.splitlines():
        if ln.startswith("TEST"):
            f = ln.split()
            res[int(f[1])] = (f[3].split("=")[1], int(f[4].split("=")[1]))
    return res, r.stdout[-400:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=64)
    ap.add_argument("--M", type=int, default=8)
    ap.add_argument("--radius", type=int, default=3)
    ap.add_argument("--hd", type=int, default=0)
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--delay-scale", type=int, default=1,
                    help="multiply the scheduling delays. The schedule only "
                         "sequences commits correctly if its delays exceed the "
                         "combinational propagation delay through the SOP; at "
                         "scale=1 the gate delays dominate and the colouring is "
                         "meaningless, which is a design-rule violation rather "
                         "than a hazard effect.")
    ap.add_argument("--keep", default=None)
    args = ap.parse_args()

    N, M = args.N, args.M
    hd = args.hd or max(3, N // 10)
    out = args.keep or tempfile.mkdtemp()
    os.makedirs(out, exist_ok=True)
    print(f"N={N} M={M} radius={args.radius} HD={hd}")

    pats, W, kappa, terms = build(N, M, args.radius, args.seed, out)
    print(f"  kappa={kappa}, stored {n_fixed(W, pats)}/{M}, {terms:,} product terms")

    n, edges = graph_from_W(W)
    colour = dsatur(n, edges)
    delays = [(colour[i] + 1) * args.delay_scale for i in range(n)]
    emit_sched(N, delays, os.path.join(out, "sched.sv"))
    # yosys elaborates the parameter away, so the gate-level netlist's
    # hopfield_lut has no N to override -- strip the override for that build
    sched_gate = os.path.join(out, "sched_gate.sv")
    open(sched_gate, "w").write(
        open(os.path.join(out, "sched.sv")).read()
        .replace("hopfield_lut #(.N(N)) lut", "hopfield_lut lut"))
    print(f"  chi={max(colour.values())+1}, max scheduling delay={max(delays)}")

    print("  synthesising to primitive gates...")
    gates, ng = synth_gates(out)
    if gates is None:
        print("  yosys failed:\n" + ng); return
    print(f"  {ng:,} gate instances")
    open(os.path.join(out, "cells.v"), "w").write(CELL_LIB)

    P01 = ((pats + 1) // 2).astype(np.int8)
    rng = np.random.default_rng(args.seed + 21)
    cases = []
    for _ in range(args.trials):
        m = int(rng.integers(M))
        v = P01[m].copy()
        v[rng.choice(N, size=hd, replace=False)] ^= 1
        cases.append((v, m))
    inits = [int("".join(str(b) for b in v[::-1]), 2) for v, _ in cases]

    tb = os.path.join(out, "tb.sv"); vec = os.path.join(out, "vec.hex")
    emit_tb(N, inits, max(delays), tb, vec)

    print("  simulating ZERO-DELAY behavioural model...")
    behav, err = run_sim([os.path.join(out, "lut_behav.sv"),
                          os.path.join(out, "sched.sv"), tb], out, "behav")
    if not behav:
        print("  failed:\n" + str(err)); return

    print("  simulating GATE-LEVEL model with unequal path delays...")
    gate, err = run_sim([gates, os.path.join(out, "cells.v"),
                         sched_gate, tb], out, "gate")
    if not gate:
        print("  failed:\n" + str(err)); return

    agree = bset = gset = bok = gok = 0
    for i, (v, m) in enumerate(cases):
        if i not in behav or i not in gate:
            continue
        tgt = int("".join(str(b) for b in P01[m][::-1]), 2)
        b_res, b_st = behav[i]; g_res, g_st = gate[i]
        bset += b_st; gset += g_st
        bok += b_st and int(b_res, 16) == tgt
        gok += g_st and int(g_res, 16) == tgt
        agree += (b_res.lower() == g_res.lower())
    n_ = len(cases)
    print()
    print(f"{'':<22}{'settled':>10}{'recall':>10}")
    print("-" * 42)
    print(f"{'zero-delay behavioural':<22}{100*bset/n_:>9.0f}%{100*bok/n_:>9.0f}%")
    print(f"{'gate-level (glitchy)':<22}{100*gset/n_:>9.0f}%{100*gok/n_:>9.0f}%")
    print("-" * 42)
    print(f"identical settled state on {agree}/{n_} inputs "
          f"({100*agree/n_:.0f}%)")
    print()
    print("The two designs are logically equivalent, so any disagreement is")
    print("caused by glitches in the gate-level logic.")
    json.dump(dict(N=N, M=M, hd=hd, kappa=kappa, terms=terms, gates=ng,
                   trials=n_, behav_settled=bset / n_, behav_recall=bok / n_,
                   gate_settled=gset / n_, gate_recall=gok / n_,
                   agreement=agree / n_),
              open(os.path.join(HERE, "results", "gate_level_hazard.json"), "w"),
              indent=2)
    if args.keep:
        print(f"\nnetlists kept in {out}")


if __name__ == "__main__":
    main()
