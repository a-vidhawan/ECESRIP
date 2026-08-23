# Prior-Art / Freedom-to-Operate Review

**Subject:** US application draft *"Self-Timed Recurrent Threshold-Logic Network with Clockless
Sequencing of Graph-Colored Node Partitions"* (Lin, Vidhawan), claims 1–24 as filled in
`patent_final.docx`.

**Reviewer posture:** adversarial. Assume a skeptical examiner with the full Camsari/Datta p-bit
corpus, the async-VLSI corpus, and the Boolean-automata-networks corpus in front of them.

---

## 0. What I could and could not verify — read this before trusting any row

This is the most important methodological caveat in the document.

**Every scholarly and patent host is blocked by this container's egress policy.** Confirmed by the
proxy's own failure log:

```
patents.google.com  ppubs.uspto.gov  api.patentsview.org  worldwide.espacenet.com
patentscope.wipo.int  register.epo.org  www.lens.org  arxiv.org  export.arxiv.org
www.nature.com  scholar.google.com  www.semanticscholar.org  api.semanticscholar.org
www.researchgate.net  openalex.org  api.openalex.org  freepatentsonline.com  patents.justia.com
```

`WebFetch` failed on **every** host attempted, including `en.wikipedia.org` and
`www.anthropic.com` — i.e. WebFetch is globally unavailable in this session, not selectively
blocked. Direct `curl` through the proxy returns 403 CONNECT (policy denial) for all of the above.

**Consequence: I read zero primary sources.** No row in the table below may be graded "(i) read the
source." The best available grade is **(ii) search-result summary** — the WebSearch tool's own
rendering of pages it can reach, which is a secondary source of unknown fidelity — or **(iii)
background knowledge only**.

**I did not retrieve claim 1 of any US patent on the list.** The specific instruction to pull claim 1
of items 4 and 5 could not be executed. Counsel must pull those documents from PatFT/Google Patents
on an unrestricted network before relying on anything in the "US patents" rows.

Hosts that worked: **WebSearch only.** Hosts that did not: all of the above, plus every host tried
via WebFetch.

---

## 1. What the draft actually claims (so the table has a target)

Independent claims:

- **Claim 1** (apparatus): threshold-logic node circuits + recurrent interconnect with a cycle +
  partition into update classes that are independent sets + *"sequencing circuitry configured to
  enforce, **in the absence of any clock signal**, an update ordering ... conditioned on signal
  propagation and settlement rather than on any periodic timing reference."*
- **Claim 14** (method of operating): the same, functionally.
- **Claim 18** (method of producing): sparsify → retrain on the support → proper vertex colour →
  assign clockless sequencing → synthesize per-node threshold logic → emit a circuit definition
  dataset.

Notable dependents: 2 (delay differentiation, class-2 delay > class-1 settling time), 3
(post-manufacture calibratable programmable delays), 4/5 (completion detection + handshake, Muller
C-element), 6 (convergence detection by a no-change pass), 7/8 (two classes / bipartite by duplicate
nodes with agreement-enforcing weight), 9 (binary-ternary weights + popcount), 11 (adder+comparator
or majority-gate network), 12 (hazards allowed to propagate as stochastic perturbations), 13 (CAM /
associative memory), 21 (enable-gating ⇒ single-input-change ⇒ SIC-hazard-free logic), 22 (inertial
delay element doubling as sequencer and hazard filter, rejection window ≥ disturbance interval), 23
(state-holding phase element), 24 (matched delay line completion).

**Two structural observations before the table, both of which matter more than any single reference:**

1. **The don't-care / bounded-operating-region claim family is not in the draft.** The brief for this
   review describes a "secondary claim family on synthesising each neuron's update function as a
   two-level logic function minimised using don't-cares derived from a bounded operating region."
   No claim in the filled draft (1–24) recites don't-cares, a care set, a Hamming radius `h`, a
   bounded operating region, or two-level/SOP minimisation. Claim 18 says only "synthesizing ...
   combinational logic implementing a Boolean threshold function." Our own `MEETING_PREP.md` calls
   the don't-care synthesis **"the strongest claim"** we have. It is currently claimed nowhere. This
   is the single largest defect I found, and it is not a prior-art defect — it is a drafting defect.

2. **The claims do not recite the measured invariant.** `CLAIMS_AUDIT.md` C3 and `MEETING_PREP.md`
   are unambiguous: a *valid proper colouring with all delay values equal settles 0% of the time.*
   Colour labels are not the invariant; **distinct delay values are**. Claim 1 recites the colouring
   and a functional result ("ordering ... conditioned on signal propagation and settlement") but
   contains **no delay-value limitation at all**. Claim 1 therefore literally reads on an embodiment
   our own data shows is inoperative. That is simultaneously (a) a §112(a) enablement-scope
   exposure, (b) a §112(b) indefiniteness exposure on "configured to enforce," since the structure
   that actually enforces is the delay-value assignment, and (c) an unnecessary novelty exposure,
   because the narrowest, best-supported, most distinguishing feature we own has been demoted to
   dependent claim 2. Fix this before filing, not after.

---

## 2. Findings table

Risk column = risk of encroachment on the draft as currently written (anticipation under §102 or a
credible §103 combination), not risk of infringement by us.

| # | Reference | What it actually discloses | Which claim element it touches | Risk | Distinguishing argument available to us | Confidence |
|---|---|---|---|---|---|---|
| 1 | Aadit et al., *Massively parallel probabilistic computing with sparse Ising machines*, Nat. Electron. 5:460 (2022); arXiv:2110.02481 | A 5,000 p-bit FPGA Ising machine using **graph-coloured (Brélaz) Gibbs sampling**: blocks of unconnected p-bits are updated simultaneously; sparse instances need **at most 6 colours**, so the master graph needs **6 phase-shifted clocks**. Flips/s scales linearly in p-bit count. | Claim 1's partition-into-independent-sets element; claim 1's update-ordering-between-classes element; claim 10 (sparse, bounded degree); claim 14; claim 18's colouring step. Does **not** disclose the clockless element — it is explicitly multi-phase clocked. | **HIGH** | Two lines. (a) *Definitional:* ¶[0019] of our spec expressly defines "a plurality of phase-shifted periodic signals constitutes a plurality of clock signals," so Aadit is squarely outside "in the absence of any clock signal." Keep that definition — it is doing all the work. (b) Aadit's classes are stochastic (Gibbs/p-bit) samplers with an RNG per node; ours are deterministic Boolean threshold functions settling to a fixed point. **But be honest:** neither line saves claim 1 from a §103 combination with items 3/6 (below). Aadit teaches every element of claim 1 except the clock, and the same research group published the motivation to remove the clock. | (ii) search-result summary of the Nature Electronics page and related arXiv items. Colour count (6), phase-shifted clocks, and Brélaz colouring are confirmed by the summary. Full text not accessed. |
| 2 | Aadit et al. (Nikhar, Kannan, Aadit, Chowdhury, Camsari), *All-to-all reconfigurability with sparse and higher-order Ising machines*, Nat. Commun. 15:8977 (2024) | Multiplexed FPGA architecture emulating all-to-all connectivity **while retaining highly parallelised chromatic Gibbs sampling**; higher-order (beyond-pairwise) interactions; benchmarked on 3R3X against D-Wave/Toshiba/Fujitsu. | Same elements as item 1, plus it extends chromatic scheduling to higher-order interaction graphs — which forecloses any argument that colouring is limited to pairwise couplings. | **MEDIUM-HIGH** | Same clockless carve-out. Also our interaction graph is fixed by a trained weight matrix, not multiplexed/reconfigured. This reference is mainly cumulative over item 1; its independent damage is that it proves chromatic scheduling was, by 2024, routine engineering practice in this exact hardware field — which is a §103 "level of ordinary skill" fact, and a bad one for us. | (ii) search-result summary (Nature Communications abstract-level). Not accessed in full. |
| 3 | Sutton, Faria, Ghantasala, Jaiswal, Camsari, Datta, *Autonomous probabilistic coprocessing with petaflips per second*, arXiv:1907.09664 / IEEE Access 8:157238 | A p-computer of p-bits in which **"there is no sequencer used to enforce an ordering of p-bit updates, as is typically required"** — explicitly *sequencerless* designs where all p-bits flip autonomously, giving operation **"unconstrained by available clock speeds."** The autonomous p-bit circuit literature states the governing design rule as **τ_S ≪ τ_N** (synapse response time much faster than neuron time), so that a p-bit that updates has already received up-to-date inputs reflecting the latest states of its neighbours. | Claim 1's clockless element and the "conditioned on signal propagation and settlement" language; **claim 2 directly** (a relation between the class delay and the settling time of the logic feeding it); claim 14/15. | **HIGH — and higher than the draft admits.** | (a) Sutton has **no colouring and no partition into independent sets** — it is deliberately unordered, and its authors accept sampling error from staleness. Our claim requires a proper colouring and an enforced ordering. (b) Sutton's τ_S ≪ τ_N is a *statistical* condition for approximately-correct Boltzmann sampling; our claim-2 condition is a *deterministic* condition for a block-sequential trajectory with a guaranteed energy decrease. **But the physics is the same rule with the labels swapped:** "synapse faster than neuron" and "node scheduling delay exceeds worst-case combinational (synapse) propagation delay" are the same inequality. Our own measured design rule is, on this evidence, already in the literature. Do not present it as novel. | (ii) search-result summary. The "no sequencer / autonomous / unconstrained by clock speeds" language and the τ_S ≪ τ_N rule both appear in search summaries of the p-bit autonomous-circuit literature. **Caveat I will not paper over:** I could not confirm that τ_S ≪ τ_N appears in 1907.09664 *specifically* rather than in a sibling paper (Faria/Camsari, *Hardware Design for Autonomous Bayesian Networks*, Front. Comput. Neurosci. 2021 / arXiv:2003.01767, which the same search surfaced). Counsel must pin the exact locus. |
| 4 | US 11,966,716 — draft characterises as *Hitachi, duplicated-spin (PCA) bipartite transformation, fully parallel clocked annealing* | **Unverified, and the draft's characterisation is in doubt.** The only retrieval I obtained describes US 11,966,716 as an *information processing apparatus* with an annealing control unit, a spin-interaction memory, a random-number generation unit and a spin-state update unit, solving via an Ising model — filed 2019-01-25, inventors **Shinya Takamaeda, Kodai Ueyoshi, Masato Motomura** (i.e. not obviously Hitachi, and no duplicated-spin/PCA language surfaced). | If the draft's characterisation is right: claims 7 and 8 (bipartite by duplicate nodes with an agreement-enforcing weight) are directly implicated, and claim 8 may be anticipated outright. If the retrieved characterisation is right, it is a clocked annealer with an RNG and touches claim 1 only weakly. | **HIGH on claims 7–8, contingent** | If duplicated-spin/PCA is disclosed: our only distinction on claim 8 is the clockless sequencing carried in claim 1, i.e. claim 8 adds nothing of its own. Consider dropping claim 8 to a spec embodiment rather than defending it. If the reference is the annealer instead: clocked, stochastic, RNG-driven, no colouring — distinguishable. | (ii)/(iii) — **contradictory**. The draft's own characterisation and the search retrieval do not agree. **Action item: counsel must pull the actual front page and claims of US 11,966,716.** Do not cite this reference in an IDS characterisation until that is done; a mischaracterised reference in an IDS is worse than an uncited one. |
| 5 | US 11,817,859; 11,716,083/084/085/086; 11,658,664; 11,652,482; 11,652,487 (Intel) — asynchronous circuits with capacitive threshold / majority gates | Not retrieved for 11,817,859. Confirmed only that **US 11,716,084 (Intel) is titled "Pull-up and pull-down networks controlled asynchronously by majority gate or minority gate logic"**, converting multi-input pull-up/pull-down networks into 1-input networks driven by a majority gate; and that Intel's related family recites that **"asynchronous logic does not use a global clock ... instead uses handshaking protocols as data propagates from one logic component to another."** | Claim 11 (majority-gate realisation of the threshold function); claim 1's "in the absence of any clock signal" + handshake framing; claims 4/5 (completion detection + C-element) at the level of generic async practice. | **MEDIUM-HIGH on claim 11; MEDIUM on claims 4/5** | These are gate-level/datapath primitives, not recurrent attractor networks. None of the retrieved material shows a recurrent interaction graph with a cycle, a colouring, or an inter-class update ordering. Our distinction is architectural, not device-level — argue at the level of claim 1's recurrence + partition + ordering. **However:** they establish that "asynchronous majority/threshold gate with handshake" was off-the-shelf in 2022–23, which makes claims 5, 11 and 23 near-worthless as independent points of novelty. | (ii) for 11,716,084 title and the Intel async boilerplate; **(iii)/not accessed for 11,817,859 and the other seven numbers.** Claim 1 of none of these was retrieved. |
| 6 | Rosin, Rontani, Gauthier, Schöll, *Excitability in autonomous Boolean networks*, arXiv:1208.6181 / EPL 100:30003 (2012); and *Experiments on autonomous Boolean networks*, Chaos 23 (2013) | Excitable systems built from **asynchronous logic gates on a reconfigurable chip (FPGA) in autonomous mode — no clock**; gates interconnected into **time-delay networks** whose dynamics show nanosecond-scale spike patterns **controllable in period and phase** via the delay lines. Recurrent, unclocked Boolean networks with per-link propagation delays as the design variable. | Claim 1's clockless + recurrent-combinational-network elements; **claim 2's delay-differentiation element** (delays as the controllable design variable in an unclocked recurrent Boolean network); claim 12 (transient propagation). | **HIGH — this reference is materially underrated in the draft.** | Rosin has (a) no threshold functions / no symmetric coupling weights / no energy function, (b) no attractor-recall or fixed-point objective — the point is sustained oscillation, which is exactly what we suppress, and (c) **no colouring and no independent-set partition**. That is a real distinction. But Rosin is the perfect §103 partner for Aadit: Aadit supplies "colour the coupling graph and update colour classes as blocks," Rosin supplies "recurrent Boolean networks run unclocked on an FPGA with per-node delays chosen to set the timing." An examiner who cites Aadit + Rosin against claim 1 has a strong case, and both are in the same technological neighbourhood. | (ii) search-result summary of the EPL/arXiv abstracts and the follow-on *Chaos* paper. Full text not accessed. |
| 7 | Hopfield, PNAS 79:2554 (1982) | Symmetric-weight recurrent binary threshold network; monotone Lyapunov energy; **asynchronous (one-at-a-time, random-order) update converges to a fixed point**; content-addressable memory framing. | Claim 1's node/interconnect/threshold-function elements; claim 13 (CAM); the entire convergence rationale in ¶[0022]–[0023]. | **HIGH as background, LOW as a standalone reference** | Nothing in claim 1 turns on the network model; Hopfield discloses no circuit-level sequencing mechanism and no colouring. It anticipates the *purpose* (CAM) and the *dynamics*, so claim 13 adds nothing patentable. Cite it, concede it, and never argue against it. | (iii) background knowledge only — nature.com and the PNAS route are blocked. Content is uncontroversial and universally known. |
| 8 | Kosko, *Bidirectional associative memories*, IEEE Trans. SMC 18:49 (1988) | Two-layer bipartite associative memory; couplings only **between** layers; stable under **alternating layer-wise (block) update** of the two layers, with a bidirectional Lyapunov function. Implemented in hardware by many groups in the late 1980s–90s. | **Claim 7 directly** ("exactly two update classes and the interaction graph is bipartite"), claim 20's "constraining training to a two-layer coupling topology," and the two-class portions of ¶[0025]. | **HIGH against claims 7 and 20 (first alternative)** | Our only distinction on claim 7 is the clockless sequencing imported from claim 1. Kosko is a §102-grade disclosure of "bipartite ⇒ two alternately-updated classes, convergence guaranteed" — that is the entire substance of claim 7. **Recommendation: claim 7 is not independently novel.** Keep it only as a scope-fence dependent, and expect it to be rejected as adding nothing over claim 1. | (ii)/(iii) — the alternating-layer-update mechanism was confirmed at summary level in general Hopfield/BAM material; the IEEE paper itself was not accessed. |
| 9 | Goles et al., block-sequential update literature (and the Boolean-automata-networks follow-on: Goles & Noual; "On the cost of simulating a parallel Boolean automata network by a block-sequential one") | Formal theory of **block-sequential update schedules** on threshold/automata networks: the state space is partitioned into blocks, blocks are updated in a fixed sequence, nodes within a block simultaneously; **the energy function decreases and fixed-point convergence holds for symmetric weights** under such schedules, whereas fully parallel update admits period-2 cycles. | The entire theoretical justification recited in ¶[0022]–[0023] and asserted as the benefit in claims 1, 14 ("whereby the network converges to a fixed point without oscillation"). | **HIGH against the rationale; MEDIUM against the claims** | The claims are to *circuitry*, and Goles discloses no circuit. That is the only defence and it is a good one — but it means **we must not argue that "block-sequential ⇒ convergence" is inventive**, and we should not let dependent claims be drafted so that their only added content is a restatement of Goles. This is precisely the "chromatic scheduling as an algorithm is textbook" concession we already made. | (ii) for the existence and framing of the block-sequential literature (confirmed via the Springer chapter and the "decreasing energy functions for threshold networks" material); (iii) for the specific Goles theorem statements. |
| 10 | Orponen, *Computing with truly asynchronous threshold logic networks*, Theor. Comput. Sci. 174:123 (1997) | Threshold-logic networks under **"truly asynchronous"** operation — arbitrary/unbounded update delays, no ordering assumption at all — and the computational characterisation thereof. Published in TCS; article page on ScienceDirect confirmed to exist. | Claim 1's premise that ordering must be *enforced*; claim 14's "whereby the network converges to a fixed point without oscillation attributable to simultaneous update." | **MEDIUM-HIGH, and dangerous in a way the draft does not anticipate** | The danger is not anticipation, it is **motivation destruction**. If a POSITA already knew that threshold-logic networks compute correctly under arbitrary asynchronous delays, an examiner can say the clockless recurrent threshold network was known and the colouring is a mere obvious optimisation. Our answer must be empirical and specific: our own measurement (C1) is that **60.2% of the 2^16 state space cycles** under simultaneous update and that *unordered* delay assignment (index parity) settles 0% on the hard set — i.e. "truly asynchronous" in the physical sense of coupled nodes commiting together does *not* converge. That is a genuine, non-obvious, measured rebuttal. Put it in the spec as a worked result, not as attorney argument. | (ii) — confirmed the paper exists at that citation with that title and that it is cited alongside Goles/Noual in the automata-network literature. **Contents not accessed** (ScienceDirect blocked). I am not going to characterise its theorems from memory. |
| 11 | Gonzalez, Low, Gretton, Guestrin, *Parallel Gibbs Sampling: From Colored Fields to Thin Junction Trees*, AISTATS 2011 (PMLR v15:324–332) | The **Chromatic parallel Gibbs sampler**: graph-colour the Markov random field and sample all variables of one colour in parallel, cycling through colours; proves this parallel schedule is equivalent to a valid sequential sweep. Plus the Splash sampler for tightly-coupled variables. | Claim 1's partition-into-independent-sets element; claim 14's method framing; claim 18's colouring step. This is the *origin* of Aadit's method. | **HIGH against method claims 14 and 18; MEDIUM against claim 1** | It is software on a 32-core CPU — no circuitry, no delays, no clocklessness, no threshold logic, no fixed-point attractor. Claim 14 is anchored to "sequencing circuitry," which saves it, and claim 18 outputs "a circuit definition dataset," which saves it. **But the draft has already flagged this as highly material and that judgement is correct.** It forecloses the colouring step as a point of novelty for all time; any claim whose novelty rests on "colour the graph and update classes in turn" is dead on Gonzalez alone. | (ii) — PMLR listing, abstract and the chromatic/Splash decomposition confirmed via search summary; PDF at proceedings.mlr.press exists but was not fetched. |
| 12 | Multicolour Gauss-Seidel / parallel-schedule-from-colouring (textbook) | Red-black and multicolour orderings of Gauss-Seidel/SOR: colour the sparse matrix graph, relax all unknowns of one colour in parallel, cycle colours; the result is provably identical to a sequential sweep in a permuted order. Standard numerical-linear-algebra material since the 1970s. | Same as item 11. Also the "aggregate effect identical to evaluating them one at a time" assertion in ¶[0023]. | **HIGH against any colouring-only novelty; LOW against the drafted claims** | Same argument as item 11 — no circuit. Its role is to make the colouring step *unarguably* old, which we have already conceded. Its practical effect is to force all of our novelty onto the physical realisation. | (iii) background knowledge only. Universally documented; not contentious. |
| 13 | Fahimi, Mahmoodi, Nili, Polishchuk, Strukov, *Combinatorial optimization by weight annealing in memristive Hopfield networks*, Sci. Rep. (2021) | Memristive-crossbar Hopfield network for combinatorial optimisation in which annealing is performed by **scaling the coupling weights** rather than by injecting noise. Analog crossbar; continuous-time settling. | Claim 1's threshold-node/recurrent-interconnect elements at the analog level; peripherally claim 12 (perturbation as a computational resource). | **LOW-MEDIUM** | Analog crossbar with continuous-valued dynamics; no Boolean threshold logic block, no update classes, no colouring, no delay-based sequencing. The only real touch is that memristive Hopfield crossbars are *inherently clockless* — see §5(d), where I argue this whole family (13–15, plus the 1980s analog Hopfield chips that are **not on this list**) is a bigger threat to claim 1's "clockless" element than the draft recognises. | (ii) title/venue/approach confirmed via search summary; (iii) for detail. Not accessed. |
| 14 | *Noise tailoring, noise annealing and external noise injection strategies in memristive Hopfield neural networks*, APL Mach. Learn. (2024) | Comparative study of intrinsic-noise, annealed-noise and externally-injected-noise strategies in memristive Hopfield networks for optimisation. | **Claim 12** (transient logic hazards permitted to propagate "as stochastic perturbations of a network state") and the annealing discussion in the spec. | **MEDIUM against claim 12** | Claim 12's novelty is not "noise helps" — that is thoroughly old (items 14, 15, 16) — it is that the noise source is *the circuit's own combinational hazards*, requiring no RNG, no noise generator and no injection path. Draft claim 12 accordingly, and recite the absence of a random number generator or noise-injection circuit as a positive limitation; as written, claim 12 is a permissive ("are permitted to propagate") and permissive limitations are weak. | (ii) venue/topic confirmed by search context; (iii) for specifics. Not accessed (APL/AIP not reachable). |
| 15 | Cai, Kumar et al., *Power-efficient combinatorial optimization using intrinsic noise in memristor Hopfield neural networks*, Nat. Electron. 3:409 (2020) (and arXiv:1903.11194) | Memristor-Hopfield crossbar solving max-cut, **harnessing intrinsic analog device noise as a computing resource** rather than suppressing it; analogue–digital hybrid with a feedback algorithm to amplify/damp the noise. | **Claim 12**, squarely — "device-intrinsic noise as a computational resource in a Hopfield network" is the exact concept. | **MEDIUM-HIGH against claim 12** | Distinction is the *kind* of noise and where it comes from: theirs is analog device/thermal noise in a crossbar, ours is a deterministic digital logic hazard arising from the multi-level SOP realisation of a threshold function. That is a real structural difference but it is a narrow one, and an examiner may well call it an obvious substitution of one perturbation source for another. **Claim 12 is the weakest "clever" claim in the set.** Either narrow it hard (no RNG, no noise-injection circuit, hazard arising from a specified multi-level realisation) or drop it. | (ii) — abstract-level content confirmed via search summary (intrinsic noise as resource, max-cut, crossbar). Not accessed in full. |
| 16 | Chen & Aihara, *Chaotic simulated annealing by a neural network model with transient chaos* (1995); *On chaotic simulated annealing*, IEEE TNN (1999) | Transiently-chaotic Hopfield-type network: a self-feedback term is annealed so the network is **deterministically chaotic early and settles to a fixed point late** — annealing without any stochastic source. | Claim 12; and the spec's suggestion that occasional ordering violations act as beneficial stochastic perturbations (¶[0029]). | **MEDIUM** | This is the most awkward reference for the ¶[0029]/claim 12 story, because it establishes that **deterministic** internal dynamics deliberately used as an annealing perturbation in a Hopfield network is a known technique. It removes the "but ours isn't random noise" distinction we might have used against items 14–15. Our remaining distinction is purely that the mechanism is a circuit-level timing hazard rather than a modelled self-feedback term. | (iii) background knowledge only. Not accessed. |
| 17 | Blake & Zisserman (GNC); Rose (deterministic annealing); Hazan et al., *Graduated optimization for stochastic non-convex problems* (2015) | Continuation / graduated non-convexity: solve a smoothed problem and track the solution as the smoothing is withdrawn. Deterministic annealing as a statistical-physics analogue of the same. | Nothing in the drafted claims. Touches only the annealing narrative in the spec. | **LOW** | Purely algorithmic optimisation theory; no circuit, no update ordering, no threshold hardware. Its only role is to make "anneal a control parameter" old, which affects no drafted claim. **This is the least material item on the list.** If it is on the list to pad an IDS, that is fine; if it is there because someone thought it was close art, it is not. | (iii) background knowledge only. Not accessed. |
| 18 | NullaNet; LogicNets; PolyLUT (arXiv:2309.02334); NeuraLUT-Assemble (arXiv:2504.00592); SparseLUT (arXiv:2503.12829) | **NullaNet: "minimises these functions' footprint using Boolean logic minimisation, selectively determining output values for specific input combinations while treating the rest as don't-care conditions to conserve resources."** LogicNets: a-priori extremely sparse networks trained so each neuron's full truth table fits a LUT, avoiding NullaNet's don't-care-induced accuracy loss. PolyLUT/NeuraLUT/SparseLUT: successive refinements of neuron→LUT mapping with structured pruning and polynomial features. | **The absent don't-care claim family**, entirely. Also claim 18's "synthesizing combinational logic implementing a Boolean threshold function," claim 9/11 (node realisation), claim 10 (bounded degree — LogicNets' central trick). | **HIGH against the don't-care family — the single most dangerous item for the claim we have not yet written** | Our real distinctions, in order of strength: (1) **the care set is derived in closed form** — `M·Σ_{j≤h} C(d,j)` states, the union of Hamming balls of radius `h` about the stored patterns — whereas NullaNet's don't-cares are the *complement of an empirically sampled activation set*, which is data-dependent, unbounded and unverifiable; (2) **the network is recurrent**, so an incorrect off-region output can create a *new spurious fixed point* — a correctness hazard that simply does not exist in NullaNet/LogicNets' feedforward setting, and which we address; (3) **a guaranteed operating region** (recall correct for all inputs within radius `h`) rather than a statistical accuracy target. Distinction (2) is the strongest and should be the centre of gravity of the claim. Distinction (1) alone risks being dismissed as an obvious choice of don't-care set. Also note claim 10 ("maximum degree bounded independently of N") is essentially LogicNets' architecture — expect a rejection there. | (ii) — NullaNet's don't-care mechanism, LogicNets' motivation for avoiding it, and PolyLUT's positioning all confirmed by search summary of the survey/NeuraLUT-Assemble material. Primary papers not accessed. |
| 19 | Unger (hazards, inertial delay); Nowick & Dill, *Exact two-level minimization of hazard-free logic with multiple-input changes* (ICCAD'92; IEEE TCAD 14:986, 1995); Theobald & Nowick, *Espresso-HF* | Nowick & Dill: **exact hazard-free two-level (SOP) minimisation**, a constrained Quine–McCluskey, producing a minimal SOP that is hazard-free for a given set of **multiple**-input changes if one exists. Espresso-HF is the heuristic version. Unger: inertial vs transport delay; pulse rejection; classical asynchronous-sequential-circuit hazard theory. | **Claim 21 directly** (enable-gating ⇒ single-input-change ⇒ "combinational logic of the node circuit is hazard-free with respect to a single input change"); **claim 22** (inertial delay element with a rejection window); and the don't-care family, adversely. | **HIGH against claim 21; MEDIUM against claim 22** | Claim 21 recites textbook fundamental-mode/burst-mode asynchronous design: gate the data, let the enable be the sole changing input, synthesise SIC-hazard-free. There is nothing novel there; its only value is as a scope fence. Claim 22 is better — the *dual role* of one element as both the class sequencer and the hazard filter, with the rejection window quantitatively tied to the preceding class's settling time, is a specific structural relation I did not find disclosed. **Claim 22 is, in my assessment, the strongest apparatus claim in the draft after a properly narrowed claim 1.** ⚠️ **Internal contradiction to resolve before filing:** hazard-free two-level synthesis requires *retaining redundant consensus product terms* — exactly the terms our don't-care minimisation deletes. Claim 21 and the (absent) don't-care family are in direct technical tension, and `MEETING_PREP.md` already identifies this. If both families are prosecuted, an examiner or an opponent will read them against each other. Additionally, Nowick & Dill's own framing already contemplates **multiple**-input changes, so the "classical theory only covers SIC" caveat in `MEETING_PREP.md` is *too generous to us* — the multiple-input-change case is covered by the 1992/1995 work. | (ii) for Nowick & Dill's exact-minimisation result and the multiple-input-change scope (confirmed via search summary and the Columbia CS6861 handout listing); (iii) for Unger. Primary texts not accessed. |

---

## 3. Separate report: NCL / QDI fallback embodiment

**Question asked:** is "dual-rail NULL Convention Logic with Muller C-element completion detection,
combined with graph-coloured update ordering in a recurrent neural network" already disclosed?

**Answer: I found no disclosure of that combination.** Every search that paired NCL/QDI vocabulary
with Hopfield/recurrent-neural-network vocabulary returned the two literatures separately and never
joined. That is a genuinely encouraging (if negative-evidence) result, and it is the cleanest white
space identified in this review. Caveat: negative search results from a summarising search tool are
weak evidence, and I could reach neither IEEE Xplore, ACM DL, nor any patent database.

**FTO on core NCL — probably clear, because the foundational patents have expired:**

| Patent | Title | Assignee history | Status |
|---|---|---|---|
| US 5,305,463 | Null convention logic system | Theseus Research → Theseus Logic → **Camgian Networks (2009)** | Filed 1991-ish; **expired** |
| US 5,664,211 | Null convention **threshold gate** (Fant & Sobelman) | Theseus Research → Theseus Logic → Camgian | Issued 1997; **expired** |
| US 5,652,902 | Asynchronous register for NCL systems | Theseus | listed **"Expired — Lifetime"** |
| US 5,764,081 | Null convention interface circuits | Theseus | expired |
| US 5,793,662 | Null convention adder | Theseus | expired |
| US 5,828,228 | Null convention logic system (Fant & Brandt) | Theseus | Issued 1998; **expired** |

All are 1991–1998 filings, so all are past the 20-year term.

**The live risk is the later NCL layer, not the Fant layer.** Specifically:

- **US 7,977,972 — "Ultra-low power multi-threshold asynchronous circuit design"** (MTNCL; Di &
  Smith lineage, issued 2011, so a filing around 2009 ⇒ term to roughly **2029**). Any
  low-power/sleep-mode NCL implementation we build should be cleared against this and its
  continuations.
- **US 12,431,188 — "Efficient Muller C-element implementation for high bit-width asynchronous
  applications"** (surfaced in search; recent, therefore live). Relevant if we claim a specific
  C-element structure rather than "at least one Muller C-element."
- The Camgian portfolio should be swept for continuations filed after 2005.

**Two things that cut against us on the NCL embodiment:**

1. **US 5,664,211 is literally titled "Null convention threshold gate."** An examiner looking for
   "asynchronous circuit whose primitive is a threshold function" will find it immediately. It is
   prior art against the general framing of "threshold-logic nodes sequenced without a clock," even
   though it discloses no recurrence and no colouring.
2. `MEETING_PREP.md` says C-elements are probably unnecessary (hazards measured benign, 98% recall
   at a 70% glitch rate) and that dual-rail would **erase our already-marginal area advantage**
   (1.52× on ASIC, **1.19× worse** on FPGA). Claiming an NCL embodiment we have not built and do not
   recommend adds prosecution surface, an enablement obligation for an unbuilt embodiment, and a
   §112 written-description exposure, in exchange for a fallback we have argued against. **My
   recommendation: describe the NCL/QDI embodiment in the specification for scope, but do not spend
   an independent claim on it.**

---

## 4. Prose analysis

### (a) Which references are genuinely dangerous, and why

**Tier 1 — will be cited against claim 1, and should be assumed fatal to it as drafted:**

1. **Aadit 2022 (item 1) + Sutton 2019 (item 3).** This is the combination that ends the current
   claim 1. Aadit discloses: threshold-like binary nodes, a recurrent sparse coupling graph, a
   partition into independent sets by graph colouring, and an enforced update ordering between
   classes. It supplies every element of claim 1 except "in the absence of any clock signal." Sutton
   — **same lab, same device family, three years earlier** — supplies exactly that missing element,
   and supplies the *motivation* in so many words: remove the sequencer and the clock so that
   operation is "unconstrained by available clock speeds." Under *KSR*, a combination with an
   express motivation, drawn from the same research group in the same field, with a predictable
   result, is about as strong a §103 case as an examiner can assemble. Claim 1 will not survive it.
2. **Rosin 2012 (item 6)** is the alternative second reference and is arguably worse for us than
   Sutton, because it is a *digital, FPGA, recurrent Boolean network run unclocked, with the
   propagation delays as the tuned design variable*. Aadit + Rosin gives the examiner colouring plus
   clockless-delay-tuned recurrent Boolean hardware. The draft treats Rosin as background. That is a
   mistake.
3. **Gonzalez 2011 (item 11)** we have already flagged, correctly. It permanently forecloses the
   colouring step as a source of novelty and reaches the method claims most directly.

**Tier 2 — will kill specific dependent claims:**

- **Kosko (item 8)** against claim 7 (bipartite two-class alternating update).
- **US 11,966,716 (item 4)**, *if* the draft's duplicated-spin characterisation is correct, against
  claim 8.
- **Nowick & Dill (item 19)** against claim 21.
- **Cai/Kumar 2020 and Chen & Aihara (items 15, 16)** against claim 12.
- **LogicNets (item 18)** against claim 10, and against the entire unwritten don't-care family.
- **Intel majority-gate async family (item 5)** against claim 11.

**Tier 3 — background, cite and concede:** items 7, 9, 12, 13, 14, 17.

### (b) Claim elements that are NOT safely novel — narrow or drop

| Element | Verdict |
|---|---|
| "Partitioned into update classes such that no two nodes in a class are directly coupled" (claim 1, 14, 18) | **Not novel.** Gonzalez 2011, multicolour Gauss-Seidel, Aadit 2022, Goles. Keep it as a limitation; never argue it as the point of novelty. |
| "Enforce an update ordering among the classes" (claim 1) | **Not novel.** Aadit does exactly this with clock phases. |
| "In the absence of any clock signal" (claim 1) | **Novel only in combination**, and the combination is obvious over Aadit + Sutton/Rosin. This element cannot carry claim 1 by itself. |
| Claim 6 — convergence detection by a no-change pass | **Not novel.** Generic quiescence/completion detection; standard in async design and in annealer patents. |
| Claim 7 — exactly two classes / bipartite | **Anticipated in substance by Kosko.** Demote to spec. |
| Claim 8 — duplicate nodes with an agreement-enforcing weight to force bipartiteness | **Probably anticipated** (item 4 / the PCA duplicated-spin technique, which is well known in the Ising-hardware literature independent of that patent). Demote to spec. |
| Claim 9 — binary/ternary weights + popcount | **Not novel.** Ubiquitous in binarised-NN hardware. |
| Claim 11 — adder+comparator or majority-gate network | **Not novel.** Intel async majority-gate family; forty years of threshold-logic implementation art. |
| Claim 13 — CAM/associative memory | **Not novel.** Hopfield 1982. Also note `CLAIMS_AUDIT.md` C16: a nearest-match CAM beats this design on both area and function at M=4 — so claim 13 asserts a use we have measured ourselves to be inferior. Claiming it invites an unnecessary utility argument. |
| Claim 21 — enable-gating for single-input-change hazard-freedom | **Not novel.** Textbook fundamental-mode asynchronous design; Nowick & Dill. |
| Claim 12 — hazards as stochastic perturbations | **Weak.** Narrow to recite the absence of an RNG/noise-injection circuit, or drop. |
| Claim 17 — read outputs responsive to the convergence signal | Trivial. |

**Elements that are worth fighting for, in order:**

1. **The delay-VALUE invariant.** Not "different classes have different delays" as a design
   preference, but: *every pair of directly coupled node circuits is associated with different
   delay values*, with the negative limitation that a proper colouring in which all classes share a
   delay value does not produce settling. This is the one thing we measured that nobody in the
   listed art states, and it is currently in *dependent claim 2 only*, and even there in a weaker
   two-class form. **Move it into claim 1.**
2. **Claim 22** — the inertial delay element serving simultaneously as class sequencer and hazard
   filter, rejection window ≥ the preceding class's settling interval. Specific, structural, and I
   found nothing disclosing the dual role.
3. **The don't-care family that isn't in the draft** — specifically the recurrence argument (an
   incorrect off-region output can create a new spurious fixed point), which is a correctness
   problem NullaNet/LogicNets never face.
4. **Claim 3** (post-manufacture calibration of the delay ratio by increasing it until oscillation
   ceases, with a guard band). This is a concrete, testable, structural procedure. It is
   underdeveloped in the draft — it deserves more dependents, not fewer.

### (c) References more material than the draft's own characterisation admits

1. **Sutton et al. 2019 (item 3) — the draft names Aadit 2022 as the closest art. On my reading that
   is wrong, or at least incomplete.** Aadit is the closest art *to the colouring*; Sutton is the
   closest art *to the clocklessness*, which is the only element the colouring art lacks and
   therefore the only element carrying our novelty. Worse: the τ_S ≪ τ_N design rule in the
   autonomous-p-bit literature is the same inequality as our own "scheduling delay must exceed
   worst-case combinational propagation delay through the node logic," which `PHASES.md` and the
   brief present as a measured contribution. **We should stop presenting that design rule as novel.**
   Treat Aadit + Sutton as a single combined closest-art unit in the background section and
   distinguish against the pair, not against Aadit alone.
2. **Rosin et al. (item 6).** Characterised in the brief as "unclocked recurrent Boolean gate
   networks on FPGA," which is accurate but reads as background. It is not background: it is a
   working demonstration that recurrent Boolean networks run unclocked with delays as the tuned
   design parameter, which is claim 2's substance in a different application. Promote it.
3. **Nowick & Dill (item 19).** `MEETING_PREP.md` says "the classical theory mostly covers
   single-input-change, while our case has many neurons changing at once." That is **too generous to
   us**: the 1992 ICCAD / 1995 TCAD paper is titled *"...hazard-free logic with **multiple**-input
   changes."* The multiple-input-change case is squarely covered. Remove that sentence from any
   argument we make.
4. **Item 4 (US 11,966,716).** Not "more material" but **mis-characterised or mis-numbered**. My
   retrieval and the draft's description do not match on assignee, inventors, or subject matter.
   Resolve this before it goes into an IDS.
5. **Item 18 / NullaNet.** The brief characterises the LUT-NN family as using "don't-cares from
   sampled activations," implying a clean distinction. That distinction is real but narrower than it
   sounds: NullaNet's disclosure is *"treating the rest as don't-care conditions"* — a general
   teaching of don't-care-based logic minimisation of neuron functions. The novelty must rest on
   recurrence and the guaranteed-radius operating region, not on the mere fact of using don't-cares.

### (d) Gaps — art I expect exists that is not on this list

The list has a conspicuous shape: it is strong on 2019–2024 p-bit/Ising hardware and on modern
LUT-NN work, and almost empty on **1985–1998 analog and asynchronous neural VLSI**, which is exactly
where the dangerous §102 art for a *clockless recurrent threshold network* lives.

1. **1980s–90s analog Hopfield VLSI. This is the biggest gap and I would treat it as urgent.**
   Graf & Jackel (AT&T Bell Labs) CMOS associative-memory chips; Sivilotti/Mead/Emerling; Verleysen
   & Jespers; Moopenn/Thakoor (JPL). These chips are *inherently clockless*: an array of amplifiers
   with resistive feedback, each node settling on its own RC time constant, converging to a fixed
   point with no periodic timing reference anywhere. That is claim 1's preamble plus its clockless
   element in 1987 silicon. What they lack is the colouring — which is why claim 1 must recite the
   colouring **and** the delay-value relation, not the clocklessness, as its point of novelty.
2. **Delay-differentiated / random-delay Hopfield hardware.** A search surfaced: *"Takeda et al.
   designed direct and differential asynchronous transition modes with random delays to address the
   oscillation problem of discrete-time Hopfield models."* If that is Takeda & Goodman (Applied
   Optics, 1986) or a successor, it is **directly on point for claim 2** — per-node delays
   deliberately differentiated to break simultaneous update of coupled neurons. I could not access
   it. **Counsel should treat this as a potential §102 reference against claim 2 and pull it first.**
3. **Fujitsu Digital Annealer patent family** (parallel-trial with single-flip acceptance), and
   **Toshiba SBM** and **D-Wave** control-sequencing patents. All concern enforcing a valid update
   order across many simultaneously-evaluated spins. None are on the list.
4. **Cellular neural networks (Chua & Yang, 1988)** and their clockless analog VLSI
   implementations — recurrent threshold arrays with local coupling that settle without a clock.
5. **Partitioned/block cellular automata hardware** — Margolus-neighbourhood and
   partitioned-CA machines are literally "partition the nodes so that a block updates without
   intra-block interaction, then alternate partitions." That is our claim 1 partition concept in
   1980s CA hardware.
6. **Asynchronous / self-timed CAM and associative-memory patents** (claim 13's territory).
7. **Boltzmann machine hardware patents, late 1980s** (Alspector at Bellcore; Bell Labs) —
   several used deliberately staggered or randomised node update timing in analog VLSI.
8. **Systolic/wavefront array "self-timed dataflow" patents** — the wavefront-array literature
   (S.-Y. Kung) is exactly "ordering enforced by data arrival rather than a clock."
9. **Neuromorphic async patents:** IBM TrueNorth, Intel Loihi, and SpiNNaker filings, which are full
   of "clockless / event-driven neuron update ordering" language.
10. **Continuations and family members of Aadit/Camsari (UCSB) and Datta (Purdue).** If a US
    application claims graph-coloured p-bit updating, it is the reference that matters most and it is
    not on this list. **Sweep UCSB/Purdue/Camsari/Datta/Aadit as assignee and inventor.**

**Search terms for counsel:**

- Classification-first: **CPC G06N 3/063** (neural network hardware), **G06N 3/047**, **G06N 10/60**,
  **H03K 19/00 / 19/20** (async logic), **G06F 1/04–1/12** (clocking), **G11C 15/00** (CAM),
  **G06F 30/327** (logic synthesis).
- `("graph coloring" OR "graph colouring" OR "vertex coloring" OR "independent set") AND (Ising OR
  Hopfield OR "Boltzmann machine" OR p-bit) AND (update OR schedule OR parallel)`
- `("clockless" OR "self-timed" OR asynchronous OR "delay insensitive" OR "quasi delay
  insensitive") AND (Hopfield OR "associative memory" OR "attractor network" OR "recurrent neural")`
- `("propagation delay" OR "delay element" OR "delay line" OR "inertial delay") AND neuron AND
  (update order OR "simultaneous update" OR oscillation OR "limit cycle")`
- `"block sequential" OR "block-sequential" AND (threshold network OR automata network) AND hardware`
- `"duplicate spin" OR "spin duplication" OR "parallel cluster annealing" OR PCA AND bipartite AND Ising`
- `"don't care" AND ("logic minimization" OR espresso OR "sum of products") AND (neuron OR "neural
  network") AND (LUT OR FPGA)` — plus `"Hamming" AND "don't care" AND "operating region"`
- `"completion detection" AND (neuron OR "neural network" OR Ising)`
- Assignee/inventor sweeps: **Camsari; Datta; Aadit; Chowdhury; UC Santa Barbara; Purdue Research
  Foundation; Hitachi (Ising/CMOS annealing); Fujitsu (Digital Annealer); Toshiba (SBM); Intel
  (asynchronous majority gate); Camgian Networks (NCL); University of Arkansas (MTNCL).**
- Non-patent: Takeda & Goodman (asynchronous transition modes, random delays, Hopfield); Graf &
  Jackel; Alspector; Chua & Yang; Margolus partitioned CA.

---

## 5. Bottom line

**Claim 1 as drafted is in trouble.** It recites a known partition (Gonzalez, Gauss-Seidel, Aadit), a
known ordering objective (Goles, Kosko, Aadit), and a known absence-of-clock (Sutton, Rosin, the
whole async-VLSI corpus), joined by a functional "configured to enforce" that recites no structure
for the enforcement. Aadit + Sutton, or Aadit + Rosin, is a straightforward §103 rejection with an
express motivation to combine. Separately, because claim 1 omits the delay-value limitation, it
covers a configuration our own measurements show settles **0% of the time**, which is an enablement
problem we would be handing to an opponent.

**The two fixes are the same fix: put what we actually measured into the independent claims.**

1. Amend claim 1 to require that **each pair of directly coupled node circuits is associated with
   different delay values**, and that the delay associated with a node circuit **exceeds the
   worst-case combinational propagation delay through that node circuit's logic**. This is
   structural, it is measured (C3, C15), it is what makes the invention work, and — with the
   Sutton caveat honestly noted — it is what the colouring art does not have, because the colouring
   art assigns *clock phases*, which are timing references, not delay values.
2. **Write the don't-care claim family.** It is currently claimed nowhere, our own record calls it
   our strongest contribution, and the closest art (NullaNet) is distinguishable on recurrence —
   spurious-fixed-point correctness — in a way the colouring claims are not distinguishable on
   anything.

And before any of that is filed: **verify US 11,966,716 and the eight Intel numbers on an
unrestricted network.** Nothing in the "US patents" rows of this review is verified, and one of them
appears to be mis-characterised in our own draft.
