#!/usr/bin/env python3
"""Apply the round-2 edits to the clean and tracked applications.

Clean: plain text replacement inside the one run that holds each phrase.
Tracked: the same edits as tracked changes by author "Round 2". Each target
lies inside an earlier w:ins, so the deleted words become a w:del nested in
that w:ins (what Word itself writes when one reviewer deletes another's
insertion), and the new words go in a sibling w:ins between the two halves
of the split parent.
"""
import copy, sys, itertools
import docx
from docx.oxml.ns import qn

AUTHOR, DATE = "Round 2", "2026-11-15T00:00:00Z"

EDITS = [  # (paragraph tag, old, new)
    ("0051",
     "synthesizing the threshold functions to a gate-level netlist 714;",
     "synthesizing the threshold functions to a gate-level netlist 714, in some "
     "embodiments each threshold function being specified only over the input "
     "combinations arising within an operating region of the network, the "
     "remaining combinations being left unspecified, and minimized as an "
     "incompletely specified Boolean function to two-level sum-of-products logic;"),
    ("0057",
     "all 2,784 initial states within Hamming distance three of a stored pattern",
     "all of the 2,784 initial states at a Hamming distance of one to three from "
     "each of the four stored patterns (4 × 696)"),
    ("0058",
     "The connectivity support was restricted to a degree bound of 16, so that each node circuit had",
     "Each node circuit had"),
    ("0060",
     "each storing M = 4 patterns with a degree bound of 24 and retrained on that support",
     "each constructed with a random connectivity support of degree twenty-four "
     "and four random stored patterns, the weights being fitted by masked least "
     "squares on that support and then symmetrized"),
]


def minimal(old, new):
    """Shrink a replacement to the span that actually differs (whole words)."""
    i = 0
    while i < min(len(old), len(new)) and old[i] == new[i]:
        i += 1
    while i > 0 and old[i - 1] != " ":
        i -= 1
    j = 0
    while j < min(len(old), len(new)) - i and old[-1 - j] == new[-1 - j]:
        j += 1
    while j > 0 and old[len(old) - j] not in " ,;":
        j -= 1
    return i, old[i:len(old) - j], new[i:len(new) - j]


def accepted_text(p):
    out = []
    for r in p.iter(qn("w:r")):
        if any(a.tag == qn("w:del") for a in r.iterancestors()):
            continue
        out.extend(t.text or "" for t in r.iter(qn("w:t")))
    return "".join(out)


def apply_clean(path_in, path_out):
    d = docx.Document(path_in)
    log = []
    for tag, old, new in EDITS:
        hits = [p for p in d.paragraphs if p.text.startswith(f"[{tag}]")]
        assert len(hits) == 1, tag
        runs = [r for r in hits[0].runs if old in r.text]
        assert len(runs) == 1 and hits[0].text.count(old) == 1, tag
        runs[0].text = runs[0].text.replace(old, new)
        log.append(tag)
    d.save(path_out)
    return log


_ids = itertools.count(90000)


def mk(tag, **attrs):
    e = docx.oxml.OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k), v)
    return e


def run_with(src_run, text, deleted=False):
    r = copy.deepcopy(src_run)
    for c in list(r):
        if c.tag != qn("w:rPr"):
            r.remove(c)
    t = mk("w:delText" if deleted else "w:t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    r.append(t)
    return r


def apply_tracked(path_in, path_out):
    d = docx.Document(path_in)
    body = d.element.body
    for tag, old, new in EDITS:
        ps = [p for p in body.iter(qn("w:p")) if accepted_text(p).startswith(f"[{tag}]")]
        assert len(ps) == 1, tag
        off, dold, dnew = minimal(old, new)
        # find the live run whose single w:t contains the full old phrase
        target = None
        for r in ps[0].iter(qn("w:r")):
            if any(a.tag == qn("w:del") for a in r.iterancestors()):
                continue
            ts = list(r.iter(qn("w:t")))
            if len(ts) == 1 and old in (ts[0].text or ""):
                target = r
        assert target is not None, f"{tag}: phrase not in a single run"
        text = target.find(qn("w:t")).text
        k = text.index(old) + off
        before, gone, after = text[:k], dold, text[k + len(dold):]
        parent = target.getparent()
        pieces = []
        if before:
            pieces.append(run_with(target, before))
        if gone:
            dl = mk("w:del", **{"w:id": str(next(_ids)), "w:author": AUTHOR, "w:date": DATE})
            dl.append(run_with(target, gone, deleted=True))
            pieces.append(dl)
        ins_new = mk("w:ins", **{"w:id": str(next(_ids)), "w:author": AUTHOR, "w:date": DATE})
        ins_new.append(run_with(target, dnew))
        tail = run_with(target, after) if after else None

        idx = list(parent).index(target)
        parent.remove(target)
        for n, el in enumerate(pieces):
            parent.insert(idx + n, el)
        if parent.tag == qn("w:ins"):
            # split the earlier insertion around our insertion
            rest = list(parent)[idx + len(pieces):]
            gp = parent.getparent()
            pos = list(gp).index(parent)
            gp.insert(pos + 1, ins_new)
            second = copy.deepcopy(parent)
            for c in list(second):
                second.remove(c)
            second.set(qn("w:id"), str(next(_ids)))
            if tail is not None:
                second.append(tail)
            for c in rest:
                second.append(c)
            if len(second):
                gp.insert(pos + 2, second)
        else:
            parent.insert(idx + len(pieces), ins_new)
            if tail is not None:
                parent.insert(idx + len(pieces) + 1, tail)
    d.save(path_out)


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    print("clean:", apply_clean(f"{src}/app_clean.docx", f"{out}/patent_app_integrated_clean.docx"))
    apply_tracked(f"{src}/app_tracked.docx", f"{out}/patent_app_integrated_tracked.docx")
    print("tracked: done")
