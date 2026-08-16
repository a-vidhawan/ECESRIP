# Meeting Prep — anticipated questions and the answers

Every number here is traceable; run `python3 audit_claims.py` to regenerate.
Where we do not know something, that is stated rather than papered over.

---

## The three things to lead with

1. **Even/odd was a special case.** It only avoids cycles on a bipartite coupling
   graph. Ours has χ=6, and parity leaves 44% of coupled pairs committing
   together. The general rule is that coupled neurons must differ in delay VALUE.
2. **Recall is now good, and it scales.** N=256 holds ≥90% recall at 19%
   corruption. Storage and recall hold to α=0.5, against the classical 0.138.
3. **Hazards look benign.** Tested at his request — 86 spurious commits out of
   123 still gives 98% recall. Probably no need for C-elements.

---

## His questions from the last message

### "Minimum vertex colouring could need more than 2 colours — does that sound right?"

Yes, and measured. N=16 max-prune network: 43 edges, 35.8% density, **χ=6**.
Parity leaves **19/43 = 44%** of coupled pairs sharing a delay; the hub neuron
(degree 11) collides with 6 of its 11 neighbours.

χ stays small as N grows — **6 at N=4096** — because the coupling graph is
sparse. So the schedule costs O(N) storage and O(χ) distinct delays, and χ does
not grow in any way that matters.

### "Do we still need differentiated delays per colour?"

Yes, and this is the sharpest result we have. The 2×2:

| | distinct delays | identical delays |
|---|---|---|
| proper colouring | **100%** settled | **0%** settled |
| no colouring (parity) | **0%** settled | — |

A *valid colouring with all delays equal* settles 0%. So the invariant is on
delay **values**, not colour labels — our own verifier had this bug and would
have passed the 0% schedule.

Surprise result: the values don't matter beyond being distinct. We expected
non-commensurate delays would be needed to avoid re-alignment. Measured: false —
powers of two settle best. 12 permutations of the same primes, sd = 0.00.

### "Are hazards a problem? How would we test it?"

**Tested. On this evidence, no.** (`hazard_analysis.py`)

Injected spurious commits — a commit latches the inverse of the computed value —
and swept the rate. N=256, M=32, starting at 10% corruption:

| glitch rate | glitches / commits | recall | settled |
|---|---|---|---|
| 0.0 | 0 / 35 | 98% | 100% |
| 0.2 | 9 / 45 | 98% | 100% |
| 0.7 | 86 / 123 | 98% | 100% |

Targeted at the highest-fan-in quarter of neurons (deepest SOP, where real
hazards concentrate): holds 86–100% to p=0.8.

**Why:** a glitched neuron re-evaluates, a correction gets scheduled, and the
basin pulls the state back. Settling never degrades, so no induced oscillation.

**Be honest about the caveats.** The model is conservative in one respect — a
latched wrong value is worse than a narrow pulse that may not be latched — and
optimistic in another: glitches are injected independently, whereas real hazards
correlate with specific input transitions. The definitive test is gate-level
simulation with annotated delays; we have the tooling (yosys + iverilog) and
have not run it.

*One trap to avoid:* at p=1.0 recall collapses to 0%. That is **not** a hazard
result — at p=1.0 a neuron always inverts, which is a stuck-at fault. Don't quote
it as one.

### "If hazards are problematic — Muller C-elements?"

Right family of answer, but worth being precise about the trade:

- **Buys:** with dual-rail plus completion detection, the timing assumption
  disappears rather than being managed.
- **Costs:** ~2× logic for dual-rail plus the C-elements and a handshake. Our
  area advantage is already marginal (1.52× on ASIC, 1.19× *worse* on FPGA), so
  this would erase it.
- **Does not replace the colouring.** A C-element makes a neuron wait for stable
  inputs; it does not stop two *coupled* neurons committing together. The two
  mechanisms compose, they don't substitute.
- **Tension worth raising:** hazard-free two-level synthesis requires retaining
  redundant consensus terms — exactly the ones our don't-care minimisation
  removes. Hazard-freedom and our area result pull against each other. And the
  classical theory mostly covers single-input-change, while our case has many
  neurons changing at once.

---

## Questions he is likely to ask next

### "What's the capacity?"

α = M/N up to **0.5** with all patterns stored and ≥95% recall (N=64 M=32; N=128
M=64). Classical Hopfield is 0.138. Sharp collapse past α≈0.6.

Caveat to volunteer: that came from switching the training rule, and the rule is
classical (Krauth–Mertens minover under a mask and symmetry constraint) — not our
invention.

### "How much corruption can it take?"

Depends on N, and improves with it:

| N | M | ≥90% recall out to |
|---|---|---|
| 64 | 32 | HD=3 (5% of bits) |
| 128 | 32 | HD=20 (16%) |
| 256 | 32 | **HD=48 (19%)** |

Bigger networks tolerate more corruption both absolutely and fractionally.

### "Is this better than just using a CAM?"

**At small M, no — and we built the baseline.** A nearest-match CAM at N=64, M=4:
2,858 gates vs our 7,020, and it recalls 100% at every Hamming distance while we
manage ~57%. It wins on both axes.

The verdict flips with the care radius (at h=2 we are 2.1× smaller) but the M
sweep is unambiguous: 4/4 patterns stored at M=4, 6/8 at M=8, 0/16 at M=16 —
we fail on *storage* before we fail on area.

Honest framing: this is a vehicle for the synthesis result, not a recommended
memory, unless the regime is small M and small guaranteed radius.

### "Does it survive process variation?"

Yes, and better than expected. 100% settling out to ±348% delay spread (3σ). And
variation *rescues* a degenerate schedule — 67% → 100% — because continuous
variation makes equal delays distinct with probability 1. Practical corollary:
silicon variation helps; the hazard is delays made equal **by construction**,
which is what an identical-buffer-chain layout would give.

### "Is any of this novel?"

Be straight about this, because he will find out otherwise:

- **Chromatic scheduling is textbook** — multicolour Gauss-Seidel; Gonzalez et
  al. 2011 built the Chromatic Gibbs sampler on the same argument. What survives
  is the hardware translation: colour classes must become distinct delay
  *values*, and a valid colouring can still fail.
- **The training rule is classical** (Krauth–Mertens minover), adapted to a
  masked symmetric matrix.
- **The don't-care synthesis is the strongest claim.** NullaNet/LogicNets use
  don't-cares from sampled activations; ours is *derivable* with closed-form size
  `M·Σ_{j≤h} C(d,j)`, polynomial where the table is exponential. And recurrence
  makes correctness non-trivial — a wrong off-region output can create a new
  fixed point.

### "Can we use it for NP problems?"

Don't oversell. The settling machinery transfers to Ising/max-cut and gives
convergence in a constant number of time slots regardless of size. But settling
reliably means reaching *a* local minimum. From a uniformly random start — what
an optimiser does — the network reaches a non-stored fixed point 90–95% of the
time. For a memory that's expected and irrelevant; for optimisation it is the
entire difficulty. **We have run zero optimisation instances.** Concrete next
step: map max-cut instances and benchmark against simulated annealing.

---

## What to admit before he asks

- **No silicon, no real PDK timing.** Area is yosys cell counts after
  technology-independent mapping.
- **RTL verification stops at N=256.** Above that is a simulator, validated at
  N=16 and N=256 but not beyond.
- **Don't-cares leave off-region behaviour unspecified** — 2% agreement with the
  exact network on uniformly random states. Fine for recall, not for adversarial
  input.
- **Random bipolar patterns only.** No correlated or real data, which would
  change basin geometry.
- **Three of our own conclusions were overturned by later measurements** (area
  estimate, CAM verdict, the Ω(M·N) argument) and two published claims were
  retracted outright. All recorded in `CLAIMS_AUDIT.md` — worth mentioning as
  evidence the process has teeth rather than hiding it.

---

## If he asks "what next"

In the order I would do them:

1. **Gate-level hazard simulation** — closes the one question he raised that we
   answered only indirectly.
2. **Max-cut instances** — decides the NP direction, which is what he cares about.
3. **Sweep the care radius h** — it is the main design knob and swings area 5.3×.
4. **Correlated/structured patterns** — everything so far is random bipolar.
