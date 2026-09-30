# Draft email to Prof. Lin — prior art conclusion and next direction

Two placeholders to fill before sending, both marked `[...]`:
the two architecture ideas, and whether you want to name a meeting time.

---

**Subject:** Update on the patent prior art — and a direction I'd like to pick up

Dear Prof. Lin,

Apologies for the long silence. I had to fly back to India earlier than planned
for a family matter, which pulled me away from the project for longer than I
expected. I'm back up to speed now.

Before I left I spent a stretch doing a proper prior-art search on the clockless
scheduling work, and I think the honest conclusion is that the scheduling idea
is not novel enough to be worth patenting. I wanted to lay out why, since it
took a while to become clear.

The algorithmic result — colour the coupling graph so that no two coupled units
update together — traces back at least to Geman & Geman (1984), and Gonzalez et
al. (AISTATS 2011) built the Chromatic Gibbs sampler on exactly the argument we
were using. I had expected that, and the position I'd been working from was that
the *hardware* translation was still ours.

That is the part that did not hold. Aadit et al. (Nature Electronics, 2022)
describe their own FPGA Ising machine as "a low level hardware-level
implementation of chromatic Gibbs sampling," and their bibliography collects a
further cluster of colour-block hardware — an FPGA parallel Gibbs accelerator
(FlexGibbs, FCCM 2019), FPGA annealing processors for the Ising model
(Yoshimura et al., 2016 and 2017), and an FPGA restricted Boltzmann machine
(Patel et al., 2020) — which they explicitly frame as the prior work they are
improving on.

Two further passages in that same paper bear directly on what we had drafted.
They state that "the MAC must finish its computation before the next color block
is updated," which is the delay sizing rule I had described to you as a finding
of ours. And they deliberately relax that timing constraint, call it
overclocking, connect it to the Hogwild!-Gibbs algorithm, and report that it
*improves* time-to-solution — which is essentially the annealing-by-timing-margin
idea from our figures, already published with a claimed advantage.

Two things did survive the search, for what it's worth. I could not find the
specific combination of colour-partitioned ordering *and* no periodic timing
reference anywhere. And I could not find anything on what turned out to be the
sharpest result of the summer: the delay element has to be inertial — it has to
cancel a pending transition when its cause goes away. Measured on identical
networks, partitions and delay values, inertial delay elements converge from 100%
of initial states where transport delay elements manage 1–16%. A phase-shifted
clock structurally cannot do this, because a clocked node samples at an edge and
never sees a transition that came and went between edges. That is a real
distinction, but I don't think it is enough on its own to carry a filing, and it
would be a narrow claim to defend.

I've left everything in a state where it can be picked up if you disagree with
that read: the draft is revised against what we measured, the figure set is
redrawn, and the prior-art findings are written up with the source passages
quoted rather than paraphrased. Happy to send any of it over.

Where I would really like to go next is the direction you raised when we last
met, and in particular the two ideas you had that sat closer to the architecture
side — [ONE LINE NAMING THE TWO IDEAS, e.g. "the X approach and the Y
question"]. Those are much closer to what I want to be working on, and after
spending a summer on the timing and synthesis end of this I think I'd bring
something useful to them rather than starting cold. I'd be glad to put together
a short plan for either one if that would help you judge whether it's a sensible
fit.

Would you have time to meet in the next couple of weeks? [OPTIONAL: name two or
three windows that work for you.]

Thank you for your patience with the gap, and for the time you put into this
over the summer — the prior-art exercise was genuinely the most instructive part
of it.

Best regards,
Aarav

---

## Notes on the draft

**On the two architecture ideas.** I don't have those in my notes from this
project, so I left a placeholder rather than guessing — naming them wrongly would
undercut the whole paragraph. If you can't recall the specifics either, it is
perfectly fine to write "the two directions you mentioned that were closer to
architecture — I'd be glad to have you refresh me on the details." Advisors
expect that after a gap and it reads as interest, not inattention.

**Why the negative conclusion is stated early and at length.** Lin will find
Aadit himself in about ten minutes, and coming to him with the finding rather
than being shown it is the stronger position. It also reads as someone who did
the work properly.

**Why the two surviving results are included.** Without them the email is purely
"I found we can't patent this", which undersells a summer. The inertial result is
genuinely good and is stated with the number attached.

**What is deliberately absent:** no recommendation on whether to abandon the
filing. It is his call and the attorney's. The email gives him the evidence and
an offer of the materials.

**Tone check on the opening.** One sentence on the family matter, no detail, no
over-apologising. That is the right amount.
