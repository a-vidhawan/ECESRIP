#!/usr/bin/env python3
"""
Revise the patent draft against what has now been measured and read.

Four kinds of edit, kept separable so counsel can accept or reject each:

  CORRECTION   paragraph [0030] presently teaches that the delay elements "may
               exhibit transport delay characteristics". Measured, transport
               semantics reach a fixed point from 1-16% of initial states under
               the identical schedule that inertial semantics carry to 100%. The
               specification therefore teaches an inoperative embodiment, which
               is an enablement problem, and it has to go.
  QUALIFY      [0009]'s "without requiring hazard-free logic synthesis" is too
               strong at gate level; [0006] and [0028] should not read as
               claiming a constraint that the closest art states.
  FILL         the experimental-examples placeholder, with measured results only.
  CLAIMS       promote the two limitations that the art does not reach, and add
               an independent claim to the don't-care synthesis, which is
               presently claimed nowhere.

Claim amendments are proposals for counsel, not filings.
"""
import copy, os, re, shutil, subprocess, sys
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
ET.register_namespace('w', W[1:-1])
SRC = os.path.dirname(os.path.abspath(__file__))
X = os.path.join(SRC, 'x')

tree = ET.parse(os.path.join(X, 'word', 'document.xml'))
root = tree.getroot()
body = root.find(W + 'body')
paras = list(root.iter(W + 'p'))


def settext(p, s):
    """Replace a paragraph's text, keeping its first run's formatting."""
    runs = p.findall(W + 'r')
    if not runs:
        r = ET.SubElement(p, W + 'r'); runs = [r]
    for extra in runs[1:]:
        p.remove(extra)
    r = runs[0]
    for t in list(r):
        if t.tag == W + 't':
            r.remove(t)
    t = ET.SubElement(r, W + 't')
    t.text = s
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')


def clone_after(ref, texts):
    """Insert new paragraphs after `ref`, copying its style."""
    parent = body
    kids = list(parent)
    idx = kids.index(ref) if ref in kids else None
    if idx is None:                       # ref nested; append at end of body
        idx = len(kids) - 1
    out = []
    for k, s in enumerate(texts):
        np_ = copy.deepcopy(ref)
        settext(np_, s)
        parent.insert(idx + 1 + k, np_)
        out.append(np_)
    return out

# ---------------------------------------------------------------- CORRECTIONS

P0006 = ("[0006] Partitioned update scheduling based on graph coloring has been "
 "employed in clocked implementations, including implementations in which "
 "distinct phase-shifted periodic clock signals are supplied to distinct color "
 "groups of stochastic units, and such implementations have been characterized "
 "by their authors as hardware realizations of chromatic Gibbs sampling. Such "
 "implementations retain clock generation and distribution circuitry and rely "
 "on open-loop timing margins fixed by the clock phases and periods. It has "
 "further been reported in such clocked implementations that deliberately "
 "shortening the interval allotted to a color group, so that a subsequent group "
 "evaluates on inputs that have not fully settled, does not necessarily prevent "
 "the network from reaching low-energy states. Conversely, sequencerless "
 "stochastic implementations have been described in which units update "
 "autonomously at random times without any enforced ordering; such "
 "implementations provide no structural guarantee against coupled units acting "
 "on stale values and lack deterministic convergence guarantees. Clockless "
 "recurrent Boolean networks employing per-link programmable delay lines have "
 "also been described, but without partitioning of the nodes and for the "
 "purpose of generating, rather than suppressing, sustained oscillation.")

P0009 = ("[0009] In some embodiments, the sequencing circuitry comprises delay "
 "circuitry establishing different signal propagation delay values for "
 "different update classes, the delay values associated with any two update "
 "classes differing from one another, such that a slower class responds to the "
 "outputs of a faster class only after the faster class has settled. In such "
 "embodiments the delay elements are inertial delay elements, which cancel a "
 "pending output transition when the value of the node circuit's threshold "
 "function reverts before the delay interval has elapsed. As set out in the "
 "Experimental Examples, this cancellation behavior is a requirement of the "
 "scheduling scheme and not merely a refinement of it: under otherwise "
 "identical networks, partitions, delay values and initial states, delay "
 "elements exhibiting transport characteristics reach a fixed point from a "
 "small minority of initial states. In other embodiments, the sequencing "
 "circuitry comprises completion detection circuitry associated with each "
 "update class and handshake circuitry, for example comprising one or more "
 "Muller C-elements, that enables evaluation of a subsequent update class in "
 "response to assertion of a completion signal by a preceding update class, "
 "providing an ordering enforced by causality rather than by timing margin and "
 "therefore robust to process, voltage, and temperature variation. Inertial "
 "delay elements additionally suppress pulses shorter than a rejection window, "
 "whereby hazard-induced glitches arising within a node circuit are "
 "substantially, though not in all cases entirely, prevented from propagating "
 "to other node circuits; residual hazard-induced disagreement measured at gate "
 "level is reported in the Experimental Examples. In some embodiments the "
 "handshake circuitry comprises a state-holding phase element, such as a "
 "generalized Muller C-element, having a set function responsive to completion "
 "of one update class and a reset function responsive to completion of another "
 "update class, the update-class enable signals being derived from the state of "
 "the phase element.")

P0028 = ("[0028] In a first family of embodiments, illustrated in FIG. 4, "
 "sequencing circuitry comprises delay circuitry establishing different signal "
 "propagation delay values for different update classes. Delay elements, for "
 "example buffer chains, current-starved buffers, or programmable delay lines, "
 "are placed in the input paths, the output paths, or within the node circuits "
 "of each class, such that the effective evaluation delay d(k) of class k "
 "differs among classes. The delay values associated with any two update "
 "classes differ from one another; as reported in the Experimental Examples, "
 "the particular values are otherwise immaterial, and partitions in which every "
 "class is assigned the same delay value fail to converge notwithstanding that "
 "the partition is a proper coloring of the interaction graph. In a two-class "
 "embodiment, the delay d(2) of the second class is selected to exceed the "
 "worst-case settling time of the first class, the settling time comprising the "
 "evaluation delay of the first class together with interconnect delay and any "
 "internal ripple time. That a class must settle before a subsequent class "
 "evaluates is a known requirement of color-partitioned updating; what is "
 "provided here is its realization by delay values in the feedback paths of the "
 "node circuits, in a circuit containing no periodic timing reference. Under "
 "this condition, whenever the second class responds to a transition, the first "
 "class has already settled, and conversely the first class, being fast, "
 "settles between successive transitions of the slow class. An alternating, "
 "block-sequential schedule thereby emerges from the delay structure itself, "
 "without any clock, sequencer, or state machine.")

P0030 = ("[0030] The delay elements are inertial delay elements, in which a "
 "pending output transition is cancelled if the value of the node circuit's "
 "threshold function reverts before the delay interval has elapsed, and in "
 "which pulses of duration shorter than a rejection window are suppressed "
 "rather than propagated. The cancellation behavior is required for correct "
 "sequencing and is not merely a hazard-filtering refinement. Because each node "
 "circuit evaluates continuously rather than once per pass, the value of a node "
 "circuit's threshold function may revert after a transition has been scheduled "
 "and before it is committed; a delay element exhibiting transport "
 "characteristics, which reproduces at its output every input feature however "
 "narrow, commits that superseded value onto neighbor node circuits whose "
 "states have since changed. As reported in the Experimental Examples, delay "
 "elements exhibiting transport characteristics reach a fixed point from a "
 "small minority of initial states under a partition and set of delay values "
 "that inertial delay elements carry to a fixed point from every initial state "
 "tested. Where the rejection window is not less than the disturbance interval "
 "of an evaluation phase, comprising the settling window of the preceding "
 "update class together with the internal settling time of the node circuit's "
 "combinational logic, transient hazard pulses generated within the "
 "combinational logic during the arrival of input changes are suppressed by the "
 "delay element, and the node output makes at most one transition per "
 "evaluation phase, to the value of the threshold function evaluated on settled "
 "inputs. The delay element thereby serves simultaneously as sequencing means "
 "and as hazard filtering means. Inertial delay elements may comprise a "
 "resistive-capacitive stage coupled to a hysteretic buffer, a current-starved "
 "buffer, or a digital pulse filter in which a signal is combined with a "
 "delayed replica of itself such that only features persisting longer than the "
 "replica delay propagate. In some embodiments the pulse filter is constructed "
 "from logic cells of the same type as the node circuit logic, whereby the "
 "rejection window tracks the settling time of the logic across process, "
 "voltage, and temperature variation. If operating conditions cause the "
 "disturbance interval to exceed the rejection window, escaping transitions "
 "constitute transient perturbations of the network state that are absorbed by "
 "the attractor dynamics as described herein, such that the circuit degrades "
 "toward stochastic convergence rather than malfunction.")

settext(paras[13], P0006)
settext(paras[17], P0009)
settext(paras[43], P0028)
settext(paras[45], P0030)
print("corrections applied")

# ------------------------------------------------------- EXPERIMENTAL EXAMPLES

EX = [
"Experimental Examples",
"[0041] The following examples report measurements obtained by register-transfer "
"and gate-level simulation of circuits produced by the methods described herein, "
"using Icarus Verilog for simulation, Yosys for technology-independent mapping, "
"and the Berkeley espresso program for two-level minimization. No integrated "
"circuit has been fabricated, and no results herein are obtained from silicon. "
"Where a quantity was estimated rather than measured, that is stated. Stored "
"patterns are random bipolar vectors unless otherwise noted.",

"[0042] Chromatic number of the interaction graph. For a network of N = 16 node "
"circuits sparsified to maximum fan-in, the interaction graph contained 43 edges "
"at a density of 35.8% and required six update classes. Partitioning the same "
"graph by parity of node index, rather than by proper coloring, left 19 of the "
"43 coupled pairs within a common class, or 44.2%; the highest-degree node, of "
"degree 11, shared a class with six of its eleven neighbors.",

"[0043] Scaling of the number of update classes. Interaction graphs obtained by "
"the sparsification and retraining method of FIG. 7 required four, five and six "
"update classes at N = 256, N = 1024 and N = 4096 respectively. The number of "
"update classes therefore does not grow appreciably with network size for "
"interaction graphs of bounded degree, and the schedule costs O(N) storage and a "
"number of distinct delay values equal to the number of classes.",

"[0044] Necessity of distinct delay values. Circuits were constructed in which "
"the partition was a proper coloring of the interaction graph and every update "
"class was assigned the same delay value. Such circuits satisfy every "
"graph-theoretic requirement of the partition and reached a fixed point from "
"none of the initial states tested. Circuits in which the same partition was "
"assigned distinct delay values reached a fixed point from every initial state "
"tested. Circuits partitioned by parity, with distinct delay values, likewise "
"reached a fixed point from none of the initial states tested. The operative "
"requirement is therefore on the delay values associated with the classes, and "
"a proper coloring alone is not sufficient.",

"[0045] Insensitivity to the particular delay values. Five families of delay "
"values were compared on identical networks and initial states: consecutive "
"integer multiples of a common scale factor; powers of two times that factor; "
"prime multiples of that factor; prime multiples offset so as to be mutually "
"coprime; and values in an irrational ratio. At N = 16, N = 32 and N = 64 all "
"five families reached a fixed point from 100% of random initial states. The "
"particular values are therefore immaterial provided that the values associated "
"with any two classes differ.",

"[0046] Necessity of inertial delay characteristics. Circuits identical in "
"network, partition, delay values and initial states were simulated with delay "
"elements exhibiting inertial characteristics, in which a pending transition is "
"cancelled when the value of the node circuit's threshold function reverts "
"before the delay interval elapses, and with delay elements exhibiting transport "
"characteristics, in which every scheduled transition is delivered. The fraction "
"of random initial states reaching a fixed point was 100% for inertial delay "
"elements at every size tested, against 1% at N = 16, 16% at N = 32, 15% at "
"N = 64 and 7% at N = 128 for transport delay elements. Transport delay "
"elements were separately observed to reach a fixed point from all initial "
"states within Hamming distance five of a stored pattern in a sparse network of "
"N = 256 with four update classes and four stored patterns; the failure of "
"transport delay elements is therefore most pronounced for initial states remote "
"from a stored pattern and for interaction graphs of higher density.",

"[0047] Register-transfer verification at N = 256. A network of 256 node "
"circuits with maximum fan-in 16 and four stored patterns was compiled to "
"synthesizable register-transfer description by the method of FIG. 7, yielding "
"12,357 product terms across 256 node circuits, and simulated over 240 input "
"vectors at Hamming distances of zero, one, three and five from a stored "
"pattern. Every vector reached a fixed point and every fixed point was the "
"intended stored pattern. The interaction graph required four update classes and "
"contained no pair of coupled node circuits sharing a delay value.",

"[0048] Tolerance to delay variation. Independent random perturbation was "
"applied to each node circuit's delay value. The fraction of initial states "
"reaching a fixed point remained at 100% for perturbations up to 348% of the "
"nominal delay value at three standard deviations. Separately, applying such "
"variation to a degenerate schedule in which all classes had been assigned the "
"same nominal delay value raised the fraction reaching a fixed point from 67% to "
"100%, because continuous variation renders nominally equal delays distinct with "
"probability one. The condition to be avoided in layout is therefore delay "
"values made equal by construction, as would result from identical buffer chains.",

"[0049] Sizing of the delay values relative to combinational propagation. "
"Circuits in which the delay values were smaller than the worst-case "
"combinational propagation delay through a node circuit's own logic did not "
"observe the intended class ordering, commits interleaving in an order the delay "
"values no longer determined. Increasing the delay values relative to the "
"combinational propagation delay restored the intended ordering. That a class "
"must settle before a subsequent class evaluates is a known requirement of "
"color-partitioned updating and is not presented here as novel; what is reported "
"is the measured consequence of violating it in a delay-sequenced realization.",

"[0050] Residual hazards at gate level. Node circuit logic was mapped to "
"primitive gates, each gate type assigned a distinct propagation delay so that "
"path lengths through the two-level realization were unequal, and simulated "
"against a logically equivalent zero-delay model. With delay elements exhibiting "
"transport characteristics, the settled state agreed with the zero-delay model "
"on 88% of inputs at N = 32. With inertial delay elements the settled state was "
"a fixed point of the implemented logic on 100% of inputs at N = 32 across "
"rejection windows spanning a sixteen-fold range. The statement that hazard-free "
"logic synthesis is not required is therefore supported for inertial delay "
"elements at the sizes tested, and is qualified accordingly.",

"[0051] Delay-insensitive embodiment. A dual-rail realization with Muller "
"C-element completion detection, as described in connection with FIG. 5, "
"reached a fixed point of the implemented logic on 100% of inputs at every size "
"tested, at 2.03 times the gate count of the corresponding single-rail "
"realization and approximately four times the settling latency. The same "
"dual-rail realization with the partition removed, so that every node circuit "
"was committed on each handshake, failed to converge. Completion detection and "
"partitioning are therefore complementary rather than alternative: a C-element "
"prevents a node circuit from acting on inputs that have not settled, and does "
"not prevent two coupled node circuits from acting on the same stale state.",

"[0052] Interaction of dual-rail encoding with incompletely specified logic. "
"Where the true-rail and false-rail functions of a node circuit were minimized "
"independently against a common set of unspecified input combinations, input "
"combinations arose that were covered by neither rail, both rails remained low, "
"and completion detection did not assert. Completion detection requires the "
"on-set and off-set to partition the input space, whereas leaving input "
"combinations unspecified exists precisely to avoid committing to such a "
"partition. In embodiments described herein the false-rail function is instead "
"obtained from the true-rail cover by De Morgan's laws, which requires no "
"inverting element because the complement of a rail is the other rail of the "
"same pair, and which cannot disagree with the true rail.",

"[0053] Storage and recall. Coupling weights obtained by margin-based retraining "
"under a sparsity mask stored all patterns with recall of at least 95% at a "
"loading of M/N = 0.5, for example at N = 64 with M = 32 and at N = 128 with "
"M = 64, against a loading of approximately 0.138 for the classical outer-product "
"rule; recall collapsed beyond a loading of approximately 0.6. Tolerance to "
"corruption of the input pattern improved with network size, recall of at least "
"90% extending to 5% of bits corrupted at N = 64, 16% at N = 128 and 19% at "
"N = 256. The retraining procedure is a perceptron-type rule of a known kind, "
"adapted to a masked symmetric weight matrix.",

"[0054] Synthesis using operating-region don't-cares. For node circuits of "
"fan-in 16, specifying the Boolean function only on the projection of the "
"operating region required 2,768 input combinations against 65,536 for the "
"complete table, and two-level minimization yielded 31 to 54 product terms "
"against 627 to 2,918 for the completely specified function. At fan-in 24 and "
"fan-in 32 the care set comprised 9,300 and 21,956 input combinations against "
"complete tables of 16,777,216 and 4,294,967,296 combinations respectively, for "
"which the completely specified function could not be enumerated at all. The "
"care set is derived in closed form from the operating region as the product of "
"the number of stored patterns and the sum of binomial coefficients C(d,k) for k "
"not exceeding the radius h, and is therefore polynomial in the fan-in where the "
"complete table is exponential. Behavior on input combinations outside the "
"operating region is unspecified; agreement with the exact threshold network on "
"uniformly random states was 2%, which is immaterial for recall from within the "
"operating region and material for adversarially chosen inputs.",

"[0055] Optimization use. Applied to maximum-cut instances on random graphs by "
"setting the coupling weights to the negated adjacency matrix, the circuit "
"reached a fixed point on 100% of instances and attained 99.4% to 99.5% of the "
"best cut weight found by any method tested, at between 60 and 99 times lower "
"simulated cost than single-flip simulated annealing given equal restarts. A "
"fixed point of the network is a locally optimal cut; no claim of asymptotic "
"advantage is made.",
]

placeholder = paras[62]
clone_after(placeholder, EX)
body.remove(placeholder) if placeholder in list(body) else None
# the concluding paragraph was [0041]; the examples now occupy [0041]-[0055]
_concl = "".join(t.text or "" for t in paras[64].iter(W + 't'))
settext(paras[64], _concl.replace("[0041]", "[0056]", 1))
print("experimental examples inserted")

# ------------------------------------------------------------------- CLAIMS
# Proposals for counsel. Two limitations are promoted because they are the ones
# the closest art does not reach -- distinctness of the delay VALUES, and the
# cancellation behavior of an inertial delay element, which a phase-shifted
# clock cannot supply because a clocked node samples at an edge and never
# observes a transition that appeared and disappeared between edges. A third
# independent claim is added to the don't-care synthesis, which the present
# claim set does not reach at all.

C1 = ("1. An integrated circuit comprising: a plurality of node circuits, each "
 "node circuit configured to produce a binary output according to a Boolean "
 "threshold function of a plurality of binary inputs; a recurrent "
 "interconnection network coupling outputs of the node circuits to inputs of "
 "other node circuits so as to define an interaction graph containing at least "
 "one cycle, wherein the plurality of node circuits is partitioned into a "
 "plurality of update classes such that no two node circuits belonging to a "
 "same update class are directly coupled to one another in the interaction "
 "graph; and sequencing circuitry configured to enforce, in the absence of any "
 "clock signal, an update ordering among the update classes in which a settled "
 "output value of a node circuit of a second update class is responsive to "
 "outputs of node circuits of a first update class only after the node circuits "
 "of the first update class have settled to stable values, the update ordering "
 "being conditioned on signal propagation and settlement rather than on any "
 "periodic timing reference, and the sequencing circuitry being further "
 "configured such that no two node circuits directly coupled to one another in "
 "the interaction graph commit output transitions concurrently.")

C2 = ("2. The integrated circuit of claim 1, wherein the sequencing circuitry "
 "comprises delay circuitry establishing different respective signal "
 "propagation delay values for different update classes, the delay value "
 "associated with any update class differing from the delay value associated "
 "with every other update class, and a propagation delay value associated with "
 "the second update class exceeding a settling time of the first update class.")

C22 = ("22. The integrated circuit of claim 2, wherein the delay circuitry "
 "comprises, for each node circuit, an inertial delay element configured to "
 "cancel a pending output transition of that node circuit when the value of the "
 "node circuit's threshold function reverts before the delay value has elapsed, "
 "and to suppress propagation of pulses of duration shorter than a rejection "
 "window, the rejection window being not less than a disturbance interval "
 "comprising the settling time of a preceding update class, whereby a "
 "superseded value is not committed to node circuits coupled to that node "
 "circuit and an output of the node circuit makes at most one transition per "
 "evaluation phase.")

NEW = [
"25. An integrated circuit comprising: a plurality of node circuits, each node "
"circuit comprising combinational logic configured to produce a binary value "
"according to a Boolean threshold function of a plurality of binary inputs; a "
"recurrent interconnection network coupling outputs of the node circuits to "
"inputs of other node circuits so as to define an interaction graph containing "
"at least one cycle, the node circuits being partitioned into a plurality of "
"update classes such that no two node circuits belonging to a same update class "
"are directly coupled to one another in the interaction graph; and, for each "
"node circuit, a delay element coupled between an output of the combinational "
"logic of that node circuit and the recurrent interconnection network, wherein "
"the delay elements of node circuits belonging to different update classes have "
"different respective delay values, wherein each delay element is an inertial "
"delay element configured to cancel a pending output transition when the value "
"produced by the combinational logic reverts before the delay value of that "
"delay element has elapsed, and wherein the integrated circuit contains no "
"periodic timing reference governing the update ordering.",

"26. The integrated circuit of claim 25, wherein each delay value exceeds a "
"worst-case propagation delay through the combinational logic of the node "
"circuit with which the delay element is associated.",

"27. The integrated circuit of claim 25, wherein the delay values are "
"programmable, and further comprising control circuitry configured to vary at "
"least one of the delay values and a rejection window of at least one of the "
"delay elements during operation according to a schedule.",

"28. A method of producing an asynchronous logic circuit implementing a "
"recurrent threshold-logic network, the method comprising: obtaining coupling "
"weights and thresholds of the network and a plurality of target states of the "
"network; defining an operating region comprising those states of the network "
"within a specified Hamming distance of a target state; for each node circuit, "
"determining a care set consisting of the projections of the states of the "
"operating region onto the inputs to which that node circuit is coupled; "
"specifying a Boolean function of that node circuit on the input combinations "
"of the care set and leaving the Boolean function unspecified on input "
"combinations outside the care set; minimizing the resulting incompletely "
"specified Boolean function to obtain a two-level logic realization; and "
"realizing the node circuit as the two-level logic realization interconnected "
"in a recurrent interconnection network.",

"29. The method of claim 28, wherein the care set is determined in closed form "
"as a product of a number of the target states and a sum of binomial "
"coefficients C(d,k) over values of k not exceeding the specified Hamming "
"distance, d being a number of inputs to which the node circuit is coupled, "
"whereby a size of the care set is polynomial in d.",

"30. The method of claim 28, wherein the care set is determined from the "
"specified Hamming distance without sampling activations of the network.",

"31. The method of claim 28, further comprising partitioning the node circuits "
"into update classes by proper vertex coloring of an interaction graph of the "
"network and associating a different respective delay value with each update "
"class.",
]

settext(paras[68], C1)
settext(paras[69], C2)
settext(paras[89], C22)
clone_after(paras[91], NEW)          # after claim 24

IDS_ADD = (" [SUPPLEMENT, from full-text review of four references by the "
 "co-inventor: (20) Nikhar, Kannan, Aadit, Chowdhury & Camsari, 'All-to-all "
 "reconfigurability with sparse and higher-order Ising machines,' Nat. Commun. "
 "15:8977 (2024) - discloses phase-shifted 'colored' clocks selected by a clock "
 "multiplexer, six phase-shifted clocks for a six-coloring, and describes the "
 "architecture as an 'asynchronous p-computer'; the word 'delay' does not appear "
 "in the reference. (21) Wang, Wu & Roychowdhury, 'Late Breaking Results: New "
 "Computational Results and Hardware Prototypes for Oscillator-based Ising "
 "Machines,' DAC 2019 - CMOS oscillator Ising machines of up to 240 spins with "
 "no clock; material to the clockless limitation. NOTE: reference (1) states at "
 "page 2 that 'the MAC must finish its computation before the next color block "
 "is updated,' which is the sizing constraint of Example [0049], and further "
 "reports that updating color blocks before completion ('overclocking') can be "
 "advantageous, which is material to the annealing embodiment. Reference (1) "
 "also characterizes itself as 'a low level hardware-level implementation of "
 "chromatic Gibbs sampling.' Counsel should assume these passages will be "
 "found.]")
_ids = "".join(t.text or "" for t in paras[65].iter(W + 't'))
settext(paras[65], _ids + IDS_ADD)

ABS = ("A clockless circuit implements a recurrent network of Boolean "
 "threshold-logic node circuits. The node circuits are partitioned into update "
 "classes forming independent sets of the network's interaction graph, so that "
 "node circuits within a class may evaluate concurrently without interacting. "
 "Sequencing circuitry enforces, without any clock signal, an ordering in which "
 "each update class settles before another update class responds, by associating "
 "a different delay value with each update class or by per-class completion "
 "detection with handshake circuitry. In delay-sequenced embodiments the delay "
 "elements are inertial, cancelling a pending transition whose cause has "
 "reverted, so that a superseded value is never committed to coupled node "
 "circuits. The aggregate evolution is equivalent to a block-sequential update "
 "schedule, guaranteeing convergence to a fixed point for symmetric coupling "
 "weights while avoiding the oscillation associated with simultaneous update of "
 "coupled nodes. Convergence detection circuitry asserts a done signal upon "
 "electrical quiescence across a full pass of the classes. Embodiments include "
 "bipartite two-class networks, population-count node circuits for binary "
 "weights, dual-rail delay-insensitive node circuits, and content-addressable "
 "associative memories, together with methods of compiling trained networks into "
 "such circuits using don't-care conditions derived from a bounded operating "
 "region.")
settext(paras[93], ABS)

tree.write(os.path.join(X, 'word', 'document.xml'),
           xml_declaration=True, encoding='UTF-8')
out = os.path.join(SRC, 'patent_draft_revised.docx')
if os.path.exists(out):
    os.remove(out)
subprocess.run(['zip', '-q', '-r', '-X', out, '.'], cwd=X, check=True)
print("wrote", out)
