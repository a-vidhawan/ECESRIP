"""
hnn_to_truth_table.py
=====================
End-to-end pipeline: train HNN on a dataset → export per-neuron truth tables.

Wires together:
    sim/python/hopfield_net.py          (training)
    hardware/hopfield_hw/python/truth_table_gen.py  (LUT enumeration)
    phase1/datasets/loaders.py          (dataset loading)

Usage
-----
    # Associative memory on random patterns
    python phase1/hnn_to_truth_table.py --dataset random --N 8 --M 3

    # Ising optimization (SK spin glass)
    python phase1/hnn_to_truth_table.py --dataset sk --N 12 --seed 0

    # MAX-CUT on random 3-regular graph
    python phase1/hnn_to_truth_table.py --dataset rrg --N 16 --k 3

    # Number partitioning
    python phase1/hnn_to_truth_table.py --dataset npp --N 12 --hardness easy

    # All outputs go to --out directory (default: phase1/out/)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "sim" / "python"))
sys.path.insert(0, str(_REPO / "hardware" / "hopfield_hw" / "python"))
sys.path.insert(0, str(Path(__file__).parent))

from hopfield_net import HopfieldNetwork, STORKEY, HEBBIAN, PSEUDOINVERSE, ASYNC_CYCLIC
from truth_table_gen import enumerate_truth_tables, save_csv, save_json, print_summary
from datasets.loaders import (
    random_bipolar_patterns,
    sk_spin_glass,
    number_partitioning,
    random_regular_maxcut,
)


# ─────────────────────────────────────────────────────────────────────────────
# Dataset → (W, meta)
# ─────────────────────────────────────────────────────────────────────────────

def load_dataset(args) -> tuple[np.ndarray, dict]:
    """
    Load the specified dataset and return (W, meta).

    For associative memory datasets: train HNN and return its W.
    For Ising/optimization datasets: W = J (coupling matrix directly).
    """
    ds = args.dataset.lower()

    if ds == 'random':
        patterns = random_bipolar_patterns(N=args.N, M=args.M, seed=args.seed)
        net = HopfieldNetwork(args.N, rule=_rule(args.rule))
        net.train(patterns)
        W = net.W
        meta = {
            "dataset": "random_bipolar",
            "N": args.N,
            "M": args.M,
            "rule": args.rule,
            "seed": args.seed,
            "load_alpha": args.M / args.N,
            "patterns_stored": args.M,
        }

    elif ds == 'sk':
        W, _, meta = sk_spin_glass(N=args.N, seed=args.seed)
        meta["dataset"] = "sk_spin_glass"

    elif ds == 'npp':
        W, _, meta = number_partitioning(
            N=args.N, seed=args.seed,
            hardness=getattr(args, 'hardness', 'easy'),
        )
        meta["dataset"] = "number_partitioning"

    elif ds == 'rrg':
        k = getattr(args, 'k', 3)
        W, _, meta = random_regular_maxcut(N=args.N, k=k, seed=args.seed)
        meta["dataset"] = "random_regular_maxcut"

    else:
        raise ValueError(
            f"Unknown dataset '{ds}'. "
            "Choose from: random, sk, npp, rrg"
        )

    return W, meta


def _rule(name: str) -> str:
    mapping = {'storkey': STORKEY, 'hebbian': HEBBIAN, 'pseudoinverse': PSEUDOINVERSE}
    return mapping.get(name.lower(), STORKEY)


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(args) -> None:
    out_dir = Path(args.out)

    # ── 1. Load dataset / train
    print(f"Loading dataset: {args.dataset} (N={args.N})")
    W, meta = load_dataset(args)
    N = W.shape[0]
    print(f"  W shape: {W.shape},  ||W||_F = {np.linalg.norm(W):.4f}")
    print(f"  W sparsity: {(W == 0).sum() / W.size:.1%} zeros")

    # ── 2. Save weight matrix
    out_dir.mkdir(parents=True, exist_ok=True)
    W_path = out_dir / "W.npy"
    np.save(W_path, W)
    print(f"  Saved W → {W_path}")

    # ── 3. Enumerate truth tables
    print(f"\nEnumerating truth tables (2^{N} = {1<<N} inputs per neuron) …")
    if N > 20:
        print(f"  WARNING: N={N} is large — this will enumerate {1<<N} × {N} = "
              f"{(1<<N)*N:,} outputs. May be slow or run out of memory.")
        print("  Consider using sparse_hopfield.py for N > 16.")

    tables = enumerate_truth_tables(W, tie_break=args.tie_break)

    # ── 4. Export
    csv_dir = out_dir / "tt_csv"
    save_csv(tables, csv_dir)
    print(f"  CSVs → {csv_dir}/")

    json_path = out_dir / "truth_tables.json"
    save_json(tables, json_path)
    print(f"  JSON → {json_path}")

    # ── 5. Summary statistics
    print()
    print_summary(tables)

    # ── 6. LUT size report
    total_entries = sum(len(tt.on_set) + len(tt.off_set) for tt in tables)
    on_entries = sum(len(tt.on_set) for tt in tables)
    print(f"\nLUT sizing:")
    print(f"  Entries per neuron : 2^{N} = {1<<N:,}")
    print(f"  Total entries      : {N} × {1<<N:,} = {total_entries:,}")
    print(f"  ON-set entries     : {on_entries:,} ({on_entries/total_entries:.1%})")
    print(f"  Memory (1 bit/entry): {total_entries / 8 / 1024:.1f} KB")

    # ── 7. Save pipeline metadata
    import json as _json
    meta_path = out_dir / "pipeline_meta.json"
    with open(meta_path, "w") as f:
        _json.dump({**meta, "lut_entries_per_neuron": 1 << N,
                    "total_lut_entries": total_entries,
                    "tie_break": args.tie_break}, f, indent=2)
    print(f"\nPipeline metadata → {meta_path}")
    print(f"\nDone. All outputs in {out_dir}/")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train HNN on a dataset and export per-neuron truth tables."
    )
    parser.add_argument("--dataset", type=str, default="random",
                        choices=["random", "sk", "npp", "rrg"],
                        help="Dataset to use")
    parser.add_argument("--N", type=int, default=8,
                        help="Number of neurons")
    parser.add_argument("--M", type=int, default=3,
                        help="Patterns to store (random dataset only)")
    parser.add_argument("--k", type=int, default=3,
                        help="Degree for random regular graph (rrg dataset)")
    parser.add_argument("--hardness", type=str, default="easy",
                        choices=["easy", "phase_transition", "hard"],
                        help="Instance hardness for NPP dataset")
    parser.add_argument("--rule", type=str, default="storkey",
                        choices=["storkey", "hebbian", "pseudoinverse"],
                        help="Training rule (random dataset only)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--tie-break", type=int, choices=[0, 1], default=1,
                        help="Output when h_i == 0 exactly")
    parser.add_argument("--out", type=str, default="phase1/out",
                        help="Output directory")
    args = parser.parse_args()

    run_pipeline(args)
