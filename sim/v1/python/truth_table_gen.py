"""
truth_table_gen.py
==================
Enumerate the **per-neuron update function** of a trained Hopfield network
into explicit truth tables.

Background
----------
The synchronous update rule for neuron i is:

    s_i(t+1) = sign( Σ_j  W_ij · s_j(t) )

where s_j ∈ {-1, +1}.

For hardware we map bipolar states to single bits:

    b_j = (s_j + 1) / 2  ∈ {0, 1}   (0 ↔ -1,  1 ↔ +1)

so the update becomes:

    h_i = Σ_j  W_ij · (2·b_j − 1)
        = 2·(Σ_j W_ij·b_j) − (Σ_j W_ij)

    b_i_new = 1  if  h_i ≥ 0
              0  otherwise

For each neuron i this defines a Boolean function
    f_i : {0,1}^N → {0,1}
which we enumerate by iterating over all 2^N input combinations.

Output format
-------------
Each truth table is a list of TruthTableRow named-tuples:
    .inputs  – tuple of N bits (b_0 … b_{N-1})
    .output  – 0 or 1 for this neuron

The module also exports the tables as:
  * CSV  ("tt_neuron_{i}.csv")
  * JSON ("truth_tables.json")
  * a compact on-set list (minterms where output = 1)

Usage
-----
    python truth_table_gen.py --N 8 --weights weights_8.npy --out tt/
"""

from __future__ import annotations

import argparse
import csv
import json
import numpy as np
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

@dataclass
class NeuronTruthTable:
    """
    Complete truth table for one Hopfield neuron's update function.

    Attributes
    ----------
    neuron_idx : int
        Index of this neuron (0-based).
    N : int
        Total number of neurons (= number of input variables).
    on_set : list[int]
        Minterms (integer encodings of input vectors) where output = 1.
    dc_set : list[int]
        Don't-care minterms (empty for Hopfield — every input is reachable).
    """
    neuron_idx: int
    N: int
    on_set: List[int] = field(default_factory=list)
    dc_set: List[int] = field(default_factory=list)

    @property
    def off_set(self) -> List[int]:
        """Minterms where output = 0 (complement of on_set)."""
        all_m = set(range(1 << self.N))
        return sorted(all_m - set(self.on_set) - set(self.dc_set))

    def output_for(self, minterm: int) -> int:
        """Return the output bit for a given minterm integer."""
        return 1 if minterm in self.on_set else 0

    def to_list(self) -> List[Tuple[Tuple[int, ...], int]]:
        """
        Return the full truth table as a list of (input_tuple, output) pairs,
        sorted by minterm index.
        """
        rows = []
        for m in range(1 << self.N):
            bits = _int_to_bits(m, self.N)
            out = self.output_for(m)
            rows.append((bits, out))
        return rows


# ---------------------------------------------------------------------------
# Core enumeration
# ---------------------------------------------------------------------------

def enumerate_truth_tables(
    W: np.ndarray,
    tie_break: int = 1,
) -> List[NeuronTruthTable]:
    """
    Enumerate per-neuron update truth tables from weight matrix W.

    Parameters
    ----------
    W : ndarray of shape (N, N)
        Hopfield weight matrix (symmetric, zero diagonal).
    tie_break : {0, 1}
        Output bit when the net input h_i == 0 exactly.
        Convention: 1 (stay high) is common; matches hardware sign(0)=+1.

    Returns
    -------
    List of N NeuronTruthTable objects (one per neuron).
    """
    W = np.asarray(W, dtype=np.float64)
    N = W.shape[0]
    if W.shape != (N, N):
        raise ValueError("W must be a square matrix.")

    # Pre-compute column sums needed for the bipolar→binary conversion:
    #   h_i(b) = 2·(W_i · b) − sum(W_i)   where b ∈ {0,1}^N
    row_sums = W.sum(axis=1)   # shape (N,)

    tables = [NeuronTruthTable(neuron_idx=i, N=N) for i in range(N)]

    # Iterate over all 2^N binary input vectors
    total = 1 << N
    # Build all input vectors at once as a 2^N × N matrix for speed
    all_inputs = np.array(
        [_int_to_bits(m, N) for m in range(total)],
        dtype=np.float64,
    )  # shape (2^N, N)

    # h_i(b) = 2*(W[i] @ b) - row_sums[i]   for every input b
    # H shape: (2^N, N)
    H = 2.0 * (all_inputs @ W.T) - row_sums[np.newaxis, :]

    for i in range(N):
        on_set = []
        for m in range(total):
            h = H[m, i]
            if h > 0:
                out = 1
            elif h < 0:
                out = 0
            else:
                out = tie_break
            if out == 1:
                on_set.append(m)
        tables[i].on_set = on_set

    return tables


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def save_csv(tables: List[NeuronTruthTable], out_dir: Path) -> None:
    """
    Write one CSV per neuron: tt_neuron_{i}.csv
    Columns: b_0, b_1, ..., b_{N-1}, f_i
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    N = tables[0].N
    header = [f"b_{j}" for j in range(N)] + ["f_i"]
    for tt in tables:
        path = out_dir / f"tt_neuron_{tt.neuron_idx:03d}.csv"
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for bits, out in tt.to_list():
                writer.writerow(list(bits) + [out])


def save_json(tables: List[NeuronTruthTable], path: Path) -> None:
    """
    Write all truth tables to a single JSON file.
    Format:
        { "N": 8, "neurons": [ {"idx": 0, "on_set": [...], "dc_set": [...]}, ... ] }
    """
    data = {
        "N": tables[0].N,
        "neurons": [
            {"idx": tt.neuron_idx, "on_set": tt.on_set, "dc_set": tt.dc_set}
            for tt in tables
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_json(path: Path) -> List[NeuronTruthTable]:
    """Load truth tables previously saved by save_json."""
    with open(path) as f:
        data = json.load(f)
    N = data["N"]
    tables = []
    for entry in data["neurons"]:
        tt = NeuronTruthTable(
            neuron_idx=entry["idx"],
            N=N,
            on_set=entry["on_set"],
            dc_set=entry["dc_set"],
        )
        tables.append(tt)
    return tables


def print_summary(tables: List[NeuronTruthTable]) -> None:
    """Print a compact summary table to stdout."""
    N = tables[0].N
    total = 1 << N
    print(f"{'Neuron':>7} | {'ON-set size':>11} | {'OFF-set size':>12} | {'const?':>6}")
    print("-" * 48)
    for tt in tables:
        on = len(tt.on_set)
        off = total - on
        const = "1" if on == total else ("0" if on == 0 else "-")
        print(f"{tt.neuron_idx:>7} | {on:>11} | {off:>12} | {const:>6}")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _int_to_bits(m: int, N: int) -> Tuple[int, ...]:
    """Convert integer m to a tuple of N bits, MSB first."""
    return tuple((m >> (N - 1 - j)) & 1 for j in range(N))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enumerate per-neuron Hopfield update truth tables."
    )
    parser.add_argument(
        "--weights", type=str, required=True,
        help="Path to weight matrix (.npy file from hopfield_train.py)"
    )
    parser.add_argument(
        "--out", type=str, default="tt",
        help="Output directory for CSV files (default: tt/)"
    )
    parser.add_argument(
        "--json", type=str, default=None,
        help="Also write combined JSON to this path"
    )
    parser.add_argument(
        "--tie-break", type=int, choices=[0, 1], default=1,
        help="Output when net input h_i == 0 (default: 1)"
    )
    args = parser.parse_args()

    W = np.load(args.weights)
    N = W.shape[0]
    print(f"Loaded {N}×{N} weight matrix from {args.weights}")
    print(f"Enumerating 2^{N} = {1<<N} input combinations per neuron …")

    tables = enumerate_truth_tables(W, tie_break=args.tie_break)

    out_dir = Path(args.out)
    save_csv(tables, out_dir)
    print(f"CSVs written to {out_dir}/")

    if args.json:
        save_json(tables, Path(args.json))
        print(f"JSON written to {args.json}")

    print()
    print_summary(tables)
