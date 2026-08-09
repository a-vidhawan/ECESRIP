"""M-sweep, tractable version.

Care radius h=2 instead of 3 shrinks the care set ~7.7x so espresso finishes in
reasonable time. h=2 FAVOURS the HNN -- fewer care rows means fewer product terms
means less area -- and it does not change the CAM at all. So if the HNN still
loses here, the conclusion is conservative rather than rigged.
"""
import os, sys, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
from gen_dc_pla import build_net, care_rows, write_pla
from verify_dc_recall import espresso_sop
from rtl_n256 import emit_lut
from synth_compare import yosys_stat
from cam_baseline import emit_cam

N = 64
R = 2
print(f"N={N}, care radius h={R} (conservative: favours the HNN).", flush=True)
print(f"{'M':>4}{'fan-in':>8}{'kept':>8}{'terms':>9}{'HNNgate':>9}{'CAMgate':>9}"
      f"{'ratio':>8}{'HNNlut':>8}{'CAMlut':>8}{'ratio':>8}", flush=True)
print("-" * 79, flush=True)

for M in (4, 8, 16, 24):
    d = min(max(16, 4 * M), 20)
    try:
        pats, W, kept = build_net(N, M, d, 11)
    except Exception as e:
        print(f"{M:>4}  build failed: {e}", flush=True)
        continue
    P01 = ((pats + 1) // 2).astype(np.int8)
    out = tempfile.mkdtemp()
    funcs = []
    for i in range(N):
        sup, dd, rows = care_rows(i, W, pats, R)
        if sup is None or dd == 0:
            funcs.append((None, None))
            continue
        p = os.path.join(out, f"n{i}.pla")
        write_pla(p, sup, dd, rows, dc=True)
        funcs.append((sup, espresso_sop(p)))
    lut = os.path.join(out, "lut.sv")
    terms = emit_lut(N, funcs, lut)
    ha = yosys_stat(lut, mode="asic")[0]
    hf = yosys_stat(lut, mode="fpga")[0]
    cam = os.path.join(out, "cam.sv")
    emit_cam(N, M, P01, cam)
    ca = yosys_stat(cam, mode="asic")[0]
    cf = yosys_stat(cam, mode="fpga")[0]
    if None in (ha, hf, ca, cf):
        print(f"{M:>4}  yosys failed", flush=True)
        continue
    print(f"{M:>4}{d:>8}{kept:>5}/{M:<2}{terms:>9,}{ha:>9,}{ca:>9,}"
          f"{ha/ca:>7.2f}x{hf:>8,}{cf:>8,}{hf/cf:>7.2f}x", flush=True)

print("-" * 79, flush=True)
print("ratio > 1 means the HNN is LARGER than the CAM.", flush=True)
print("'kept' < M means the HNN cannot store the patterns at that fan-in, so its "
      "row is moot -- the CAM stores them by construction.", flush=True)
