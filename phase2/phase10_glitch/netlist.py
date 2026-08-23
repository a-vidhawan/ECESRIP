#!/usr/bin/env python3
"""
Structural gate emitters for the two glitch-mitigation schemes.

Everything here bypasses yosys/abc deliberately. The earlier gate-level study
let abc remap the logic, which is fine for a single-rail SOP but would destroy a
dual-rail one: NCL's hazard-freedom comes from the netlist being MONOTONE (no
inversions inside the datapath), and a resynthesis tool that has never heard of
that invariant will happily introduce an inverter and break it. Emitting the
gates ourselves also makes the comparison exact -- both schemes get the same
cell library and the same delays, so the only difference between them is the
logic structure, which is the thing under test.
"""

# Distinct per-type delays. Equal delays would balance every path and hide the
# very hazards this is built to observe.
CELLS = r"""
`timescale 1ns/1ps
module g_inv (input a, output y);        assign #1 y = ~a;    endmodule
module g_and2(input a, b, output y);     assign #3 y = a & b; endmodule
module g_or2 (input a, b, output y);     assign #4 y = a | b; endmodule
// Muller C-element: drives when its inputs agree, holds when they disagree.
// The hold is what gives it hysteresis, and the hysteresis is what makes it
// immune to an input that briefly disagrees -- i.e. to a glitch.
module g_c2  (input a, b, output reg y);
  initial y = 1'b0;
  always @(a or b) begin
    if      ( a &&  b) y <= #2 1'b1;
    else if (!a && !b) y <= #2 1'b0;
  end
endmodule
"""


class Net:
    """Tiny structural netlist builder: 2-input gates, balanced trees."""

    def __init__(self):
        self.wires, self.gates, self._n = [], [], 0

    def new(self):
        self._n += 1
        w = f"n{self._n}"
        self.wires.append(w)
        return w

    def g(self, typ, ins):
        o = self.new()
        self.gates.append((typ, ins, o))
        return o

    def inv(self, a):
        return self.g("g_inv", [a])

    def _tree(self, typ, xs):
        if not xs:
            return None
        while len(xs) > 1:
            nxt = [self.g(typ, [xs[i], xs[i + 1]]) for i in range(0, len(xs) - 1, 2)]
            if len(xs) % 2:
                nxt.append(xs[-1])
            xs = nxt
        return xs[0]

    def ands(self, xs):
        return self._tree("g_and2", list(xs))

    def ors(self, xs):
        return self._tree("g_or2", list(xs))

    def cs(self, xs):
        return self._tree("g_c2", list(xs))

    def render(self, header, assigns):
        L = [header]
        if self.wires:
            L.append("  wire " + ", ".join(self.wires) + ";")
        for typ, ins, o in self.gates:
            ports = ", ".join(f".{p}({v})" for p, v in
                              zip("ab" if len(ins) == 2 else "a", ins))
            L.append(f"  {typ} u_{o} ({ports}, .y({o}));")
        L += [f"  assign {lhs} = {rhs};" for lhs, rhs in assigns]
        L.append("endmodule")
        return "\n".join(L)

    def count(self):
        return len(self.gates)


def emit_single_rail(N, funcs, path):
    """Ordinary SOP, one wire per signal.

    Negative literals need inverters, so the AND plane sees the true and
    complemented forms of an input at DIFFERENT times. That skew is precisely
    what turns a logically-correct SOP into a glitching one.
    """
    net = Net()
    invs, assigns = {}, []

    def lit(j, bit):
        if bit == "1":
            return f"s[{j}]"
        if j not in invs:
            invs[j] = net.inv(f"s[{j}]")
        return invs[j]

    for i, (sup, cubes) in enumerate(funcs):
        if sup is None or not cubes:
            assigns.append((f"s_next[{i}]", f"s[{i}]"))
            continue
        prods = [net.ands([lit(sup[k], b) for k, b in cube]) for cube in cubes]
        assigns.append((f"s_next[{i}]", net.ors(prods)))
    hdr = (f"`timescale 1ns/1ps\nmodule lut_sr "
           f"(input wire [{N-1}:0] s, output wire [{N-1}:0] s_next);")
    open(path, "w").write(net.render(hdr, assigns))
    return net.count()


def emit_dual_rail(N, funcs, path):
    """Dual-rail NCL datapath: monotone in the rails, so hazard-free by
    construction rather than by timing argument.

    Each spin arrives as a pair (t,f). NULL is both rails low; DATA is exactly
    one high. A literal is now a WIRE rather than a possibly-inverted wire, so
    every product term is monotone in the rails and so is their OR. Coming out
    of NULL every internal node can only go 0->1, and a node that never falls
    cannot glitch.

    The false rail is NOT a second don't-care minimisation. That was the first
    thing tried and it deadlocks: two covers minimised independently against the
    same don't-care set leave points covered by NEITHER, both rails stay low,
    and the completion detector waits forever for a DATA that never arrives.
    Don't-care minimisation and dual-rail completion are in direct conflict --
    completion needs the ON-set and OFF-set to PARTITION the input space, and
    don't-cares exist precisely to avoid committing to a partition.

    So the false rail is built by De Morgan on the true rail's cover instead:

        f.t = OR_c AND_{l in c}  rail(l)
        f.f = AND_c OR_{l in c}  rail(not l)

    which is exact for any DATA input, costs the same literal count, and needs
    no inverter -- the complement of a rail is simply the other rail of the same
    pair, which is already there. It also inherits whatever don't-care choice
    espresso made for the true rail, so the two rails cannot disagree.
    """
    net = Net()
    assigns, valid = [], []

    for i in range(N):
        sup, cubes = funcs[i]
        if sup is None:
            assigns += [(f"f_t[{i}]", f"r_t[{i}]"), (f"f_f[{i}]", f"r_f[{i}]")]
            valid.append(net.g("g_or2", [f"r_t[{i}]", f"r_f[{i}]"]))
            continue
        # a constant function still has to WAIT for its inputs, or completion
        # would fire before the wavefront has actually arrived
        arrived = net.ands([net.g("g_or2", [f"r_t[{j}]", f"r_f[{j}]"]) for j in sup])
        if not cubes:                       # constant 0 over the care set
            t, g = "1'b0", arrived
        elif any(len(c) == 0 for c in cubes):   # tautology cube -> constant 1
            t, g = arrived, "1'b0"
        else:
            t = net.ors([net.ands([f"r_t[{sup[k]}]" if b == "1" else f"r_f[{sup[k]}]"
                                   for k, b in c]) for c in cubes])
            g = net.ands([net.ors([f"r_f[{sup[k]}]" if b == "1" else f"r_t[{sup[k]}]"
                                   for k, b in c]) for c in cubes])
        assigns += [(f"f_t[{i}]", t), (f"f_f[{i}]", g)]
        valid.append(net.g("g_or2", [t, g]))

    # completion detection: a C-element tree, so `complete` rises only once
    # every neuron is DATA and falls only once every neuron is back to NULL
    assigns.append(("complete", net.cs(valid)))
    hdr = (f"`timescale 1ns/1ps\nmodule lut_dr (\n"
           f"  input  wire [{N-1}:0] r_t, r_f,\n"
           f"  output wire [{N-1}:0] f_t, f_f,\n"
           f"  output wire complete);")
    open(path, "w").write(net.render(hdr, assigns))
    return net.count()
