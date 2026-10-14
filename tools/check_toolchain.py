#!/usr/bin/env python3
"""
Verify the toolchain actually works, not just that the binaries exist.

Each check runs the real thing on a tiny input. Several hours of this project
were lost to a binary that was present but unusable, or absent entirely after a
container restart, so "which espresso" is not a sufficient test.
"""
import shutil, subprocess, sys, tempfile, os

OK, BAD = "  ok   ", "  FAIL "
fails = []


def check(name, fn):
    try:
        detail = fn()
        print(f"{OK}{name:<22}{detail}")
    except Exception as e:
        print(f"{BAD}{name:<22}{e}")
        fails.append(name)


def py_deps():
    import numpy, matplotlib
    return f"numpy {numpy.__version__}, matplotlib {matplotlib.__version__}"


def iverilog():
    if not shutil.which("iverilog"):
        raise RuntimeError("not on PATH — run 'make setup'")
    d = tempfile.mkdtemp()
    src = os.path.join(d, "t.v")
    open(src, "w").write(
        'module t; initial begin $display("IVOK"); $finish; end endmodule')
    subprocess.run(["iverilog", "-o", os.path.join(d, "t.vvp"), src],
                   check=True, capture_output=True)
    out = subprocess.run(["vvp", os.path.join(d, "t.vvp")],
                         capture_output=True, text=True).stdout
    if "IVOK" not in out:
        raise RuntimeError("compiled but did not run")
    return "compiles and simulates"


def yosys():
    if not shutil.which("yosys"):
        raise RuntimeError("not on PATH — run 'make setup'")
    d = tempfile.mkdtemp()
    src = os.path.join(d, "t.v")
    open(src, "w").write("module t(input a,b,output y); assign y=a&b; endmodule")
    r = subprocess.run(
        ["yosys", "-p", f"read_verilog {src}; synth; stat"],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[-120:])
    return "synthesises"


def espresso():
    exe = shutil.which("espresso") or os.environ.get("ESPRESSO")
    if not exe:
        raise RuntimeError("not on PATH — run 'make setup'")
    d = tempfile.mkdtemp()
    pla = os.path.join(d, "t.pla")
    open(pla, "w").write(".i 2\n.o 1\n.p 3\n00 0\n01 1\n11 1\n.e\n")
    r = subprocess.run([exe, pla], capture_output=True, text=True)
    if r.returncode != 0 or ".p" not in r.stdout:
        raise RuntimeError("ran but produced no cover")
    return "minimises"


def pipeline():
    """The smallest real end-to-end slice: train, colour, schedule, settle."""
    sys.path.insert(0, "phase2/clockless")
    import numpy as np
    from improve_capacity import train_margin_auto
    from scale_study import make_support
    from schedule_hnn import graph_from_W, dsatur
    from pvt_analysis import settle_event_driven
    rng = np.random.default_rng(0)
    N, M = 32, 4
    pats = rng.choice([-1, 1], size=(M, N)).astype(float)
    W, _ = train_margin_auto(pats, make_support(N, 8, "regular", rng), seed=0)
    n, edges = graph_from_W(W)
    col = dsatur(n, edges)
    delays = [(col[i] + 1) * 10 for i in range(N)]
    bad = [(i, j) for i, j in edges if delays[i] == delays[j]]
    if bad:
        raise RuntimeError(f"{len(bad)} coupled pairs share a delay value")
    ok = sum(settle_event_driven(
        rng.integers(0, 2, size=N).astype(np.int8), W, delays)[1]
        for _ in range(20))
    if ok < 20:
        raise RuntimeError(f"only {ok}/20 initial states settled")
    return f"chi={max(col.values())+1}, 20/20 settled, 0 conflicts"


print("Checking toolchain\n")
for name, fn in (("python deps", py_deps), ("iverilog", iverilog),
                 ("yosys", yosys), ("espresso", espresso),
                 ("pipeline (N=32)", pipeline)):
    check(name, fn)

print()
if fails:
    print(f"{len(fails)} check(s) failed: {', '.join(fails)}")
    sys.exit(1)
print("All checks passed.")
