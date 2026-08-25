# Prior art — findings from reading the sources

Unlike `PRIOR_ART_REVIEW.md`, which worked from abstracts and background
knowledge, everything below is from the full text of the PDF. Page references
are to the supplied file.

Four references read: Aadit 2022 (sIM), Nikhar/Aadit 2024 (Nat. Commun.),
Rosin 2012 (EPL), and Wang/Wu/Roychowdhury (DAC 2019 LBR) — the last of which
is not on the IDS and should be.

---

## 1. Aadit et al. 2022 — "Massively parallel probabilistic computing with sparse Ising machines"

Supplied as a 25-page scanned preprint with no text layer; read as page images.
All quotations below are from p. 2, §II "Summary of Main Results".

### What it discloses, in its own words

> "This is achieved by using **multiple phase shifted clocks** controlling the
> activation of probabilistic bits (p-bits)."

> "This architecture can be considered to be a **low level hardware-level
> implementation of chromatic Gibbs sampling** [34] where large blocks of
> conditionally independent nodes are updated in parallel."

> "connected nodes need to be updated one after the other since **parallel
> updating leads to repeated oscillations** in the network state, preventing the
> network from converging"

> "the only requirement that the graphs are sparse enough to be **colored by a
> few colors (typically ≤ 4-8)**"

### Two quotations that damage the draft

**(a) The sizing rule is disclosed.**

> "For this sampling to be exact, **the MAC must finish its computation before
> the next color block is updated.**"

That is ¶[0047] — the delay design rule — in substance, published in 2022.

**I have to correct myself here.** When I filled the patent I flagged ¶[0047] as
new subject matter possibly supporting an independent claim. That was wrong. The
rule is stated in the closest art. What remains ours is the *measurement* of what
happens when it is violated, not the rule.

**(b) The annealing-by-timing-margin embodiment is largely anticipated.**

> "An unexpected finding however is even when **color blocks are updated before
> the MAC operation is completed**, the network is often able to find exact
> ground states in model optimization problems. This inexact Gibbs sampling
> approach is reminiscent of the Hogwild!-Gibbs algorithm [35] and we show how
> this **overclocking** strategy can lead to further advantages."

Deliberately violating the timing rule, and finding it *helps*, is the core idea
of FIGS. 2–4 of the figure set — timing margin as a control variable. Aadit
2022 discloses it, names it (overclocking), ties it to a known algorithm
(Hogwild!-Gibbs), and reports an advantage from it.

### What still distinguishes us

The timing reference. Their colour classes are activated by **phase-shifted
periodic clocks** — a clock generator and distribution network are present, and
the phases are open-loop. Ours are per-node inertial delays in the feedback path
with no periodic reference anywhere. That distinction is real, and it is narrow.

---

## 2. Nikhar, Kannan, Aadit, Chowdhury & Camsari 2024 — Nat. Commun. 15:8977

Full text available. Confirms and sharpens the same picture.

> "a master graph architecture that can multiplex different connectivity and
> **phase-shifted (colored) clocks** for a given p-bit"

> "Our p-computer employs **graph-colored³⁰ Gibbs sampling** to achieve massive
> parallelism by updating blocks of unconnected p-bits at the same time"

> "graph coloring their graph representation requires a maximum of **6 colors**.
> Since only one instance is selected at a time, the master graph needs only
> **6 phase-shifted clocks**."

Their block diagram contains an explicit **clock MUX** alongside the neighbour
MUX, tanh, comparator and PRNG.

**The single most useful fact in this paper:** the word **"delay" appears zero
times in it.** No delay elements, no delay lines, no propagation-delay
sequencing. Their entire timing mechanism is clock phase.

**The most dangerous fact:** they describe their own architecture as an
"**asynchronous p-computer**", and Fig. 1's caption reads "asynchronous dynamics
(**clockless**)". They mean the *physics* is clockless and their p-bits are not
globally synchronous — the circuit plainly has clocks — but an examiner quoting
the abstract and figure caption has "asynchronous" and "clockless" in a p-bit
Ising machine that uses graph colouring. We would be arguing against their
words, not their circuit.

---

## 3. Rosin, Rontani, Gauthier & Schöll 2012 — "Excitability in autonomous Boolean networks", EPL

High risk, but on a different axis than the review assumed.

**What it discloses:** a clockless recurrent Boolean network implemented with
asynchronous logic gates on an FPGA, in which each link carries a **programmable
delay line built from pairs of inverters**, τ_n ≈ 2n·τ_gate, and the network
dynamics are "controllable by the network's **link delay times**". 61 occurrences
of "delay"; one occurrence of "clock", and that one refers to a flip-flop input
inside a pulse generator, not a system clock.

That is, structurally, FIG. 3's delay element — an inverter-chain delay line with
a selectable tap — inside a clockless recurrent Boolean network, in 2012, on an
FPGA.

**What it does not disclose:** no Hopfield network, no threshold logic, no
weights, no graph colouring, no partition, and no convergence to a fixed point.
Zero occurrences of "Hopfield". The delays are used to *create and control*
oscillation and spike-synchronisation patterns — the opposite objective.

**Why it is still dangerous:** it supplies, in a single reference, "clockless
recurrent Boolean network on an FPGA with per-node programmable delay elements."
Combined with Aadit 2022 supplying "colour the coupling graph and update classes
in a staggered order to prevent oscillation", the combination reads on claim 1
without much strain. Both are in the same field and both address update timing
in recurrent networks, so a motivation to combine is easy to articulate.

---

## 4. Wang, Wu & Roychowdhury 2019 — DAC Late Breaking Results

**Not on the IDS. It should be.**

> "a novel Ising machine technology for solving combinatorial optimization
> problems using networks of **coupled self-sustaining oscillators** … several
> working hardware prototypes using CMOS electronic oscillators … Ising machines
> consisting of up to 240 spins with programmable couplings"

Oscillator-based Ising machines have no clock — the spins are oscillator phases
and the network settles by phase locking. This is further art against the
clockless element standing alone, from a third independent direction. It does
not touch the colouring.

---

## Where this leaves the claim elements

| element | status after reading |
|---|---|
| clockless recurrent threshold network | **not novel** — Rosin 2012, Sutton 2019, oscillator IMs, and 1986 analog VLSI all reach it |
| colour the coupling graph to order updates | **not novel** — Gonzalez 2011 as algorithm; Aadit 2022 expressly as *hardware* |
| node logic must settle before the next class evaluates | **not novel** — stated in Aadit 2022 |
| annealing by relaxing that timing margin | **substantially anticipated** — Aadit 2022 "overclocking" / inexact Gibbs |
| colour classes realised as per-node **inertial delay values in the feedback path, with no periodic timing reference** | **not found in any of the four.** Aadit uses clock phase; Rosin has delay lines but no colouring |
| the invariant being on delay **values** — a proper colouring with equal delays settles 0% | **not found anywhere** |
| operating-region don't-care synthesis | **not addressed by any of these four**, and claimed nowhere in the draft |

## Consequences for the draft

1. **Claim 1 must recite the delay-value relation.** It is presently in dependent
   claim 2. As drafted, claim 1 literally covers a proper colouring with all
   delays equal — the configuration measured settling 0% of the time. That is
   both unnecessary novelty exposure and a §112(a) problem.
2. **¶[0047] cannot be presented as new subject matter.** Aadit 2022 states the
   rule. Recast it as a measurement of the consequence of violating it.
3. **The annealing embodiment needs re-scoping or dropping.** Aadit 2022's
   overclocking result is the same idea with a published advantage.
4. **The don't-care synthesis should be claimed.** It is the element none of
   these four touch, and the review reached the same conclusion independently.
5. **Add Wang/Wu/Roychowdhury 2019 to the IDS.**

## Still not read

Takeda & Goodman 1986; Graf 1986; Sivilotti/Mead 1986; Moopenn 1987; claim 1 of
the nine cited US patents. The Takeda question — whether it discloses
deliberately differentiated per-node delays to break simultaneous update — is
still the one that could do the most damage, because that is the element the four
papers above leave standing.
