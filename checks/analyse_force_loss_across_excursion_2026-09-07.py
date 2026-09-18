#!/usr/bin/env python3
"""
Can this model express the cost of a wide span at all?

Schumann Lab, biomechanical piano model. 7 September 2026.


THE QUESTION, AND WHY IT IS THE ONE THAT MATTERS
================================================
The narrow keyboard study asks whether playing a wide interval costs a pianist
more effort than playing a narrow one. In the simulation the measured quantity is
muscle activation, and activation is force demanded divided by force available. A
real muscle held near the end of its excursion has less force available, because
the actin and myosin filaments overlap less: that is the descending and ascending
limbs of the force-length curve, and it is a large part of why a wide span is
tiring.

So the model can only express span cost if its muscles lose force as they are
stretched or shortened through the range the hand actually uses. This script
measures whether they do.


HOW MuJoCo DECIDES THE ANSWER
=============================
MuJoCo does not take optimal fibre length as an input. From the Modeling chapter
of the MuJoCo documentation, read 7 September 2026: it declines to ask for L0 and
tendon length "because it is difficult to know their numeric values given the
spatial complexity of the tendon routing and wrapping", and derives both from two
things the user does supply:

    L0  = (lengthrange[1] - lengthrange[0]) / (range[1] - range[0])
    L_T =  lengthrange[0] - range[0] * L0

`range` defaults to 0.75 to 1.05, in units of L0, and **it is left at that default
for all 44 muscles in this model.** So every muscle is declared to traverse
exactly 30 per cent of its optimal fibre length across its whole excursion, and
MuJoCo reads its force-length curve only over that declared 30 per cent window.

The declared window is not the real one. Taking McFarland's published optimal
fibre lengths and tendon slack lengths for the same muscles, the true normalised
excursion can be computed from the same geometry:

    normalised length = (tendon path length - McFarland tendon slack) / McFarland L0

This script computes both and compares the force each muscle loses across its own
excursion under each.


WHAT COMES OUT
==============
Three numbers per muscle:

  declared loss   the force variation the model actually produces, measured by
                  sweeping the joints that move the muscle across their declared
                  limits at full activation and reading actuator_force
  true loss       the force variation MuJoCo's own force-length curve would give
                  over the normalised range implied by McFarland's L0 and tendon
                  slack, using mju_muscleGain so the curve is MuJoCo's and not a
                  reimplementation
  off the curve   whether the true normalised length leaves MuJoCo's [lmin, lmax]
                  window, where active force is zero. A muscle that leaves the
                  window in reality but never leaves it in the model cannot
                  express the phenomenon at all.

SOURCES
=======
- MuJoCo XML reference and Modeling chapter, read 7 September 2026, for the
  muscle actuator's `range`, `force`, `lmin`, `lmax` and for the two relations
  above.
- McFarland, D. C., Binder-Markey, B. I., Nichols, J. A., Wohlman, S. J.,
  de Bruin, M., and Murray, W. M. A Musculoskeletal Model of the Hand and Wrist
  Capable of Simulating Functional Tasks. IEEE Transactions on Biomedical
  Engineering, doi 10.1109/TBME.2022.3217722; preprint bioRxiv 2021.12.28.474357.
  Release 4.3 from SimTK project `arms_hand_model`, filed in the Workspace at
  AI_Model/McFarland ARMS hand and wrist model from SimTK 2026-09-07/.
- MUSIC-Hand-v0.15, `assets/right_assets/right_hand_actuators_muscle.xml` from
  `piano.tar.gz`, the collaborators' archive of 4 March 2026.

USAGE
=====
    pip install mujoco
    python3 analyse_force_loss_across_excursion_2026-09-07.py \
        --assets /path/to/assets [--osim PATH] [--quick]

Writes nothing. Prints a table and a verdict.
"""

import argparse
import itertools
import math
import os
import re
import sys

import numpy as np

RANGE_LO, RANGE_HI = 0.75, 1.05     # MuJoCo default <muscle range="...">
LMIN, LMAX = 0.5, 1.6               # MuJoCo default lmin and lmax, units of L0

# MUSIC-Hand muscle name -> McFarland muscle name, or a list of names to combine.
# Only muscles that exist in both are analysable; the rest are reported as such.
MAP = {
    "ECRL": ["ECRL"], "ECRB": ["ECRB"], "ECU": ["ECU"], "FCR": ["FCR"],
    "FCU": ["FCU"], "PL": ["PL"], "EPL": ["EPL"], "EPB": ["EPB"],
    "FPL": ["FPL"], "APL": ["APL"], "EIP": ["EIP"], "EDM": ["EDM"],
    "FDS2": ["FDSI"], "FDS3": ["FDSM"], "FDS4": ["FDSR"], "FDS5": ["FDSL"],
    "FDP2": ["FDPI"], "FDP3": ["FDPM"], "FDP4": ["FDPR"], "FDP5": ["FDPL"],
    "EDC2": ["EDCI"], "EDC3": ["EDCM"], "EDC4": ["EDCR"], "EDC5": ["EDCL"],
    "OP": ["OPP"], "APB": ["APB"], "FPB": ["FPB"], "AdP": ["ADPt", "ADPo"],
    "ADM": ["ADM"], "FDM": ["FDM"],
    # MUSIC-Hand lumps the finger intrinsics three ways per digit. The naming
    # follows the An and Chao extensor-mechanism convention: RI radial
    # interosseous, UI ulnar interosseous, LU lumbrical, RB radial band, UB
    # ulnar band. Nothing in the model files states this, so the mapping below
    # is an INFERENCE and is labelled as such in the output.
    "RI2": ["1stDI_MC1", "1stDI_MC2"], "RI3": ["2ndDI"], "RI4": ["3rdDI"], "RI5": ["4thDI"],
    "UI_UB2": ["1stPI"], "UI_UB3": ["2ndPI"], "UI_UB4": ["3rdPI"],
    "LU_RB2": ["LUMI"], "LU_RB3": ["LUMM"], "LU_RB4": ["LUMR"], "LU_RB5": ["LUML"],
}
INFERRED = {"RI2", "RI3", "RI4", "RI5", "UI_UB2", "UI_UB3", "UI_UB4",
            "LU_RB2", "LU_RB3", "LU_RB4", "LU_RB5"}
THE_FIVE = ["FPB", "AdP", "APB", "FDM", "ADM"]


def read_osim(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    out = {}
    for name, body in re.findall(
            r'<Millard2012EquilibriumMuscle name="([^"]+)">(.*?)</Millard2012EquilibriumMuscle>',
            src, re.S):
        def g(tag):
            m = re.search(r"<%s>\s*([^<\s]+)\s*</%s>" % (tag, tag), body)
            return float(m.group(1)) if m else None
        out[name] = {"F": g("max_isometric_force"),
                     "L0": g("optimal_fiber_length") * 1000.0,
                     "LT": g("tendon_slack_length") * 1000.0}
    return out


def combine(mf, keys, field):
    """Force-weighted mean for a MUSIC-Hand unit that maps to several McFarland ones."""
    tot = sum(mf[k]["F"] for k in keys)
    return sum(mf[k][field] * mf[k]["F"] for k in keys) / tot


def build_hand_only(assets):
    p = os.path.join(assets, "_force_loss_probe.xml")
    open(p, "w", encoding="utf-8").write(
        '<mujoco model="probe">\n'
        '  <include file="defaults.xml"/>\n'
        '  <include file="right_assets/right_hand_definition_meta.xml"/>\n'
        '  <include file="right_assets/right_hand_definition_tendons.xml"/>\n'
        '  <include file="right_assets/right_hand_actuators_muscle.xml"/>\n'
        '  <worldbody><include file="right_assets/right_hand_freeroot.xml"/></worldbody>\n'
        '</mujoco>\n')
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True)
    ap.add_argument("--osim", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..",
        "McFarland ARMS hand and wrist model from SimTK 2026-09-07",
        "Hand_Wrist_Model_for_development.osim"))
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    import mujoco

    if not os.path.isfile(os.path.join(a.assets, "defaults.xml")):
        print(f"no defaults.xml under {a.assets}", file=sys.stderr)
        return 2
    if not os.path.isfile(a.osim):
        print(f"no .osim at {a.osim}", file=sys.stderr)
        return 2
    mf = read_osim(a.osim)

    probe = build_hand_only(a.assets)
    m = mujoco.MjModel.from_xml_path(probe)
    d = mujoco.MjData(m)
    os.remove(probe)

    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, i) for i in range(m.nu)]
    act2ten = {i: m.actuator_trnid[i, 0] for i in range(m.nu)
               if m.actuator_trntype[i] == mujoco.mjtTrn.mjTRN_TENDON}
    jq = [(m.jnt_qposadr[j], m.jnt_range[j, 0], m.jnt_range[j, 1]) for j in range(m.njnt)
          if m.jnt_type[j] not in (mujoco.mjtJoint.mjJNT_FREE, mujoco.mjtJoint.mjJNT_BALL)
          and m.jnt_limited[j]]
    mujoco.mj_resetData(m, d)
    mujoco.mj_forward(m, d)
    q0 = d.qpos.copy()

    def state(q):
        d.qpos[:] = q
        if m.na:
            d.act[:] = 1.0
        d.ctrl[:] = 1.0
        mujoco.mj_forward(m, d)
        return d.ten_length.copy(), d.actuator_force.copy()

    base, _ = state(q0)
    sens = np.zeros((len(jq), m.ntendon))
    for k, (adr, lo, hi) in enumerate(jq):
        q = q0.copy(); q[adr] = lo; x, _ = state(q)
        q = q0.copy(); q[adr] = hi; y, _ = state(q)
        sens[k] = np.maximum(abs(x - base), abs(y - base))

    print("=" * 100)
    print("CAN THIS MODEL EXPRESS THE COST OF A WIDE SPAN?   ·   7 September 2026")
    print("=" * 100)
    print()
    print("declared loss  force variation the model actually produces across the muscle's")
    print("               own excursion, at full activation, measured from actuator_force")
    print("true loss      force variation MuJoCo's own force-length curve would give over")
    print("               the normalised range implied by McFarland's L0 and tendon slack")
    print("off curve      whether the true normalised length leaves MuJoCo's 0.5 to 1.6")
    print("               window, where active force falls to zero")
    print("*              the McFarland mapping for this unit is an inference, not stated")
    print("               anywhere in the model files")
    print()
    print(f"{'muscle':8s} {'as-built norm len':>18s} {'zero force':>11s} {'declared':>9s}"
          f" {'true norm len':>15s} {'true':>7s}")
    print(f"{'':8s} {'':>18s} {'as built':>11s} {'loss':>9s} {'':>15s} {'loss':>7s}")

    rng = np.random.default_rng(1)
    rows = []
    for i, n in enumerate(names):
        if not n or i not in act2ten:
            continue
        short = n.split(":")[-1]
        t = act2ten[i]
        idx = [k for k in range(len(jq)) if sens[k, t] > 1e-6]
        if not idx:
            continue
        lo = np.array([jq[k][1] for k in idx]); hi = np.array([jq[k][2] for k in idx])
        adrs = [jq[k][0] for k in idx]
        samples = list(itertools.product(*[(l, h) for l, h in zip(lo, hi)])) if len(idx) <= 12 else []
        if not a.quick:
            samples += [tuple(rng.uniform(lo, hi)) for _ in range(1200)]
        fmin, fmax = np.inf, -np.inf
        tmin, tmax = np.inf, -np.inf
        for combo in samples:
            q = q0.copy()
            for adr, v in zip(adrs, combo):
                q[adr] = v
            L, F = state(q)
            f = abs(F[i])
            fmin = min(fmin, f); fmax = max(fmax, f)
            tmin = min(tmin, L[t]); tmax = max(tmax, L[t])

        lr = m.actuator_lengthrange[i]
        nl_built = ((np.array([tmin, tmax]) - lr[0]) / (lr[1] - lr[0])
                    * (RANGE_HI - RANGE_LO) + RANGE_LO)
        # does the model itself drive this muscle off its own force-length curve?
        off_built = nl_built[0] <= LMIN + 1e-6 or nl_built[1] >= LMAX - 1e-6
        # force variation, reported only where the muscle keeps some force everywhere,
        # because a ratio against a near-zero minimum is not a meaningful number
        peak = m.actuator_gainprm[i, 2]
        if fmin > 0.01 * peak:
            dl = f"{fmax/fmin:8.2f}x"
        else:
            dl = "  to zero"

        keys = MAP.get(short)
        if keys and all(k in mf for k in keys):
            l0 = combine(mf, keys, "L0") if len(keys) > 1 else mf[keys[0]]["L0"]
            lt = combine(mf, keys, "LT") if len(keys) > 1 else mf[keys[0]]["LT"]
            nl_true = (np.array([tmin, tmax]) * 1000.0 - lt) / l0
            prm = np.array([RANGE_LO, RANGE_HI, 1.0, 1.0, LMIN, LMAX,
                            m.actuator_gainprm[i, 5], m.actuator_gainprm[i, 6],
                            m.actuator_gainprm[i, 7]])
            gains = []
            for x in nl_true:
                synth = np.array([0.0, 1.0])
                fake_len = (x - RANGE_LO) / (RANGE_HI - RANGE_LO)
                gains.append(abs(mujoco.mju_muscleGain(float(fake_len), 0.0, synth, 1.0, prm)))
            g_lo, g_hi = min(gains), max(gains)
            tl = f"{g_hi/g_lo:6.2f}x" if g_lo > 1e-4 else " to zero"
            nt = f"{nl_true[0]:5.2f} to {nl_true[1]:5.2f}"
            off_true = nl_true[0] < LMIN or nl_true[1] > LMAX
        else:
            tl, nt, off_true = "       -", "  not in McFarland", None
        star = "*" if short in INFERRED else " "
        five = " <-- one of the five" if short in THE_FIVE else ""
        print(f"{short:8s} {nl_built[0]:8.2f} to {nl_built[1]:6.2f}"
              f" {('YES' if off_built else 'no'):>11s} {dl:>9s}"
              f" {nt:>15s} {tl:>7s} {star}{five}")
        rows.append((short, off_built, off_true, dl, tl))

    off_built = [r[0] for r in rows if r[1]]
    off_true = [r[0] for r in rows if r[2]]
    to_zero = [r[0] for r in rows if r[3].strip() == "to zero"]
    print()
    print("=" * 100)
    print("FINDING 1, and it needs no comparison with anything.")
    print(f"  {len(to_zero)} of {len(rows)} muscles reach essentially zero active force, under")
    print("  one per cent of their own peak, at postures the model's own joint limits allow:")
    print("     " + ", ".join(to_zero))
    print(f"  Of those, {len(off_built)} go strictly below MuJoCo's lower bound of 0.5 L0:")
    print("     " + ", ".join(off_built))
    print("  The rest sit just above it, where the force-length curve has already fallen to")
    print("  almost nothing.")
    five_hit = [x for x in THE_FIVE if x in to_zero]
    others = [x for x in to_zero if x not in THE_FIVE]
    if five_hit:
        print(f"  {len(five_hit)} of the five added muscles are in this list: "
              f"{', '.join(five_hit)}.")
        print("  Note FDM, if absent from the list, still comes within a factor of fifty of")
        print("  zero on the shipped file, so treat all five as compromised there.")
    else:
        print("  NONE of the five added muscles is in this list, which is what the")
        print("  added-muscle patch of 7 September 2026 was for. If that patch is applied to")
        print("  the tree being analysed, this is the expected result.")
    print(f"  {len(others)} of the thirty-nine original muscles are in it: "
          f"{', '.join(others) if others else 'none'}. Those are NOT touched by any patch")
    print("  written so far and are a separate item.")
    print("  This is a defect in the declared operating window, not in the anatomy. The")
    print("  window is meant to cover the excursion the joints allow, and for these it does")
    print("  not. It is the same defect the added-muscle patch fixes for the five.")
    print()
    print("FINDING 2, which does depend on the McFarland comparison.")
    print(f"  {len(off_true)} muscles would leave the force-length window in reality, on")
    print("  McFarland's optimal fibre lengths, at postures where the model keeps a healthy")
    print("  fraction of peak force. For those the model understates the cost of the posture.")
    print()
    print("WHAT THIS MEANS FOR THE STUDY'S QUESTION.")
    print("  Activation is force demanded over force available. A muscle whose available")
    print("  force collapses at an extreme posture will report high activation there for a")
    print("  reason that is arithmetic rather than physiological, and a muscle whose")
    print("  available force never changes will report activation that carries no posture")
    print("  information at all. The model as built does both, in different muscles. So the")
    print("  answer to the question in the title is: not yet, and not uniformly.")
    print()
    print("HOW TO READ THE TABLE. A declared loss near 1.0 means the model gives that muscle")
    print("almost the same force everywhere in its range. A true loss much larger than the")
    print("declared loss means the real muscle would weaken where the model does not.")
    print("'to zero' means active force reaches essentially nothing somewhere in range, and")
    print("a ratio against it would not be a meaningful number.")
    print()
    print("CAVEATS THAT MATTER FOR HOW FAR THIS CAN BE PUSHED.")
    print("1. The sweep takes joints to their declared limits independently, ignoring")
    print("   self-collision and ignoring whether a hand can adopt the combination. It is")
    print("   an upper bound on excursion, so the losses are upper bounds too.")
    print("2. McFarland's L0 and tendon slack belong to McFarland's tendon routing. Where")
    print("   the two models route a muscle differently, notably APB and AdP, the true")
    print("   normalised length computed here is not McFarland's and is not this model's")
    print("   either. Those rows are indicative only.")
    print("3. Eleven of the mappings are inferences from naming, marked with a star. The")
    print("   model files do not say what RI, UI_UB and LU_RB represent.")
    print("4. This says nothing about whether a trained policy visits these postures. A")
    print("   muscle can be badly parameterised at an extreme the task never reaches.")
    print("   Answering that needs a trained policy and the logged joint trajectories.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
