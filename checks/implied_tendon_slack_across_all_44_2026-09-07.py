#!/usr/bin/env python3
"""If `lengthrange` were recomputed, how many of the 44 would get an impossible tendon?

Schumann Lab, biomechanical piano model, MUSIC-Hand-v0.15. Written 7 September 2026.

WHY THIS EXISTS
===============
Recomputing `lengthrange` for LU_RB4, RI5 and LU_RB5 puts each muscle's declared window
back onto the geometry the model has, which removes the zero-force artefact by
construction. For RI5 it also does something else, and the something else is the reason
this script was written: at MuJoCo's default `range` of 0.75 to 1.05,

    L0  = (lengthrange[1] - lengthrange[0]) / 0.30
    L_T =  lengthrange[0] - 0.75 * L0

and RI5's recomputed window gives L_T = -17.0 mm. A tendon of negative length is not a
parameter that can be shipped. The record already lists four muscles carrying a negative
implied tendon length as shipped: PQ, OP, AdP and RI3. The question this script answers
is how far that goes if the repair is applied more widely, because Elizabeth Schumann has
an open decision on whether `range` is corrected for all 44 muscles or for none, and the
answer changes shape if recomputing `lengthrange` creates new impossible tendons.

WHAT IT MEASURES, FOR ALL 44 MUSCLES ON BOTH HANDS
==================================================
  shipped window      the `lengthrange` attribute as it stands
  recomputed window   MuJoCo's own compiler with that one muscle's attribute deleted
  reachable window    a kinematic sweep of every joint that moves the tendon
  implied L0, L_T     under each window, at the default range
  excursion ratio     reachable excursion divided by the shortest reachable path length.
                      A muscle whose path changes by a large fraction of its own length
                      cannot be given a physiological fibre and tendon split at any
                      `range`, and that is a geometry problem rather than a parameter one.

and, for the three muscles under repair, which joints produce the excursion and how much
each contributes, so that an excursion which looks extreme can be traced to the joint
limit that produces it.

WHAT IT WRITES, STATED EXACTLY: no model file is modified. It writes one temporary probe
XML into the assets directory it is pointed at, and one temporary copy of the actuator
file while the compiler route runs, and deletes both. That is why it must be pointed at a
scratch copy. Everything it finds it prints.

SOURCES
=======
- MuJoCo 3.12.0 XML reference and Modeling chapter, for the two relations above, the
  `range` default of 0.75 to 1.05, and the active-force window 0.5 to 1.6.
- MUSIC-Hand-v0.15, `assets/` from `piano.tar.gz`, the collaborators' archive of
  4 March 2026.

USAGE
=====
    python3 implied_tendon_slack_across_all_44_2026-09-07.py --assets /path/to/scratch/assets
"""

import argparse
import itertools
import os
import re
import sys

import numpy as np
import mujoco

RANGE_LO, RANGE_HI = 0.75, 1.05
LMIN, LMAX = 0.5, 1.6
THREE = ["LU_RB4", "RI5", "LU_RB5"]
FIVE = ["FPB", "AdP", "APB", "FDM", "ADM"]

PROBE = ('<mujoco model="probe">\n'
         '  <include file="defaults.xml"/>\n'
         '  <include file="{side}_assets/{side}_hand_definition_meta.xml"/>\n'
         '  <include file="{side}_assets/{side}_hand_definition_tendons.xml"/>\n'
         '  <include file="{side}_assets/{act}"/>\n'
         '  <worldbody><include file="{side}_assets/{side}_hand_freeroot.xml"/></worldbody>\n'
         '</mujoco>\n')


def load(assets, side, actfile, stem):
    p = os.path.join(assets, stem + ".xml")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(PROBE.format(side=side, act=actfile))
    try:
        return mujoco.MjModel.from_xml_path(p)
    finally:
        os.remove(p)


def joint_table(m):
    return [(j, m.jnt_qposadr[j], m.jnt_range[j, 0], m.jnt_range[j, 1])
            for j in range(m.njnt)
            if m.jnt_type[j] not in (mujoco.mjtJoint.mjJNT_FREE, mujoco.mjtJoint.mjJNT_BALL)
            and m.jnt_limited[j]]


def sensitivity(m, d, q0, jq):
    """Per joint, per tendon: how far that one joint alone moves the tendon."""
    def L(q):
        d.qpos[:] = q
        mujoco.mj_forward(m, d)
        return d.ten_length.copy()
    base = L(q0)
    sens = np.zeros((len(jq), m.ntendon))
    for k, (_, adr, lo, hi) in enumerate(jq):
        q = q0.copy(); q[adr] = lo; x = L(q)
        q = q0.copy(); q[adr] = hi; y = L(q)
        sens[k] = np.maximum(abs(x - base), abs(y - base))
    return sens, base


def sweep(m, d, q0, jq, sens, tid, nrand, seed):
    idx = [k for k in range(len(jq)) if sens[k, tid] > 1e-6]
    if not idx:
        return None
    lo = np.array([jq[k][2] for k in idx])
    hi = np.array([jq[k][3] for k in idx])
    adrs = [jq[k][1] for k in idx]
    rng = np.random.default_rng(seed)
    samples = list(itertools.product(*[(l, h) for l, h in zip(lo, hi)])) if len(idx) <= 14 else []
    samples += [tuple(rng.uniform(lo, hi)) for _ in range(nrand)]
    tmin, tmax = np.inf, -np.inf
    for combo in samples:
        q = q0.copy()
        for adr, v in zip(adrs, combo):
            q[adr] = v
        d.qpos[:] = q
        mujoco.mj_forward(m, d)
        v = d.ten_length[tid]
        tmin = min(tmin, v); tmax = max(tmax, v)
    return tmin, tmax, idx


def derived(lo, hi):
    L0 = (hi - lo) / (RANGE_HI - RANGE_LO)
    return L0, lo - RANGE_LO * L0


def run_side(assets, side, nrand, seed):
    actrel = f"{side}_hand_actuators_muscle.xml"
    apath = os.path.join(assets, f"{side}_assets", actrel)
    src = open(apath, encoding="utf-8").read()
    order = [n for n in re.findall(r'<muscle name="([^"]+)"', src)]

    m = load(assets, side, actrel, f"_slack_ship_{side}")
    d = mujoco.MjData(m)
    mujoco.mj_resetData(m, d)
    mujoco.mj_forward(m, d)
    q0 = d.qpos.copy()
    jq = joint_table(m)
    sens, _ = sensitivity(m, d, q0, jq)

    rows = []
    for i in range(m.nu):
        name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
        if not name or m.actuator_trntype[i] != mujoco.mjtTrn.mjTRN_TENDON:
            continue
        short = name.split(":")[-1]
        tid = m.actuator_trnid[i, 0]
        sw = sweep(m, d, q0, jq, sens, tid, nrand, seed)
        if sw is None:
            continue
        s = m.actuator_lengthrange[i].copy() * 1000.0

        # compiler, this muscle alone
        k = order.index(name)
        lines = src.splitlines(keepends=True)
        out, seen = [], 0
        for ln in lines:
            if "<muscle name=" in ln:
                if seen == k:
                    ln = re.sub(r'\s+lengthrange="[^"]*"', "", ln)
                seen += 1
            out.append(ln)
        tmp = f"_{side}_slack_ONE.xml"
        tp = os.path.join(assets, f"{side}_assets", tmp)
        with open(tp, "w", encoding="utf-8") as fh:
            fh.write("".join(out))
        comp, cerr = None, None
        try:
            mm = load(assets, side, tmp, f"_p_slack_{side}")
            comp = mm.actuator_lengthrange[k].copy() * 1000.0
        except Exception as e:  # noqa: BLE001
            cerr = str(e).strip().splitlines()[0]
        finally:
            os.remove(tp)

        rows.append({"muscle": short, "index": i, "tendon": tid,
                     "shipped": s, "compiler": comp, "compiler_err": cerr,
                     "sweep": (sw[0] * 1000.0, sw[1] * 1000.0),
                     "joint_idx": sw[2]})
    return m, d, q0, jq, sens, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True)
    ap.add_argument("--nrand", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sides", default="right,left")
    a = ap.parse_args()

    print("=" * 122)
    print("IMPLIED TENDON SLACK LENGTH ACROSS ALL 44 MUSCLES, SHIPPED AND RECOMPUTED   ·   mm")
    print("Schumann Lab, biomechanical piano model, 7 September 2026")
    print(f"MuJoCo {mujoco.__version__}   ·   assets {a.assets}   ·   range at MuJoCo's default 0.75 to 1.05")
    print("=" * 122)

    for side in [s.strip() for s in a.sides.split(",") if s.strip()]:
        m, d, q0, jq, sens, rows = run_side(a.assets, side, a.nrand, a.seed)
        print(f"\n--- {side.upper()} HAND " + "-" * 104)
        print(f"{'muscle':9s}{'shipped span':>13s}{'L_T shipped':>13s}"
              f"{'recomputed span':>17s}{'L_T recomputed':>16s}"
              f"{'excursion':>11s}{'shortest':>10s}{'exc/short':>11s}   flags")
        print("-" * 122)
        neg_ship, neg_recomp, failed = [], [], []
        ratios = []
        for r in rows:
            s = r["shipped"]
            L0s, LTs = derived(s[0], s[1])
            if r["compiler"] is None:
                failed.append(r["muscle"])
                span_c = LTc = float("nan")
            else:
                c = r["compiler"]
                L0c, LTc = derived(c[0], c[1])
                span_c = c[1] - c[0]
                if LTc < 0:
                    neg_recomp.append(r["muscle"])
            if LTs < 0:
                neg_ship.append(r["muscle"])
            exc = r["sweep"][1] - r["sweep"][0]
            short_len = r["sweep"][0]
            ratio = exc / short_len
            ratios.append((ratio, r["muscle"]))
            flags = []
            if LTs < 0:
                flags.append("shipped L_T negative")
            if r["compiler"] is not None and LTc < 0:
                flags.append("RECOMPUTED L_T NEGATIVE")
            if r["compiler"] is None:
                flags.append("compiler failed")
            if r["muscle"] in THREE:
                flags.append("<-- the three")
            elif r["muscle"] in FIVE:
                flags.append("added")
            print(f"{r['muscle']:9s}{s[1] - s[0]:13.3f}{LTs:13.3f}"
                  f"{span_c:17.3f}{LTc:16.3f}"
                  f"{exc:11.3f}{short_len:10.3f}{ratio:11.3f}   {'; '.join(flags)}")

        print()
        print(f"negative implied tendon slack AS SHIPPED     : {len(neg_ship)} of {len(rows)}"
              f"   {', '.join(neg_ship) if neg_ship else 'none'}")
        print(f"negative implied tendon slack IF RECOMPUTED  : {len(neg_recomp)} of {len(rows)}"
              f"   {', '.join(neg_recomp) if neg_recomp else 'none'}")
        if failed:
            print(f"compiler refused a value for                 : {', '.join(failed)}")
            print("   For those the recomputed window cannot be produced, so they are absent")
            print("   from the count above. The kinematic sweep still gives an ESTIMATE of what")
            print("   the window would be, and therefore of the sign of the derived tendon:")
            for r in rows:
                if r["muscle"] not in failed:
                    continue
                lo, hi = r["sweep"]
                L0e, LTe = derived(lo, hi)
                print(f"     {r['muscle']:9s} sweep window {lo:8.3f} to {hi:8.3f} mm"
                      f"   estimated L0 {L0e:8.3f}   estimated L_T {LTe:9.3f}"
                      f"{'   ESTIMATED NEGATIVE' if LTe < 0 else ''}")
            print("   An estimate is not a measurement. It is printed because a count that")
            print("   silently omits a muscle reads as a count of the whole model.")
        ratios.sort(reverse=True)
        print()
        print("Reachable excursion as a fraction of the muscle's own shortest path length,")
        print("ten largest. A muscle high on this list cannot be given a physiological fibre")
        print("and tendon split at any `range`, because the path itself moves too far.")
        for ratio, name in ratios[:10]:
            print(f"    {name:9s}{ratio:8.3f}")

        if side == "right":
            print()
            print("--- WHICH JOINTS PRODUCE THE EXCURSION, FOR THE THREE UNDER REPAIR " + "-" * 50)
            for r in rows:
                if r["muscle"] not in THREE:
                    continue
                contrib = sorted(
                    ((sens[k, r["tendon"]] * 1000.0,
                      mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, jq[k][0]),
                      np.degrees(jq[k][2]), np.degrees(jq[k][3]))
                     for k in r["joint_idx"]), reverse=True)
                total = r["sweep"][1] - r["sweep"][0]
                print(f"\n  {r['muscle']}: reachable excursion {total:.3f} mm across "
                      f"{len(contrib)} joints")
                for mm_, jname, lo_deg, hi_deg in contrib:
                    print(f"      {jname:34s} single-joint travel {mm_:7.3f} mm"
                          f"   limits {lo_deg:8.2f} to {hi_deg:7.2f} deg")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
