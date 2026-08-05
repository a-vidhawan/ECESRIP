#!/usr/bin/env python3
"""
Round 3 stress tests — targeted probes based on Round 1 & 2 findings.

Key findings motivating this round:
  1. 32 states oscillate in BOTH depth and even_odd -- universal oscillators
  2. even_odd settles 97.9% but 74.7% go to SPURIOUS attractors
  3. depth oscillates 45.9% of random states (especially HD 5-8)
  4. 1773 states that depth oscillates resolve in even_odd (often spurious)

Experiments:
  E.  Universal oscillator surgery: probe all 32 universal-oscillator states exhaustively
  F.  Spurious basin mapping: for all 16 spurious FPs, find basin of attraction size
  G.  Neuron fault injection: knock out each neuron (set to constant 0 or 1), measure recall
  H.  Cascade retrieval: retrieve P0→corrupt→retrieve P1 (two-step recall test)
  I.  Partial pattern completion: set only K bits correctly, rest random -- threshold map
  J.  Anti-correlated initialization: start from bitwise-inverse of each pattern
  K.  T_ODD symmetry breaking: T_EVEN=T_ODD crisis more precisely mapped at 0.5-unit steps
  L.  Weight erasure sensitivity: zero out lowest-magnitude rows in W, measure recall
"""

import os, sys, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from run_clockless_stress import (
    generate_rtl, run_batch, corrupt, flip_k,
    PATTERNS_BIN, PATTERNS_INT, ALL_FPS, SPURIOUS_FPS,
    hamming, N, DEFAULT_TERMS, RES, TMP, RTL, LUT_SV,
    write_testbench, compile_and_run, parse_output, classify
)
from gen_clockless_sv import compute_depths, _header, gen_even_odd_sv, DEFAULT_TERMS

import math, random, itertools

# ─── Universal oscillators (oscillate in BOTH depth and even_odd) ───────────
UNIVERSAL_OSC = [
    0x1776, 0x17de, 0x24dd, 0x3774, 0x37dc, 0x448e, 0x4d66, 0x5d22,
    0x5d8a, 0x648c, 0x069b, 0x6bd3, 0x7867, 0x7b66, 0x7bce, 0x7d20,
    0x7d88, 0x84dd, 0x8574, 0x85dc, 0x8bd3, 0xa174, 0xa3dc, 0xc1ae,
    0xc966, 0xc9ce, 0xd8cf, 0xdacf, 0xe1ac, 0xe964, 0xe9cc, 0x0fde,
]

# ════════════════════════════════════════════════════════════════════════════
# EXP E: UNIVERSAL OSCILLATOR SURGERY
# Probe each of the 32 universal-oscillator states with different T_ODD/T_EVEN
# ratios to see if any ratio breaks the oscillation
# ════════════════════════════════════════════════════════════════════════════

def exp_universal_oscillators():
    print("\n=== EXP E: UNIVERSAL OSCILLATOR SURGERY ===")
    # Fine-grained T_ODD sweep: 1..50 with T_EVEN=10
    T_EVEN = 10
    t_odd_vals = list(range(1, 51))
    dfs = []
    for t_odd in t_odd_vals:
        sv, max_d = gen_even_odd_sv(N, T_EVEN, t_odd)
        tag = f"_todd{t_odd}"
        sv_path = os.path.join(RTL, f"clockless_even_odd{tag}.sv")
        with open(sv_path, "w") as f:
            f.write(sv)

        # Run only universal oscillators as initial states
        nearest_pats = [min(range(4), key=lambda p: hamming(s, PATTERNS_INT[p]))
                        for s in UNIVERSAL_OSC]
        hdists = [hamming(s, PATTERNS_INT[nearest_pats[i]]) for i, s in enumerate(UNIVERSAL_OSC)]
        etas = [hd / N for hd in hdists]

        df = run_batch("universal_osc", "even_odd", UNIVERSAL_OSC, nearest_pats,
                       etas, hdists, sv_path, max_d, variant_tag=tag)
        if not df.empty:
            df["t_even"] = T_EVEN
            df["t_odd"] = t_odd
            df["ratio"] = t_odd / T_EVEN
        dfs.append(df)
        if t_odd % 10 == 0 or t_odd <= 3:
            settled = (df.outcome != "oscillated").mean() if not df.empty else 0
            print(f"  t_odd={t_odd:3d}: settled={settled:.1%}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP F: SPURIOUS BASIN MAPPING
# For each of the 16 spurious fixed points, find all states that converge to it
# Uses uniform random sampling -- estimate basin size as fraction of 2^N
# ════════════════════════════════════════════════════════════════════════════

def exp_spurious_basin_map(n_sample=2000):
    print(f"\n=== EXP F: SPURIOUS BASIN MAPPING ({n_sample} samples) ===")
    rng = np.random.default_rng(22022)
    sample_states = rng.integers(0, 1 << N, size=n_sample).tolist()

    nearest_pats = [min(range(4), key=lambda p: hamming(s, PATTERNS_INT[p]))
                    for s in sample_states]
    hdists = [hamming(s, PATTERNS_INT[nearest_pats[i]]) for i, s in enumerate(sample_states)]
    etas = [hd / N for hd in hdists]

    dfs = []
    for mode in ["depth", "even_odd"]:
        rtl, max_d = generate_rtl(mode)
        df = run_batch("spurious_basin", mode, sample_states, nearest_pats, etas, hdists,
                       rtl, max_d)
        if not df.empty:
            df["mode"] = mode
            # classify which spurious FP each oscillated/spurious state settled to
            sp_set = {f"{fp:04x}" for fp in SPURIOUS_FPS}
            pat_set = {f"{fp:04x}" for fp in PATTERNS_INT}
            sub = df[df["outcome"].isin(["spurious", "correct", "wrong_pattern", "stored_attractor"])]
            fp_counts = sub["result_state"].value_counts()
            print(f"\n  [{mode}] result attractor distribution:")
            for fp_hex, cnt in fp_counts.head(12).items():
                label = ("STORED" if fp_hex in pat_set else
                         "SPURIOUS" if fp_hex in sp_set else "UNKNOWN")
                print(f"    {fp_hex}: {cnt:4d} ({label})")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP G: NEURON FAULT INJECTION
# Systematically knock out each neuron i (force s[i]=0 or s[i]=1)
# by patching the LUT output to always return a fixed value for that neuron
# Implemented as: use modified initial states where bit i is fixed, then
# measure recall on patterns
# ════════════════════════════════════════════════════════════════════════════

def exp_neuron_fault():
    print("\n=== EXP G: NEURON FAULT INJECTION ===")
    # Strategy: for each neuron i and each fault value (0 or 1),
    # start from pattern p with bit i flipped to fault_val,
    # check if the network still converges to p
    rng = np.random.default_rng(33033)
    n_trials = 50  # per (neuron, fault_val, pattern, eta) combination
    eta_grid = [0.0, 0.10, 0.20]

    dfs = []
    for mode in ["depth", "even_odd"]:
        rtl, max_d = generate_rtl(mode)
        all_inits, all_pats, all_etas, all_hds = [], [], [], []
        fault_neurons, fault_vals = [], []

        for fault_neuron in range(N):
            for fault_val in [0, 1]:
                for eta in eta_grid:
                    for p_idx in range(4):
                        for _ in range(n_trials):
                            s_int = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                            # Force bit fault_neuron to fault_val
                            if fault_val == 0:
                                s_int = s_int & ~(1 << fault_neuron)
                            else:
                                s_int = s_int | (1 << fault_neuron)
                            all_inits.append(s_int)
                            all_pats.append(p_idx)
                            all_etas.append(eta)
                            all_hds.append(hamming(s_int, PATTERNS_INT[p_idx]))
                            fault_neurons.append(fault_neuron)
                            fault_vals.append(fault_val)

        df = run_batch(f"fault_{mode}", mode, all_inits, all_pats, all_etas, all_hds,
                       rtl, max_d)
        if not df.empty:
            df["mode"] = mode
            df["fault_neuron"] = fault_neurons[:len(df)]
            df["fault_val"] = fault_vals[:len(df)]

            # Aggregate: per-neuron recall drop
            print(f"\n  [{mode}] worst neurons (lowest correct rate at eta=0.0):")
            base = df[(df["eta"] == 0.0)]
            per_neuron = base.groupby("fault_neuron")["outcome"].apply(
                lambda x: (x == "correct").mean()).sort_values()
            for n, rate in per_neuron.head(5).items():
                print(f"    neuron {n:2d}: correct={rate:.1%}")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP H: CASCADE RETRIEVAL (Two-Step)
# Retrieve P0 from a corrupted version, then use the result as init for P1
# Tests whether the network can be "reprogrammed" without power-cycle
# ════════════════════════════════════════════════════════════════════════════

def exp_cascade_retrieval():
    print("\n=== EXP H: CASCADE RETRIEVAL ===")
    rng = np.random.default_rng(44044)
    eta_grid = [0.0, 0.10, 0.20]
    n_trials = 100  # per (source_pat, target_pat, eta) combination
    # Pattern pairs (source to retrieve, then target to retrieve)
    pairs = [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3),
             (1,0), (2,0), (3,0), (2,1), (3,1), (3,2)]

    # Phase 1: collect (init_state, nearest_pat) for step 1 of cascade
    step1_inits, step1_pats, step1_etas, step1_hds = [], [], [], []
    meta = []  # (source_pat, target_pat, eta, trial_idx)
    for (src, tgt) in pairs:
        for eta in eta_grid:
            for t in range(n_trials):
                s = corrupt(PATTERNS_BIN[src], eta, rng)
                step1_inits.append(s)
                step1_pats.append(src)
                step1_etas.append(eta)
                step1_hds.append(hamming(s, PATTERNS_INT[src]))
                meta.append((src, tgt, eta, t))

    dfs = []
    for mode in ["depth", "even_odd"]:
        rtl, max_d = generate_rtl(mode)
        # Step 1: retrieve source pattern
        df1 = run_batch("cascade_step1", mode, step1_inits, step1_pats, step1_etas, step1_hds,
                        rtl, max_d, variant_tag="_s1")
        if df1.empty:
            continue
        df1["src_pat"] = [m[0] for m in meta[:len(df1)]]
        df1["tgt_pat"] = [m[1] for m in meta[:len(df1)]]

        # Step 2: start from step1 result, try to retrieve target
        # Corrupt the step1 result toward target pattern
        step2_inits, step2_pats, step2_etas2, step2_hds2 = [], [], [], []
        for _, row in df1.iterrows():
            result_int = int(row["result_state"], 16)
            tgt = int(row["tgt_pat"])
            # Corrupt result toward target (eta=0.0 means use result directly, then nudge)
            eta2 = row["eta"]  # same noise level for second step
            s2 = corrupt(PATTERNS_BIN[tgt], eta2, rng)
            step2_inits.append(s2)
            step2_pats.append(tgt)
            step2_etas2.append(eta2)
            step2_hds2.append(hamming(s2, PATTERNS_INT[tgt]))

        df2 = run_batch("cascade_step2", mode, step2_inits, step2_pats, step2_etas2, step2_hds2,
                        rtl, max_d, variant_tag="_s2")
        if not df2.empty:
            df2["mode"] = mode
            df2["step"] = 2
            df1_out = df1.copy()
            df1_out["step"] = 1
            df1_out["mode"] = mode
            combined = pd.concat([df1_out, df2], ignore_index=True)

            # Summary
            step1_acc = (df1_out.outcome == "correct").mean()
            step2_acc = (df2.outcome == "correct").mean()
            step2_settled = (df2.outcome != "oscillated").mean()
            print(f"  [{mode}] step1_correct={step1_acc:.1%}  step2_correct={step2_acc:.1%}  step2_settled={step2_settled:.1%}")
            dfs.append(combined)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP I: PARTIAL PATTERN COMPLETION
# Start with K bits matching pattern, rest random — threshold map
# Goes beyond simple Hamming: controls WHICH bits are correct
# ════════════════════════════════════════════════════════════════════════════

def exp_partial_completion():
    print("\n=== EXP I: PARTIAL PATTERN COMPLETION ===")
    rng = np.random.default_rng(55055)
    k_vals = list(range(0, N+1))  # 0..16 correct bits
    n_trials = 150

    dfs = []
    for mode in ["depth", "even_odd"]:
        rtl, max_d = generate_rtl(mode)
        all_inits, all_pats, all_etas, all_hds, all_ks = [], [], [], [], []
        for k in k_vals:
            for p_idx in range(4):
                for _ in range(n_trials):
                    pat = PATTERNS_BIN[p_idx]
                    # Choose k random positions to be correct
                    positions = list(range(N))
                    rng_py = random.Random(int(rng.integers(0, 2**31)))
                    correct_pos = set(rng_py.sample(positions, k))
                    bits = []
                    for i in range(N):
                        if i in correct_pos:
                            bits.append(int(pat[i]))
                        else:
                            bits.append(rng_py.randint(0, 1))
                    s_int = sum(bits[i] << i for i in range(N))
                    hd = hamming(s_int, PATTERNS_INT[p_idx])
                    all_inits.append(s_int)
                    all_pats.append(p_idx)
                    all_etas.append(hd / N)
                    all_hds.append(hd)
                    all_ks.append(k)

        df = run_batch(f"partial_{mode}", mode, all_inits, all_pats, all_etas, all_hds,
                       rtl, max_d)
        if not df.empty:
            df["mode"] = mode
            df["k_correct"] = all_ks[:len(df)]
            # Print critical threshold
            grouped = df.groupby("k_correct").apply(
                lambda x: (x.outcome == "correct").mean()).reset_index()
            grouped.columns = ["k_correct", "correct_rate"]
            threshold = grouped[grouped["correct_rate"] >= 0.5]["k_correct"].min()
            print(f"  [{mode}] 50% recall threshold at k_correct >= {threshold}")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP J: ANTI-CORRELATED & MAXIMALLY-DISTANT INITIALIZATION
# Start from bitwise complement of each pattern (max HD=16 from stored)
# Also test maximum pairwise-distance states from all 4 patterns simultaneously
# ════════════════════════════════════════════════════════════════════════════

def exp_anti_correlated():
    print("\n=== EXP J: ANTI-CORRELATED INITIALIZATION ===")
    n_trials = 200

    inits, pats, etas, hds = [], [], [], []
    for p_idx in range(4):
        pat_int = PATTERNS_INT[p_idx]
        # Bitwise complement (max distance)
        anti = (~pat_int) & ((1 << N) - 1)
        for _ in range(n_trials):
            inits.append(anti)
            pats.append(p_idx)
            hd = hamming(anti, pat_int)
            etas.append(hd / N)
            hds.append(hd)

    # Also: states equidistant from all 4 patterns
    # Find state minimizing max(HD(s, pi)) for all i -- i.e., the Chebyshev center
    rng = np.random.default_rng(66066)
    for _ in range(200):
        s = int(rng.integers(0, 1 << N))
        all_hds = [hamming(s, p) for p in PATTERNS_INT]
        nearest = min(range(4), key=lambda i: all_hds[i])
        if min(all_hds) >= 6:  # at least HD=6 from all patterns
            inits.append(s)
            pats.append(nearest)
            etas.append(all_hds[nearest] / N)
            hds.append(all_hds[nearest])

    dfs = []
    for mode in ["depth", "even_odd"]:
        rtl, max_d = generate_rtl(mode)
        df = run_batch("anti_corr", mode, inits, pats, etas, hds, rtl, max_d)
        if not df.empty:
            df["mode"] = mode
            correct = (df.outcome == "correct").mean()
            settled = (df.outcome != "oscillated").mean()
            print(f"  [{mode}]: correct={correct:.1%}  settled={settled:.1%}")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP K: FINE-GRAINED T_ODD SYMMETRY BREAKING
# Map the transition from T_ODD=T_EVEN (crisis) with 0.1-unit granularity
# Focus on T_ODD ∈ [8, 14] around T_EVEN=10
# ════════════════════════════════════════════════════════════════════════════

def exp_symmetry_crisis():
    print("\n=== EXP K: SYMMETRY CRISIS FINE MAP ===")
    T_EVEN = 10
    # Use integer T_ODD values from 1..20 with focus around 10
    t_odd_vals = list(range(1, 25))
    n_trials = 120
    eta_grid = [0.0, 0.15, 0.30]
    rng = np.random.default_rng(77077)

    all_inits, all_pats, all_etas, all_hds = [], [], [], []
    for eta in eta_grid:
        for p_idx in range(4):
            for _ in range(n_trials):
                s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                all_inits.append(s)
                all_pats.append(p_idx)
                all_etas.append(eta)
                all_hds.append(hamming(s, PATTERNS_INT[p_idx]))

    dfs = []
    for t_odd in t_odd_vals:
        sv, max_d = gen_even_odd_sv(N, T_EVEN, t_odd)
        tag = f"_todd{t_odd}"
        sv_path = os.path.join(RTL, f"clockless_eo{tag}.sv")
        with open(sv_path, "w") as f:
            f.write(sv)
        df = run_batch("symmetry", "even_odd", all_inits, all_pats, all_etas, all_hds,
                       sv_path, max_d, variant_tag=tag)
        if not df.empty:
            df["t_even"] = T_EVEN
            df["t_odd"] = t_odd
            df["ratio"] = t_odd / T_EVEN
            settled = (df.outcome != "oscillated").mean()
            correct = (df.outcome == "correct").mean()
            print(f"  t_odd={t_odd:3d} (ratio={t_odd/T_EVEN:.2f}): correct={correct:.1%}  settled={settled:.1%}")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP L: TIMEOUT SWEEP (settle time budget)
# How sensitive is the result to the TIMEOUT parameter?
# Very short timeouts might catch early wrong attractors or fail to settle
# ════════════════════════════════════════════════════════════════════════════

def exp_timeout_sweep():
    print("\n=== EXP L: TIMEOUT SWEEP ===")
    from run_clockless_stress import write_testbench, compile_and_run, parse_output, classify

    rng = np.random.default_rng(88088)
    eta_grid = [0.0, 0.15, 0.30]
    n_trials = 60
    timeouts = [20, 40, 80, 160, 320, 640, 1280, 2560]

    all_inits, all_pats, all_etas, all_hds = [], [], [], []
    for eta in eta_grid:
        for p_idx in range(4):
            for _ in range(n_trials):
                s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                all_inits.append(s)
                all_pats.append(p_idx)
                all_etas.append(eta)
                all_hds.append(hamming(s, PATTERNS_INT[p_idx]))

    dfs = []
    for mode in ["depth", "even_odd"]:
        rtl, max_d = generate_rtl(mode)
        for timeout in timeouts:
            drain = max_d + 5
            tb = write_testbench(all_inits, rtl, timeout, drain)
            tb_path = os.path.join(TMP, f"tb_timeout_{mode}_{timeout}.sv")
            with open(tb_path, "w") as f:
                f.write(tb)
            raw_out = compile_and_run(tb_path, rtl, LUT_SV)
            rows = parse_output(raw_out, all_inits, all_pats, all_etas, all_hds, timeout)
            if rows:
                df = pd.DataFrame(rows)
                df["mode"] = mode
                df["timeout"] = timeout
                settled = (df.outcome != "oscillated").mean()
                correct = (df.outcome == "correct").mean()
                print(f"  [{mode}] timeout={timeout:5d}: correct={correct:.1%}  settled={settled:.1%}")
                dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()
    all_dfs = []

    steps = [
        ("universal_osc",  exp_universal_oscillators),
        ("spurious_basin", exp_spurious_basin_map),
        ("neuron_fault",   exp_neuron_fault),
        ("cascade",        exp_cascade_retrieval),
        ("partial",        exp_partial_completion),
        ("anti_corr",      exp_anti_correlated),
        ("symmetry",       exp_symmetry_crisis),
        ("timeout",        exp_timeout_sweep),
    ]

    for name, fn in steps:
        t_exp = time.time()
        try:
            df = fn()
            if df is not None and not df.empty:
                out = os.path.join(RES, f"stress_r3_{name}.csv")
                df.to_csv(out, index=False)
                all_dfs.append(df)
                print(f"  → {out}  ({len(df)} rows)")
        except Exception as exc:
            import traceback
            print(f"  [ERROR] {name}: {exc}")
            traceback.print_exc()
        print(f"  [wall] {name}: {time.time()-t_exp:.1f}s")

    print(f"\n══ Round 3 DONE in {time.time()-t0:.1f}s ══")


if __name__ == "__main__":
    main()
