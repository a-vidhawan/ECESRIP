#!/usr/bin/env python3
"""
Drawing primitives for patent figures.

Constrained by 37 CFR 1.84: black ink on white, no colour, no greyscale fills,
no photographs. Distinctions that would normally be carried by colour -- which
colour class a node belongs to -- have to be carried by hatching or by an
explicit label instead. Everything is vector so it survives the PTO's scan and
reprint at any size.

Page is US Letter; drawing coordinates are 0..100 across and 0..130 down the
page, which makes one unit almost exactly square.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow, Polygon, Circle, Rectangle
from matplotlib.lines import Line2D

W, H = 100.0, 130.0
LW = 1.1                      # body line weight
TH = 0.7                      # thin (lead lines, hatching)
FS = 7.4                      # body text
FN = 7.4                      # reference numeral


def page(title=None):
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_axes([0.055, 0.045, 0.89, 0.91])
    ax.set_xlim(0, W); ax.set_ylim(0, H)
    ax.set_aspect("equal"); ax.axis("off")
    if title:
        ax.text(W / 2, H - 2, title, ha="center", va="top",
                fontsize=8.6, weight="bold")
    return fig, ax


def finish(fig, ax, n, out):
    ax.text(W / 2, 1.5, f"FIG. {n}", ha="center", va="bottom",
            fontsize=13, weight="bold")
    fig.savefig(f"{out}/fig{n:02d}.pdf")
    fig.savefig(f"{out}/fig{n:02d}.png", dpi=170)
    plt.close(fig)


def box(ax, x, y, w, h, text="", fs=FS, dashed=False, hatch=None, lw=LW,
        va_pad=0.0):
    ax.add_patch(Rectangle((x, y), w, h, fill=False, lw=lw,
                           linestyle="--" if dashed else "-", hatch=hatch,
                           edgecolor="k"))
    if text:
        ax.text(x + w / 2, y + h / 2 + va_pad, text, ha="center", va="center",
                fontsize=fs, linespacing=1.35)
    return (x, y, w, h)


def rounded(ax, x, y, w, h, text="", fs=FS):
    """Terminator shape for flowchart start/end."""
    from matplotlib.patches import FancyBboxPatch
    ax.add_patch(FancyBboxPatch((x + h / 2, y), w - h, h,
                                boxstyle=f"round,pad=0,rounding_size={h/2}",
                                fill=False, lw=LW, edgecolor="k"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            linespacing=1.35)


def diamond(ax, cx, cy, w, h, text="", fs=FS):
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy),
                          (cx, cy - h / 2), (cx - w / 2, cy)],
                         fill=False, lw=LW, edgecolor="k"))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            linespacing=1.3)


def arrow(ax, pts, head=True, lw=LW, dashed=False, both=False):
    """Orthogonal polyline with an arrowhead on the last segment.

    Routing is done by giving explicit waypoints rather than letting anything
    auto-route: the original figures crossed their own signal lines in several
    places, which a draftsperson would reject.
    """
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ax.add_line(Line2D(xs, ys, lw=lw, color="k", solid_capstyle="round",
                       linestyle="--" if dashed else "-"))
    if head:
        _head(ax, pts[-2], pts[-1], lw)
    if both:
        _head(ax, pts[1], pts[0], lw)


def _head(ax, a, b, lw=LW, size=1.6):
    import numpy as np
    d = np.array(b, float) - np.array(a, float)
    n = np.hypot(*d)
    if n == 0:
        return
    d /= n
    p = np.array([-d[1], d[0]])
    tip = np.array(b, float)
    ax.add_patch(Polygon([tip, tip - d * size * 1.9 + p * size * 0.72,
                          tip - d * size * 1.9 - p * size * 0.72],
                         closed=True, facecolor="k", edgecolor="k", lw=0))


def numeral(ax, n, tx, ty, ax_, ay_, fs=FN):
    """Reference numeral with a lead line, drawn the way the PTO expects:
    the numeral sits clear of the drawing and a straight lead touches the
    feature it identifies."""
    ax.add_line(Line2D([tx, ax_], [ty, ay_], lw=TH, color="k"))
    ax.text(tx, ty, str(n), fontsize=fs, style="italic",
            ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none"))


def label(ax, x, y, s, fs=FS, ha="center", va="center", it=False, box_=False):
    ax.text(x, y, s, fontsize=fs, ha=ha, va=va, linespacing=1.35,
            style="italic" if it else "normal",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none")
            if box_ else None)


def waveform(ax, x0, x1, y, segs, amp=2.6, lw=LW):
    """Digital waveform. `segs` is [(t_fraction, level 0/1), ...] giving the
    level that begins at that fraction of the span."""
    pts = []
    for k, (t, lv) in enumerate(segs):
        xx = x0 + (x1 - x0) * t
        if pts:
            pts.append((xx, pts[-1][1]))
        pts.append((xx, y + amp * lv))
    pts.append((x1, pts[-1][1]))
    ax.add_line(Line2D([p[0] for p in pts], [p[1] for p in pts], lw=lw,
                       color="k", solid_capstyle="butt"))
