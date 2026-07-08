"""
csv_to_pla.py
=============
Convert Hopfield neuron truth tables to PLA format for Espresso.

Reads from either:
  - sparse_truth_tables.json  (preferred — only 2^dᵢ rows per neuron)
  - truth_tables.json         (dense — 2^N rows per neuron)

Produces one .pla file per neuron, with input variable labels that reflect
the ACTUAL neuron indices (not sequential column positions). This matters for
sparse networks where neuron i's inputs are a subset of all N neurons:

    Neuron 3, neighbors = [0, 5, 7]:
        .ilb b_0 b_5 b_7     ← physical indices in the state vector
        .ob  f_3

So Espresso sees only 2^3 = 8 rows and the output SV will reference
s[0], s[5], s[7] correctly.

Optionally produces a single combined PLA with N outputs (for small N only).

Usage
-----
    # From sparse truth tables (recommended)
    python phase2/csv_to_pla.py \\
      --input phase1/results/truth_tables/storkey_s0p75/ \\
      --out   phase2/pla/

    # From dense truth tables
    python phase2/csv_to_pla.py \\
      --input phase1/results/truth_tables/storkey_s0p00/ \\
      --out   phase2/pla/ --dense

    # Also write a combined multi-output PLA (only sensible for N <= 16)
    python phase2/csv_to_pla.py --input ... --out phase2/pla/ --combined
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# PLA building
# ─────────────────────────────────────────────────────────────────────────────

def _int_to_bits(m: int, n: int) -> str:
    """Integer minterm → binary string of length n, MSB first."""
    return format(m, f'0{n}b')


def build_pla_sparse(
    neuron_idx: int,
    neighbors: List[int],
    on_set: List[int],
    N_total: int,
    tie_break: int = 1,
) -> str:
    """
    Build a PLA string for one neuron using its sparse truth table.

    Parameters
    ----------
    neuron_idx : global index of this neuron (for .ob label)
    neighbors  : sorted list of global neuron indices that feed this neuron
    on_set     : list of local minterms (over neighbors only) where output = 1
    N_total    : total neurons in the network (for context only)
    tie_break  : output value when h_i == 0 (baked into on_set already)
    """
    d = len(neighbors)
    total = 1 << d
    on_set_s = set(on_set)

    lines = []
    lines.append(f"# Neuron {neuron_idx}  |  neighbors: {neighbors}  |  N={N_total}")
    lines.append(f".i {d}")
    lines.append(f".o 1")
    lines.append(f".ilb {' '.join(f'b_{j}' for j in neighbors)}")
    lines.append(f".ob f_{neuron_idx}")
    lines.append(f".p {total}")   # Espresso can handle redundant entries; it will minimize

    for m in range(total):
        bits = _int_to_bits(m, d)
        out = "1" if m in on_set_s else "0"
        lines.append(f"{bits} {out}")

    lines.append(".e")
    return "\n".join(lines) + "\n"


def build_pla_dense(
    neuron_idx: int,
    N: int,
    on_set: List[int],
) -> str:
    """
    Build a PLA string for one neuron using the full dense truth table (2^N rows).
    Input labels are b_0 .. b_{N-1} (all neurons).
    """
    total = 1 << N
    on_set_s = set(on_set)

    lines = []
    lines.append(f"# Neuron {neuron_idx}  |  N={N}  (dense)")
    lines.append(f".i {N}")
    lines.append(f".o 1")
    lines.append(f".ilb {' '.join(f'b_{j}' for j in range(N))}")
    lines.append(f".ob f_{neuron_idx}")
    lines.append(f".p {total}")

    for m in range(total):
        bits = _int_to_bits(m, N)
        out = "1" if m in on_set_s else "0"
        lines.append(f"{bits} {out}")

    lines.append(".e")
    return "\n".join(lines) + "\n"


def build_pla_combined(
    all_neurons: list[dict],
    N: int,
) -> str:
    """
    Build a single PLA with N outputs (one per neuron) over 2^N input rows.
    Only sensible for N <= 16.
    """
    total = 1 << N

    # Build output column for each neuron
    on_sets = [set(n["on_set"]) for n in all_neurons]

    lines = []
    lines.append(f"# Combined PLA  N={N}  neurons={len(all_neurons)}")
    lines.append(f".i {N}")
    lines.append(f".o {N}")
    lines.append(f".ilb {' '.join(f'b_{j}' for j in range(N))}")
    ob_labels = " ".join(f"f_{n['idx']}" for n in all_neurons)
    lines.append(f".ob {ob_labels}")
    lines.append(f".p {total}")

    for m in range(total):
        bits = _int_to_bits(m, N)
        outs = "".join("1" if m in on_sets[i] else "0" for i in range(N))
        lines.append(f"{bits} {outs}")

    lines.append(".e")
    return "\n".join(lines) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────────────────────────────────────

def load_sparse(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def load_dense(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# Main conversion
# ─────────────────────────────────────────────────────────────────────────────

def convert(
    input_dir: Path,
    out_dir: Path,
    use_dense: bool = False,
    combined: bool = False,
    verbose: bool = True,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    sparse_path = input_dir / "sparse_truth_tables.json"
    dense_path  = input_dir / "truth_tables.json"

    if not use_dense and sparse_path.exists():
        data = load_sparse(sparse_path)
        N = data["N"]
        neurons = data["neurons"]
        mode = "sparse"
    elif dense_path.exists():
        data = load_dense(dense_path)
        N = data["N"]
        neurons = data["neurons"]
        # Dense JSON doesn't have neighbors — treat all neurons as neighbors
        for n in neurons:
            if "neighbors" not in n:
                n["neighbors"] = list(range(N))
        mode = "dense"
    else:
        raise FileNotFoundError(
            f"No truth table JSON found in {input_dir}. "
            "Run phase1/hnn_to_truth_table.py first."
        )

    if verbose:
        print(f"Loaded {mode} truth tables: N={N}, {len(neurons)} neurons")
        print(f"Output → {out_dir}/")

    n_entries_total = 0

    for n in neurons:
        idx       = n["idx"]
        neighbors = n.get("neighbors", list(range(N)))
        on_set    = n["on_set"]
        d         = len(neighbors)
        n_entries = 1 << d

        if mode == "sparse" and "neighbors" in n:
            pla_str = build_pla_sparse(idx, neighbors, on_set, N)
        else:
            pla_str = build_pla_dense(idx, N, on_set)

        pla_path = out_dir / f"neuron_{idx:03d}.pla"
        pla_path.write_text(pla_str)
        n_entries_total += n_entries

        if verbose:
            print(f"  neuron {idx:3d}: neighbors={neighbors}  "
                  f"d={d}  entries={n_entries}  → {pla_path.name}")

    if combined:
        if N > 16:
            print(f"  WARNING: N={N} > 16, combined PLA will have {1<<N} rows — may be slow")
        pla_str = build_pla_combined(neurons, N)
        comb_path = out_dir / "combined.pla"
        comb_path.write_text(pla_str)
        if verbose:
            print(f"\nCombined PLA → {comb_path}  ({1<<N} rows × {N} outputs)")

    if verbose:
        print(f"\nTotal PLA entries across all neurons: {n_entries_total:,}")
        print(f"(Dense would be: {N * (1 << N):,}   "
              f"compression: {N * (1 << N) / max(n_entries_total, 1):.0f}×)")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert Hopfield truth tables to PLA files for Espresso."
    )
    parser.add_argument("--input", type=str, required=True,
                        help="Directory containing sparse_truth_tables.json or truth_tables.json")
    parser.add_argument("--out",   type=str, required=True,
                        help="Output directory for .pla files")
    parser.add_argument("--dense", action="store_true",
                        help="Force use of dense truth_tables.json even if sparse exists")
    parser.add_argument("--combined", action="store_true",
                        help="Also write a single combined.pla with all N outputs")
    args = parser.parse_args()

    convert(
        input_dir=Path(args.input),
        out_dir=Path(args.out),
        use_dense=args.dense,
        combined=args.combined,
    )
