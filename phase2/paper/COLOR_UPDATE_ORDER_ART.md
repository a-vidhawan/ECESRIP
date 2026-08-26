# "Colouring determines update order" in recurrent networks — the art

Bibliographic details below are transcribed from the reference list of Aadit et
al. 2022 (pp. 12–13 of the supplied PDF), so the author/title/venue/year fields
are **verified against a primary source**. The URLs are constructed from those
fields and are convenience links, not verified retrievals — the arXiv numbers are
the exception, since the reference list prints them.

## Why this list and not a search result

The closest art assembles it itself. Aadit et al. 2022 at p. 2:

> "The idea of block updating is commonly used for regular graphs. For example,
> **as first noted in Ref. [36]**, when the graph is bipartite (as in Restricted
> Boltzmann Machines or chessboard lattices), trivial colorings (with two colors,
> black and white or four colors in King's graphs) are possible and **this is
> often exploited in updating each color block in parallel [4, 19, 37–41]**."

> "**Compared to prior works on block updating [4, 19, 37–41]**, our contributions
> are twofold: First, we extend the block updating scheme such that it applies to
> regular *and* irregular graphs…"

So an examiner does not have to construct a §103 stack for the colouring
limitation. It is printed in the closest reference, framed as the prior art that
reference improves on.

---

## The origin

**[36] Geman & Geman (1984)** — the earliest, and Aadit's own "as first noted".
Colour-partitioned parallel updating of a recurrent stochastic network, forty
years old.

> S. Geman and D. Geman, "Stochastic relaxation, Gibbs distributions, and the
> Bayesian restoration of images," *IEEE Transactions on Pattern Analysis and
> Machine Intelligence*, PAMI-6(6):721–741, 1984.
> https://doi.org/10.1109/TPAMI.1984.4767596

## The algorithmic statement

**[34] Gonzalez, Low, Gretton & Guestrin (2011)** — the Chromatic Gibbs sampler,
already flagged HIGH in our review.

> *Proceedings of the Fourteenth International Conference on Artificial
> Intelligence and Statistics*, pages 324–332, JMLR W&CP, 2011.
> https://proceedings.mlr.press/v15/gonzalez11a.html

**[30] Koller & Friedman (2009)** — textbook treatment.

> D. Koller and N. Friedman, *Probabilistic Graphical Models: Principles and
> Techniques*, MIT Press, 2009.

**[35] Johnson, Saunderson & Willsky (2013)** — what happens when you *violate*
the ordering. Relevant to the annealing embodiment, not to claim 1.

> "Analyzing Hogwild parallel Gaussian Gibbs sampling," *Advances in Neural
> Information Processing Systems*, 26:2715–2723, 2013.

## Hardware implementations — the ones that matter most

**[4] Mansinghka, Jonas & Tenenbaum (2008)** — stochastic digital circuits for
probabilistic inference. Earliest hardware entry in Aadit's block-updating list.

> MIT Technical Report MITCSAIL-TR 2069, 2008.

**[19] Patel, Chen, Canoza & Salahuddin (2020)** — FPGA-accelerated restricted
Boltzmann machine for Ising optimisation. Bipartite ⇒ 2-colouring.

> arXiv:2008.04436 — https://arxiv.org/abs/2008.04436

**[20] Patel et al. (2020)** — logically synthesised, hardware-accelerated RBMs.
Not in the block-updating citation cluster but adjacent, and it is *logic
synthesis of a recurrent stochastic network*, so it also touches our second
independent claim.

> arXiv:2007.13489 — https://arxiv.org/abs/2007.13489

**[37] Ko, Chai, Rutenbar, Brooks & Wei (2019)** — "FlexGibbs", a reconfigurable
parallel Gibbs sampling accelerator for structured graphs. On the title alone
this is the closest hardware analogue to the colouring limitation after Aadit.

> *2019 IEEE 27th Annual International Symposium on Field-Programmable Custom
> Computing Machines (FCCM)*, pages 334–334, IEEE, 2019.

**[38] Fang, Feng, Tam, Yun, Moreno, Ramanujam & Jarrell (2014)** — parallel
tempering of the 3D Edwards–Anderson model with compact **asynchronous** multispin
coding on GPU. Note the word asynchronous; worth reading for what it means there.

> *Computer Physics Communications*, 185(10):2467–2478, 2014.

**[39] Yang, Chen, Roumpos, Colby & Anderson (2019)** — Ising model Monte Carlo
on TPU clusters.

> *Proceedings of the International Conference for High Performance Computing,
> Networking, Storage and Analysis (SC '19)*, pages 1–15, 2019.

**[40] Yoshimura, Hayashi, Okuyama & Yamaoka (2016)** — FPGA-based annealing
processor for the Ising model.

> *2016 Fourth International Symposium on Computing and Networking (CANDAR)*,
> pages 436–442, IEEE, 2016.

**[41] Yoshimura, Hayashi, Okuyama & Yamaoka (2017)** — the same, with resource
sharing.

> *International Journal of Networking and Computing*, 7(2):154–172, 2017.

## Also in that bibliography, relevant elsewhere

**[11] Wang & Roychowdhury (2019)** — "OIM: Oscillator-based Ising machines for
solving combinatorial optimisation problems," *International Conference on
Unconventional Computation and Natural Computation*, pages 232–256, Springer,
2019. The journal companion to the DAC paper you sent. Clockless, no colouring.

**[12] Ahmed, Chiu & Kim (2020)** — "A probabilistic self-annealing compute fabric
based on 560 hexagonally coupled ring oscillators," *2020 IEEE Symposium on VLSI
Circuits*. Ring oscillators, self-annealing — worth checking against the
annealing embodiment.

---

## What this list does and does not reach

Every entry is either software, or hardware driven by a clock. **None is
clockless.** The conjunction — colouring determines the update order *and* there
is no periodic timing reference — is still not found in anything read.

But the list is long, it starts in 1984, and it is printed in the closest
reference. The consequence for the draft is the one already acted on: the
colouring limitation cannot carry novelty by itself, and claim 25 should carry
the weight, because it recites something none of these can do — a delay element
that cancels a superseded transition. Every implementation above samples at a
clock edge, so a transition that appeared and disappeared between edges is never
seen and there is nothing to cancel.

## Still worth pulling

**[37] FlexGibbs** first. "Reconfigurable parallel Gibbs sampling accelerator for
structured graphs" is a two-page FCCM abstract, so it will be quick, and if it
partitions by colouring in reconfigurable hardware it belongs in the IDS
alongside Aadit rather than below it.

Then **[4] Mansinghka 2008**, as the earliest hardware entry.
