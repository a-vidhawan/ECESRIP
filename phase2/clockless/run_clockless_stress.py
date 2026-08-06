#!/usr/bin/env python3
"""
Exhaustive stress test suite for the clockless HNN settling simulation.

Bit convention: bit i of an integer = neuron i = s[i] in SV (LSB = neuron 0).

Experiments:
  1  fp_verify      – stored patterns + 1-bit nbrs + complements
  2  noise_sweep    – η 0→60%, all 3 modes, 100 trials/cell
  3  hamming_sweep  – exact Hamming distance 1..N, all 3 modes
  4  random_states  – 2000 random states, all 3 modes
  5  extreme_noise  – η 60→100%, find hard cliff
  6  adversarial    – states ≥5 Hamming from every stored pattern
  7  timing_sweep   – even_odd mode, T_ODD swept
  8  seed_sweep     – noise mode, 50 different delay seeds
  9  delay_scale    – depth mode, delays multiplied by 0.5..5×
  10 oscillation    – systematic state-space coverage for oscillation map
"""

import os, sys, subprocess, math, random, time
import numpy as np
import pandas as pd

# ─── Paths ──────────────────────────────────────────────────────────────────
ROOT   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RTL    = os.path.join(ROOT, "phase2", "rtl")
CL     = os.path.join(ROOT, "phase2", "clockless")
RES    = os.path.join(CL, "results")
LUT_SV = os.path.join(RTL, "pseudo_maxprune.sv")
TMP    = os.path.join(RES, "_tmp")

os.makedirs(RES, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

# ─── Network constants ───────────────────────────────────────────────────────
N = 16
DEFAULT_TERMS = [3, 3, 13, 13, 7, 3, 13, 126, 3, 7, 3, 19, 19, 3, 386, 3]

# Stored patterns – seed=42, N=16, M=4  (same RNG as Phase 1)
_RNG0 = np.random.default_rng(42)
_PAT_BIP = _RNG0.choice([-1, 1], size=(4, N))          # ±1 bipolar
PATTERNS_BIN = ((_PAT_BIP + 1) // 2).astype(int)       # 0/1, shape (4, 16)
# Integer encoding: bit i = neuron i = s[i]  (LSB = neuron 0)
PATTERNS_INT = [sum(int(p[i]) << i for i in range(N)) for p in PATTERNS_BIN]

# Weight matrix (max-prune pseudoinverse)
W = np.load(os.path.join(ROOT, "phase1", "results", "truth_tables",
                         "pseudo_s_maxprune", "W_pruned.npy"))

# ─── LUT update (Python mirror of the SV truth table) ───────────────────────
def lut_update(s_int: int) -> int:
    """Apply one synchronous HNN update step.  Bit i = neuron i (LSB-first)."""
    s = np.array([(s_int >> i) & 1 for i in range(N)], dtype=float)
    h = W @ (2 * s - 1)
    s_next = (h > 0).astype(int)
    s_next[h == 0] = s[h == 0].astype(int)          # tie-break: hold
    return sum(int(s_next[i]) << i for i in range(N))  # LSB-first

# ─── Build fixed-point sets ──────────────────────────────────────────────────
print("[init] Building fixed-point table …", end=" ", flush=True)
ALL_FPS = set()
for _st in range(1 << N):
    if lut_update(_st) == _st:
        ALL_FPS.add(_st)
STORED_FPS  = set(PATTERNS_INT)
SPURIOUS_FPS = ALL_FPS - STORED_FPS
print(f"done  ({len(ALL_FPS)} total: {len(STORED_FPS)} stored, "
      f"{len(SPURIOUS_FPS)} spurious)")

# ─── Helpers ─────────────────────────────────────────────────────────────────
def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")

def nearest_pat(s_int: int) -> tuple:
    dists = [hamming(s_int, p) for p in PATTERNS_INT]
    idx   = int(np.argmin(dists))
    return idx, dists[idx]

def corrupt(pat_bin: np.ndarray, eta: float, rng) -> int:
    """Flip each bit independently with probability eta."""
    mask = rng.random(N) < eta
    s = pat_bin.copy(); s[mask] ^= 1
    return sum(int(s[i]) << i for i in range(N))

def flip_k(pat_bin: np.ndarray, k: int, rng) -> int:
    """Flip exactly k randomly chosen bits."""
    idx = rng.choice(N, size=k, replace=False)
    s = pat_bin.copy(); s[idx] ^= 1
    return sum(int(s[i]) << i for i in range(N))

def int_to_hex(v: int) -> str:
    return f"{v:04x}"

# ─── RTL generation ─────────────────────────────────────────────────────────
sys.path.insert(0, CL)
from gen_clockless_sv import (gen_depth_sv, gen_even_odd_sv, gen_noise_sv,
                               compute_depths, _header, DEFAULT_TERMS)

def generate_rtl(mode, variant_tag="", t_even=10, t_odd=24,
                 noise_seed=99, noise_scale=0.5):
    if mode == "depth":
        sv, max_d, _ = gen_depth_sv(N, DEFAULT_TERMS)
        fname = f"clockless_depth{variant_tag}.sv"
    elif mode == "even_odd":
        sv, max_d = gen_even_odd_sv(N, t_even, t_odd)
        fname = f"clockless_even_odd{variant_tag}.sv"
    elif mode == "noise":
        sv, max_d, _ = gen_noise_sv(N, DEFAULT_TERMS, noise_seed, noise_scale)
        fname = f"clockless_noise{variant_tag}.sv"
    else:
        raise ValueError(mode)
    path = os.path.join(RTL, fname)
    with open(path, "w") as f:
        f.write(sv)
    return path, max_d

# ─── Testbench writer ────────────────────────────────────────────────────────

def write_testbench(module_name: str, init_states: list,
                    max_depth: int, tb_path: str, vec_path: str):
    n_tests = len(init_states)
    timeout = 64 * max_depth + 100
    drain   = max_depth + 5

    with open(vec_path, "w") as f:
        for s in init_states:
            f.write(f"{s:04x}\n")

    # Use forever+disable pattern instead of fork/join_any to avoid iverilog 12 bugs
    tb = f"""\
`timescale 1ns/1ps
module tb;
    parameter int N = {N};
    localparam int NTESTS  = {n_tests};
    localparam int TIMEOUT = {timeout};
    localparam int DRAIN   = {drain};

    logic          init_en  = 1;
    logic [N-1:0]  init_val = '0;
    wire  [N-1:0]  s, s_next;
    wire           stable;

    {module_name} #(.N(N)) dut (
        .init_en (init_en),
        .init_val(init_val),
        .s       (s),
        .s_next  (s_next),
        .stable  (stable)
    );

    logic [N-1:0] tv_init [0:NTESTS-1];
    initial $readmemh("{vec_path}", tv_init);

    integer t_start;
    logic [N-1:0] result;

    task run_test(input integer idx);
        integer elapsed;
        init_val = tv_init[idx];
        #1;
        init_en = 1;
        #2;
        init_en = 0;
        t_start = $time;
        elapsed = 0;
        // Poll each time unit; exit when stable or timeout
        begin : SETTLE
            forever begin
                if (stable || elapsed >= TIMEOUT) disable SETTLE;
                #1; elapsed = elapsed + 1;
            end
        end
        result = s;
        $display("T:%0d I:%0h R:%0h ST:%0d OK:%0b",
                 idx, tv_init[idx], result,
                 ($time - t_start),
                 (elapsed < TIMEOUT) ? 1 : 0);
        init_en = 1;
        #DRAIN;
    endtask

    integer i;
    initial begin
        init_en  = 1;
        init_val = '0;
        #5;
        for (i = 0; i < NTESTS; i = i + 1)
            run_test(i);
        $finish;
    end
endmodule
"""
    with open(tb_path, "w") as f:
        f.write(tb)

# ─── compile + run ───────────────────────────────────────────────────────────

def compile_and_run(module_sv: str, tb_sv: str, tag: str,
                    timeout_sec: int = 300) -> list:
    sim_bin = os.path.join(TMP, f"{tag}.vvp")
    r = subprocess.run(
        ["iverilog", "-g2012", "-o", sim_bin, LUT_SV, module_sv, tb_sv],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"[ERROR] Compile failed ({tag}):\n{r.stderr[:400]}")
        return []
    r2 = subprocess.run(["vvp", sim_bin], capture_output=True, text=True,
                        timeout=timeout_sec)
    if r2.returncode not in (0, 1):
        print(f"[WARN] vvp exit {r2.returncode} for {tag}:\n{r2.stderr[:200]}")
    return r2.stdout.splitlines()

# ─── output parsing ──────────────────────────────────────────────────────────

def parse_output(lines: list) -> list:
    rows = []
    for line in lines:
        if not line.startswith("T:"):
            continue
        try:
            parts = dict(kv.split(":") for kv in line.split())
            rows.append({
                "test_idx":    int(parts["T"]),
                "init_hex":    parts["I"],
                "result_hex":  parts["R"],
                "settle_time": int(parts["ST"]),
                "settled":     bool(int(parts["OK"])),
            })
        except Exception:
            pass
    return rows

# ─── classify outcome ────────────────────────────────────────────────────────

def classify(init_int: int, result_int: int, settled: bool,
             expected_pat_idx: int = -1) -> tuple:
    if not settled:
        return "oscillated", -1
    if result_int in STORED_FPS:
        pat_idx = PATTERNS_INT.index(result_int)
        if expected_pat_idx >= 0:
            return ("correct" if pat_idx == expected_pat_idx
                    else "wrong_pattern"), pat_idx
        return "stored_attractor", pat_idx
    elif result_int in SPURIOUS_FPS:
        return "spurious", -1
    elif result_int in ALL_FPS:
        return "spurious", -1
    else:
        return "not_fixed_point", -1

# ─── batch runner ────────────────────────────────────────────────────────────

def run_batch(exp_name: str, mode: str, init_states: list, pat_indices: list,
              eta_vals: list, hamming_in: list,
              rtl_sv: str, max_depth: int, variant_tag: str = "") -> pd.DataFrame:
    module_name = {
        "depth":    "hopfield_clockless_depth",
        "even_odd": "hopfield_clockless_even_odd",
        "noise":    "hopfield_clockless_noise",
        "coloring": "hopfield_clockless_coloring",
    }[mode]
    tag = f"{exp_name}_{mode}{variant_tag}"
    tb_path  = os.path.join(TMP, f"{tag}_tb.sv")
    vec_path = os.path.join(TMP, f"{tag}_vec.hex")

    write_testbench(module_name, init_states, max_depth, tb_path, vec_path)
    t0 = time.time()
    lines = compile_and_run(rtl_sv, tb_path, tag)
    elapsed = time.time() - t0

    parsed = parse_output(lines)
    if not parsed:
        print(f"  [WARN] No output for {tag} (got {len(lines)} lines)")
        return pd.DataFrame()

    rows = []
    for p in parsed:
        idx = p["test_idx"]
        if idx >= len(init_states):
            continue
        init_int   = init_states[idx]
        result_int = int(p["result_hex"], 16)
        pidx       = pat_indices[idx] if pat_indices else -1
        outcome, recalled = classify(init_int, result_int, p["settled"], pidx)
        rows.append({
            "experiment":   exp_name,
            "mode":         mode,
            "variant":      variant_tag,
            "pat_idx":      pidx,
            "eta":          eta_vals[idx] if eta_vals else -1.0,
            "hamming_in":   hamming_in[idx] if hamming_in else -1,
            "init_state":   p["init_hex"],
            "result_state": p["result_hex"],
            "settled":      p["settled"],
            "settle_time":  p["settle_time"],
            "outcome":      outcome,
            "recalled_pat": recalled,
            "correct":      outcome == "correct",
        })
    df = pd.DataFrame(rows)
    rate = df["correct"].mean() * 100 if len(df) else 0
    srate = df["settled"].mean() * 100 if len(df) else 0
    print(f"  [{tag}] {len(df)} tests  {elapsed:.1f}s  "
          f"correct={rate:.1f}%  settled={srate:.1f}%")
    return df


# ════════════════════════════════════════════════════════════════════════════
# EXPERIMENTS
# ════════════════════════════════════════════════════════════════════════════

def exp_fp_verify(modes=("depth", "even_odd", "noise"), n_reps=50):
    """Exact stored patterns (zero noise) – must always be correct."""
    print("\n=== EXP 1: FIXED POINT VERIFICATION ===")
    rng = np.random.default_rng(1001)
    init_states, pats, etas, hdists = [], [], [], []

    # Exact patterns, multiple reps
    for _ in range(n_reps):
        for p_idx in range(4):
            init_states.append(PATTERNS_INT[p_idx])
            pats.append(p_idx); etas.append(0.0); hdists.append(0)

    # Single-bit perturbations (Hamming 1 neighbourhood)
    for p_idx in range(4):
        for bit in range(N):
            s = PATTERNS_INT[p_idx] ^ (1 << bit)
            init_states.append(s)
            pats.append(p_idx); etas.append(1/N); hdists.append(1)

    # Bit-complements (maximum distance)
    for p_idx in range(4):
        s = (~PATTERNS_INT[p_idx]) & ((1 << N) - 1)
        init_states.append(s)
        pats.append(p_idx); etas.append(1.0); hdists.append(N)

    dfs = []
    for mode in modes:
        rtl, md = generate_rtl(mode)
        dfs.append(run_batch("fp_verify", mode, init_states, pats, etas, hdists, rtl, md))
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def exp_noise_sweep(modes=("depth", "even_odd", "noise"), n_trials=100):
    """η from 0% to 60% in 5% steps."""
    print("\n=== EXP 2: NOISE SWEEP (0→60%) ===")
    eta_grid = [round(e, 2) for e in np.arange(0.0, 0.65, 0.05)]
    rng = np.random.default_rng(2002)
    init_states, pats, etas, hdists = [], [], [], []
    for eta in eta_grid:
        for p_idx in range(4):
            for _ in range(n_trials):
                s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                init_states.append(s)
                pats.append(p_idx)
                etas.append(eta)
                hdists.append(hamming(s, PATTERNS_INT[p_idx]))
    dfs = []
    for mode in modes:
        rtl, md = generate_rtl(mode)
        dfs.append(run_batch("noise_sweep", mode, init_states, pats, etas, hdists, rtl, md))
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def exp_hamming_sweep(modes=("depth", "even_odd", "noise"), n_trials=50):
    """Exact Hamming distance k ∈ {1..N} from each stored pattern."""
    print("\n=== EXP 3: HAMMING DISTANCE SWEEP ===")
    rng = np.random.default_rng(3003)
    init_states, pats, etas, hdists = [], [], [], []
    for k in range(1, N + 1):
        for p_idx in range(4):
            for _ in range(n_trials):
                s = flip_k(PATTERNS_BIN[p_idx], k, rng)
                init_states.append(s)
                pats.append(p_idx); etas.append(k/N); hdists.append(k)
    dfs = []
    for mode in modes:
        rtl, md = generate_rtl(mode)
        dfs.append(run_batch("hamming_sweep", mode, init_states, pats, etas, hdists, rtl, md))
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def exp_random_states(modes=("depth", "even_odd", "noise"), n_states=2000):
    """Random initial states sampled from {0,1}^N."""
    print("\n=== EXP 4: RANDOM STATE SPACE ===")
    rng = np.random.default_rng(4004)
    states = rng.integers(0, 1 << N, size=n_states).tolist()
    pats, etas, hdists = [], [], []
    for s in states:
        pidx, hd = nearest_pat(s)
        pats.append(pidx); hdists.append(hd); etas.append(hd / N)
    dfs = []
    for mode in modes:
        rtl, md = generate_rtl(mode)
        dfs.append(run_batch("random_states", mode, states, pats, etas, hdists, rtl, md))
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def exp_extreme_noise(modes=("depth", "even_odd", "noise"), n_trials=150):
    """η from 60% to 100% – find the hard convergence cliff."""
    print("\n=== EXP 5: EXTREME NOISE (60→100%) ===")
    eta_grid = [round(e, 2) for e in np.arange(0.60, 1.05, 0.05)]
    rng = np.random.default_rng(5005)
    init_states, pats, etas, hdists = [], [], [], []
    for eta in eta_grid:
        for p_idx in range(4):
            for _ in range(n_trials):
                s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                init_states.append(s)
                pats.append(p_idx); etas.append(eta)
                hdists.append(hamming(s, PATTERNS_INT[p_idx]))
    dfs = []
    for mode in modes:
        rtl, md = generate_rtl(mode)
        dfs.append(run_batch("extreme_noise", mode, init_states, pats, etas, hdists, rtl, md))
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def exp_adversarial(modes=("depth", "even_odd", "noise"),
                    n_states=1000, min_hd=5):
    """States that are at least min_hd bits from EVERY stored pattern."""
    print(f"\n=== EXP 6: ADVERSARIAL STATES (min HD≥{min_hd}) ===")
    rng = np.random.default_rng(6006)
    adv = []
    attempts = 0
    while len(adv) < n_states and attempts < 1_000_000:
        attempts += 1
        s = int(rng.integers(0, 1 << N))
        if min(hamming(s, p) for p in PATTERNS_INT) >= min_hd:
            adv.append(s)
    print(f"  Found {len(adv)} adversarial states after {attempts} attempts")
    pats, etas, hdists = [], [], []
    for s in adv:
        pidx, hd = nearest_pat(s); pats.append(pidx)
        hdists.append(hd); etas.append(hd / N)
    dfs = []
    for mode in modes:
        rtl, md = generate_rtl(mode)
        dfs.append(run_batch("adversarial", mode, adv, pats, etas, hdists, rtl, md))
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def exp_timing_sweep(n_trials=60):
    """even_odd mode: sweep T_ODD holding T_EVEN=10 fixed."""
    print("\n=== EXP 7: T_ODD TIMING SWEEP ===")
    t_odd_vals = [2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 30, 40, 50, 64, 100]
    eta_grid = [0.0, 0.15, 0.30, 0.45]
    rng = np.random.default_rng(7007)
    init_states, pats, etas, hdists = [], [], [], []
    for eta in eta_grid:
        for p_idx in range(4):
            for _ in range(n_trials):
                s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                init_states.append(s); pats.append(p_idx)
                etas.append(eta); hdists.append(hamming(s, PATTERNS_INT[p_idx]))
    dfs = []
    for t_odd in t_odd_vals:
        tag = f"_todd{t_odd}"
        rtl, md = generate_rtl("even_odd", variant_tag=tag, t_even=10, t_odd=t_odd)
        df = run_batch("timing_sweep", "even_odd", init_states, pats, etas, hdists,
                       rtl, md, variant_tag=tag)
        if not df.empty:
            df["t_odd"] = t_odd
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def exp_seed_sweep(n_seeds=50, n_trials=40):
    """noise mode: sweep 50 different delay seeds."""
    print("\n=== EXP 8: NOISE SEED SENSITIVITY ===")
    eta_grid = [0.0, 0.15, 0.30]
    rng = np.random.default_rng(8008)
    init_states, pats, etas, hdists = [], [], [], []
    for eta in eta_grid:
        for p_idx in range(4):
            for _ in range(n_trials):
                s = corrupt(PATTERNS_BIN[p_idx], eta, rng)
                init_states.append(s); pats.append(p_idx)
                etas.append(eta); hdists.append(hamming(s, PATTERNS_INT[p_idx]))
    dfs = []
    for seed in range(n_seeds):
        tag = f"_seed{seed}"
        rtl, md = generate_rtl("noise", variant_tag=tag, noise_seed=seed)
        df = run_batch("seed_sweep", "noise", init_states, pats, etas, hdists,
                       rtl, md, variant_tag=tag)
        if not df.empty:
            df["noise_seed"] = seed
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def exp_delay_scale(scales=(0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0), n_trials=60):
    """depth mode: multiply all delays by a scale factor."""
    print("\n=== EXP 9: DELAY SCALE SENSITIVITY ===")
    eta_grid = [0.0, 0.15, 0.30]
    rng = np.random.default_rng(9009)
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
        scaled = [max(1, round(d * scale)) for d in base_depths]
        max_d  = max(scaled)
        tag    = f"_scale{str(scale).replace('.', 'p')}"
        lines  = [_header("hopfield_clockless_depth", N)]
        lines += [f"    // delay_scale={scale}",
                  "    always @(s_next or init_en or init_val) begin",
                  "        if (init_en) begin",
                  "            s_settle <= #0 init_val;",
                  "        end else begin"]
        for i, d in enumerate(scaled):
            lines.append(f"            s_settle[{i:3d}] <= #({d:3d}) s_next[{i:3d}];")
        lines += ["        end", "    end", "endmodule"]
        sv_path = os.path.join(RTL, f"clockless_depth{tag}.sv")
        with open(sv_path, "w") as f:
            f.write("\n".join(lines))
        df = run_batch("delay_scale", "depth", init_states, pats, etas, hdists,
                       sv_path, max_d, variant_tag=tag)
        if not df.empty:
            df["delay_scale"] = scale
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def exp_oscillation(modes=("depth", "even_odd", "noise"), n_states=4000):
    """Dense state-space sample to map which states oscillate."""
    print("\n=== EXP 10: OSCILLATION MAP ===")
    rng = np.random.default_rng(10010)
    # Structured sample: every 16th state + random fill
    states = list(range(0, 1 << N, max(1, (1 << N) // 2500)))
    states += rng.integers(0, 1 << N, size=1500).tolist()
    states  = list(dict.fromkeys(states))[:n_states]   # deduplicate, keep order
    pats, etas, hdists = [], [], []
    for s in states:
        pidx, hd = nearest_pat(s)
        pats.append(pidx); hdists.append(hd); etas.append(hd / N)
    dfs = []
    for mode in modes:
        rtl, md = generate_rtl(mode)
        dfs.append(run_batch("oscillation", mode, states, pats, etas, hdists, rtl, md))
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    t_global = time.time()
    all_dfs = []

    steps = [
        ("fp_verify",    exp_fp_verify),
        ("noise_sweep",  exp_noise_sweep),
        ("hamming",      exp_hamming_sweep),
        ("random",       exp_random_states),
        ("extreme",      exp_extreme_noise),
        ("adversarial",  exp_adversarial),
        ("timing_sweep", exp_timing_sweep),
        ("seed_sweep",   exp_seed_sweep),
        ("delay_scale",  exp_delay_scale),
        ("oscillation",  exp_oscillation),
    ]

    for name, fn in steps:
        t0 = time.time()
        try:
            df = fn()
            if df is not None and not df.empty:
                out = os.path.join(RES, f"stress_{name}.csv")
                df.to_csv(out, index=False)
                all_dfs.append(df)
                print(f"  → {out}  ({len(df)} rows)")
        except Exception as exc:
            import traceback
            print(f"  [ERROR] {name}: {exc}")
            traceback.print_exc()
        print(f"  [wall] {name}: {time.time()-t0:.1f}s")

    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        out_all = os.path.join(RES, "stress_all.csv")
        combined.to_csv(out_all, index=False)
        print(f"\n══ DONE: {len(combined)} total rows in {time.time()-t_global:.1f}s ══")
        print(f"Combined: {out_all}")


if __name__ == "__main__":
    main()
