# Draft reply — Bill Lin, "Re: Progress on Logic Synthesis"

Answers his three points directly. Numbers are traceable via `audit_claims.py`
(C2, C3, C19). Deliberately short — he writes brief emails.

Supporting figures if he wants them: `fig2_scheduling_rule.png` (the 2x2),
`fig9_hd_sweep.png` (recall vs corruption). Hazard data has no figure yet.

---

**Subject:** Re: Progress on Logic Synthesis

Hi Professor Lin,

Both points are right, and the second one turned out to be answerable — I ran it
this week.

**On the colouring.** Yes, more than 2 colours. I extracted the actual coupling
graph for our N=16 max-prune network: 43 edges, ~36% density, and **χ = 6**.
Assigning delays by index parity leaves **19 of those 43 coupled pairs committing
at the same instant** — 44% — with the worst case being the highest-degree neuron
sharing its delay with 6 of its 11 neighbours. Even/odd is only correct when the
graph happens to be bipartite, and ours isn't. And yes, per-colour delays.

One refinement worth flagging: the invariant is on the delay **values**, not the
colour classes. A *valid* 6-colouring in which all six classes are given the same
delay settles 0% of the hard states — the colouring is meaningless unless it's
realised as distinct delays. Conversely, distinct delays without a colouring is
also 0%. Both ingredients are necessary, neither is sufficient. Encouragingly, χ
stays around 6 even at N=4096, since sparse graphs colour cheaply.

**On hazards.** You're right that the delays only address oscillation, and that
we hadn't touched hazards — our RTL is zero-delay combinational logic, so glitches
have zero width in simulation and never reach the state element. We'd assumed the
problem away.

I tested it by injecting spurious commits — a commit latches the *inverse* of the
computed value — and sweeping the rate. At N=256 with 10% of bits corrupted at
the start, **86 glitches against 123 commits still gives 98% recall**, and
settling stays at 100% at every rate tested. Targeting only the highest-fan-in
quarter of neurons (deepest SOP, where hazards would concentrate) holds up to an
80% glitch rate.

So on this evidence hazards look benign: a glitched neuron re-evaluates, a
correction gets scheduled, and the basin pulls the state back. Two caveats — my
model latches a full wrong value, which is more severe than a narrow pulse, but
injects glitches *independently*, whereas real hazards correlate with specific
input transitions. The definitive test is gate-level simulation with annotated
delays; we have the tooling (yosys + iverilog) and I can run it next.

**On C-elements.** Agreed that's the right mechanism if we do need it, but worth
noting two things. It doesn't replace the colouring — a C-element makes a neuron
wait for stable inputs, but doesn't stop two *coupled* neurons committing
together, so the two compose rather than substitute. And dual-rail plus
completion detection roughly doubles the logic, which we can't easily afford: our
area advantage over a conventional threshold-gate implementation is already
marginal.

There's also a tension I'd like your read on — hazard-free two-level synthesis
needs redundant consensus terms, which is exactly what our don't-care
minimisation strips out. If hazards do matter, that trade may be the more
important question.

Happy to go through any of this when we meet.

Best,
Aarav
