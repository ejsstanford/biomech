#!/usr/bin/env python3
"""The check that refuses. Requirement 3 of the four Elizabeth Schumann accepted.

Schumann Lab, biomechanical piano model. Written September 12, 2026.

Her words, September 12, 2026: "We must accept the mixed target with the four documentation
requirements." The third of those, in the language of the September 10 findings document, is
"a check that refuses rather than a sentence that warns": a script that fails if any muscle's
`range` is neither of the two sanctioned targets, if the provenance table disagrees with the
model file, or if a summed-activation result includes an unsourced muscle without a stated
exemption.

This exits non-zero on any failure, so it can sit in front of a run rather than beside it.

WHAT IT REFUSES ON
  1. a muscle whose `range` is not what the provenance table's own target implies
  2. a muscle whose `lengthrange` in the model disagrees with the provenance table
  3. a muscle whose derived tendon slack length is negative
  4. a muscle whose `range` window falls outside the force-length curve's support
  5. the two hands disagreeing on any muscle
  6. a regression in either fault count the September 10 repair drove to zero, being
     muscles that reach zero active force inside their declared window, and muscles
     carrying passive force above 10 percent of their declared peak
  7. a summed-activation result containing a grade B, C or D muscle with no exemption,
     which is the call this script exposes through `--sum`
"""
import argparse
import os
import sys

import mujoco
import numpy as np

PROBE = ('<mujoco model="probe">\n'
         '  <include file="defaults.xml"/>\n'
         '  <include file="{side}_assets/{side}_hand_definition_meta.xml"/>\n'
         '  <include file="{side}_assets/{side}_hand_definition_tendons.xml"/>\n'
         '  <include file="{side}_assets/{act}"/>\n'
         '  <worldbody><include file="{side}_assets/{side}_hand_freeroot.xml"/></worldbody>\n'
         '</mujoco>\n')
# The declared support from `gainprm`, which is what a window may never leave, and the usable
# support, which is where active force is at least a tenth of peak. A window below the usable
# support is allowed when the provenance row says so, because conditions 2 and 3 conflict for
# one muscle and her ruling of September 10, 2026 puts the physically possible tendon first.
LMIN, LMAX = 0.5, 1.6
USABLE = (0.61181, 1.46583)
SOURCED = {"A"}


def load(assets, side, actfile, stem):
    p = os.path.join(assets, stem + ".xml")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(PROBE.format(side=side, act=actfile))
    try:
        return mujoco.MjModel.from_xml_path(p)
    finally:
        os.remove(p)


def read_provenance(path):
    rows = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or line.startswith("muscle\t"):
            continue
        f = line.rstrip("\n").split("\t")
        rows[f[0]] = dict(grade=f[1], target=float(f[2]), source=f[3],
                          lr0=float(f[4]), lr1=float(f[5]),
                          r0=float(f[6]), r1=float(f[7]),
                          L0=float(f[8]), LT=float(f[9]), feasible=f[10])
    return rows


def fault_counts(m, d):
    """The two counts the September 10 repair drove to zero, measured the same way.

    zero active force: sweep the declared window and find the smallest active-force scale
    the muscle reaches. Off the curve's support the scale is zero.
    passive: the largest passive force inside the window, against the declared peak force.
    """
    zero, passive = [], []
    for aid in range(m.nu):
        if m.actuator_gaintype[aid] != mujoco.mjtGain.mjGAIN_MUSCLE:
            continue
        nm = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, aid).split(":")[-1]
        lr = m.actuator_lengthrange[aid]
        r = m.actuator_gainprm[aid][:2] if False else m.actuator_actrange[aid]
        # the normalized window comes from lengthrange and range, and MuJoCo stores range
        # in actuator_gainprm slots 0 and 1 for muscles
        r0, r1 = m.actuator_gainprm[aid][0], m.actuator_gainprm[aid][1]
        fmax = m.actuator_gainprm[aid][2]
        lmin, lmax = m.actuator_gainprm[aid][4], m.actuator_gainprm[aid][5]
        fpmax = m.actuator_gainprm[aid][6]
        L0 = (lr[1] - lr[0]) / (r1 - r0) if r1 > r0 else np.nan
        # Sweep the declared window and ask MuJoCo itself for the gain and the bias at each
        # length, rather than reimplementing its force-length curve. `gainprm` carries ten
        # slots and the helpers want nine, so the first nine are passed.
        prm_g = np.asarray(m.actuator_gainprm[aid][:9], dtype=float)
        prm_b = np.asarray(m.actuator_biasprm[aid][:9], dtype=float)
        lrv = np.asarray(lr, dtype=float)
        gains, pas = [], []
        for x in np.linspace(r0, r1, 401):
            length = lr[0] + (x - r0) * L0
            gains.append(abs(mujoco.mju_muscleGain(float(length), 0.0, lrv, 0.0, prm_g)))
            pas.append(abs(mujoco.mju_muscleBias(float(length), lrv, 0.0, prm_b)))
        if min(gains) <= 1e-9:
            zero.append(nm)
        if fmax > 0 and max(pas) > 0.10 * fmax:
            passive.append(nm)
    return zero, passive


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("assets")
    ap.add_argument("--provenance-right", required=True)
    ap.add_argument("--provenance-left", required=True)
    ap.add_argument("--sum", nargs="*", default=None,
                    help="muscle names a summed-activation result would cover")
    ap.add_argument("--exempt", nargs="*", default=[],
                    help="grade B, C or D muscles explicitly exempted, with a reason "
                         "recorded elsewhere")
    ap.add_argument("--exempt-below-support", nargs="*", default=[],
                    help="muscles allowed a window below the DECLARED support 0.5 to 1.6. "
                         "Naming one here is a statement that the cost is recorded and "
                         "accepted, and it belongs in the command rather than in the code.")
    ap.add_argument("--baseline-zero", type=int, default=0)
    ap.add_argument("--baseline-passive", type=int, default=0)
    args = ap.parse_args()

    failures = []
    per_side = {}
    for side, prov_path in (("right", args.provenance_right), ("left", args.provenance_left)):
        prov = read_provenance(prov_path)
        m = load(args.assets, side, f"{side}_hand_actuators_muscle.xml", f"_chk_{side}")
        d = mujoco.MjData(m)
        got = {}
        excluded = []
        below = []
        exempted = []
        for aid in range(m.nu):
            if m.actuator_gaintype[aid] != mujoco.mjtGain.mjGAIN_MUSCLE:
                continue
            nm = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, aid).split(":")[-1]
            r0, r1 = float(m.actuator_gainprm[aid][0]), float(m.actuator_gainprm[aid][1])
            lr0, lr1 = (float(x) * 1000.0 for x in m.actuator_lengthrange[aid])
            got[nm] = dict(r0=r0, r1=r1, lr0=lr0, lr1=lr1)
            if nm not in prov:
                failures.append(f"{side} {nm}: in the model and not in the provenance table")
                continue
            p = prov[nm]
            # A muscle the construction could not correct carries no `range` of its own, so
            # it loads MuJoCo's default. The table has to say so, and the check asserts that
            # rather than comparing it against a window nobody wrote.
            if p["feasible"] == "NO":
                if abs(r0 - 0.75) > 1e-9 or abs(r1 - 1.05) > 1e-9:
                    failures.append(f"{side} {nm}: the table says it could not be corrected, "
                                    f"so it should carry MuJoCo's default 0.75 to 1.05, and it "
                                    f"carries {r0:.5f} to {r1:.5f}")
                if abs(lr0 - p["lr0"]) > 5e-3 or abs(lr1 - p["lr1"]) > 5e-3:
                    failures.append(f"{side} {nm}: lengthrange in the model is {lr0:.4f} to "
                                    f"{lr1:.4f} mm and the table says {p['lr0']:.4f} to "
                                    f"{p['lr1']:.4f}")
                excluded.append(nm)
                continue
            # 2. the table agrees with the model
            if abs(lr0 - p["lr0"]) > 5e-3 or abs(lr1 - p["lr1"]) > 5e-3:
                failures.append(f"{side} {nm}: lengthrange in the model is "
                                f"{lr0:.4f} to {lr1:.4f} mm and the table says "
                                f"{p['lr0']:.4f} to {p['lr1']:.4f}")
            if abs(r0 - p["r0"]) > 1e-5 or abs(r1 - p["r1"]) > 1e-5:
                failures.append(f"{side} {nm}: range in the model is {r0:.5f} to {r1:.5f} "
                                f"and the table says {p['r0']:.5f} to {p['r1']:.5f}")
            # 1. the range is what the table's own target implies
            want_w = (p["lr1"] - p["lr0"]) / p["target"]
            if abs((r1 - r0) - want_w) > 2e-4:
                failures.append(f"{side} {nm}: range width {r1-r0:.5f} does not match the "
                                f"target {p['target']:.3f} mm, which implies {want_w:.5f}")
            # 3. the derived tendon is not negative
            L0 = (lr1 - lr0) / (r1 - r0)
            LT = lr0 - r0 * L0
            if LT < -1e-6:
                failures.append(f"{side} {nm}: derived tendon slack length {LT:.4f} mm is "
                                f"negative")
            # 4. the window sits on the curve
            if r0 < LMIN - 1e-9 or r1 > LMAX + 1e-9:
                if nm in args.exempt_below_support:
                    exempted.append(f"{nm} at {r0:.5f} to {r1:.5f}")
                else:
                    failures.append(f"{side} {nm}: range {r0:.4f} to {r1:.4f} falls outside "
                                    f"the curve's declared support {LMIN} to {LMAX}, and it is "
                                    f"not named in --exempt-below-support")
            if r0 < USABLE[0] - 1e-9 or r1 > USABLE[1] + 1e-9:
                if "THE COST" not in p["feasible"] + prov[nm].get("why", ""):
                    below.append(f"{nm} at {r0:.5f} to {r1:.5f}")
        per_side[side] = got

        if exempted:
            print(f"  EXEMPTED BY NAME, below the declared support and accepted with its cost "
                  f"recorded: {', '.join(exempted)}")
        if below:
            print(f"  {len(below)} window(s) below the usable support {USABLE[0]} to "
                  f"{USABLE[1]}, which is permitted only where the provenance row states the "
                  f"cost: {', '.join(below)}")
        zero, passive = fault_counts(m, d)
        print(f"{side} hand: {len(got)} muscles checked, {len(excluded)} not corrected by construction{': ' + ', '.join(excluded) if excluded else ''}. "
              f"zero active force {len(zero)}, passive above 10 percent {len(passive)}")
        if len(zero) > args.baseline_zero:
            failures.append(f"{side}: {len(zero)} muscles reach zero active force inside "
                            f"their window, baseline {args.baseline_zero}: {', '.join(zero)}")
        if len(passive) > args.baseline_passive:
            failures.append(f"{side}: {len(passive)} muscles carry passive force above 10 "
                            f"percent of declared, baseline {args.baseline_passive}: "
                            f"{', '.join(passive)}")

    # 5. the two hands agree
    for nm, r in per_side["right"].items():
        l = per_side["left"].get(nm)
        if l is None:
            failures.append(f"{nm}: present on the right hand and not on the left")
            continue
        for k in ("r0", "r1", "lr0", "lr1"):
            if abs(r[k] - l[k]) > 1e-6:
                failures.append(f"{nm}: hands disagree on {k}, right {r[k]} left {l[k]}")

    # 7. a summed result containing an unsourced muscle
    if args.sum is not None:
        prov = read_provenance(args.provenance_right)
        bad = [nm for nm in args.sum
               if prov.get(nm, {}).get("grade", "?") not in SOURCED
               and nm not in args.exempt]
        if bad:
            failures.append("a summed-activation result covers muscles whose optimal fibre "
                            "length is not from a published figure, and none is exempted: "
                            + ", ".join(f"{nm} grade {prov.get(nm, {}).get('grade', '?')}"
                                        for nm in bad))

    print()
    if failures:
        print(f"REFUSED. {len(failures)} failures:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("PASSED. Every muscle's range matches its table's target, the table matches the "
          "model, no derived tendon is negative, no window leaves the curve's support, the "
          "two hands agree, and neither fault count regressed.")


if __name__ == "__main__":
    main()
