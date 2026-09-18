#!/usr/bin/env python3
"""The other end of the stale length range: muscles that become springs.

Schumann Lab, biomechanical piano model, MUSIC-Hand-v0.15. Written 8 September 2026.

WHY THIS EXISTS
===============
Every pass so far has counted muscles that reach zero ACTIVE force. That test finds
muscles whose declared window sits above the excursion the joints allow, so the muscle is
driven off the short end of its own force-length curve and can produce nothing. It cannot
find the opposite fault, and the opposite fault turns out to be present.

MuJoCo's muscle model adds a PASSIVE force that rises once normalised length passes about
1.0 and keeps rising with no upper limit, while ACTIVE force falls to zero outside 0.5 to
1.6. A muscle whose declared window is far below its real excursion is therefore driven
off the LONG end, where it produces no active force and a large passive one. A passive
force is not under the controller's command at all: it is a spring, and no activation
measurement can see it.

`LU_RB5` as shipped was found to deliver 120.60 N at one reachable posture against a
declared 47.90, which is 2.52 times, and all of it passive with active force at exactly
zero. Nothing in the record said so. This script counts the fault across all 44.

WHAT IT MEASURES
================
For every muscle, over the corners of the box of joints that move its tendon plus random
interior samples: the largest total actuator force at full activation, the passive part of
it with the control set to zero at the same posture, and the normalised length there. It
reports the muscles whose passive force exceeds a stated fraction of declared force, and
separately the muscles whose active force falls under one per cent, so the two faults can
be read side by side.

The six muscles whose shipped `lengthrange` already reproduces the geometry, `PQ`, `ECRB`,
`ECU`, `FCR`, `PL` and `PT`, are the control. If the method reports appreciable passive
force for them it is measuring an artefact of the method rather than of the model.

WHAT IT WRITES, STATED EXACTLY: no model file is modified. One temporary probe XML into
the assets directory it is pointed at, removed in a `finally` block. Point it at a scratch
copy, never at the Workspace.

SOURCES: MuJoCo 3.12.0 Modeling chapter, for the passive force term and the active window
0.5 to 1.6; MUSIC-Hand-v0.15 from `piano.tar.gz`, the collaborators' archive of
4 March 2026.

USAGE
=====
    python3 passive_force_across_all_44_2026-09-08.py --tree shipped=/path/to/scratch \
        --tree repaired=/path/to/other --threshold 0.10
"""

import argparse
import itertools
import os
import sys

import numpy as np
import mujoco

PROBE = ('<mujoco model="probe">\n'
         '  <include file="defaults.xml"/>\n'
         '  <include file="right_assets/right_hand_definition_meta.xml"/>\n'
         '  <include file="right_assets/right_hand_definition_tendons.xml"/>\n'
         '  <include file="right_assets/right_hand_actuators_muscle.xml"/>\n'
         '  <worldbody><include file="right_assets/right_hand_freeroot.xml"/></worldbody>\n'
         '</mujoco>\n')

CONTROLS = {"PQ", "ECRB", "ECU", "FCR", "PL", "PT"}
RANGE_LO, RANGE_HI = 0.75, 1.05


def load(assets, stem="_passive_probe"):
    p = os.path.join(assets, stem + ".xml")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(PROBE)
    try:
        return mujoco.MjModel.from_xml_path(p)
    finally:
        os.remove(p)


def run(path, nrand, seed):
    assets = os.path.join(path, "assets") if os.path.isdir(os.path.join(path, "assets")) else path
    m = load(assets)
    d = mujoco.MjData(m)
    mujoco.mj_resetData(m, d)
    mujoco.mj_forward(m, d)
    q0 = d.qpos.copy()
    jq = [(int(m.jnt_qposadr[j]), float(m.jnt_range[j, 0]), float(m.jnt_range[j, 1]))
          for j in range(m.njnt) if m.jnt_limited[j]
          and m.jnt_type[j] not in (mujoco.mjtJoint.mjJNT_FREE, mujoco.mjtJoint.mjJNT_BALL)]

    def L(q):
        d.qpos[:] = q
        mujoco.mj_forward(m, d)
        return d.ten_length.copy()

    base = L(q0)
    rows = []
    for ai in range(m.nu):
        an = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, ai)
        if an is None or m.actuator_trntype[ai] != mujoco.mjtTrn.mjTRN_TENDON:
            continue
        name = an.replace("R:", "")
        ti = int(m.actuator_trnid[ai][0])
        mv = []
        for adr, lo, hi in jq:
            q = q0.copy(); q[adr] = lo; x = L(q)
            q = q0.copy(); q[adr] = hi; y = L(q)
            if max(abs(x[ti] - base[ti]), abs(y[ti] - base[ti])) > 1e-6:
                mv.append((adr, lo, hi))
        if not mv:
            continue
        rng = np.random.default_rng(seed)
        samples = list(itertools.product(*[(l, h) for _, l, h in mv])) if len(mv) <= 12 else []
        samples += [tuple(rng.uniform([l for _, l, _ in mv], [h for _, _, h in mv]))
                    for _ in range(nrand)]
        dec = abs(float(m.actuator_gainprm[ai][2]))
        lr = m.actuator_lengthrange[ai]
        L0 = (lr[1] - lr[0]) / (RANGE_HI - RANGE_LO)
        LT = lr[0] - RANGE_LO * L0
        best = (-1.0, None, 0.0)
        act_min, act_max = np.inf, 0.0
        for combo in samples:
            q = q0.copy()
            for (adr, _, _), v in zip(mv, combo):
                q[adr] = v
            d.qpos[:] = q
            if m.na:
                d.act[:] = 1.0
            d.ctrl[:] = 1.0
            mujoco.mj_forward(m, d)
            full = abs(float(d.actuator_force[ai]))
            ln = float(d.ten_length[ti])
            if m.na:
                d.act[:] = 0.0
            d.ctrl[:] = 0.0
            mujoco.mj_forward(m, d)
            pas = abs(float(d.actuator_force[ai]))
            act = full - pas
            act_min, act_max = min(act_min, act), max(act_max, act)
            if pas > best[0]:
                best = (pas, ln, full)
        pas, ln, full = best
        norm = (ln - LT) / L0 if L0 > 0 else float("nan")
        rows.append(dict(name=name, dec=dec, pas=pas, full=full, norm=norm,
                         act_min=act_min, act_max=act_max))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", action="append", required=True, help="label=path")
    ap.add_argument("--threshold", type=float, default=0.10)
    ap.add_argument("--nrand", type=int, default=600)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()

    print("=" * 104)
    print("PASSIVE FORCE ACROSS ALL 44 MUSCLES, at the reachable posture where it is largest")
    print(f"MuJoCo {mujoco.__version__}   ·   active force is zero outside normalised 0.5 to 1.6")
    print(f"threshold for the count: passive force above {a.threshold:.0%} of declared force")
    print("=" * 104)

    for spec in a.tree:
        label, path = spec.split("=", 1)
        rows = run(path, a.nrand, a.seed)
        print(f"\n\n### {label}   ({len(rows)} muscles measured)")
        print(f"\n{'muscle':9s}{'declared N':>12s}{'passive N':>11s}{'passive %':>11s}"
              f"{'total N':>10s}{'total %':>9s}{'norm len':>10s}{'active min %':>14s}")
        hits, zeros = [], []
        for r in sorted(rows, key=lambda x: -x["pas"] / x["dec"]):
            frac = r["pas"] / r["dec"]
            amin = 100 * r["act_min"] / r["dec"]
            tag = "  (control)" if r["name"] in CONTROLS else ""
            if frac >= a.threshold or r["name"] in CONTROLS:
                print(f"{r['name']:9s}{r['dec']:12.2f}{r['pas']:11.2f}{100 * frac:11.1f}"
                      f"{r['full']:10.2f}{100 * r['full'] / r['dec']:9.1f}{r['norm']:10.3f}"
                      f"{amin:14.2f}{tag}")
            if frac >= a.threshold:
                hits.append(r["name"])
            if r["act_max"] > 0 and r["act_min"] / r["act_max"] < 0.01:
                zeros.append(r["name"])
        print(f"\n  {len(hits)} muscles carry passive force above {a.threshold:.0%} of declared"
              f" at some reachable posture:")
        print("     " + ", ".join(sorted(hits)) if hits else "     none")
        print(f"  {len(zeros)} muscles fall under one per cent of their own peak ACTIVE force:")
        print("     " + ", ".join(sorted(zeros)) if zeros else "     none")
        ctrl = [r for r in rows if r["name"] in CONTROLS]
        if ctrl:
            worst = max(100 * r["pas"] / r["dec"] for r in ctrl)
            print(f"  control band: the six muscles whose shipped window already matched the")
            print(f"  geometry carry at most {worst:.1f} per cent of declared force passively.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
