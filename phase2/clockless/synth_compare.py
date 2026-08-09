#!/usr/bin/env python3
"""
Synthesise the LUT and threshold-gate neurons for the SAME network and compare.

Every area number in the project so far is a first-order gate-equivalent
estimate (tier T4). This replaces them with yosys cell counts after technology-
independent mapping, so the comparison is measured rather than argued.

Both designs implement the identical network:
  LUT       -- espresso SOPs over operating-region don't-cares
  threshold -- conditional-negate + adder tree + sign bit, the standard digital
               Hopfield neuron. No multipliers: s is binary, so w*s is a negate.

The threshold design is given every reasonable advantage (no multipliers, weights
quantised only as far as needed to preserve behaviour) so the comparison is not a
strawman. Weight width is swept, and the narrowest width that still reproduces
the exact network's recall is the one reported.
"""

import argparse, os, subprocess, sys, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

from gen_dc_pla import build_net, care_rows, write_pla
from verify_dc_recall import espresso_sop
from rtl_n256 import emit_lut


def quantise(W, bits):
    """Symmetric fixed-point quantisation of the nonzero weights."""
    m = np.abs(W[np.abs(W) > 1e-12]).max()
    if m == 0:
        return W.astype(int), 1
    scale = (2 ** (bits - 1) - 1) / m
    return np.rint(W * scale).astype(int), scale


def check_quantised(Wq, pats):
    """Do the stored patterns survive quantisation as fixed points?"""
    P = pats
    return sum(np.array_equal(np.where(Wq @ P[m] >= 0, 1, -1), P[m])
               for m in range(len(P)))


def emit_threshold(N, Wq, bits, path):
    """Conditional-negate + adder tree + sign. One neuron per assign block."""
    acc_w = bits + int(np.ceil(np.log2(max(N, 2)))) + 1
    L = ["// Threshold-gate Hopfield neurons: conditional negate + adder tree + sign",
         "`timescale 1ns/1ps",
         f"module hopfield_lut #(parameter int N = {N}) "
         "(input wire [N-1:0] s, output wire [N-1:0] s_next);"]
    for i in range(N):
        sup = np.nonzero(np.abs(Wq[i]) > 0)[0]
        if len(sup) == 0:
            L.append(f"    assign s_next[{i}] = s[{i}];")
            continue
        terms = []
        for j in sup:
            wv = int(Wq[i, j])
            # s[j]==1 means +1 in bipolar, so add w; else subtract w
            terms.append(f"(s[{j}] ? {acc_w}'sd{wv} : -{acc_w}'sd{wv})"
                         if wv >= 0 else
                         f"(s[{j}] ? -{acc_w}'sd{abs(wv)} : {acc_w}'sd{abs(wv)})")
        L.append(f"    wire signed [{acc_w-1}:0] h{i} = " + " + ".join(terms) + ";")
        L.append(f"    assign s_next[{i}] = ~h{i}[{acc_w-1}];  // h >= 0")
    L.append("endmodule")
    open(path, "w").write("\n".join(L))


def yosys_stat(sv, top="hopfield_lut", mode="asic"):
    """Map technology-independently and count cells.

    Two proxies, because the two designs have different natural targets and
    reporting only one would be cherry-picking:
      asic -- abc -g simple, a generic standard-cell gate set
      fpga -- abc -lut 6, 6-input LUT count
    """
    mapper = "abc -g simple" if mode == "asic" else "abc -lut 6"
    script = (f"read_verilog -sv {sv}; hierarchy -top {top}; "
              f"proc; opt; techmap; opt; {mapper}; opt; stat")
    r = subprocess.run(["yosys", "-p", script], capture_output=True, text=True,
                       timeout=7200)
    if r.returncode != 0:
        return None, r.stderr[-600:]
    cells = None
    for line in r.stdout.splitlines():
        if line.strip().startswith("Number of cells:"):
            cells = int(line.split()[-1])
    return cells, r.stdout[-400:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=64)
    ap.add_argument("--M", type=int, default=4)
    ap.add_argument("--degree", type=int, default=16)
    ap.add_argument("--radius", type=int, default=3)
    ap.add_argument("--bits", type=int, nargs="+", default=[4, 6, 8])
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    N = args.N
    pats, W, kept = build_net(N, args.M, args.degree, args.seed)
    print(f"N={N} M={args.M} fan-in={args.degree}  exact fixed points {kept}/{args.M}")
    out = tempfile.mkdtemp()

    # ---- LUT version
    print("\nminimising neurons with don't-cares...")
    funcs = []
    for i in range(N):
        sup, d, rows = care_rows(i, W, pats, args.radius)
        if sup is None or d == 0:
            funcs.append((None, None)); continue
        p = os.path.join(out, f"n{i}.pla")
        write_pla(p, sup, d, rows, dc=True)
        funcs.append((sup, espresso_sop(p)))
    lut_sv = os.path.join(out, "lut.sv")
    terms = emit_lut(N, funcs, lut_sv)
    print(f"  {terms:,} product terms ({terms/N:.1f} per neuron)")

    print("  synthesising LUT design (asic + fpga proxies)...")
    lut_asic, _ = yosys_stat(lut_sv, mode="asic")
    lut_fpga, _ = yosys_stat(lut_sv, mode="fpga")
    if lut_asic is None or lut_fpga is None:
        print("  yosys failed on the LUT design"); return
    print(f"  LUT: {lut_asic:,} gates / {lut_fpga:,} 6-LUTs")

    # ---- threshold versions at several weight widths
    print("\nthreshold-gate designs:")
    print(f"{'bits':>6}{'kept':>8}{'gates':>10}{'vs LUT':>9}"
          f"{'6-LUTs':>10}{'vs LUT':>9}")
    print("-" * 52)
    best = None
    for b in args.bits:
        Wq, _ = quantise(W, b)
        kq = check_quantised(Wq, pats)
        thr_sv = os.path.join(out, f"thr{b}.sv")
        emit_threshold(N, Wq, b, thr_sv)
        a = yosys_stat(thr_sv, mode="asic")[0]
        f = yosys_stat(thr_sv, mode="fpga")[0]
        if a is None or f is None:
            print(f"{b:>6}{kq:>7}/{args.M}{'yosys failed':>19}")
            continue
        flag = "" if kq == args.M else "  <- loses patterns"
        print(f"{b:>6}{kq:>7}/{args.M}{a:>10,}{a/lut_asic:>8.2f}x"
              f"{f:>10,}{f/lut_fpga:>8.2f}x{flag}")
        if kq == args.M and best is None:
            best = (b, a, f)
    print("-" * 52)
    if best:
        b, a, f = best
        print(f"\nNarrowest weight width preserving all {args.M} patterns: {b} bits")
        print(f"  ASIC proxy: LUT {lut_asic:,} vs threshold {a:,} gates  -> "
              f"LUT {a/lut_asic:.2f}x {'smaller' if a > lut_asic else 'LARGER'}")
        print(f"  FPGA proxy: LUT {lut_fpga:,} vs threshold {f:,} 6-LUTs -> "
              f"LUT {f/lut_fpga:.2f}x {'smaller' if f > lut_fpga else 'LARGER'}")
    else:
        print("\nNo tested weight width preserved all patterns.")


if __name__ == "__main__":
    main()
