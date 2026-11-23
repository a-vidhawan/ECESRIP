#!/usr/bin/env python3
"""Close the don't-care gap: one Summary sentence, claim 1 and claim 18
wording, and new dependent claims 25 to 27.

Clean file: plain edits. Tracked file: the same as tracked changes by author
"Claims and summary"; the new claims are inserted paragraphs.
"""
import copy, sys, itertools
import docx
from docx.oxml.ns import qn

AUTHOR, DATE = "Claims and summary", "2026-11-23T00:00:00Z"

REPLACE = [  # (paragraph start, old, new)
    ("[0010]",
     "substantially reducing the logic cost of each node circuit.",
     "substantially reducing the logic cost of each node circuit. In other "
     "embodiments each threshold function is realized as a two-level "
     "sum-of-products network obtained by minimizing an incompletely specified "
     "Boolean function, the function being specified only on the combinations "
     "of node inputs arising within an operating region of the network, such as "
     "the network states within a bounded Hamming distance of a stored pattern, "
     "and left unspecified elsewhere, the care set being enumerated directly by "
     "complementing up to that distance of the input bits in the projection of "
     "each stored pattern onto the node inputs rather than by sampling network "
     "states, whereby the coupling weights are consumed at design time and no "
     "arithmetic is performed during operation."),
    ("1. ",
     "according to a Boolean threshold function of a plurality of binary inputs;",
     "according to a Boolean threshold function of a plurality of binary inputs, "
     "at least for combinations of the binary inputs arising within an operating "
     "region of the integrated circuit;"),
    ("18. ",
     "combinational logic implementing a Boolean threshold function defined by "
     "the retrained coupling weights and threshold of that node;",
     "combinational logic implementing, at least for combinations of node inputs "
     "arising within an operating region of the network, a Boolean threshold "
     "function defined by the retrained coupling weights and threshold of that "
     "node;"),
]

NEW_CLAIMS = [
    "25. The integrated circuit of claim 1, wherein the operating region "
    "comprises states of the node circuits within a bounded Hamming distance of "
    "at least one stored pattern, and wherein at least one node circuit "
    "comprises a two-level sum-of-products network minimized from an "
    "incompletely specified Boolean function that is specified, for the "
    "combinations of the binary inputs of that node circuit arising within the "
    "operating region, to agree with the Boolean threshold function of that "
    "node circuit, and is unspecified for other combinations.",
    "26. The method of claim 18, wherein the operating region comprises states "
    "of the network within a bounded Hamming distance of at least one stored "
    "pattern, and wherein synthesizing comprises, for each node: determining a "
    "care set consisting of the combinations of node inputs arising within the "
    "operating region; specifying the Boolean threshold function of that node "
    "only on the care set, all other combinations of node inputs being left "
    "unspecified; and minimizing the resulting incompletely specified Boolean "
    "function to a two-level sum-of-products network.",
    "27. The method of claim 26, wherein determining the care set comprises "
    "enumerating, for each stored pattern, the projection of that stored "
    "pattern onto the inputs of the node with every combination of at most the "
    "bounded Hamming distance of those inputs complemented, whereby the care "
    "set is determined without sampling states of the network.",
]
AFTER_CLAIM = "24. "

_ids = itertools.count(97000)


def mk(tag, **attrs):
    e = docx.oxml.OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k), v)
    return e


def rev(tag):
    return mk(tag, **{"w:id": str(next(_ids)), "w:author": AUTHOR, "w:date": DATE})


def live(p):
    return [r for r in p.iter(qn("w:r"))
            if not any(a.tag == qn("w:del") for a in r.iterancestors())]


def text_of(p):
    return "".join(t.text or "" for r in live(p) for t in r.iter(qn("w:t")))


def run_like(src, text, deleted=False):
    r = copy.deepcopy(src)
    for c in list(r):
        if c.tag != qn("w:rPr"):
            r.remove(c)
    t = mk("w:delText" if deleted else "w:t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    r.append(t)
    return r


def clean(pin, pout):
    d = docx.Document(pin)
    for start, old, new in REPLACE:
        ps = [p for p in d.paragraphs if p.text.startswith(start) and old in p.text]
        assert len(ps) == 1, start
        rs = [r for r in ps[0].runs if old in r.text]
        assert len(rs) == 1, start
        rs[0].text = rs[0].text.replace(old, new)
    anchor = [p for p in d.paragraphs if p.text.startswith(AFTER_CLAIM)]
    assert len(anchor) == 1
    prev = anchor[0]._element
    for c in NEW_CLAIMS:
        np_ = copy.deepcopy(prev)
        for ch in list(np_):
            if ch.tag != qn("w:pPr"):
                np_.remove(ch)
        np_.append(run_like(anchor[0].runs[0]._element, c))
        prev.addnext(np_)
        prev = np_
    d.save(pout)


def tracked(pin, pout):
    d = docx.Document(pin)
    body = d.element.body
    paras = list(body.iter(qn("w:p")))
    for start, old, new in REPLACE:
        ps = [p for p in paras if text_of(p).startswith(start) and old in text_of(p)]
        assert len(ps) == 1, start
        rs = [r for r in live(ps[0]) if old in "".join(t.text or "" for t in r.iter(qn("w:t")))]
        assert len(rs) == 1 and rs[0].getparent().tag == qn("w:p"), start
        r = rs[0]
        txt = "".join(t.text or "" for t in r.iter(qn("w:t")))
        i = 0
        while i < min(len(old), len(new)) and old[i] == new[i]:
            i += 1
        j = 0
        while j < min(len(old), len(new)) - i and old[-1 - j] == new[-1 - j]:
            j += 1
        k = txt.index(old)
        before = txt[:k + i]
        gone = old[i:len(old) - j]
        add = new[i:len(new) - j]
        after = txt[k + len(old) - j:]
        parts = [run_like(r, before)]
        if gone:
            dl = rev("w:del"); dl.append(run_like(r, gone, deleted=True)); parts.append(dl)
        ins = rev("w:ins"); ins.append(run_like(r, add)); parts.append(ins)
        if after:
            parts.append(run_like(r, after))
        for el in parts:
            r.addprevious(el)
        r.getparent().remove(r)
    anchor = [p for p in paras if text_of(p).startswith(AFTER_CLAIM)]
    assert len(anchor) == 1
    src_run = live(anchor[0])[0]
    prev = anchor[0]
    for c in NEW_CLAIMS:
        np_ = mk("w:p")
        ppr = anchor[0].find(qn("w:pPr"))
        ppr = copy.deepcopy(ppr) if ppr is not None else mk("w:pPr")
        rpr = ppr.find(qn("w:rPr"))
        if rpr is None:
            rpr = mk("w:rPr"); ppr.append(rpr)
        rpr.append(rev("w:ins"))  # inserted paragraph mark
        np_.append(ppr)
        ins = rev("w:ins"); ins.append(run_like(src_run, c)); np_.append(ins)
        prev.addnext(np_)
        prev = np_
    d.save(pout)


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    clean(f"{src}/patent_app_integrated_clean.docx", f"{out}/patent_app_integrated_clean.docx")
    tracked(f"{src}/patent_app_integrated_tracked.docx", f"{out}/patent_app_integrated_tracked.docx")
    print("done")
