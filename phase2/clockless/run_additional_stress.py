#!/usr/bin/env python3
"""
Additional stress tests — runs AFTER the main suite.
Focuses on:
  A. Noise scale sweep: probe when delay perturbations actually matter
  B. Large-scale seed sweep with noise_scale=1.5 (forces real delay variation)
  C. Extreme capacity stress: random initial states at high Hamming distance
  D. Per-neuron fault injection: knock out each neuron, measure recall
"""

import os, sys, time
import numpy as np
import pandas as pd

# ─── shared infrastructure ───────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from run_clockless_stress import (
    generate_rtl, run_batch, corrupt, flip_k,
    PATTERNS_BIN, PATTERNS_INT, ALL_FPS, SPURIOUS_FPS,
    hamming, N, DEFAULT_TERMS, RES, TMP, RTL, LUT_SV,
    write_testbench, compile_and_run, parse_output, classify
)
from gen_clockless_sv import compute_depths, _header, DEFAULT_TERMS

import math, random


# ════════════════════════════════════════════════════════════════════════════
# EXP A: NOISE SCALE SWEEP
# Does the SV settle differently when delays have larger perturbations?
# ════════════════════════════════════════════════════════════════════════════

def exp_noise_scale_sweep(scales=(0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0),
                          n_trials=80, n_seeds=20):
    print("\n=== EXP A: NOISE SCALE SWEEP (depth mode) ===")
    eta_grid = [0.0, 0.15, 0.30]
    rng = np.random.default_rng(11011)
    init_states, pats, etas, hdists = [], [], [], []
    for eta in eta_grid:
        for p_idx in range(4):
            for _ in range(n_trials):
                s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                init_states.append(s); pats.append(p_idx)
                etas.append(eta); hdists.append(hamming(s, PATTERNS_INT[p_idx]))

    base_depths = compute_depths(DEFAULT_TERMS)
    dfs = []
    for scale in scales:
        for seed in range(n_seeds):
            rng2 = random.Random(seed * 1000 + int(scale * 100))
            delays = [max(1, round(d + rng2.uniform(-scale, scale)))
                      for d in base_depths]
            max_d = max(delays)
            tag = f"_nscale{str(scale).replace('.','p')}_s{seed}"

            lines = [_header("hopfield_clockless_depth", N)]
            lines += [f"    // noise_scale={scale} seed={seed}",
                      "    always @(s_next or init_en or init_val) begin",
                      "        if (init_en) begin",
                      "            s_settle <= #0 init_val;",
                      "        end else begin"]
            for i, d in enumerate(delays):
                lines.append(f"            s_settle[{i:3d}] <= #({d:3d}) s_next[{i:3d}];")
            lines += ["        end", "    end", "endmodule"]
            sv_path = os.path.join(RTL, f"clockless_depth{tag}.sv")
            with open(sv_path, "w") as f:
                f.write("\n".join(lines))

            df = run_batch("noise_scale", "depth", init_states, pats, etas, hdists,
                           sv_path, max_d, variant_tag=tag)
            if not df.empty:
                df["noise_scale"] = scale
                df["noise_seed"]  = seed
                df["actual_delays"] = str(delays)
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP B: LARGE NOISE SCALE SEED SWEEP
# Fixed scale=2.0, 50 seeds — see how much seed matters when delays vary a lot
# ════════════════════════════════════════════════════════════════════════════

def exp_large_noise_seed(n_seeds=50, n_trials=80, noise_scale=2.0):
    print(f"\n=== EXP B: LARGE NOISE SEED SWEEP (scale={noise_scale}) ===")
    eta_grid = [0.0, 0.15, 0.30]
    rng = np.random.default_rng(12012)
    init_states, pats, etas, hdists = [], [], [], []
    for eta in eta_grid:
        for p_idx in range(4):
            for _ in range(n_trials):
                s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                init_states.append(s); pats.append(p_idx)
                etas.append(eta); hdists.append(hamming(s, PATTERNS_INT[p_idx]))

    base_depths = compute_depths(DEFAULT_TERMS)
    dfs = []
    for seed in range(n_seeds):
        rng2 = random.Random(seed)
        delays = [max(1, round(d + rng2.uniform(-noise_scale, noise_scale)))
                  for d in base_depths]
        max_d = max(delays)
        tag = f"_bigscale_s{seed}"

        lines = [_header("hopfield_clockless_depth", N)]
        lines += [f"    // big noise scale={noise_scale} seed={seed}",
                  "    always @(s_next or init_en or init_val) begin",
                  "        if (init_en) begin",
                  "            s_settle <= #0 init_val;",
                  "        end else begin"]
        for i, d in enumerate(delays):
            lines.append(f"            s_settle[{i:3d}] <= #({d:3d}) s_next[{i:3d}];")
        lines += ["        end", "    end", "endmodule"]
        sv_path = os.path.join(RTL, f"clockless_depth{tag}.sv")
        with open(sv_path, "w") as f:
            f.write("\n".join(lines))

        df = run_batch("large_noise_seed", "depth", init_states, pats, etas, hdists,
                       sv_path, max_d, variant_tag=tag)
        if not df.empty:
            df["noise_seed"]  = seed
            df["noise_scale"] = noise_scale
            df["max_delay"]   = max_d
            df["min_delay"]   = min(delays)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP C: EVEN-ODD RATIO SWEEP
# Fix ratio T_ODD/T_EVEN while keeping T_EVEN constant
# Test ratios: 0.25, 0.5, 1, 1.5, 2, 3, 4, 6, 8, 10, 20
# ════════════════════════════════════════════════════════════════════════════

def exp_ratio_sweep(n_trials=80):
    from gen_clockless_sv import gen_even_odd_sv
    print("\n=== EXP C: T_ODD/T_EVEN RATIO SWEEP ===")
    T_EVEN = 10
    ratios = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 20.0]
    eta_grid = [0.0, 0.15, 0.30, 0.45]
    rng = np.random.default_rng(13013)
    init_states, pats, etas, hdists = [], [], [], []
    for eta in eta_grid:
        for p_idx in range(4):
            for _ in range(n_trials):
                s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                init_states.append(s); pats.append(p_idx)
                etas.append(eta); hdists.append(hamming(s, PATTERNS_INT[p_idx]))

    dfs = []
    for ratio in ratios:
        t_odd = max(1, round(T_EVEN * ratio))
        tag   = f"_ratio{str(ratio).replace('.','p')}"
        sv, max_d = gen_even_odd_sv(N, T_EVEN, t_odd)
        sv_path = os.path.join(RTL, f"clockless_even_odd{tag}.sv")
        with open(sv_path, "w") as f:
            f.write(sv)
        df = run_batch("ratio_sweep", "even_odd", init_states, pats, etas, hdists,
                       sv_path, max_d, variant_tag=tag)
        if not df.empty:
            df["t_even"] = T_EVEN
            df["t_odd"]  = t_odd
            df["ratio"]  = ratio
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# EXP D: ALL-INITIAL-STATE CONVERGENCE MAP
# For every state in {0,1}^N, determine attractor (using fast Python sim)
# then compare with SV simulation on a sample
# ════════════════════════════════════════════════════════════════════════════

def exp_python_vs_sv_convergence(n_sample=500):
    """
    Compare Python HNN synchronous convergence with clockless SV for a sample.
    Python: iterate LUT update until fixed point or cycle detected.
    SV: async settling.
    Discrepancy reveals oscillation-causing states.
    """
    print("\n=== EXP D: PYTHON vs SV CONVERGENCE COMPARISON ===")
    import numpy as np

    W = np.load(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                             "phase1", "results", "truth_tables",
                             "pseudo_s_maxprune", "W_pruned.npy"))

    def sync_converge(s_int: int, max_steps: int = 50) -> tuple:
        """Synchronous HNN update until fixed point or cycle."""
        seen = {}
        cur = s_int
        for step in range(max_steps):
            if cur in seen:
                return "cycle", cur, step - seen[cur]
            seen[cur] = step
            s = np.array([(cur >> i) & 1 for i in range(N)], dtype=float)
            h = W @ (2 * s - 1)
            s_next = (h > 0).astype(int)
            s_next[h == 0] = s[h == 0].astype(int)
            nxt = sum(int(s_next[i]) << i for i in range(N))
            if nxt == cur:
                return "fixed", cur, step + 1
            cur = nxt
        return "timeout", cur, max_steps

    rng = np.random.default_rng(14014)
    sample_states = rng.integers(0, 1 << N, size=n_sample).tolist()

    python_results = []
    for s in sample_states:
        outcome, attractor, steps = sync_converge(s)
        in_stored = attractor in set(PATTERNS_INT)
        python_results.append({
            "init_state": f"{s:04x}",
            "py_outcome": outcome,
            "py_attractor": f"{attractor:04x}",
            "py_steps": steps,
            "py_in_stored": in_stored,
        })
    py_df = pd.DataFrame(python_results)

    # Now run SV simulation on same states
    rtl, max_d = generate_rtl("depth")
    dfs_sv = []
    for mode in ["depth", "even_odd"]:
        rtl, max_d = generate_rtl(mode)
        sv_df = run_batch("py_vs_sv", mode, sample_states,
                          [min(range(4), key=lambda p: hamming(s, PATTERNS_INT[p]))
                           for s in sample_states],
                          [hamming(s, PATTERNS_INT[min(range(4), key=lambda p: hamming(s, PATTERNS_INT[p]))]) / N
                           for s in sample_states],
                          [hamming(s, PATTERNS_INT[min(range(4), key=lambda p: hamming(s, PATTERNS_INT[p]))])
                           for s in sample_states],
                          rtl, max_d)
        if not sv_df.empty:
            sv_df["mode"] = mode
            # Merge with Python results
            sv_df_with_py = sv_df.merge(py_df, on="init_state", how="left")
            sv_df_with_py["agree"] = (
                sv_df_with_py["result_state"] == sv_df_with_py["py_attractor"]
            )
            dfs_sv.append(sv_df_with_py)

    if dfs_sv:
        combined = pd.concat(dfs_sv, ignore_index=True)
        for mode in ["depth", "even_odd"]:
            sub = combined[combined.mode == mode]
            if not sub.empty:
                agree = sub["agree"].mean()
                osc_sv = (sub.outcome == "oscillated").mean()
                cycle_py = (sub.py_outcome == "cycle").mean()
                print(f"  [{mode}] agree={agree:.1%}  sv_osc={osc_sv:.1%}  py_cycle={cycle_py:.1%}")
        return combined
    return pd.DataFrame()


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()
    all_dfs = []

    steps = [
        ("noise_scale",    exp_noise_scale_sweep),
        ("large_noise",    exp_large_noise_seed),
        ("ratio_sweep",    exp_ratio_sweep),
        ("py_vs_sv",       exp_python_vs_sv_convergence),
    ]

    for name, fn in steps:
        t_exp = time.time()
        try:
            df = fn()
            if df is not None and not df.empty:
                out = os.path.join(RES, f"stress_add_{name}.csv")
                df.to_csv(out, index=False)
                all_dfs.append(df)
                print(f"  → {out}  ({len(df)} rows)")
        except Exception as exc:
            import traceback
            print(f"  [ERROR] {name}: {exc}")
            traceback.print_exc()
        print(f"  [wall] {name}: {time.time()-t_exp:.1f}s")

    if all_dfs:
        print(f"\n=== Additional tests done in {time.time()-t0:.1f}s ===")


if __name__ == "__main__":
    main()
