#!/usr/bin/env python3
"""Where in its range does a corrected muscle actually carry passive tension.

Schumann Lab, biomechanical piano model. Written September 12, 2026.

THE QUESTION THIS EXISTS TO SETTLE, WHICH IS OPEN ITEM 31. The `range` correction of
September 12, 2026 takes the count of muscles carrying passive force above a tenth of their
declared peak from 0 to 40 of 44. The record calls that count a fault. Her own ruling asks
for the physiology that produces it. Both cannot stand, and the question put to her was
which gives.

THE THIRD ROUTE THIS TESTS, AND IT IS NOT THE ONE THE STATE FILE PROPOSED. The state file
proposed reporting passive force over postures the hand can hold rather than over the whole
declared window. **That route is void and this script establishes why**: the corrected
`lengthrange` was itself measured over postures with no interpenetration, so its upper end
is attained at a holdable posture by construction, and filtering changes nothing at all.

WHAT IS ACTUALLY WORTH KNOWING, AND WHAT THIS MEASURES. The defect the count was earned on
was a muscle behaving like a stretched rubber band the controller could not switch off. That
is a statement about where in the range the tension sits, not about whether it exists. A
muscle that carries passive tension only in the last few percent of its stretch is a real
muscle. One that carries it at rest is broken. So for every muscle, over postures the hand
can hold:

    at rest        passive force at the model's default posture
    median         passive force at the median of the reachable holdable lengths
    90th           passive force at the 90th percentile of them
    max            passive force at the longest holdable length
    share          the share of holdable postures whose passive force is above a tenth of peak

Measured on the shipped tree, on the repaired tree, and on the corrected tree, so the three
are read side by side rather than argued about.
"""
import argparse
import itertools
import os

import mujoco
import numpy as np

PROBE = ('<mujoco model="probe">\n'
         '  <include file="defaults.xml"/>\n'
         '  <include file="{side}_assets/{side}_hand_definition_meta.xml"/>\n'
         '  <include file="{side}_assets/{side}_hand_definition_tendons.xml"/>\n'
         '  <include file="{side}_assets/{act}"/>\n'
         '  <worldbody><include file="{side}_assets/{side}_hand_freeroot.xml"/></worldbody>\n'
         '</mujoco>\n')


def load(assets, side, stem):
    p = os.path.join(assets, stem + ".xml")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(PROBE.format(side=side, act=f"{side}_hand_actuators_muscle.xml"))
    try:
        return mujoco.MjModel.from_xml_path(p)
    finally:
        os.remove(p)


def moving_joints(m, d, tid, q0):
    out = []
    for j in range(m.njnt):
        if m.jnt_type[j] in (mujoco.mjtJoint.mjJNT_FREE, mujoco.mjtJoint.mjJNT_BALL):
            continue
        if not m.jnt_limited[j]:
            continue
        adr = m.jnt_qposadr[j]
        lo, hi = m.jnt_range[j]
        d.qpos[:] = q0; mujoco.mj_forward(m, d); base = d.ten_length[tid]
        q = q0.copy(); q[adr] = lo
        d.qpos[:] = q; mujoco.mj_forward(m, d); a = d.ten_length[tid]
        q = q0.copy(); q[adr] = hi
        d.qpos[:] = q; mujoco.mj_forward(m, d); b = d.ten_length[tid]
        if max(abs(a - base), abs(b - base)) > 1e-6:
            out.append((adr, lo, hi))
    return out


def holdable_lengths(m, d, tid, js, q0, nrand, grid, seed=0):
    adrs = [a for a, _, _ in js]
    los = np.array([l for _, l, _ in js]); his = np.array([h for _, _, h in js])
    rng = np.random.default_rng(seed)
    samples = []
    if len(adrs) <= 14:
        samples += list(itertools.product(*[(l, h) for l, h in zip(los, his)]))
    if len(adrs) <= 3 and grid:
        samples += list(itertools.product(*[np.linspace(l, h, grid) for l, h in zip(los, his)]))
    samples += [tuple(rng.uniform(los, his)) for _ in range(nrand)]
    keep = []
    for combo in samples:
        q = q0.copy()
        for adr, v in zip(adrs, combo):
            q[adr] = v
        d.qpos[:] = q
        mujoco.mj_forward(m, d)
        if all(d.contact[c].dist >= 0.0 for c in range(d.ncon)):
            keep.append(d.ten_length[tid])
    return np.array(keep)


def passive_share(m, aid, lengths):
    """Passive force as a share of declared peak, at each length."""
    lr = np.asarray(m.actuator_lengthrange[aid], dtype=float)
    prm_b = np.asarray(m.actuator_biasprm[aid][:9], dtype=float)
    fmax = m.actuator_gainprm[aid][2]
    if fmax <= 0:
        return np.zeros_like(lengths)
    return np.array([abs(mujoco.mju_muscleBias(float(L), lr, 0.0, prm_b)) / fmax
                     for L in lengths])


def run(assets, label, nrand, grid):
    side = "right"
    m = load(assets, side, "_pw")
    d = mujoco.MjData(m)
    q0 = m.qpos0.copy()
    rows = []
    for aid in range(m.nu):
        if m.actuator_gaintype[aid] != mujoco.mjtGain.mjGAIN_MUSCLE:
            continue
        nm = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, aid).split(":")[-1]
        tid = m.actuator_trnid[aid][0]
        js = moving_joints(m, d, tid, q0)
        if not js:
            continue
        L = holdable_lengths(m, d, tid, js, q0, nrand, grid)
        if len(L) == 0:
            rows.append(dict(name=nm, n=0))
            continue
        p = passive_share(m, aid, L)
        d.qpos[:] = q0
        mujoco.mj_forward(m, d)
        rest = passive_share(m, aid, np.array([d.ten_length[tid]]))[0]
        order = np.argsort(L)
        Ls = L[order]; ps = p[order]
        rows.append(dict(name=nm, n=len(L), rest=rest,
                         median=float(np.interp(np.median(Ls), Ls, ps)),
                         p90=float(ps[int(0.90 * (len(ps) - 1))]),
                         pmax=float(ps.max()),
                         share=float((p > 0.10).mean()),
                         r0=float(m.actuator_gainprm[aid][0]),
                         r1=float(m.actuator_gainprm[aid][1])))
    print(f"\n{label}")
    print(f"  {'muscle':10s} {'range':>15s} {'at rest':>8s} {'median':>8s} "
          f"{'90th':>8s} {'max':>8s} {'share over 0.10':>16s}")
    over_any = over_rest = over_median = 0
    for r in rows:
        if r["n"] == 0:
            print(f"  {r['name']:10s} no holdable posture sampled")
            continue
        if r["pmax"] > 0.10:
            over_any += 1
        if r["rest"] > 0.10:
            over_rest += 1
        if r["median"] > 0.10:
            over_median += 1
        print(f"  {r['name']:10s} {r['r0']:6.3f} to {r['r1']:5.3f} {r['rest']:8.3f} "
              f"{r['median']:8.3f} {r['p90']:8.3f} {r['pmax']:8.3f} {r['share']:15.1%}")
    print(f"\n  muscles above a tenth of peak somewhere in the holdable range: {over_any} of "
          f"{len(rows)}")
    print(f"  muscles above a tenth of peak at the MEDIAN holdable posture:   {over_median} of "
          f"{len(rows)}")
    print(f"  muscles above a tenth of peak AT REST:                          {over_rest} of "
          f"{len(rows)}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trees", nargs="+", help="label=path pairs")
    ap.add_argument("--nrand", type=int, default=600)
    ap.add_argument("--grid", type=int, default=13)
    args = ap.parse_args()
    print(f"MuJoCo {mujoco.__version__}. Passive force is read from MuJoCo's own bias "
          f"function, as a share of each muscle's declared peak isometric force.")
    print("Postures are filtered to those where no two of the hand's own geoms interpenetrate.")
    for spec in args.trees:
        label, path = spec.split("=", 1)
        run(path, label, args.nrand, args.grid)


if __name__ == "__main__":
    main()
