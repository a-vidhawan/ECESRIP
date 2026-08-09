#!/usr/bin/env python3
"""
End-to-end RTL run at N=256: espresso SOPs -> SystemVerilog -> iverilog.

Every scaling result above N=16 so far comes from the Python schedule simulator
(evidence tier T3). This closes that gap for one point: it builds a real N=256
network, minimises every neuron with don't-cares, emits the SOPs as synthesisable
SystemVerilog, schedules them with the graph colouring, and runs the whole thing
under iverilog -- the same tool that produced the N=16 results.

If the RTL agrees with the simulator here, the scaling claim moves from T3 to T1
at N=256. If it disagrees, the simulator's periodic-firing approximation is
unsound above N=16 and every large-N number needs re-stating.
"""

import argparse, os, subprocess, sys, tempfile, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

from gen_dc_pla import build_net, care_rows, write_pla
from verify_dc_recall import espresso_sop, simulate, sop_eval
from schedule_hnn import graph_from_W, dsatur


def emit_lut(N, funcs, path):
    """Combinational LUT block: one sum-of-products per neuron."""
    L = ["// Auto-generated from espresso SOPs (operating-region don't-cares)",
         "`timescale 1ns/1ps",
         f"module hopfield_lut #(parameter int N = {N}) "
         "(input wire [N-1:0] s, output wire [N-1:0] s_next);"]
    for i, (sup, cubes) in enumerate(funcs):
        if sup is None or not cubes:
            L.append(f"    assign s_next[{i}] = s[{i}];  // unconnected neuron")
            continue
        terms = []
        for cube in cubes:
            lits = [f"{'' if b == '1' else '~'}s[{sup[j]}]" for j, b in cube]
            terms.append("(" + " & ".join(lits) + ")" if len(lits) > 1 else lits[0])
        L.append(f"    assign s_next[{i}] = " + " | ".join(terms) + ";")
    L.append("endmodule")
    open(path, "w").write("\n".join(L))
    return sum(len(c) for _, c in funcs if c)


def emit_sched(N, delays, path):
    L = [f"""// Graph-coloured clockless schedule
`timescale 1ns/1ps
module hopfield_clockless #(parameter int N = {N}) (
    input  wire          init_en,
    input  wire [N-1:0]  init_val,
    output wire [N-1:0]  s,
    output wire [N-1:0]  s_next,
    output wire          stable
);
    logic [N-1:0] s_settle;
    initial s_settle = '0;
    assign s = init_en ? init_val : s_settle;
    hopfield_lut #(.N(N)) lut (.s(s), .s_next(s_next));
    assign stable = (&(s|~s)) & (&(s_next|~s_next)) & (s === s_next);

    always @(init_en or init_val) begin
        if (init_en) s_settle <= #0 init_val;
    end

    always @(s_next or init_en or init_val) begin
        if (init_en) begin
            s_settle <= #0 init_val;
        end else begin"""]
    for i, d in enumerate(delays):
        L.append(f"            s_settle[{i}] <= #({d}) s_next[{i}];")
    L += ["        end", "    end", "endmodule"]
    open(path, "w").write("\n".join(L))


def emit_tb(N, inits, max_delay, tb_path, vec_path):
    nib = (N + 3) // 4
    with open(vec_path, "w") as f:
        for s in inits:
            f.write(format(int(s), f"0{nib}x") + "\n")
    timeout = 256 * max_delay + 200
    drain = max_delay + 5
    tb = f"""`timescale 1ns/1ps
module tb;
    parameter int N = {N};
    localparam int NTESTS  = {len(inits)};
    localparam int TIMEOUT = {timeout};
    localparam int DRAIN   = {drain};

    logic         init_en  = 1;
    logic [N-1:0] init_val = '0;
    wire  [N-1:0] s, s_next;
    wire          stable;

    hopfield_clockless #(.N(N)) dut (
        .init_en(init_en), .init_val(init_val),
        .s(s), .s_next(s_next), .stable(stable));

    logic [N-1:0] vectors [0:NTESTS-1];
    integer t, k;
    time t0;
    reg done;

    initial begin
        $readmemh("{vec_path}", vectors);
        for (t = 0; t < NTESTS; t = t + 1) begin
            init_en  = 1;
            init_val = vectors[t];
            #(DRAIN);
            init_en = 0;
            t0 = $time;
            done = 0;
            // forever+disable rather than fork/join_any (iverilog 12 aborts on the latter)
            begin : settle
                forever begin
                    #1;
                    if (stable) begin done = 1; disable settle; end
                    if ($time - t0 > TIMEOUT) disable settle;
                end
            end
            $display("TEST %0d init=%0h result=%0h settled=%0d time=%0d",
                     t, vectors[t], s, done, $time - t0);
            init_en = 1; init_val = '0; #(DRAIN);
        end
        $display("ALLDONE");
        $finish;
    end
endmodule
"""
    open(tb_path, "w").write(tb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=256)
    ap.add_argument("--M", type=int, default=4)
    ap.add_argument("--degree", type=int, default=16)
    ap.add_argument("--radius", type=int, default=3)
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--keep", default=None, help="dir to keep generated RTL in")
    args = ap.parse_args()

    N = args.N
    print(f"building N={N} M={args.M} fan-in={args.degree} radius={args.radius}")
    pats, W, kept = build_net(N, args.M, args.degree, args.seed)
    print(f"  fixed points kept: {kept}/{args.M}")

    n, edges = graph_from_W(W)
    colour = dsatur(n, edges)
    chi = max(colour.values()) + 1
    delays = [colour[i] + 1 for i in range(n)]
    bad = [(i, j) for i, j in edges if delays[i] == delays[j]]
    print(f"  coupling graph: {len(edges)} edges, chi={chi}, "
          f"delay-value conflicts={len(bad)}")
    assert not bad, "schedule invalid: coupled neurons share a delay value"

    out = args.keep or tempfile.mkdtemp()
    os.makedirs(out, exist_ok=True)
    print("  minimising every neuron with espresso (this is the slow part)...")
    t0 = time.time()
    funcs = []
    for i in range(N):
        sup, d, rows = care_rows(i, W, pats, args.radius)
        if sup is None or d == 0:
            funcs.append((None, None)); continue
        p = os.path.join(out, f"n{i}.pla")
        write_pla(p, sup, d, rows, dc=True)
        funcs.append((sup, espresso_sop(p)))
    total = emit_lut(N, funcs, os.path.join(out, "hopfield_lut.sv"))
    print(f"  {total:,} product terms across {N} neurons "
          f"({total/N:.1f} avg), {time.time()-t0:.0f}s")

    emit_sched(N, delays, os.path.join(out, "hopfield_clockless.sv"))

    # test vectors: HD 0..5 from stored patterns, plus the exact patterns
    rng = np.random.default_rng(args.seed + 7)
    P01 = ((pats + 1) // 2).astype(np.int8)
    cases = []
    for hd in (0, 1, 3, 5):
        for _ in range(args.trials // 4):
            m = int(rng.integers(args.M))
            v = P01[m].copy()
            if hd:
                v[rng.choice(N, size=hd, replace=False)] ^= 1
            cases.append((v, m, hd))
    inits = [int("".join(str(b) for b in v[::-1]), 2) for v, _, _ in cases]

    tb = os.path.join(out, "tb.sv")
    vec = os.path.join(out, "vec.hex")
    emit_tb(N, inits, max(delays), tb, vec)

    vvp = os.path.join(out, "sim.vvp")
    print("  compiling with iverilog...")
    c = subprocess.run(["iverilog", "-g2012", "-o", vvp,
                        os.path.join(out, "hopfield_lut.sv"),
                        os.path.join(out, "hopfield_clockless.sv"), tb],
                       capture_output=True, text=True)
    if c.returncode != 0:
        print("  COMPILE FAILED:\n" + c.stderr[:2000]); return
    print("  running...")
    r = subprocess.run(["vvp", vvp], capture_output=True, text=True, timeout=3600)
    lines = [l for l in r.stdout.splitlines() if l.startswith("TEST")]
    if not lines:
        print("  NO OUTPUT:\n" + (r.stdout[-1500:] or r.stderr[-1500:])); return

    # compare RTL against the Python simulator on identical inputs
    print()
    print(f"{'HD':>4}{'n':>5}{'RTL settled':>13}{'RTL recall':>12}"
          f"{'sim settled':>13}{'sim recall':>12}{'RTL==sim':>10}")
    print("-" * 69)
    by = {}
    for ln, (v, m, hd) in zip(lines, cases):
        f = ln.split()
        res = int(f[3].split("=")[1], 16)
        st = int(f[4].split("=")[1])
        rtl = np.array([(res >> b) & 1 for b in range(N)], dtype=np.int8)
        sim, oks = simulate(v.copy(), W, delays, funcs)
        rec = np.array_equal(rtl, P01[m])
        by.setdefault(hd, []).append((st, rec, oks,
                                      np.array_equal(sim, P01[m]),
                                      np.array_equal(rtl, sim)))
    agree_all = True
    for hd in sorted(by):
        g = by[hd]
        n_ = len(g)
        f = lambda k: 100 * sum(x[k] for x in g) / n_
        if f(4) < 100:
            agree_all = False
        print(f"{hd:>4}{n_:>5}{f(0):>12.0f}%{f(1):>11.0f}%"
              f"{f(2):>12.0f}%{f(3):>11.0f}%{f(4):>9.0f}%")
    print("-" * 69)
    print("RTL and simulator agree on every input" if agree_all else
          "MISMATCH -- the simulator approximation does not hold at this N")
    if args.keep:
        print(f"\nRTL kept in {out}")


if __name__ == "__main__":
    main()
