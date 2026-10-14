# Patent finalization — what's left, and one blocker

## The blocker: the spec and the drawings don't match

The application's BRIEF DESCRIPTION OF THE DRAWINGS promises FIG. 1–7, and the
detailed description references FIG. 3, 4, 5, 6 and 7 by number. The twelve
sheets in `../patent_figures/` are a **different figure set**, drawn against the
annealing-oriented figure PDF rather than against this application.

They disagree on nearly every number. The spec's FIG. 2 is a coloured
interaction graph; our FIG. 2 is the timing-margin annealing curve. An
application cannot be filed in this state.

### What the spec asks for, and what exists

| spec | required content | nearest drawn sheet | status |
|---|---|---|---|
| FIG. 1 | block diagram of the network circuit | sheet 1 (apparatus overview) | **adapt** — drop the annealing-control blocks |
| FIG. 2 | interaction graph partitioned by proper colouring, incl. bipartite case | sheet 6, panels A–B | **adapt** — add the bipartite case |
| FIG. 3 | node circuit: input gating, population-count summation, threshold | sheet 8 | **redraw** — ours is an SOP plane, spec says popcount |
| FIG. 4 | timing diagram, delay-differentiated, second class delay > first class settling | sheet 7 | **reuse** — near-exact match |
| FIG. 5 | handshake embodiment: per-class completion detection, C-element phase element | sheet 9 | **adapt** — ours is the dual-rail datapath, spec wants the phase element |
| FIG. 6 | convergence detection circuitry | — | **missing entirely** |
| FIG. 7 | flowchart: sparsify, retrain, colour, synthesise | sheets 5 + 10 | **merge** |

### Drawn material the spec does not cover

Four sheets have no home in the current application and are worth adding as
FIG. 8–11, since each supports a claim or an example paragraph:

- delay-value derivation and the distinctness constraint (sheet 6, panel C)
- operating-region don't-care synthesis flow (sheet 10) — supports claim 28
- measured care-set and term counts (sheet 11) — supports ¶[0054]
- the inertial requirement, measured (sheet 12) — supports claim 25 and ¶[0046]

Adding them means four new paragraphs in BRIEF DESCRIPTION OF THE DRAWINGS.

### Annealing material that does not belong here

Sheets 2, 3 and 4 (timing margin as annealing control, programmable inertial
delay element with rejection window, matched-delay completion generator) were
drawn for the annealing disclosure. The rejection-window and matched-delay
content is relevant to this application; the annealing-control framing is not,
and the prior-art review found it substantially anticipated. Recommend keeping
the element drawings and dropping the annealing framing, or splitting the
annealing material into its own disclosure.

---

## The rest of the open items

**[3] Docket number** — `[TO BE ASSIGNED BY UC SAN DIEGO OFFICE OF INNOVATION AND
COMMERCIALIZATION]`. Administrative; the OIC assigns it at filing.

**[28] Note to patent agent on formal drawings** — resolves once the figure set
above is settled. Formal drawings still need a draftsperson; the sheets in this
repository are 37 CFR 1.84-compliant line art but have not been through one.

**[50] Inventor finalization, three parts:**

- *(a) matched-delay sizing methodology and guard-band margin.* Partly answerable
  now. ¶[0048] measures 100% settling out to ±348% delay spread at 3σ, and
  ¶[0049] records that delay values below worst-case combinational propagation
  make the class ordering inoperative. What is still missing is a guard-band
  *number*, which needs a target process.
- *(b) four-phase versus two-phase signalling.* Not determined by anything
  measured. The dual-rail work used a four-phase NULL/DATA protocol because
  monotonicity requires a spacer; if the handshake embodiment is kept, four-phase
  follows from that choice.
- *(c) power-on reset and initialization protocol.* Not addressed anywhere in the
  work. The RTL initialises through an `init_en` port, which is a simulation
  convenience, not a reset protocol.

**[80] IDS** — the supplement is appended rather than merged, so items (1)–(19)
and (20)–(21) read as two lists. Worth consolidating into one numbered list
before filing.

---

## Decisions that are not mine to make

1. **Whether to file at all.** The prior-art conclusion was that the scheduling
   mechanism is not novel. If filing proceeds, the weight sits on claim 25
   (inertial delay realisation) and claim 28 (don't-care synthesis).
2. **Whether the annealing embodiment stays.** Aadit 2022 reports the same
   overclocking effect with a claimed advantage. Narrowing it is Prof. Lin's
   call.
3. **Which figure set the application uses** — the spec's seven, or the expanded
   eleven. The expanded set is better supported by measurement.
