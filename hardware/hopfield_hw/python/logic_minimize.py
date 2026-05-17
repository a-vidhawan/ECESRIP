"""
logic_minimize.py
=================
Two-level Boolean minimization for Hopfield neuron update functions,
with explicit **hazard-free** cover generation.

Algorithm
---------
1. **Quine-McCluskey (Q-M)** — find all prime implicants of each
   neuron's Boolean function  f_i : {0,1}^N → {0,1}.

2. **Essential prime implicant selection** (Petrick's method or greedy)
   — choose a minimal cover that hits every minterm in the ON-set.

3. **Hazard-free cover** — static-1 hazards occur when two adjacent
   minterms (differ in exactly one variable) are both in the ON-set
   but NOT covered by a single prime implicant.  We add the *consensus*
   prime implicant that covers each such pair to the cover, guaranteeing
   that no glitch can propagate even with unequal gate delays.

Definitions
-----------
Implicant : a product term represented as a tuple of length N, where
            each element is 0, 1, or '-' (don't-care).

Minterm   : an implicant with no don't-cares (all 0 or 1).

Usage
-----
    from logic_minimize import minimize_all, print_cover
    from truth_table_gen import NeuronTruthTable

    covers = minimize_all(tables)          # list of covers, one per neuron
    for i, cover in enumerate(covers):
        print_cover(i, cover)
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from truth_table_gen import NeuronTruthTable, _int_to_bits


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Implicant = Tuple[int, ...]   # length-N tuple of 0 / 1 / 2 (2 = don't-care)
Cover = List[Implicant]
DC = 2   # sentinel value for "don't-care" in an implicant position


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def minimize_all(
    tables: List[NeuronTruthTable],
    hazard_free: bool = True,
) -> List[Cover]:
    """
    Minimize all neuron truth tables and return a list of Boolean covers.

    Parameters
    ----------
    tables       : list of NeuronTruthTable (from truth_table_gen.py)
    hazard_free  : if True (default), augment the minimal cover with
                   extra consensus prime implicants to eliminate static
                   hazards.

    Returns
    -------
    List of N covers, each cover is a list of Implicants (product terms).
    """
    covers = []
    for tt in tables:
        cover = _minimize_one(tt, hazard_free=hazard_free)
        covers.append(cover)
    return covers


def implicant_to_sv(imp: Implicant, var_names: Optional[List[str]] = None) -> str:
    """
    Convert an implicant to a SystemVerilog AND expression.

    Example (N=4, implicant (1, DC, 0, DC)):
        "b[3] & ~b[1]"
    """
    N = len(imp)
    if var_names is None:
        var_names = [f"b[{j}]" for j in range(N)]
    terms = []
    for j, v in enumerate(imp):
        if v == 1:
            terms.append(var_names[j])
        elif v == 0:
            terms.append(f"~{var_names[j]}")
        # DC → skip
    if not terms:
        return "1'b1"   # tautology (covers all minterms)
    return " & ".join(terms)


def cover_to_sv_expr(cover: Cover, var_names: Optional[List[str]] = None) -> str:
    """
    Convert a cover (list of implicants) to a SV OR-of-AND expression.
    Each implicant becomes one AND clause; clauses are OR'd together.
    """
    if not cover:
        return "1'b0"
    clauses = [f"({implicant_to_sv(imp, var_names)})" for imp in cover]
    return " | ".join(clauses)


def print_cover(neuron_idx: int, cover: Cover) -> None:
    """Pretty-print a Boolean cover in SOP notation."""
    N = len(cover[0]) if cover else 0
    print(f"  Neuron {neuron_idx:3d}  ({len(cover)} product terms):")
    for imp in cover:
        sym = "".join("1" if v == 1 else ("0" if v == 0 else "-") for v in imp)
        sv = implicant_to_sv(imp)
        print(f"    {sym}   →   {sv}")


# ---------------------------------------------------------------------------
# Quine-McCluskey implementation
# ---------------------------------------------------------------------------

def _minimize_one(tt: NeuronTruthTable, hazard_free: bool) -> Cover:
    """Run Q-M + (optionally) hazard-free consensus for one neuron."""
    on_set: Set[int] = set(tt.on_set)
    dc_set: Set[int] = set(tt.dc_set)
    N = tt.N

    # Trivial cases
    if not on_set:
        return []
    if len(on_set) + len(dc_set) == (1 << N):
        return [tuple(DC for _ in range(N))]   # tautology

    # Step 1: find all prime implicants
    prime_implicants = _find_prime_implicants(on_set | dc_set, N)

    # Step 2: cover the ON-set (don't need to cover dc_set)
    cover = _cover_on_set(prime_implicants, on_set, N)

    # Step 3 (optional): make hazard-free
    if hazard_free:
        cover = _make_hazard_free(cover, prime_implicants, on_set, N)

    return cover


def _find_prime_implicants(
    mint_plus_dc: Set[int], N: int
) -> List[Implicant]:
    """
    Standard Quine-McCluskey prime implicant generation.
    Works on combined ON-set ∪ DC-set.
    """
    # Represent implicants as tuples of (0, 1, DC)
    # Start: each minterm is a length-N tuple
    groups: Dict[int, Set[Tuple[int, ...]]] = defaultdict(set)
    for m in mint_plus_dc:
        imp = tuple((m >> (N - 1 - j)) & 1 for j in range(N))
        ones = sum(v for v in imp if v == 1)
        groups[ones].add(imp)

    prime_imps: Set[Tuple[int, ...]] = set()
    current_groups = dict(groups)

    while True:
        next_groups: Dict[int, Set[Tuple[int, ...]]] = defaultdict(set)
        combined: Set[Tuple[int, ...]] = set()

        sorted_keys = sorted(current_groups.keys())
        for i in range(len(sorted_keys) - 1):
            k0, k1 = sorted_keys[i], sorted_keys[i + 1]
            if k1 - k0 != 1:
                continue
            for a in current_groups[k0]:
                for b in current_groups[k1]:
                    merged = _try_merge(a, b)
                    if merged is not None:
                        combined.add(a)
                        combined.add(b)
                        ones = sum(1 for v in merged if v == 1)
                        next_groups[ones].add(merged)

        # Implicants that couldn't be merged are prime
        for imp_set in current_groups.values():
            for imp in imp_set:
                if imp not in combined:
                    prime_imps.add(imp)

        if not next_groups:
            break
        current_groups = dict(next_groups)

    return list(prime_imps)


def _try_merge(
    a: Tuple[int, ...], b: Tuple[int, ...]
) -> Optional[Tuple[int, ...]]:
    """
    Try to merge two implicants.  They must differ in exactly one
    non-DC position; that position becomes DC in the result.
    Returns None if they cannot be merged.
    """
    diffs = []
    for j, (va, vb) in enumerate(zip(a, b)):
        if va != vb:
            if va == DC or vb == DC:
                return None   # DC positions must already match
            diffs.append(j)
    if len(diffs) != 1:
        return None
    result = list(a)
    result[diffs[0]] = DC
    return tuple(result)


def _implicant_covers_minterm(imp: Tuple[int, ...], m: int, N: int) -> bool:
    """Return True iff the implicant covers minterm m."""
    for j, v in enumerate(imp):
        bit = (m >> (N - 1 - j)) & 1
        if v != DC and v != bit:
            return False
    return True


def _cover_on_set(
    prime_imps: List[Implicant], on_set: Set[int], N: int
) -> Cover:
    """
    Greedy essential-PI selection:
    1. Find essential PIs (minterms covered by exactly one PI).
    2. Greedily add the PI that covers the most uncovered minterms.
    """
    # Build coverage map: minterm → set of PI indices that cover it
    coverage: Dict[int, List[int]] = {m: [] for m in on_set}
    for idx, pi in enumerate(prime_imps):
        for m in on_set:
            if _implicant_covers_minterm(pi, m, N):
                coverage[m].append(idx)

    selected: Set[int] = set()
    covered: Set[int] = set()

    # Essential PIs
    for m, pi_list in coverage.items():
        if len(pi_list) == 1:
            pi_idx = pi_list[0]
            if pi_idx not in selected:
                selected.add(pi_idx)
                for m2 in on_set:
                    if _implicant_covers_minterm(prime_imps[pi_idx], m2, N):
                        covered.add(m2)

    # Greedy for remaining minterms
    uncovered = on_set - covered
    while uncovered:
        best_idx = max(
            range(len(prime_imps)),
            key=lambda idx: sum(
                1 for m in uncovered
                if _implicant_covers_minterm(prime_imps[idx], m, N)
            ),
        )
        selected.add(best_idx)
        for m in list(uncovered):
            if _implicant_covers_minterm(prime_imps[best_idx], m, N):
                uncovered.discard(m)

    return [prime_imps[i] for i in sorted(selected)]


# ---------------------------------------------------------------------------
# Hazard-free augmentation
# ---------------------------------------------------------------------------

def _make_hazard_free(
    cover: Cover,
    prime_imps: List[Implicant],
    on_set: Set[int],
    N: int,
) -> Cover:
    """
    Static-1 hazard elimination by consensus.

    A static-1 hazard exists when two ON-set minterms m_a and m_b differ
    in exactly one variable (they are adjacent) but no single implicant
    in the cover covers both.

    Remedy: find (or construct) the prime implicant that covers both, and
    add it to the cover.  This is the *consensus* implicant for that pair.

    We iterate until no new implicants are needed (fixed point).
    """
    cover_set: List[Implicant] = list(cover)

    changed = True
    while changed:
        changed = False
        # Check all pairs of adjacent ON-set minterms
        on_list = sorted(on_set)
        for i in range(len(on_list)):
            for j in range(i + 1, len(on_list)):
                ma, mb = on_list[i], on_list[j]
                if bin(ma ^ mb).count("1") != 1:
                    continue   # not adjacent
                # Are both covered by a single implicant in the current cover?
                shared_cover = [
                    imp for imp in cover_set
                    if _implicant_covers_minterm(imp, ma, N)
                    and _implicant_covers_minterm(imp, mb, N)
                ]
                if shared_cover:
                    continue   # already hazard-free for this pair

                # Need to add a consensus term.
                # The consensus of ma and mb is the implicant that covers
                # the entire cube containing both (the bit that differs → DC).
                diff_pos = next(
                    j2 for j2 in range(N)
                    if ((ma >> (N - 1 - j2)) & 1) != ((mb >> (N - 1 - j2)) & 1)
                )
                # Build the tightest implicant covering both: same as ma
                # but with the differing bit set to DC.
                consensus = list(
                    (ma >> (N - 1 - j2)) & 1 for j2 in range(N)
                )
                consensus[diff_pos] = DC
                consensus_imp = tuple(consensus)

                # Expand to a prime implicant: try to merge further
                pi = _expand_to_prime(consensus_imp, on_set, N)

                if pi not in cover_set:
                    cover_set.append(pi)
                    changed = True

    return cover_set


def _expand_to_prime(
    imp: Implicant, on_dc: Set[int], N: int
) -> Implicant:
    """
    Try to expand an implicant into a prime implicant by introducing
    additional don't-care positions, as long as we don't cover any
    minterms outside on_dc.
    """
    current = list(imp)
    for pos in range(N):
        if current[pos] == DC:
            continue
        trial = list(current)
        trial[pos] = DC
        trial_imp = tuple(trial)
        # Check that no off-set minterm is newly covered
        if _covers_only(trial_imp, on_dc, N):
            current = trial
    return tuple(current)


def _covers_only(imp: Implicant, allowed: Set[int], N: int) -> bool:
    """Return True iff every minterm covered by imp is in the allowed set."""
    for m in range(1 << N):
        if _implicant_covers_minterm(imp, m, N) and m not in allowed:
            return False
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    from truth_table_gen import load_json

    parser = argparse.ArgumentParser(
        description="Minimize Hopfield neuron truth tables (Q-M + hazard-free)."
    )
    parser.add_argument(
        "--tt-json", type=str, required=True,
        help="JSON truth-table file produced by truth_table_gen.py"
    )
    parser.add_argument(
        "--no-hazard-free", action="store_true",
        help="Skip hazard-free augmentation (not recommended for hardware)"
    )
    args = parser.parse_args()

    tables = load_json(args.tt_json)
    covers = minimize_all(tables, hazard_free=not args.no_hazard_free)

    print("Minimized Boolean covers:")
    for i, cover in enumerate(covers):
        print_cover(i, cover)
