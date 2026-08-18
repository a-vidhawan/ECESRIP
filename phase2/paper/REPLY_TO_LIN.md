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

I then ran the gate-level version, which produces glitches from the circuit
rather than inventing them: the neuron logic is synthesised to primitive gates
(671 of them for a small N=32 network), each gate type given a different delay so
paths through the AND/OR planes are genuinely unequal, and the netlist simulated
against the zero-delay behavioural model on identical vectors. The two are
logically equivalent, so any disagreement is glitch-induced.

That turned up something more useful than a yes/no on hazards. Initially the
gate-level model agreed with the behavioural one on only 50% of inputs — but most
of that was **not** hazards. The gate delays (1–5 ns each over several levels)
exceeded the scheduling delays (1–7 ns), so commits were being sequenced on stale
logic and the colouring was meaningless. Scaling the scheduling delays up by 20×
took agreement to 90%, and scaling a further 5× changed nothing.

So there is a design rule we had not stated: **the scheduling delays must exceed
the worst-case combinational propagation delay through the neuron.** That seems
obvious in hindsight but it is a real constraint on how the delays get sized, and
it interacts with your per-colour delay question — the *spread* between colours
has to sit on top of a floor set by the logic depth.

Once that rule is satisfied, the residual hazard effect is real but modest: ~10%
of inputs settle to a different fixed point, costing about 5 points of recall
(95% → 90%). It does not improve with further delay margin, which is what tells
us it is genuinely a hazard rather than a timing shortfall. That is a smaller
effect than I would want to ignore in a final design, but much smaller than the
delay-budgeting problem it was hiding behind.

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
