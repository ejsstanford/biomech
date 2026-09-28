#!/usr/bin/env python3
"""Passive force check, read at the MEDIAN reachable posture. Pass or fail.

WHY THIS EXISTS. `check_range_correction_2026-09-12.py` fails a correctly applied
tree. It counts passive force over the WHOLE window, and Elizabeth Schumann
retired that as a pass criterion on September 18, 2026, six days after that
check was written, replacing it with the same count read at the median
reachable posture, 2 of 44, with a named exception for the finger flexors and
interossei at full extension. Run on a correct tree the old check reports
REFUSED with 41 muscles flagged, which is exactly the number a correct tree has.

THIS DOES NOT REIMPLEMENT THE MEASUREMENT. A first version of this file did, and
it disagreed with the established instrument, reporting 7 at the median against
its 1, because sampling whole-hand postures uniformly is a different quantity
from sampling each muscle's own reachable lengths. **There is one sampler and it
is `passive_where_it_actually_sits_2026-09-12.py`.** This file imports it and
applies the criterion to what it returns.

    python3 check_passive_at_median_2026-09-28.py <assets_dir>
            [--measurer PATH] [--max-at-median 2] [--threshold 0.10] [--nrand 400]

Exit 0 on pass, 1 on fail. Requires mujoco>=3.13, numpy, and the measurer script.
"""
import argparse, importlib.util, os, sys
import numpy as np

DEFAULT_MEASURER = ("/Users/ejs/Library/Mobile Documents/com~apple~CloudDocs/Workspace/"
                    "Research_Projects/AI_Model/The range correction, all 44 muscles, "
                    "mixed target 2026-09-12_run12/passive_where_it_actually_sits_2026-09-12.py")

# Her named exception of September 18, 2026: the finger flexors and interossei,
# which are stretched at the model's default flat fully extended hand.
EXCEPTED = {"FDS2","FDS3","FDS4","FDS5","FDP2","FDP3","FDP4","FDP5","FPL",
            "RI2","RI3","RI4","RI5","UI_UB2","UI_UB3","UI_UB4","UI_UB5",
            "LU_RB2","LU_RB3","LU_RB4","LU_RB5"}


def load_measurer(path):
    if not os.path.exists(path):
        sys.exit(f"measurer not found: {path}\nPass --measurer with its location.")
    spec = importlib.util.spec_from_file_location("measurer", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    for fn in ("load", "moving_joints", "holdable_lengths", "passive_share"):
        if not hasattr(mod, fn):
            sys.exit(f"measurer has no {fn}(); this wrapper expects the September 12, 2026 script.")
    return mod


def measure(mod, assets, side, nrand, grid):
    """Per-muscle passive force as a share of declared peak: at rest, median, max.

    Uses the measurer's own load / moving_joints / holdable_lengths / passive_share
    with its own signatures. Nothing here is a reimplementation.
    """
    import mujoco
    m = mod.load(assets, side, "_pw_check")
    d = mujoco.MjData(m)
    q0 = m.qpos0.copy()
    rows = []
    for aid in range(m.nu):
        if m.actuator_gaintype[aid] != mujoco.mjtGain.mjGAIN_MUSCLE:
            continue
        name = (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, aid) or "").split(":")[-1]
        tid = m.actuator_trnid[aid][0]
        js = mod.moving_joints(m, d, tid, q0)
        if not js:
            rows.append((name, None, None, None)); continue
        L = mod.holdable_lengths(m, d, tid, js, q0, nrand, grid)
        if len(L) == 0:
            rows.append((name, None, None, None)); continue
        share = mod.passive_share(m, aid, L)
        d.qpos[:] = q0; mujoco.mj_forward(m, d)
        rest = mod.passive_share(m, aid, np.array([d.ten_length[tid]]))[0]
        rows.append((name, float(rest), float(np.median(share)), float(share.max())))
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("assets")
    p.add_argument("--measurer", default=DEFAULT_MEASURER)
    p.add_argument("--max-at-median", type=int, default=2)
    p.add_argument("--threshold", type=float, default=0.10)
    p.add_argument("--nrand", type=int, default=400)
    p.add_argument("--grid", type=int, default=0)
    a = p.parse_args()
    mod = load_measurer(a.measurer)
    failed = False
    for side in ("right", "left"):
        rows = measure(mod, a.assets, side, a.nrand, a.grid)
        med = sorted(n for n, r, md, mx in rows if md is not None and md > a.threshold)
        anyw = sorted(n for n, r, md, mx in rows if mx is not None and mx > a.threshold)
        rest = sorted(n for n, r, md, mx in rows if r is not None and r > a.threshold)
        print(f"\n{side} hand, threshold {a.threshold:.2f} of declared peak, {len(rows)} muscles")
        print(f"  somewhere in the holdable range : {len(anyw)}   (RETIRED as a criterion, Sept 18 2026)")
        print(f"  at the MEDIAN holdable posture  : {len(med)}   <-- THE CRITERION IN FORCE")
        print(f"  at the default flat posture     : {len(rest)}   (the flexor and interossei exception)")
        if med:
            outside = [x for x in med if x not in EXCEPTED]
            print(f"    over at the median: {', '.join(med)}")
            if outside: print(f"    outside the named exception: {', '.join(outside)}")
        if len(med) > a.max_at_median:
            print(f"  FAIL: {len(med)} over at the median, limit {a.max_at_median}"); failed = True
        else:
            print(f"  PASS: at or under the limit of {a.max_at_median}")
    print("\n" + ("REFUSED" if failed else "PASSED"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
