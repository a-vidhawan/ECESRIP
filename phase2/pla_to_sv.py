"""
pla_to_sv.py
============
Convert Espresso-minimized PLA files to a synthesizable SystemVerilog module.

Reads the .ilb (input labels) and .ob (output label) from each minimized PLA
to correctly map bit positions back to physical neuron indices. A product term
like:

    1-0  1

with .ilb b_2 b_5 b_7  means:  b_2=1, b_5=don't care, b_7=0 → output 1

which becomes in SV:

    (s[2] & ~s[7])

The output is a single SystemVerilog module with:
  - input  logic [N-1:0] s       current state
  - output logic [N-1:0] s_next  next state (one async update step)

Each neuron's next-state logic is an assign statement in sum-of-products form.

Usage
-----
    python phase2/pla_to_sv.py \\
      --input  phase2/pla_min/ \\
      --out    phase2/rtl/hopfield_lut.sv \\
      --module hopfield_lut \\
      --N      16
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# PLA parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_pla(path: Path) -> dict:
    """
    Parse a (possibly Espresso-minimized) PLA file.

    Returns
    -------
    dict with keys:
        n_inputs  : int
        n_outputs : int
        ilb       : list[str]  — input label names (e.g. ['b_2', 'b_5', 'b_7'])
        ob        : list[str]  — output label names (e.g. ['f_3'])
        products  : list[tuple[str, str]]  — (input_pattern, output_pattern)
    """
    result = {
        "n_inputs": 0, "n_outputs": 0,
        "ilb": [], "ob": [],
        "products": [],
    }

    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(".i "):
                result["n_inputs"] = int(line.split()[1])
            elif line.startswith(".o "):
                result["n_outputs"] = int(line.split()[1])
            elif line.startswith(".ilb"):
                result["ilb"] = line.split()[1:]
            elif line.startswith(".ob"):
                result["ob"] = line.split()[1:]
            elif line.startswith(".e") or line.startswith(".end"):
                break
            elif re.match(r'^[01\-]+\s+[01\-]+$', line):
                parts = line.split()
                result["products"].append((parts[0], parts[1]))

    # If no .ilb present, generate default b_0 .. b_{n-1}
    if not result["ilb"] and result["n_inputs"]:
        result["ilb"] = [f"b_{j}" for j in range(result["n_inputs"])]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# SOP expression builder
# ─────────────────────────────────────────────────────────────────────────────

def _label_to_sv_signal(label: str) -> str:
    """
    Convert a PLA label like 'b_5' to a SV signal reference 's[5]'.
    Labels not matching b_{N} pattern are kept as-is.
    """
    m = re.match(r'^b_(\d+)$', label)
    if m:
        return f"s[{m.group(1)}]"
    return label


def product_term_to_sv(input_pattern: str, ilb: list[str]) -> str:
    """
    Convert one product term (e.g. '1-0') + input labels to a SV AND expression.

    '1-0' with ilb = ['b_2', 'b_5', 'b_7']
    →  (s[2] & ~s[7])
    """
    literals = []
    for bit, label in zip(input_pattern, ilb):
        sig = _label_to_sv_signal(label)
        if bit == "1":
            literals.append(sig)
        elif bit == "0":
            literals.append(f"~{sig}")
        # '-' = don't care → omit

    if not literals:
        return "1'b1"   # tautology (all don't-cares → always true)
    if len(literals) == 1:
        return literals[0]
    return "(" + " & ".join(literals) + ")"


def pla_to_sop_sv(pla: dict, output_idx: int = 0) -> str:
    """
    Convert parsed PLA to a SV expression for one output (SOP form).

    output_idx selects which output column to use (for multi-output PLAs).
    """
    # Filter product terms where this output = '1'
    on_products = [
        inp for inp, out in pla["products"]
        if output_idx < len(out) and out[output_idx] == "1"
    ]

    if not on_products:
        return "1'b0"

    terms = [product_term_to_sv(inp, pla["ilb"]) for inp in on_products]

    if len(terms) == 1:
        return terms[0]
    return "\n        | ".join(terms)


# ─────────────────────────────────────────────────────────────────────────────
# SV module generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_sv_module(
    pla_dir: Path,
    N: int,
    module_name: str = "hopfield_lut",
    update_mode: str = "async_cyclic",
) -> str:
    """
    Read all neuron_*.pla files from pla_dir and emit a SystemVerilog module.

    The module is purely combinational: given the current state s, it computes
    s_next for all neurons simultaneously (or one at a time in hardware flow).

    Parameters
    ----------
    pla_dir     : directory of minimized .pla files (one per neuron)
    N           : total number of neurons
    module_name : SV module name
    update_mode : 'async_cyclic' adds a note; hardware FSM controls which
                  neuron's s_next is applied each cycle
    """
    # Load all per-neuron PLAs
    neuron_exprs = {}   # neuron_idx → SV expression string

    pla_files = sorted(pla_dir.glob("neuron_*.pla"))
    if not pla_files:
        raise FileNotFoundError(f"No neuron_*.pla files found in {pla_dir}")

    for pla_path in pla_files:
        m = re.search(r'neuron_(\d+)\.pla', pla_path.name)
        if not m:
            continue
        idx = int(m.group(1))
        pla = parse_pla(pla_path)

        if not pla["products"]:
            # Constant 0 (no on-set entries after minimization)
            neuron_exprs[idx] = "1'b0"
        else:
            neuron_exprs[idx] = pla_to_sop_sv(pla, output_idx=0)

    # Fill any missing neurons with constant (shouldn't happen)
    for i in range(N):
        if i not in neuron_exprs:
            neuron_exprs[i] = "1'b0"

    # Emit SV
    lines = []
    lines.append(f"// Auto-generated by pla_to_sv.py")
    lines.append(f"// Hopfield LUT update logic — N={N} neurons")
    lines.append(f"// Update mode: {update_mode}")
    lines.append(f"// Source PLA directory: {pla_dir}")
    lines.append(f"")
    lines.append(f"module {module_name} #(")
    lines.append(f"    parameter int N = {N}")
    lines.append(f") (")
    lines.append(f"    input  logic [N-1:0] s,       // current state (binary {{0,1}})")
    lines.append(f"    output logic [N-1:0] s_next   // next state (one update step)")
    lines.append(f");")
    lines.append(f"")
    lines.append(f"    // Per-neuron combinational update (SOP from Espresso)")

    for i in range(N):
        expr = neuron_exprs[i]
        # Multi-line expressions: indent continuation lines
        if "\n" in expr:
            expr_indented = expr.replace("\n", "\n    ")
            lines.append(f"    assign s_next[{i:3d}] = {expr_indented};")
        else:
            lines.append(f"    assign s_next[{i:3d}] = {expr};")

    lines.append(f"")
    lines.append(f"endmodule  // {module_name}")
    lines.append(f"")

    return "\n".join(lines)


def generate_sv_with_fsm(
    N: int,
    module_name: str = "hopfield_top",
    lut_module: str  = "hopfield_lut",
) -> str:
    """
    Emit a clocked FSM wrapper that drives the combinational LUT module
    with async-cyclic updates (neuron 0 → 1 → … → N-1 → repeat).

    This is the top-level synthesizable module that goes to Vivado.
    """
    lines = []
    lines.append(f"// Auto-generated FSM wrapper for {lut_module}")
    lines.append(f"// Async-cyclic update: neurons 0..{N-1} in sequence")
    lines.append(f"")
    lines.append(f"module {module_name} #(")
    lines.append(f"    parameter int N = {N}")
    lines.append(f") (")
    lines.append(f"    input  logic             clk,")
    lines.append(f"    input  logic             rst_n,")
    lines.append(f"    input  logic             load,      // 1: load i_state, 0: run")
    lines.append(f"    input  logic [N-1:0]     i_state,   // initial/probe state")
    lines.append(f"    output logic [N-1:0]     o_state,   // current state")
    lines.append(f"    output logic             o_done     // high when fixed point reached")
    lines.append(f");")
    lines.append(f"")
    lines.append(f"    logic [N-1:0] s, s_next_all;")
    lines.append(f"    logic [$clog2(N)-1:0] neuron_idx;")
    lines.append(f"    logic changed;")
    lines.append(f"")
    lines.append(f"    // Combinational LUT block")
    lines.append(f"    {lut_module} #(.N(N)) lut_inst (.s(s), .s_next(s_next_all));")
    lines.append(f"")
    lines.append(f"    assign o_state = s;")
    lines.append(f"")
    lines.append(f"    always_ff @(posedge clk or negedge rst_n) begin")
    lines.append(f"        if (!rst_n) begin")
    lines.append(f"            s          <= '0;")
    lines.append(f"            neuron_idx <= '0;")
    lines.append(f"            changed    <= 1'b0;")
    lines.append(f"            o_done     <= 1'b0;")
    lines.append(f"        end else if (load) begin")
    lines.append(f"            s          <= i_state;")
    lines.append(f"            neuron_idx <= '0;")
    lines.append(f"            changed    <= 1'b0;")
    lines.append(f"            o_done     <= 1'b0;")
    lines.append(f"        end else if (!o_done) begin")
    lines.append(f"            // Apply update for current neuron")
    lines.append(f"            s[neuron_idx] <= s_next_all[neuron_idx];")
    lines.append(f"            changed <= changed | (s_next_all[neuron_idx] != s[neuron_idx]);")
    lines.append(f"")
    lines.append(f"            if (neuron_idx == N-1) begin")
    lines.append(f"                // End of sweep")
    lines.append(f"                if (!changed && !(s_next_all[neuron_idx] != s[neuron_idx]))")
    lines.append(f"                    o_done <= 1'b1;  // no neuron changed → fixed point")
    lines.append(f"                neuron_idx <= '0;")
    lines.append(f"                changed    <= 1'b0;")
    lines.append(f"            end else begin")
    lines.append(f"                neuron_idx <= neuron_idx + 1;")
    lines.append(f"            end")
    lines.append(f"        end")
    lines.append(f"    end")
    lines.append(f"")
    lines.append(f"endmodule  // {module_name}")
    lines.append(f"")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert minimized Espresso PLA files to SystemVerilog."
    )
    parser.add_argument("--input",  type=str, required=True,
                        help="Directory of minimized neuron_*.pla files")
    parser.add_argument("--out",    type=str, required=True,
                        help="Output .sv file path")
    parser.add_argument("--N",      type=int, required=True,
                        help="Number of neurons")
    parser.add_argument("--module", type=str, default="hopfield_lut",
                        help="SV module name for the LUT logic")
    parser.add_argument("--with-fsm", action="store_true",
                        help="Also emit a clocked FSM wrapper module")
    args = parser.parse_args()

    pla_dir = Path(args.input)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Reading PLAs from {pla_dir}")
    sv = generate_sv_module(pla_dir, args.N, module_name=args.module)

    if args.with_fsm:
        fsm_name = args.module.replace("_lut", "_top")
        sv += "\n" + generate_sv_with_fsm(args.N, module_name=fsm_name, lut_module=args.module)
        print(f"FSM wrapper module: {fsm_name}")

    out_path.write_text(sv)
    print(f"SystemVerilog → {out_path}")

    # Print stats
    n_assigns = sv.count("assign s_next")
    n_terms   = sv.count("(s[") + sv.count("~s[")
    print(f"  {n_assigns} assign statements, ~{n_terms} literals")
