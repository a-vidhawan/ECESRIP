# LinkedIn / portfolio text

Copy-paste ready. Three places this goes, in order of how much they matter.

---

## 1. Experience entry — this is the one that counts

**Undergraduate Researcher**
University of California San Diego · Summer Research Internship Program (SRIP)
Jun 2026 – Sep 2026 · San Diego, CA

Hardware for recurrent neural networks, advised by Prof. Bill Lin.

Built a compiler that turns a trained Hopfield associative memory into
synthesizable SystemVerilog — each neuron minimized to two-level Boolean logic
via Berkeley Espresso, with update order set by a graph coloring of the coupling
matrix rather than a clock. Verified end-to-end at N=256 neurons and 12,357
product terms, recalling the correct stored pattern on 240 of 240 test vectors
in RTL simulation.

Cut per-neuron logic from 627–2,918 product terms to 31–54 by specifying each
neuron only over a bounded operating region and leaving the rest as don't-cares
— a care set that is polynomial in fan-in where the full truth table is
exponential, making fan-in 32 tractable where the complete 4.3×10⁹-row table
cannot be enumerated at all.

Raised storage capacity from the classical α=0.138 to α=0.5 at ≥95% recall using
margin-based retraining under a sparsity mask.

Tools: SystemVerilog, Python, Yosys, Icarus Verilog, Berkeley Espresso, Git.

---

## 2. Featured section — add both

- **Repository** — `github.com/a-vidhawan/ECESRIP`
  Title it: *LUT-HNN — a Hopfield network compiled to clockless logic*
- **Project report (PDF)** — upload `REPORT.pdf` directly
  Title it: *Compiling a Hopfield Network into Clockless Logic — project report*

The Featured section is what separates "claims to have done research" from
"did research." It takes two minutes and it is worth more than any wording
change above.

---

## 3. A post — optional, and genuinely optional

Only worth doing if you want the reach. The Experience entry plus Featured link
does the job without it.

> Spent the summer on a question that sounds simple: can you build a Hopfield
> associative memory with no multipliers and no clock?
>
> No multipliers, because each neuron's update is just a Boolean function of its
> neighbors — so it can be compiled into two-level logic instead of a
> multiply-accumulate. The obstacle is that a neuron with 32 inputs has a
> 4.3-billion-row truth table, which you cannot even write down.
>
> The way around it: an associative memory doesn't need to be correct
> everywhere, only on the states it actually visits. Specify each neuron over a
> bounded region around the stored patterns, leave everything else as a
> don't-care, and the specification drops from 65,536 rows to 2,768 at fan-in 16
> — and from 627–2,918 product terms down to 31–54 after minimization.
>
> No clock, because the network settles rather than computes. The catch is that
> if two connected neurons update at the same instant, each acts on the other's
> stale value and the network oscillates instead of converging — measured
> exhaustively, 60.2% of all states do exactly that under synchronous updating.
> Coloring the connection graph and giving each color class a different
> propagation delay prevents it.
>
> Built the whole pipeline — trained weights in, synthesizable SystemVerilog out
> — and verified it at 256 neurons across 240 test vectors.
>
> Code and a short write-up: github.com/a-vidhawan/ECESRIP
>
> Thanks to Prof. Bill Lin for the advising.

Why this structure: it opens with a question rather than a credential, explains
one real obstacle and one real solution, and the numbers are specific enough
that a hardware person can tell it's real. It never uses "novel," "pioneering,"
or "breakthrough."

---

## Words to never use about this work

**novel · pioneering · breakthrough · first-ever · state-of-the-art ·
revolutionary · cutting-edge**

Every one of them is checkable and at least one person who reads this will
check. The colored-scheduling idea traces to 1984 and exists in FPGA hardware
published in 2022. Claiming novelty is the single fastest way to turn a solid
project into an embarrassing one.

**Also never:** "though it wasn't published," "unfortunately," "we weren't able
to." Nobody asked. Raising it creates a frame that otherwise doesn't exist.

---

## If someone asks "did anything come of it?"

The honest answer is also the strong one:

> "The hardware works and it's all on GitHub. What I spent the back half of the
> summer on was the prior-art search, and the conclusion was that the scheduling
> idea wasn't as new as we thought — it traces back to parallel Gibbs sampling
> in the 80s, and there's FPGA hardware doing colored-block updating published
> in 2022. So I wrote that up honestly rather than pushing it further. The
> synthesis result is the part I'd still defend."

This answer is better than a publication for the kind of group you want to join.
It says you can evaluate your own work, you read primary sources, and you don't
oversell. Most undergrads cannot do any of the three.

Do not lead with this on a profile. It's an answer, not a headline.

---

## One thing to reconsider

The report currently has the inertial-delay result and the negative-results
section removed. That's a defensible choice for a general audience — it's
shorter and nothing in it is wrong.

But for the research group specifically, those were the two sections doing the
most work. The inertial finding was the one result not found anywhere in the
prior art, and the negatives section — two retractions, an area estimate wrong
by 2× in the wrong direction, a baseline that beats the design — is what makes
a reader trust the rest. A five-page report where everything worked is a weaker
signal to a research audience than a seven-page one where two things didn't.

Worth keeping both versions: the short one for general use, the full one for
the group you're actually applying to.
