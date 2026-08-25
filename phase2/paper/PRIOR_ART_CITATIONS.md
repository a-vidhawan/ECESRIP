# Prior art — full citations for retrieval

Every entry is marked:

- **[V]** verified against a source in this session
- **[K]** from background knowledge, not verified — check before relying on it
- **[?]** I could not identify the item confidently. Do not cite as written.

Numbers 1–19 follow the IDS numbering. Items G1–G8 are the gap the review
identified: 1985–98 analog and asynchronous neural VLSI, which is where §102 art
for a clockless recurrent threshold network actually lives.

---

## TIER A — pull these first

These are the ones where an examiner could build a rejection.

**G4. Takeda & Goodman (1986)** — highest priority. A survey attributes to
"Takeda et al." the design of *direct and differential asynchronous transition
modes with random delays to address the oscillation problem of discrete-time
Hopfield models*. If that is this paper, it is on point for the delay-value
limitation and potentially §102.

> M. Takeda and J. W. Goodman, "Neural networks for computation: number
> representations and programming complexity," *Applied Optics* **25**(18),
> 3033–3046 (1986). **[V]** title/venue/pages
> https://opg.optica.org/ao/abstract.cfm?uri=ao-25-18-3033

**Caveat [?]:** I could not confirm that the transition-mode/random-delay content
is in *this* paper. Its abstract is about number representation and programming
complexity. The attribution may belong to a different Takeda paper. When you
pull it, search the PDF for "asynchronous", "transition mode", "random delay",
and "oscillation". If it is not there, tell me and I will chase the survey that
made the attribution.

**G5. Related, same question, same era [?]** — appeared twice in searching and is
squarely about update order:

> "Synchronous vs asynchronous behavior of Hopfield's CAM neural net,"
> *Applied Optics* **26**(22), 4808 (1987).
> https://opg.optica.org/ao/abstract.cfm?uri=ao-26-22-4808
> **Authors not confirmed** — the listing page will have them.

**1. Aadit et al. 2022** — the draft's own "closest art."

> N. A. Aadit, A. Grimaldi, M. Carpentieri, L. Theogarajan, J. M. Martinis,
> G. Finocchio, K. Y. Camsari, "Massively parallel probabilistic computing with
> sparse Ising machines," *Nature Electronics* **5**, 460–468 (2022). **[K]**
> arXiv:2110.02481 — https://arxiv.org/abs/2110.02481

Pull the **Methods** section. The distinction our draft rests on is that their
colour groups are driven by *phase-shifted periodic clocks*. I have never read
that sentence in the source — the egress proxy here blocks nature.com and arXiv —
and the entire clocked/clockless distinction depends on it being accurate.

**11. Gonzalez et al. 2011** — flagged HIGH.

> J. Gonzalez, Y. Low, A. Gretton, C. Guestrin, "Parallel Gibbs Sampling: From
> Colored Fields to Thin Junction Trees," *AISTATS 2011*, PMLR **15**, 324–332. **[K]**
> https://proceedings.mlr.press/v15/gonzalez11a.html

**19. Nowick & Dill; Unger** — flagged HIGH.

> S. M. Nowick and D. L. Dill, "Exact two-level minimization of hazard-free logic
> with multiple-input changes," *IEEE Trans. Computer-Aided Design* **14**(8),
> 986–997 (1995). **[K]**
>
> S. H. Unger, *Asynchronous Sequential Switching Circuits*, Wiley-Interscience
> (1969). **[K]** — book, chapters on hazards

**8. Kosko 1988** — flagged HIGH.

> B. Kosko, "Bidirectional associative memories," *IEEE Trans. Systems, Man, and
> Cybernetics* **18**(1), 49–60 (1988). **[K]**

**18. The LUT-network family** — flagged HIGH.

> M. Nazemi, G. Pasandi, M. Pedram, "NullaNet: Training deep neural networks for
> reduced-memory-access inference," arXiv:1807.08716 **[K]**
>
> Y. Umuroglu, Y. Akhauri, N. J. Fraser, M. Blott, "LogicNets: Co-designed neural
> networks and circuits for extreme-throughput applications," *FPL 2020* **[K]**
>
> PolyLUT — arXiv:2309.02334 **[K]**
> NeuraLUT-Assemble — arXiv:2504.00592 **[K]**
> SparseLUT — arXiv:2503.12829 **[K]**

**6. Rosin et al.** — flagged HIGH.

> arXiv:1208.6181. The IDS gives the title as "Excitability in autonomous Boolean
> networks." **[?]** I believe the authors are D. P. Rosin, D. Rontani,
> D. J. Gauthier and E. Schöll, and that this appeared in *EPL* **100**, 30003
> (2012) — but the same group has a closely-related *Chaos* **23**, 025102 (2013)
> paper on autonomous Boolean networks, and I may be conflating them. Check the
> arXiv listing, which is authoritative and reachable from your machine.

---

## TIER B — the 1985–98 VLSI gap

Analog Hopfield networks in silicon, each node on its own RC constant, converging
with no periodic reference. That is claim 1's preamble plus the clockless
element, in 1986–87 hardware.

**G1.** H. P. Graf, L. D. Jackel, R. E. Howard, B. Straughn, J. S. Denker,
W. Hubbard, D. M. Tennant, D. Schwartz, "VLSI implementation of a neural network
memory with several hundreds of neurons," *AIP Conference Proceedings* **151**,
182–187 (1986). **[V]**
https://pubs.aip.org/aip/acp/article-abstract/151/1/182/755660

**G2.** M. A. Sivilotti, M. R. Emerling, C. A. Mead, "VLSI architectures for
implementation of neural networks," *AIP Conference Proceedings* **151**, 408–413
(1986). **[V]** — Snowbird, UT, April 1986, ed. J. S. Denker.
https://authors.library.caltech.edu/records/5ghjd-stc46

**G3.** A. Moopenn, J. Lambe, A. P. Thakoor, "Electronic implementation of
associative memory based on neural network models," *IEEE Trans. Systems, Man,
and Cybernetics* **SMC-17**(2), 325–331 (1987). **[V]** title/venue/year;
**[K]** page numbers. https://ieeexplore.ieee.org/document/4309044/
32-neuron electronic network, 1024-element programmable binary connection matrix.

**G6.** H. P. Graf, L. D. Jackel, "Analog electronic neural network circuits,"
*IEEE Circuits and Devices Magazine* **5**(4), 44–49 (1989). **[K]**

**G7.** J. J. Hopfield, D. W. Tank, "'Neural' computation of decisions in
optimization problems," *Biological Cybernetics* **52**, 141–152 (1985). **[K]**

**G8.** M. Verleysen, P. G. A. Jespers, "An analog VLSI implementation of
Hopfield's neural network," *IEEE Micro* **9**(6), 46–55 (1989). **[K]**

---

## TIER C — the rest of the IDS

**2.** N. A. Aadit et al., "All-to-all reconfigurability with sparse and
higher-order Ising machines," *Nature Communications* (2024). **[K]** — volume
and article number not confirmed.

**3.** B. Sutton, R. Faria, L. A. Ghantasala, R. Jaiswal, K. Y. Camsari,
S. Datta, "Autonomous probabilistic coprocessing with petaflips per second,"
*IEEE Access* **8**, 157238–157252 (2020); arXiv:1907.09664. **[K]**

**4.** US Patent **11,966,716** (Hitachi).
https://patents.google.com/patent/US11966716

**5.** Intel: US **11,817,859**; **11,716,083**; **11,716,084**; **11,716,085**;
**11,716,086**; **11,658,664**; **11,652,482**; **11,652,487**.
`https://patents.google.com/patent/US<number>` for each.

> **Outstanding:** claim 1 of none of these nine patents was retrieved. For a
> freedom-to-operate opinion the claims are what matter, not the abstracts, so
> these need pulling on an unrestricted network before they go into an IDS.

**7.** J. J. Hopfield, "Neural networks and physical systems with emergent
collective computational abilities," *PNAS* **79**(8), 2554–2558 (1982). **[K]**

**9.** E. Goles, J. Olivos, "Comportement périodique des fonctions à seuil
binaires et applications," *Discrete Applied Mathematics* **3**, 93–105 (1981).
**[K]** Also E. Goles, S. Martínez, *Neural and Automata Networks*, Kluwer (1990).

**10.** P. Orponen, "Computing with truly asynchronous threshold logic networks,"
*Theoretical Computer Science* **174**(1–2), 123–136 (1997). **[K]**

**12.** Multicolour Gauss–Seidel. Textbook; cite whichever counsel prefers:
> L. M. Adams, H. F. Jordan, "Is SOR color-blind?", *SIAM J. Sci. Stat. Comput.*
> **7**(2), 490–506 (1986). **[K]**
> Y. Saad, *Iterative Methods for Sparse Linear Systems*, 2nd ed., SIAM (2003),
> §12.4. **[K]**

**13.** Z. Fahimi, M. R. Mahmoodi, H. Nili, V. Polishchuk, D. B. Strukov,
"Combinatorial optimization by weight annealing in memristive Hopfield networks,"
*Scientific Reports* **11**, 16383 (2021). **[V]** exists; **[K]** article number.
https://www.nature.com/articles/s41598-020-78944-5

**14.** "Noise tailoring, noise annealing and external noise injection strategies
in memristive Hopfield neural networks," *APL Machine Learning* (2024). **[?]**
Authors not confirmed — I believe a Budapest group (Molnár, Rakyta and
colleagues) but do not cite that without checking.

**15.** F. Cai, S. Kumar, T. Van Vaerenbergh, et al., "Power-efficient
combinatorial optimization using intrinsic noise in memristor Hopfield neural
networks," *Nature Electronics* **3**, 409–418 (2020). **[K]**

**16.** L. Chen, K. Aihara, "Chaotic simulated annealing by a neural network model
with transient chaos," *Neural Networks* **8**(6), 915–930 (1995). **[K]**
The companion the IDS calls "On chaotic simulated annealing" is an *IEEE Trans.
Neural Networks* comment/paper in the late 1990s — **[?]** I am not confident of
the volume, issue or year.

**17.** A. Blake, A. Zisserman, *Visual Reconstruction*, MIT Press (1987). **[K]**
K. Rose, "Deterministic annealing for clustering, compression, classification,
regression, and related optimization problems," *Proc. IEEE* **86**(11),
2210–2239 (1998). **[K]**
E. Hazan, K. Y. Levy, S. Shalev-Shwartz, "On graduated optimization for
stochastic non-convex problems," *ICML 2016*; arXiv:1503.03712. **[K]**

---

## TIER D — the rest of the review's gap list

Not yet searched. Full citations so counsel can pull them without a second
identification pass. All **[K]** unless marked otherwise.

**Cellular neural networks** — recurrent threshold arrays with local coupling
that settle without a clock:
> L. O. Chua, L. Yang, "Cellular neural networks: Theory," *IEEE Trans. Circuits
> and Systems* **35**(10), 1257–1272 (1988); and "Cellular neural networks:
> Applications," same issue, 1273–1290.

**Partitioned cellular automata** — "partition the nodes so a block updates with
no intra-block interaction, then alternate partitions" is claim 1's partition
concept in 1980s CA hardware:
> N. Margolus, "Physics-like models of computation," *Physica D* **10**, 81–95 (1984).
> T. Toffoli, N. Margolus, *Cellular Automata Machines: A New Environment for
> Modeling*, MIT Press (1987).

**Boltzmann-machine analog VLSI with staggered/randomised node timing:**
> J. Alspector, R. B. Allen, "A neuromorphic VLSI learning system," in
> *Advanced Research in VLSI* (1987), 313–349.
> J. Alspector, B. Gupta, R. B. Allen, "Performance of a stochastic learning
> microchip," *NIPS 1988*.
> Also sweep **Alspector / Bellcore** as inventor and assignee — the patents
> matter more than the papers here.

**Wavefront arrays** — ordering enforced by data arrival rather than a clock:
> S. Y. Kung, K. S. Arun, R. J. Gal-Ezer, D. V. Bhaskar Rao, "Wavefront array
> processor: language, architecture, and applications," *IEEE Trans. Computers*
> **C-31**(11), 1054–1066 (1982).
> S. Y. Kung, *VLSI Array Processors*, Prentice Hall (1988).

**Commercial annealers — enforcing a valid update order across simultaneously
evaluated spins:**
> M. Aramon, G. Rosenberg, E. Valiante, T. Miyazawa, H. Tamura, H. G. Katzgraber,
> "Physics-inspired optimization for quadratic unconstrained problems using a
> digital annealer," *Frontiers in Physics* **7**, 48 (2019). — Fujitsu
> H. Goto, K. Tatsumura, A. R. Dixon, "Combinatorial optimization by simulating
> adiabatic bifurcations in nonlinear Hamiltonian systems," *Science Advances*
> **5**, eaav2372 (2019). — Toshiba SBM
> Plus the Fujitsu, Toshiba and D-Wave **patent families** on control sequencing,
> which is where the risk actually is.

**Neuromorphic, for the "clockless / event-driven update ordering" language:**
> P. A. Merolla et al., "A million spiking-neuron integrated circuit with a
> scalable communication network and interface," *Science* **345**, 668–673
> (2014). — IBM TrueNorth
> M. Davies et al., "Loihi: A neuromorphic manycore processor with on-chip
> learning," *IEEE Micro* **38**(1), 82–99 (2018). — Intel
> S. B. Furber, F. Galluppi, S. Temple, L. A. Plana, "The SpiNNaker project,"
> *Proc. IEEE* **102**(5), 652–665 (2014).

**Highest-value patent sweep, per the review:** continuations and family members
of **Aadit / Camsari (UCSB)** and **Datta (Purdue)**. If a US application claims
graph-coloured p-bit updating, that is the single reference that matters most and
it is on no list we have. Sweep by inventor and by assignee, not by keyword.

---

## What to send me

Priority order, if you are downloading by hand:

1. **G4 Takeda & Goodman 1986** — decides whether claim 2 has a §102 problem
2. **G1 Graf 1986** and **G2 Sivilotti/Mead 1986** — decide whether claim 1's
   preamble plus the clockless element is 1986 art
3. **Aadit 2022 Methods** — the sentence the whole clocked/clockless distinction
   rests on
4. **G3 Moopenn 1987**
5. Claim 1 of the nine US patents

I have not read any of these in full. Everything I have said about their contents
is either from an abstract or from background knowledge, and is marked as such
above.
