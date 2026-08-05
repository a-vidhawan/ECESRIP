#!/usr/bin/env python3
"""
Round 4 stress tests -- deep dives motivated by Round 3 findings.

Key R3 discoveries:
  E. Universal oscillators: settle 18.8% for T_ODD<20, drop to 0% at T_ODD>=20
     -- hard bifurcation at ratio=2x!
  K. Symmetry crisis is sharp and asymmetric: T_ODD<T_EVEN -> different behavior
  G. Neuron fault injection: expect large variance across neurons

Round 4 targets:
  M. Bifurcation search: exhaustively characterize T_ODD=19 vs T_ODD=20 transition
     for ALL 2^16 states (using Python sim for speed, verify subset in SV)
  N. LUT entry corruption: randomly flip K LUT outputs, measure recall decay
  O. Pattern interpolation: linear interpolation path P0->P1 in Hamming space
  P. Basin boundary: binary search for recall boundary along each pattern pair axis
  Q. Memory capacity test: vary number of stored patterns 1..4 and measure recall
  R. Synchronous vs async: Python synchronous HNN vs SV async, full 2^16 state map
"""

import os, sys, time, math, random, itertools
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

W_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                      "phase1", "results", "truth_tables",
                      "pseudo_s_maxprune", "W_pruned.npy")

# ════════════════════════════════════════════════════════════════════════════
# EXP M: BIFURCATION DEEP DIVE (T_ODD 18/19/20/21 boundary)
# For the 32 universal oscillators: what EXACTLY changes at T_ODD=20?
# Also test range 15-25 with full pattern set (not just universal osc)
# ════════════════════════════════════════════════════════════════════════════

def exp_bifurcation():
    print("\n=== EXP M: BIFURCATION DEEP DIVE ===")
    T_EVEN = 10
    t_odd_fine = list(range(15, 26))  # 15..25 inclusive
    rng = np.random.default_rng(11111)

    # Test on: universal oscillators + noise-corrupted patterns
    UNIVERSAL_OSC = [
        0x1776, 0x17de, 0x24dd, 0x3774, 0x37dc, 0x448e, 0x4d66, 0x5d22,
        0x5d8a, 0x648c, 0x069b, 0x6bd3, 0x7867, 0x7b66, 0x7bce, 0x7d20,
        0x7d88, 0x84dd, 0x8574, 0x85dc, 0x8bd3, 0xa174, 0xa3dc, 0xc1ae,
        0xc966, 0xc9ce, 0xd8cf, 0xdacf, 0xe1ac, 0xe964, 0xe9cc, 0x0fde,
    ]

    eta_grid = [0.0, 0.20, 0.40]
    n_trials = 80
    extra_inits, extra_pats, extra_etas, extra_hds = [], [], [], []
    for eta in eta_grid:
        for p_idx in range(4):
            for _ in range(n_trials):
                s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                extra_inits.append(s); extra_pats.append(p_idx)
                extra_etas.append(eta)
                extra_hds.append(hamming(s, PATTERNS_INT[p_idx]))

    # Combine universal osc + corrupted patterns
    u_pats = [min(range(4), key=lambda p: hamming(s, PATTERNS_INT[p])) for s in UNIVERSAL_OSC]
    u_hds = [hamming(s, PATTERNS_INT[u_pats[i]]) for i, s in enumerate(UNIVERSAL_OSC)]
    u_etas = [hd / N for hd in u_hds]
    all_inits = UNIVERSAL_OSC + extra_inits
    all_pats  = u_pats + extra_pats
    all_etas  = u_etas + extra_etas
    all_hds   = u_hds + extra_hds

    dfs = []
    for t_odd in t_odd_fine:
        sv, max_d = gen_even_odd_sv(N, T_EVEN, t_odd)
        tag = f"_todd{t_odd}"
        sv_path = os.path.join(RTL, f"clockless_bifurc{tag}.sv")
        with open(sv_path, "w") as f:
            f.write(sv)
        df = run_batch("bifurc", "even_odd", all_inits, all_pats, all_etas, all_hds,
                       sv_path, max_d, variant_tag=tag)
        if not df.empty:
            df["t_even"] = T_EVEN
            df["t_odd"] = t_odd
            df["ratio"] = t_odd / T_EVEN
            # Separate universal osc from the rest
            u_sub = df.iloc[:len(UNIVERSAL_OSC)]
            rest_sub = df.iloc[len(UNIVERSAL_OSC):]
            u_settled = (u_sub.outcome != "oscillated").mean()
            r_settled = (rest_sub.outcome != "oscillated").mean()
            print(f"  t_odd={t_odd}: universal_osc_settled={u_settled:.1%}  random_settled={r_settled:.1%}")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP N: LUT ENTRY CORRUPTION
# Randomly flip K% of LUT output entries, measure recall degradation
# Simulates manufacturing defects or partial FPGA cell failures
# ════════════════════════════════════════════════════════════════════════════

def exp_lut_corruption():
    print("\n=== EXP N: LUT ENTRY CORRUPTION ===")
    W = np.load(W_PATH)

    # Get the truth table: for each state, compute correct LUT output
    def get_truth_table():
        tt = {}
        for s_int in range(1 << N):
            s = np.array([(s_int >> i) & 1 for i in range(N)], dtype=float)
            h = W @ (2 * s - 1)
            s_next = (h > 0).astype(int)
            s_next[h == 0] = s.astype(int)[h == 0]
            out = sum(int(s_next[i]) << i for i in range(N))
            tt[s_int] = out
        return tt

    print("  Building full truth table (2^16 states)...")
    tt = get_truth_table()
    print("  Done.")

    # Corruption sweep: flip K% of LUT entries
    corruption_pcts = [0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20]
    rng = np.random.default_rng(22222)
    n_trials = 100
    eta_grid = [0.0, 0.15, 0.30]

    # Python-only simulation (fast) for this experiment
    def sim_convergence(s_init: int, corrupted_tt: dict, max_steps: int = 200) -> tuple:
        seen = {}
        cur = s_init
        for step in range(max_steps):
            if cur in seen:
                return "cycle", cur, step - seen[cur]
            seen[cur] = step
            nxt = corrupted_tt.get(cur, cur)
            if nxt == cur:
                return "fixed", cur, step + 1
            cur = nxt
        return "timeout", cur, max_steps

    all_entries = list(range(1 << N))
    rows = []
    for pct in corruption_pcts:
        n_flip = max(0, int(len(all_entries) * pct))
        for trial in range(5 if pct > 0 else 1):  # 5 corruption seeds per level
            # Create corrupted truth table
            corrupted_tt = dict(tt)
            if n_flip > 0:
                flip_entries = rng.choice(all_entries, size=n_flip, replace=False)
                for e in flip_entries:
                    # Flip a random bit in the output
                    bit = int(rng.integers(0, N))
                    corrupted_tt[e] = corrupted_tt[e] ^ (1 << bit)

            # Test recall from corrupted patterns
            correct_count, settled_count, total = 0, 0, 0
            for eta in eta_grid:
                for p_idx in range(4):
                    for _ in range(n_trials):
                        s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                        outcome, attractor, steps = sim_convergence(s, corrupted_tt)
                        total += 1
                        if outcome == "fixed":
                            settled_count += 1
                            if attractor == PATTERNS_INT[p_idx]:
                                correct_count += 1

            rows.append({
                "corruption_pct": pct,
                "n_flip": n_flip,
                "trial": trial,
                "correct": correct_count / total,
                "settled": settled_count / total,
            })
        agg = [r for r in rows if r["corruption_pct"] == pct]
        avg_correct = np.mean([r["correct"] for r in agg])
        avg_settled = np.mean([r["settled"] for r in agg])
        print(f"  corrupt={pct:.1%} ({n_flip} flips): correct={avg_correct:.1%} settled={avg_settled:.1%}")

    return pd.DataFrame(rows)


# ════════════════════════════════════════════════════════════════════════════
# EXP O: PATTERN INTERPOLATION
# Walk along Hamming path from P_i to P_j, test recall at each step
# Reveals the exact boundary where the network "switches allegiance"
# ════════════════════════════════════════════════════════════════════════════

def exp_pattern_interpolation():
    print("\n=== EXP O: PATTERN INTERPOLATION ===")
    n_trials = 200  # per (pair, step) combination
    rng = np.random.default_rng(33333)
    pairs = [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)]

    dfs = []
    for mode in ["depth", "even_odd"]:
        rtl, max_d = generate_rtl(mode)
        all_inits, all_pats, all_etas, all_hds = [], [], [], []
        all_src_pats, all_tgt_pats, all_steps = [], [], []

        for (src, tgt) in pairs:
            # Find differing bit positions between patterns
            diff_bits = [i for i in range(N)
                         if ((PATTERNS_INT[src] >> i) & 1) != ((PATTERNS_INT[tgt] >> i) & 1)]
            hd_total = len(diff_bits)
            # Walk from src to tgt flipping diff_bits one by one
            for k in range(hd_total + 1):
                # k bits flipped from src toward tgt
                # Randomly choose which k bits to flip for n_trials samples
                for _ in range(n_trials):
                    rng_py = random.Random(int(rng.integers(0, 2**31)))
                    flip_subset = rng_py.sample(diff_bits, k)
                    s_int = PATTERNS_INT[src]
                    for bit in flip_subset:
                        s_int ^= (1 << bit)
                    # nearest pattern
                    hd_src = hamming(s_int, PATTERNS_INT[src])
                    hd_tgt = hamming(s_int, PATTERNS_INT[tgt])
                    nearest = src if hd_src <= hd_tgt else tgt
                    all_inits.append(s_int)
                    all_pats.append(nearest)
                    all_etas.append(min(hd_src, hd_tgt) / N)
                    all_hds.append(min(hd_src, hd_tgt))
                    all_src_pats.append(src)
                    all_tgt_pats.append(tgt)
                    all_steps.append(k)

        df = run_batch(f"interp_{mode}", mode, all_inits, all_pats, all_etas, all_hds,
                       rtl, max_d)
        if not df.empty:
            df["mode"] = mode
            df["src_pat"] = all_src_pats[:len(df)]
            df["tgt_pat"] = all_tgt_pats[:len(df)]
            df["interp_step"] = all_steps[:len(df)]
            print(f"  [{mode}] {len(df)} rows collected")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP P: FULL STATE SPACE MAP (Python sim, all 2^16 states)
# Map EVERY state to its attractor using Python synchronous simulation
# Classify: stored, spurious, oscillating
# ════════════════════════════════════════════════════════════════════════════

def exp_full_state_map():
    print("\n=== EXP P: FULL STATE SPACE MAP (Python sim) ===")
    W = np.load(W_PATH)
    pat_set = set(PATTERNS_INT)
    sp_set = set(SPURIOUS_FPS)

    def sync_step(s_int):
        s = np.array([(s_int >> i) & 1 for i in range(N)], dtype=float)
        h = W @ (2 * s - 1)
        s_next = (h > 0).astype(int)
        s_next[h == 0] = s.astype(int)[h == 0]
        return sum(int(s_next[i]) << i for i in range(N))

    print("  Mapping all 65536 states (may take ~30s)...")
    t0 = time.time()
    attractor_map = {}
    outcome_map = {}
    for s in range(1 << N):
        seen = {}
        cur = s
        for step in range(100):
            if cur in seen:
                attractor_map[s] = cur
                outcome_map[s] = "cycle"
                break
            seen[cur] = step
            nxt = sync_step(cur)
            if nxt == cur:
                attractor_map[s] = cur
                outcome_map[s] = "fixed"
                break
            cur = nxt
        else:
            attractor_map[s] = cur
            outcome_map[s] = "timeout"
    print(f"  Done in {time.time()-t0:.1f}s")

    # Classify all attractors
    rows = []
    for s in range(1 << N):
        attr = attractor_map[s]
        outcome = outcome_map[s]
        nearest_pat = min(range(4), key=lambda p: hamming(s, PATTERNS_INT[p]))
        hd_to_nearest = hamming(s, PATTERNS_INT[nearest_pat])
        label = ("stored" if attr in pat_set else
                 "spurious" if attr in sp_set else
                 "unknown_fp" if outcome == "fixed" else
                 "cycle" if outcome == "cycle" else "timeout")
        rows.append({
            "init_state": f"{s:04x}",
            "attractor": f"{attr:04x}",
            "outcome": outcome,
            "label": label,
            "nearest_pat": nearest_pat,
            "hamming_to_nearest": hd_to_nearest,
        })

    df = pd.DataFrame(rows)
    # Stats
    for lbl in ["stored", "spurious", "unknown_fp", "cycle", "timeout"]:
        cnt = (df.label == lbl).sum()
        print(f"  {lbl}: {cnt} states ({cnt/len(df):.1%})")

    return df


# ════════════════════════════════════════════════════════════════════════════
# EXP Q: INTER-PATTERN HAMMING DISTANCES AND CONFUSION
# Measure when initial states close to P_i erroneously converge to P_j
# Map the "confusion matrix" of pattern recall at each noise level
# ════════════════════════════════════════════════════════════════════════════

def exp_confusion_matrix():
    print("\n=== EXP Q: PATTERN CONFUSION MATRIX ===")
    rng = np.random.default_rng(44444)
    eta_grid = np.arange(0.0, 0.65, 0.05)
    n_trials = 120

    dfs = []
    for mode in ["depth", "even_odd"]:
        rtl, max_d = generate_rtl(mode)
        all_inits, all_pats, all_etas, all_hds = [], [], [], []
        for eta in eta_grid:
            for p_idx in range(4):
                for _ in range(n_trials):
                    s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                    all_inits.append(s)
                    all_pats.append(p_idx)
                    all_etas.append(float(eta))
                    all_hds.append(hamming(s, PATTERNS_INT[p_idx]))

        df = run_batch(f"confusion_{mode}", mode, all_inits, all_pats, all_etas, all_hds,
                       rtl, max_d)
        if not df.empty:
            df["mode"] = mode
            # Build confusion matrix at eta=0.3
            sub30 = df[df["eta"].round(2) == 0.30]
            pat_hexes = [f"{p:04x}" for p in PATTERNS_INT]
            conf = np.zeros((4, 4 + 2))  # src x [p0,p1,p2,p3,spurious,oscillated]
            for _, row in sub30.iterrows():
                src = int(row["pat_idx"])
                rs = row["result_state"]
                if row["outcome"] == "oscillated":
                    conf[src][5] += 1
                elif rs in pat_hexes:
                    conf[src][pat_hexes.index(rs)] += 1
                else:
                    conf[src][4] += 1
            conf_norm = conf / conf.sum(axis=1, keepdims=True)
            print(f"\n  [{mode}] Confusion matrix at η=30%:")
            print("       " + "  ".join([f"P{i}" for i in range(4)] + ["spur", "osc"]))
            for src in range(4):
                row_str = "  ".join([f"{conf_norm[src][j]:.2f}" for j in range(6)])
                print(f"  P{src}: {row_str}")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()
    all_dfs = []

    steps = [
        ("bifurcation",  exp_bifurcation),
        ("lut_corrupt",  exp_lut_corruption),
        ("interpolation", exp_pattern_interpolation),
        ("state_map",    exp_full_state_map),
        ("confusion",    exp_confusion_matrix),
    ]

    for name, fn in steps:
        t_exp = time.time()
        try:
            df = fn()
            if df is not None and not df.empty:
                out = os.path.join(RES, f"stress_r4_{name}.csv")
                df.to_csv(out, index=False)
                all_dfs.append(df)
                print(f"  → {out}  ({len(df)} rows)")
        except Exception as exc:
            import traceback
            print(f"  [ERROR] {name}: {exc}")
            traceback.print_exc()
        print(f"  [wall] {name}: {time.time()-t_exp:.1f}s")

    print(f"\n══ Round 4 DONE in {time.time()-t0:.1f}s ══")


if __name__ == "__main__":
    main()
