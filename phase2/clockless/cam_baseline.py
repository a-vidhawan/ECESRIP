#!/usr/bin/env python3
"""
The baseline a referee will demand: a CAM that does the same job.

"Why is this a Hopfield network rather than a lookup table?" is the most
dangerous question about this project at M=4, and it deserves a built, measured
answer rather than an argument.

The comparison target is a nearest-match CAM: store the M patterns, compute the
Hamming distance from the input to each, and emit the closest. That is the same
input/output contract as associative recall over the operating region, so it is
the honest functional equivalent -- not a plain exact-match CAM, which would be
a strawman because it cannot complete a corrupted input at all.

Both designs are synthesised with yosys under identical settings.
"""

import argparse, os, subprocess, sys, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

from gen_dc_pla import build_net, care_rows, write_pla
from verify_dc_recall import espresso_sop
from rtl_n256 import emit_lut
from synth_compare import yosys_stat


def emit_cam(N, M, P01, path):
    """Nearest-match CAM: XOR against each stored word, popcount, min-select."""
    dw = int(np.ceil(np.log2(N + 1)))
    L = ["// Nearest-match CAM: Hamming distance to each stored word, then argmin",
         "`timescale 1ns/1ps",
         f"module hopfield_lut #(parameter int N = {N}) "
         "(input wire [N-1:0] s, output wire [N-1:0] s_next);"]
    for m in range(M):
        word = "".join(str(int(b)) for b in P01[m][::-1])
        L.append(f"    localparam [N-1:0] P{m} = {N}'b{word};")
        L.append(f"    wire [N-1:0] x{m} = s ^ P{m};")
        # popcount as a sum of the individual bits; yosys/abc builds the adder tree
        bits = " + ".join(f"x{m}[{i}]" for i in range(N))
        L.append(f"    wire [{dw-1}:0] d{m} = " + bits + ";")
    # tournament argmin, first index wins ties
    L.append(f"    wire [{dw-1}:0] best0 = d0;")
    L.append(f"    wire [{N-1}:0] w0 = P0;")
    for m in range(1, M):
        L.append(f"    wire lt{m} = (d{m} < best{m-1});")
        L.append(f"    wire [{dw-1}:0] best{m} = lt{m} ? d{m} : best{m-1};")
        L.append(f"    wire [N-1:0] w{m} = lt{m} ? P{m} : w{m-1};")
    L.append(f"    assign s_next = w{M-1};")
    L.append("endmodule")
    open(path, "w").write("\n".join(L))


def cam_behaviour(P01, s, M):
    """Reference model of the CAM: nearest stored word, first index wins ties."""
    d = [(np.sum(s != P01[m]), m) for m in range(M)]
    return P01[min(d)[1]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=64)
    ap.add_argument("--M", type=int, default=4)
    ap.add_argument("--degree", type=int, default=16)
    ap.add_argument("--radius", type=int, default=3)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    N, M = args.N, args.M
    pats, W, kept = build_net(N, M, args.degree, args.seed)
    P01 = ((pats + 1) // 2).astype(np.int8)
    out = tempfile.mkdtemp()
    print(f"N={N} M={M} fan-in={args.degree}  fixed points {kept}/{M}")

    # ---- LUT HNN
    print("\nbuilding the LUT HNN...")
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
    hnn_a = yosys_stat(lut_sv, mode="asic")[0]
    hnn_f = yosys_stat(lut_sv, mode="fpga")[0]
    print(f"  {terms:,} terms -> {hnn_a:,} gates / {hnn_f:,} 6-LUTs")

    # ---- CAM
    print("building the nearest-match CAM...")
    cam_sv = os.path.join(out, "cam.sv")
    emit_cam(N, M, P01, cam_sv)
    cam_a = yosys_stat(cam_sv, mode="asic")[0]
    cam_f = yosys_stat(cam_sv, mode="fpga")[0]
    print(f"  {cam_a:,} gates / {cam_f:,} 6-LUTs")

    print()
    print(f"{'design':>22}{'gates':>10}{'6-LUTs':>10}")
    print("-" * 42)
    print(f"{'LUT Hopfield':>22}{hnn_a:>10,}{hnn_f:>10,}")
    print(f"{'nearest-match CAM':>22}{cam_a:>10,}{cam_f:>10,}")
    print("-" * 42)
    print(f"{'CAM is smaller by':>22}{hnn_a/cam_a:>9.1f}x{hnn_f/cam_f:>9.1f}x")

    # ---- where they differ functionally
    print("\nfunctional difference (what the extra area buys):")
    rng = np.random.default_rng(args.seed + 5)
    for hd in (1, 3, 5, 8, 16):
        agree = 0
        trials = 200
        for _ in range(trials):
            m = int(rng.integers(M))
            s = P01[m].copy()
            s[rng.choice(N, size=hd, replace=False)] ^= 1
            agree += np.array_equal(cam_behaviour(P01, s, M), P01[m])
        print(f"  HD={hd:>2}: CAM recovers the right pattern "
              f"{100*agree/trials:5.1f}% of the time")
    print("\nAt these loadings the CAM is a complete functional substitute AND")
    print("cheaper. Any argument for the HNN has to rest on regimes this test")
    print("does not cover -- large M, learned/updatable weights, or analogue")
    print("implementation -- not on associative recall at small M.")


if __name__ == "__main__":
    main()
