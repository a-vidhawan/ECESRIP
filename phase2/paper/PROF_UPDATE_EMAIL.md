# Draft — update email to professor

_Attach: `fig2_scheduling_rule.png`, `fig8_capacity_frontier.png`, and
optionally `fig7_pvt.png`. Edit freely — figure references assume all three._

---

**Subject:** Async HNN update — cycle-free settling generalised, and capacity/recall results

Hi Professor [NAME],

Wanted to give you an update since we last spoke about the even/odd scheme and
avoiding cycles. Quite a lot has moved, and the short version is that even/odd
turned out to be a special case of a more general rule, and recall is now much
better than what we had.

**On cycles.** When we looked at why even/odd was still leaving oscillations, we
extracted the actual coupling graph of the network — which neurons read which —
and found that assigning delays by index parity leaves **44% of coupled neuron
pairs updating at the same instant**. The worst case was the highest-degree
neuron, which shared its delay with six of its eleven neighbours. Even/odd only
avoids cycles when the coupling graph happens to be bipartite, and ours isn't.

The general version is: **two neurons that are coupled must not commit at the
same time**, which is a graph-colouring problem on the coupling graph. The
energy argument is that a simultaneous update of two coupled neurons contributes
a cross term W_ij·Δs_i·Δs_j that can break the monotonic energy decrease; if
they're uncoupled that term is zero, so updating them together is exactly
equivalent to updating them in sequence. (Figure 1 attached.)

We ran this as a proper 2×2 to be sure — colouring with distinct delays settles
100% of the hardest states, while both controls (a valid colouring with equal
delays, and distinct delays without colouring) settle 0%. One thing that
surprised us: the delay *values* don't matter at all beyond being distinct.
We'd assumed non-commensurate delays would be needed to avoid re-alignment;
that turned out to be false. The number of distinct delays needed stays around
6 even at N=4096, because sparse graphs colour cheaply.

**On recall**, which I know is the thing you care most about. After replacing
the training rule (the old one solved a least-squares fit per neuron and then
symmetrised, which destroys the fit — the new one maintains symmetry throughout
a margin-maximising solve), we now get:

| N | patterns M | recall from HD≤3 corruption |
|---|---|---|
| 64 | 32 | 95% |
| 128 | 64 | 98% |
| 256 | 64 | 100% |

That's α = M/N = 0.5 with essentially perfect storage and recall, against the
classical Hopfield capacity of ≈0.138. Beyond α≈0.6 it collapses within a single
step — the cliff is very sharp (Figure 2). We also verified the whole flow end
to end in RTL at N=256 (generated SystemVerilog, simulated in iverilog), and it
matched our model on 240/240 test inputs, so this isn't only a Python result.

**Honest caveats.** Two worth flagging. First, the high-capacity points need
near-full connectivity, and our lookup-table implementation gets expensive as
fan-in grows — so the *network's* capacity and the *implementable* capacity are
different limits and we shouldn't quote them interchangeably. Second, we built a
content-addressable memory as a baseline, and at small pattern counts it is both
smaller and functionally better than our design. Our approach only wins in a
fairly narrow regime, and I'd rather we know exactly where that boundary is than
overstate it.

**On NP solvers.** I want to be careful here. What we have is machinery that
makes an asynchronous network settle reliably and quickly — which is genuinely
relevant, since Ising/max-cut solvers need exactly that, and our scheduling
gives convergence with a constant number of time slots regardless of network
size. But settling reliably means reaching *a* local minimum, and our own data
shows ~76% of random initial states land on spurious attractors rather than
stored patterns. For associative memory that's a failure mode; for optimisation
it's the central difficulty. We haven't run a single optimisation instance yet,
so I don't want to claim anything there. If it's a direction you'd like to
pursue, the concrete next step would be mapping some max-cut instances onto this
and comparing solution quality against simulated annealing — the settling
infrastructure would carry over essentially unchanged.

Happy to walk through any of this whenever suits you.

Best,
[NAME]
