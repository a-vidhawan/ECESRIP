#!/usr/bin/env python3
"""
Extract the neuron coupling graph from the max-prune PLAs and evaluate
delay-class assignments against it.

A delay class is "safe" if no two coupled neurons share it -- i.e. the delay
assignment is a proper vertex colouring of the coupling graph. The even_odd
scheme colours by index parity, which ignores coupling entirely; this script
measures how many coupled pairs that leaves firing simultaneously.
"""

import os, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
PLA_DIR = os.path.join(HERE, "..", "pla_min", "pseudo_maxprune")
N = 16


def parse_neighbors(path):
    """Neighbours + term count straight from the PLA header/.p line."""
    nbrs, n_terms = [], 0
    with open(path) as f:
        for line in f:
            m = re.search(r"neighbors:\s*\[([^\]]*)\]", line)
            if m:
                body = m.group(1).strip()
                nbrs = [int(x) for x in body.split(",")] if body else []
            if line.startswith(".p "):
                n_terms = int(line.split()[1])
            if line.startswith(".e"):
                break
    return nbrs, n_terms


def build_graph():
    supports, terms = {}, {}
    for i in range(N):
        nbrs, t = parse_neighbors(os.path.join(PLA_DIR, f"neuron_{i:03d}.pla"))
        supports[i], terms[i] = set(nbrs), t
    # undirected: i--j if either reads the other
    edges = set()
    for i in range(N):
        for j in supports[i]:
            if j != i:
                edges.add((min(i, j), max(i, j)))
    return supports, terms, sorted(edges)


def conflicts(edges, classes):
    """Coupled pairs that land in the same delay class."""
    return [(i, j) for (i, j) in edges if classes[i] == classes[j]]


def greedy_colour(edges, order):
    adj = {i: set() for i in range(N)}
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    colour = {}
    for v in order:
        used = {colour[u] for u in adj[v] if u in colour}
        c = 0
        while c in used:
            c += 1
        colour[v] = c
    return colour


def main():
    supports, terms, edges = build_graph()
    adj_deg = {i: 0 for i in range(N)}
    for i, j in edges:
        adj_deg[i] += 1
        adj_deg[j] += 1

    max_edges = N * (N - 1) // 2
    print(f"coupling graph: {len(edges)} edges / {max_edges} possible "
          f"({100*len(edges)/max_edges:.1f}% dense)")
    print(f"degrees: {dict(sorted(adj_deg.items()))}")
    print(f"terms:   {dict(sorted(terms.items()))}")

    # --- scheme 1: index parity (what even_odd actually does)
    parity = {i: i % 2 for i in range(N)}
    pc = conflicts(edges, parity)
    print(f"\nPARITY (even_odd): {len(pc)}/{len(edges)} coupled pairs "
          f"fire SIMULTANEOUSLY ({100*len(pc)/len(edges):.1f}%)")
    print(f"  conflicting pairs: {pc}")

    # --- scheme 2: proper colouring (Welsh-Powell, high degree first)
    order = sorted(range(N), key=lambda v: -adj_deg[v])
    col = greedy_colour(edges, order)
    k = max(col.values()) + 1
    cc = conflicts(edges, col)
    print(f"\nGRAPH COLOURING: {k} classes, {len(cc)} conflicts")
    for c in range(k):
        print(f"  class {c}: {[i for i in range(N) if col[i] == c]}")

    out = {
        "edges": edges,
        "degrees": adj_deg,
        "terms": terms,
        "supports": {i: sorted(s) for i, s in supports.items()},
        "parity_classes": parity,
        "parity_conflicts": pc,
        "colour_classes": col,
        "n_colours": k,
    }
    dest = os.path.join(HERE, "results", "coupling_graph.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
