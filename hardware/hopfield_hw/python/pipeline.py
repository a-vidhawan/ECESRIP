"""
pipeline.py
===========
End-to-end driver:  patterns → weights → truth tables → minimized logic → SV.

This script is the single entry point for the entire Hopfield-to-hardware
flow.  It ties together the other four Python modules and writes all
intermediate and final artefacts to a structured output directory.

Output layout
-------------
    <out_dir>/
    ├── weights.npy                 weight matrix
    ├── truth_tables/
    │   ├── tt_neuron_000.csv
    │   ├── ...
    │   └── truth_tables.json
    ├── covers/
    │   └── covers.json             minimized Boolean covers
    └── rtl/
        └── neuron_logic_generated.sv

Usage examples
--------------
    # Train from randomly generated patterns
    python pipeline.py --N 8 --P 3 --rule hebbian --out build_8

    # Train from a file of patterns (one pattern per line, space-separated ±1)
    python pipeline.py --N 8 --patterns data/patterns_8.txt --out build_8

    # Load pre-existing weights and re-run from truth-table step
    python pipeline.py --N 8 --weights build_8/weights.npy --out build_8
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# Local modules
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "sim" / "python"))
from hopfield_net import HopfieldNetwork, HEBBIAN, STORKEY
from truth_table_gen import enumerate_truth_tables, save_csv, save_json

def random_patterns(N, P, seed=None):
    import numpy as np
    rng = np.random.default_rng(seed)
    return [rng.choice([-1, 1], size=N).astype(float) for _ in range(P)]
from logic_minimize import minimize_all, print_cover
from sv_export import generate_sv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_patterns_from_file(path: str, N: int):
    """
    Load patterns from a text file.
    Each line: N space-separated integers, each ±1.
    Lines starting with '#' are ignored.
    """
    patterns = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            vals = list(map(int, line.split()))
            if len(vals) != N:
                raise ValueError(
                    f"Pattern has {len(vals)} entries, expected {N}: {line!r}"
                )
            patterns.append(np.array(vals, dtype=np.int8))
    return patterns


def _covers_to_json(covers, N: int) -> dict:
    """Serialize covers to a JSON-serializable dict."""
    return {
        "N": N,
        "neurons": [
            [list(imp) for imp in cover]
            for cover in covers
        ],
    }


def _covers_from_json(data: dict):
    """Deserialize covers from the JSON dict."""
    return [
        [tuple(imp) for imp in cover]
        for cover in data["neurons"]
    ]


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def stage_train(args, out_dir: Path) -> np.ndarray:
    """Load or compute the weight matrix."""
    if args.weights:
        W = np.load(args.weights)
        print(f"[1/4] Loaded weights from {args.weights}  (N={W.shape[0]})")
        return W

    N = args.N
    if args.patterns:
        patterns = _load_patterns_from_file(args.patterns, N)
        print(f"[1/4] Loaded {len(patterns)} patterns from {args.patterns}")
    else:
        patterns = random_patterns(N, args.P, seed=args.seed)
        print(f"[1/4] Generated {len(patterns)} random patterns  (N={N}, seed={args.seed})")

    rule = HEBBIAN if args.rule == "hebbian" else STORKEY
    net = HopfieldNetwork(N, rule=rule)
    net.train(np.array(patterns))
    print(f"      Rule: {args.rule}")

    weights_path = out_dir / "weights.npy"
    np.save(weights_path, net.W)
    print(f"      Weights saved to {weights_path}")
    return net.W


def stage_truth_tables(W: np.ndarray, out_dir: Path, tie_break: int):
    """Enumerate truth tables for all neurons."""
    N = W.shape[0]
    print(f"[2/4] Enumerating truth tables  (2^{N} = {1<<N} rows per neuron)")
    tables = enumerate_truth_tables(W, tie_break=tie_break)

    tt_dir = out_dir / "truth_tables"
    save_csv(tables, tt_dir)
    json_path = tt_dir / "truth_tables.json"
    save_json(tables, json_path)
    print(f"      CSVs + JSON → {tt_dir}/")
    return tables


def stage_minimize(tables, out_dir: Path, hazard_free: bool):
    """Minimize Boolean functions and optionally add hazard-free terms."""
    hf_str = "hazard-free " if hazard_free else ""
    print(f"[3/4] Q-M minimization ({hf_str}cover) …")
    covers = minimize_all(tables, hazard_free=hazard_free)

    # Print summary
    total_terms = sum(len(c) for c in covers)
    print(f"      Total product terms across all neurons: {total_terms}")

    # Save covers
    covers_dir = out_dir / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)
    covers_path = covers_dir / "covers.json"
    with open(covers_path, "w") as f:
        json.dump(_covers_to_json(covers, tables[0].N), f, indent=2)
    print(f"      Covers saved to {covers_path}")
    return covers


def stage_sv_export(tables, covers, out_dir: Path):
    """Emit SystemVerilog."""
    print("[4/4] Emitting SystemVerilog …")
    sv_dir = out_dir / "rtl"
    sv_path = sv_dir / "neuron_logic_generated.sv"
    generate_sv(tables, covers, sv_path)
    print(f"      RTL → {sv_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Hopfield → hardware full pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Network parameters
    parser.add_argument("--N",        type=int, default=8,
                        help="Number of neurons")
    parser.add_argument("--P",        type=int, default=3,
                        help="Number of random patterns to generate (if --patterns not given)")
    parser.add_argument("--rule",     choices=["hebbian", "storkey"], default="hebbian",
                        help="Learning rule")
    parser.add_argument("--seed",     type=int, default=42,
                        help="RNG seed for random pattern generation")

    # Input overrides
    parser.add_argument("--patterns", type=str, default=None,
                        help="Path to patterns file (one per line, ±1 ints)")
    parser.add_argument("--weights",  type=str, default=None,
                        help="Skip training; load weights from .npy file")

    # Output
    parser.add_argument("--out",      type=str, default="build",
                        help="Output directory")

    # Logic options
    parser.add_argument("--tie-break",      type=int, choices=[0, 1], default=1,
                        help="Output when net input = 0 exactly")
    parser.add_argument("--no-hazard-free", action="store_true",
                        help="Disable hazard-free augmentation")

    args = parser.parse_args()

    if args.weights is None and args.patterns is None and args.N is None:
        parser.error("Provide --N, --weights, or --patterns.")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {out_dir.resolve()}\n")

    W      = stage_train(args, out_dir)
    tables = stage_truth_tables(W, out_dir, tie_break=args.tie_break)
    covers = stage_minimize(tables, out_dir, hazard_free=not args.no_hazard_free)
    stage_sv_export(tables, covers, out_dir)

    print("\nDone.  All artefacts written to", out_dir.resolve())


if __name__ == "__main__":
    main()
