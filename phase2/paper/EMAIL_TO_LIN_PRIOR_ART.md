# Draft email to Prof. Lin — prior art findings and figure set

Written as the honest internal version. Reasoning: he will find Aadit and
Gonzalez himself in about ten minutes, and there is a duty-of-candor dimension
once we are filing. Much better coming from us. If you want a softer version
that leads with the results and puts the overlap later, say so.

---

**Subject:** Prior art overlap on the clockless HNN — what survives, what doesn't, and revised figures

Prof. Lin,

I've gone through the prior art on the clockless/graph-colouring work properly,
and read the four highest-risk references in full rather than from abstracts.
Some of it lands squarely on what we're claiming, including one thing I'd
previously told you was novel and isn't. Laying it out plainly, along with a
revised figure set.

**The closest reference is closer than we thought.**

Aadit et al., *Massively parallel probabilistic computing with sparse Ising
machines* (Nature Electronics 5, 460, 2022) describes its own architecture as
"a low level hardware-level implementation of chromatic Gibbs sampling," colours
the coupling graph, and reports that sparse problem graphs need "typically ≤ 4–8"
colours — the same regime as our χ = 6. Their stated motivation is ours verbatim:
"parallel updating leads to repeated oscillations in the network state,
preventing the network from converging."

Two specific sentences matter.

First: *"For this sampling to be exact, the MAC must finish its computation
before the next color block is updated."* That is the delay sizing rule I
described to you as our own finding. It's stated in the closest art, in 2022.
I was wrong about that one, and it needs correcting in the draft — what we
actually have is the *measurement* of what happens when the rule is violated,
not the rule.

Second: *"even when color blocks are updated before the MAC operation is
completed, the network is often able to find exact ground states … this
overclocking strategy can lead to further advantages."* They deliberately violate
the timing margin, find it helps, and connect it to Hogwild!-Gibbs. That is the
annealing-by-timing-margin idea from your figures, published with a claimed
advantage. I think that embodiment needs re-scoping or dropping.

**What does survive.**

Their timing reference is a set of phase-shifted periodic clocks. There is a
clock generator, a distribution network, and — in the 2024 follow-up
(Nikhar et al., Nat. Commun. 15:8977) — an explicit *clock multiplexer* in the
p-bit block diagram, with "6 phase-shifted clocks" for a 6-colouring. The word
"delay" does not appear anywhere in that paper. Not once.

So the distinction is: colour classes realised as **phase-shifted clocks** versus
colour classes realised as **per-node inertial delay values in the feedback
path**, with no periodic reference anywhere. I could not find that second thing
in any of the four references. It is a real distinction, and it is narrower than
I would like.

The other thing that survives is the result I've mentioned before, which now
carries more weight: the invariant is on delay *values*, not on class labels. A
valid proper colouring with all classes assigned the same delay is graph-
theoretically correct and settles in 0% of trials. Nothing in the art states
that, because in a clocked implementation a colour *is* a phase and the
distinction is invisible.

**A combination risk worth knowing about.**

Rosin et al., *Excitability in autonomous Boolean networks* (EPL, 2012), builds a
clockless recurrent Boolean network on an FPGA where each link carries a
programmable delay line made of inverter pairs, and the dynamics are controlled
by those link delay times. No Hopfield, no threshold logic, no colouring — the
delays are used to *create* oscillation patterns rather than prevent them. But it
supplies "clockless recurrent network with per-node programmable delay elements"
in one reference, and Aadit supplies "colour the graph to prevent oscillation."
The combination reads on our claim 1 without much strain.

**Two problems in the draft itself, independent of the art.**

Claim 1 omits the delay-value limitation — it's in dependent claim 2 only. So
claim 1 as drafted literally covers the configuration we measured settling 0% of
the time. That's an enablement problem on top of unnecessary novelty exposure,
and it should move up into claim 1.

And the don't-care synthesis isn't claimed at all. It's the one element none of
these references touch: the care set is derivable in closed form as
M·Σ_{k≤h}C(d,k) from a bounded operating region, where the prior LUT-network work
(NullaNet, LogicNets, PolyLUT) samples observed activations instead. Measured, it
takes a neuron from 627–2,918 product terms down to 31–54. I think that's our
strongest position and it's currently unprotected.

**Figures.**

I've redrawn the set — eleven sheets attached. Beyond cleaning up the routing,
three of the originals had errors worth flagging: in FIG. 3 the delay taps ran to
the pulse filter while the multiplexer output looped backwards into it, which
isn't a circuit; FIG. 5's restart edge had no decision node to originate from,
and its loop-back would have reset the annealing margin on every pass; and FIG. 1
showed no delay elements or class partition at all, so it didn't depict the
mechanism the claims recite.

The new sheets cover what was missing: the derivation of delay values from the
coupling graph, a timing diagram for a coupled pair under equal versus distinct
delays, the node circuit and its sizing rule, the dual-rail/C-element
alternative, and the don't-care synthesis. Reference numerals are unchanged so
the spec doesn't need renumbering.

Only two sheets carry measured values and both are labelled as such with
conditions stated. One sheet — FIG. 2, the perturbation-versus-margin curve —
asserts a monotone relationship we have *not* measured. It's drawn as a
relationship rather than as data, which is permissible, but I'd rather measure it
than assert it, and the harness can produce it.

**On the hazard question you raised.**

I built both mitigations. Inertial delay costs 64 gates on a 30,000-gate design
and does not fix the problem — fixed-point correctness goes from 68% to 75% at
N=32 and doesn't move at N=64. Dual-rail with Muller C-elements fixes it
completely, 100% at every size tested, at 2.03× the gates and roughly 4× the
latency. Two things fell out of building it: the C-elements do *not* replace the
colouring — the same dual-rail array with the partitioning removed stops
converging — and dual-rail is incompatible with don't-care minimisation, because
completion detection needs the on-set and off-set to partition the input space
while don't-cares exist precisely to avoid committing to one. Minimise both rails
independently and the completion detector deadlocks. The fix is De Morgan on the
true rail's cover, which is free in dual-rail.

**What I still need to check.**

There's a survey attributing to "Takeda et al." the design of asynchronous
transition modes with *random delays* to address the oscillation problem in
discrete-time Hopfield models. If that's real and dated to 1986, it's the closest
thing yet to the one element the four papers above leave standing, and I haven't
been able to get the source. Also outstanding: the 1986–87 analog Hopfield VLSI
(Graf & Jackel; Sivilotti & Mead; Moopenn & Thakoor) — arrays of amplifiers with
resistive feedback, each node on its own RC constant, converging with no periodic
reference, which is claim 1's preamble in 1987 silicon. And claim 1 of the nine
cited US patents, none of which I've been able to retrieve.

Happy to walk through any of this.

[name]

---

## Attachments to send

- `phase2/patent_figures/out/patent_figures_v2.pdf` — the eleven sheets
- optionally `phase2/paper/PRIOR_ART_FINDINGS_READ.md` — the per-reference detail
  with quotations

## Things deliberately not in the email

- The nine-patent claim-1 gap is mentioned but not dwelt on; it is counsel's job.
- No recommendation on whether to file, narrow, or abandon. That is his call and
  the attorney's, and offering one would overstep.
