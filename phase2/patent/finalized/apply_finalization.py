#!/usr/bin/env python3
"""Resolve the INVENTOR FINALIZATION bracket.

The bracket is deleted and each of its three items is resolved inside the
paragraph it belongs to, so no paragraph is renumbered:
  (b) signalling discipline      -> appended to [0042]
  (c) reset and initialization   -> appended to [0043]
  (a) matched-delay sizing       -> appended to [0044]

Clean file: text appended, bracket paragraph removed.
Tracked file: the same as tracked changes by author "Finalization"; the
bracket's runs and its paragraph mark are marked deleted.
"""
import copy, sys, itertools
import docx
from docx.oxml.ns import qn

AUTHOR, DATE = "Finalization", "2026-11-18T00:00:00Z"
BRACKET = "[INVENTOR FINALIZATION"

ADD = {
    "0042": (
        " In some embodiments the handshake operates under the four-phase"
        " discipline. In dual-rail embodiments, successive evaluations are"
        " separated by a spacer phase in which both rails of every node output"
        " are deasserted, so that each evaluation proceeds monotonically from"
        " the spacer; the node state is captured while the outputs of the"
        " evaluated class are valid and is written back to the node outputs"
        " only during the following spacer phase, because writing the state"
        " back while the outputs are valid would cause a rail to fall during"
        " evaluation and defeat the monotonicity on which completion detection"
        " relies. In other embodiments the handshake operates under a"
        " two-phase, transition-signaling discipline, in which each transition"
        " of a completion signal, in either direction, denotes completion and"
        " the phase element toggles in response, halving the number of signal"
        " transitions per cycle at the cost of completion detection that"
        " responds to transitions rather than to levels. The claims are not"
        " limited to either discipline."),
    "0043": (
        " Initialization/readout circuitry 112 provides an initialization"
        " signal, which is asserted at power-on, for example by a power-on"
        " reset circuit, until the supply has stabilized, and whenever a new"
        " input pattern is to be loaded. While the initialization signal is"
        " asserted, (i) each node output is forced to the corresponding bit of"
        " the input pattern by an override at the output stage 318 of the node"
        " circuit, bypassing the node function; (ii) each delay element in the"
        " output path of a node circuit, such as the inertial delay element"
        " 316, is held at the loaded value, so that no transition is pending"
        " upon release; (iii) the completion signals DONE_1 518 and DONE_2 516"
        " are held deasserted; (iv) the phase latch 510 is held in the state in"
        " which the phase signal P 520 enables the first update class, the"
        " enable signals EN_1 512 and EN_2 514 both being gated off for the"
        " duration of initialization; and (v) the full-pass quiescence logic"
        " 606 of FIG. 6A is cleared, so that the convergence signal cannot be"
        " asserted until at least one complete pass through all update classes"
        " has occurred after release. Release of the initialization signal is a"
        " single transition. In handshake-sequenced embodiments it enables the"
        " first update class, and evaluation proceeds through the cyclic order;"
        " in delay-differentiated embodiments it releases every node circuit at"
        " once, and the ordering emerges from the delay values. The node outputs"
        " constitute the result when the convergence signal is asserted."),
    "0044": (
        " The matched delay line of each update class is sized so that, at each"
        " characterized operating corner, its delay exceeds the worst-case"
        " settling time of that class by a guard band, the settling time"
        " comprising the delay of the longest sensitizable path through any"
        " node circuit of the class, the interconnect delay to the node circuits"
        " that receive its outputs, and the delay of any delay element in the"
        " node output path. In some embodiments the worst-case settling time of"
        " each class and the delay of one stage of the matched delay line are"
        " determined at each corner by static timing analysis, the number of"
        " stages is selected as the smallest number whose delay exceeds the"
        " settling time at every corner, and that number is increased by the"
        " guard band, which covers local variation not tracked by the matching."
        " In some embodiments the guard band is determined from a statistical"
        " timing analysis of the target process at a selected number of"
        " standard deviations, and in some embodiments it is between 10% and 50%"
        " of the settling time. In further embodiments the matched delay line is"
        " programmable and is calibrated after manufacture in the manner"
        " described above for delay-differentiated embodiments."),
}

_ids = itertools.count(95000)


def mk(tag, **attrs):
    e = docx.oxml.OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k), v)
    return e


def live_runs(p):
    return [r for r in p.iter(qn("w:r"))
            if not any(a.tag == qn("w:del") for a in r.iterancestors())]


def accepted_text(p):
    return "".join(t.text or "" for r in live_runs(p) for t in r.iter(qn("w:t")))


def new_run(src, text, deleted=False):
    r = copy.deepcopy(src)
    for c in list(r):
        if c.tag != qn("w:rPr"):
            r.remove(c)
    rpr = r.find(qn("w:rPr"))
    if rpr is not None:  # never carry a highlight into new body text
        for h in rpr.findall(qn("w:highlight")):
            rpr.remove(h)
    t = mk("w:delText" if deleted else "w:t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    r.append(t)
    return r


def clean(path_in, path_out):
    d = docx.Document(path_in)
    done = []
    for p in d.paragraphs:
        for tag, add in ADD.items():
            if p.text.startswith(f"[{tag}]"):
                p.runs[-1].text = p.runs[-1].text + add
                done.append(tag)
    br = [p for p in d.paragraphs if p.text.startswith(BRACKET)]
    assert len(br) == 1 and sorted(done) == sorted(ADD)
    br[0]._element.getparent().remove(br[0]._element)
    d.save(path_out)


def tracked(path_in, path_out):
    d = docx.Document(path_in)
    body = d.element.body
    paras = list(body.iter(qn("w:p")))
    done = []
    for p in paras:
        t = accepted_text(p)
        for tag, add in ADD.items():
            if t.startswith(f"[{tag}]"):
                last = live_runs(p)[-1]
                ins = mk("w:ins", **{"w:id": str(next(_ids)), "w:author": AUTHOR, "w:date": DATE})
                ins.append(new_run(last, add))
                p.append(ins)
                done.append(tag)
    assert sorted(done) == sorted(ADD), done
    br = [p for p in paras if accepted_text(p).startswith(BRACKET)]
    assert len(br) == 1
    p = br[0]
    for r in live_runs(p):
        dl = mk("w:del", **{"w:id": str(next(_ids)), "w:author": AUTHOR, "w:date": DATE})
        r.addprevious(dl)
        dl.append(r)
        for t in r.findall(qn("w:t")):
            t.tag = qn("w:delText")
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        ppr = mk("w:pPr"); p.insert(0, ppr)
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = mk("w:rPr"); ppr.append(rpr)
    rpr.append(mk("w:del", **{"w:id": str(next(_ids)), "w:author": AUTHOR, "w:date": DATE}))
    d.save(path_out)


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    clean(f"{src}/patent_app_integrated_clean.docx", f"{out}/patent_app_integrated_clean.docx")
    tracked(f"{src}/patent_app_integrated_tracked.docx", f"{out}/patent_app_integrated_tracked.docx")
    print("done")
