# Patent draft — what changed and why

`patent_draft_original.docx` is the draft as supplied.
`patent_draft_revised.docx` is the revision. `revise.py` regenerates it.

Both are committed because this container has repeatedly lost files.

94 → 116 paragraphs. ¶[0001]–[0056] contiguous, no gaps or duplicates.
Claims 1–31 contiguous. Claim amendments are **proposals for counsel**.

---

## 1. A correction that had to be made

¶[0030] as supplied read:

> "The delay elements **may exhibit transport delay characteristics**, in which
> any input feature, however narrow, is reproduced at the output after the delay
> interval, **or** inertial delay characteristics…"

Measured, on identical networks, partitions, delay values and initial states:

| N | inertial | transport |
|---|---|---|
| 16 | 100% | 1% |
| 32 | 100% | 16% |
| 64 | 100% | 15% |
| 128 | 100% | 7% |

The specification was therefore teaching an inoperative embodiment as an
equal alternative — an enablement problem. ¶[0030] now requires the inertial
characteristic and explains the mechanism: because each node evaluates
continuously rather than once per pass, a node's target can revert after a
transition is scheduled and before it is committed, and a transport element
commits that superseded value onto neighbours whose states have since changed.

Recorded honestly: transport reaches 100% in the sparse, low-loading,
near-pattern regime of the N=256 result, which is why the defect did not show up
earlier. ¶[0046] says so.

## 2. Reframing against art now read in full

- **¶[0006]** now records that clocked colour-partitioned implementations
  characterise themselves as hardware chromatic Gibbs sampling, that relaxing the
  per-class interval has been reported *not* to prevent convergence, and that
  clockless recurrent Boolean networks with per-link programmable delay lines
  exist (for generating oscillation, not suppressing it).
- **¶[0028]** now states that "a class must settle before a subsequent class
  evaluates" is a *known* requirement, and that what is provided is its
  realisation by delay values in the feedback path with no periodic reference.
- **¶[0009]** softened from "without requiring hazard-free logic synthesis" to
  "substantially, though not in all cases entirely", pointing at ¶[0050].

## 3. Experimental examples — ¶[0041]–[0055]

Measured results only; ¶[0041] states plainly that nothing came from silicon.
Covers chromatic number and its scaling, necessity of distinct delay values,
insensitivity to which values, **necessity of the inertial characteristic**,
N=256 RTL verification, delay variation tolerance, the sizing rule as a measured
consequence rather than a discovery, residual gate-level hazards, the dual-rail
embodiment and its measured cost, the dual-rail/don't-care incompatibility,
storage and recall, don't-care synthesis, and max-cut.

## 4. Claim amendments (proposals)

- **Claim 1** gains: "the sequencing circuitry being further configured such that
  no two node circuits directly coupled to one another in the interaction graph
  commit output transitions concurrently." Without it the claim's structural
  limitation is satisfied by a proper colouring with all delays equal — the
  configuration measured settling 0% of the time.
- **Claim 2** now requires the delay value of each class to differ from that of
  *every* other class, not merely that classes have "different delays".
- **Claim 22** recast from hazard filtering to **cancellation of a superseded
  transition**, which is what the measurement shows matters.
- **New claim 25** (independent): the delay realisation — per-node inertial delay
  elements in the feedback path, distinct values per class, no periodic timing
  reference. This is the limitation the closest art cannot reach, because a
  phase-shifted clock samples at an edge and never observes a transition that
  appeared and disappeared between edges. Claims 26–27 depend on it.
- **New claim 28** (independent): the operating-region don't-care synthesis,
  which the supplied claim set did not reach at all. Claims 29–31 depend on it,
  including the closed-form care-set size and the express distinction from
  methods that sample activations.

## 5. IDS supplemented

Items (20) Nikhar et al. 2024 and (21) Wang/Wu/Roychowdhury DAC 2019, plus a
note flagging the two passages in the closest art that counsel must assume will
be found: the settle-before-next-class sentence, and the overclocking result.

---

## Left alone deliberately

The **[INVENTOR FINALIZATION]** block. It asks for (a) matched-delay sizing and
guard band, (b) four-phase versus two-phase signalling, (c) power-on reset
protocol. Those are design decisions for the inventors, not results. ¶[0049] and
¶[0048] now inform (a).

## Still needed before filing

- Takeda 1986, and the 1986–87 analog Hopfield VLSI (Graf; Sivilotti/Mead;
  Moopenn) — see `../paper/PRIOR_ART_CITATIONS.md`
- Claim 1 of the nine cited US patents; none has been retrieved
- A decision on the annealing embodiment, which the overclocking art substantially
  anticipates. It is Lin's idea and narrowing it is his call, not ours.
