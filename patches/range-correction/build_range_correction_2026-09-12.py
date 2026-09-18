#!/usr/bin/env python3
"""Build the all-44 `range` correction against the mixed target, and its provenance table.

Schumann Lab, biomechanical piano model, `MUSIC-Hand-v0.15`. Written September 12, 2026.

WHY. Elizabeth Schumann answered D3 on September 10, 2026 with "Do it," accepted the mixed
target and its four documentation requirements on September 12, 2026, and cleared the
ordering the same day: "Since range does not have to wait on the wrapping surface, perhaps
we move forward." This is that correction.

WHAT `range` DOES, IN ONE PARAGRAPH. MuJoCo takes no attribute for optimal fibre length and
none for tendon slack length. It derives both from `lengthrange`, the muscle's reachable
length, and `range`, the same interval in units of the muscle's own optimal fibre length:

    L0  = (lengthrange[1] - lengthrange[0]) / (range[1] - range[0])
    L_T =  lengthrange[0] - range[0] * L0

Every muscle in this model leaves `range` at MuJoCo's default of 0.75 to 1.05, which makes
the derived L0 about three times too wide, so no muscle loses appreciable force at any
length. A model whose muscles never weaken at a wide span cannot answer whether a wide span
costs effort, which is the study's question.

THE CONSTRUCTION, which is four conditions and no free parameters left over.
  1. The derived optimal fibre length equals the target:   range[1] - range[0] = span / L0*
  2. The derived tendon slack length is not negative:      range[0] <= lengthrange[0] / L0*
  3. The muscle stays on its own force-length curve:       0.5 <= range[0], range[1] <= 1.6,
     those being `lmin` and `lmax` from `gainprm` for every muscle in this model
  4. Within what 1 to 3 leave, the window is centred in the curve's support, which puts the
     muscle's mid-range length at the peak of its force-length curve

THE MIXED TARGET, which is what she accepted.
  sourced   L0* is McFarland's published optimal fibre length for the same muscle, for the
            30 muscles that map to his model by name. `AdP` maps to two of his units and
            takes their force-weighted mean, which is the convention this project already
            uses in `analyse_force_loss_across_excursion_2026-09-07.py`.
  fallback  for the other 14, L0* = span / 1.10, which is the value that makes the muscle's
            reachable travel exactly fill its force-length curve. It uses no published
            figure and invents none.

THE LENGTH WINDOW THIS IS COMPUTED AGAINST, and it is a change of instrument that she
should know about. `lengthrange` is measured here over postures in which no two of the
hand's own geoms interpenetrate, rather than over the whole declared joint box. The reason
is the finding of September 12, 2026: over the whole box `AdP` admits no `range` at all, and
the postures responsible have the thumb 5.7 mm inside the second metacarpal and 10.3 mm
inside the little finger. The filter is applied to all 44 muscles rather than to `AdP`
alone, because one instrument for all 44 is the only defensible choice, and the per-muscle
table below reports what it moves.

WHAT THIS WRITES. Two drop-in actuator files, one per hand, in a dated output folder, plus
the provenance table requirement 1 asks for, generated from the built model rather than
typed. **It modifies nothing in the Workspace and nothing in the model archive.**
"""
import argparse
import itertools
import os
import re
import shutil

import mujoco
import numpy as np

PROBE = ('<mujoco model="probe">\n'
         '  <include file="defaults.xml"/>\n'
         '  <include file="{side}_assets/{side}_hand_definition_meta.xml"/>\n'
         '  <include file="{side}_assets/{side}_hand_definition_tendons.xml"/>\n'
         '  <include file="{side}_assets/{act}"/>\n'
         '  <worldbody><include file="{side}_assets/{side}_hand_freeroot.xml"/></worldbody>\n'
         '</mujoco>\n')

# MUSIC-Hand name -> McFarland name or names, from
# `analyse_force_loss_across_excursion_2026-09-07.py`. The eleven finger intrinsic mappings
# in that table are an INFERENCE from the An and Chao naming convention and are not used as
# a source here: every one of them falls in the fallback set below.
MAP = {
    "ECRL": ["ECRL"], "ECRB": ["ECRB"], "ECU": ["ECU"], "FCR": ["FCR"],
    "FCU": ["FCU"], "PL": ["PL"], "EPL": ["EPL"], "EPB": ["EPB"],
    "FPL": ["FPL"], "APL": ["APL"], "EIP": ["EIP"], "EDM": ["EDM"],
    "FDS2": ["FDSI"], "FDS3": ["FDSM"], "FDS4": ["FDSR"], "FDS5": ["FDSL"],
    "FDP2": ["FDPI"], "FDP3": ["FDPM"], "FDP4": ["FDPR"], "FDP5": ["FDPL"],
    "EDC2": ["EDCI"], "EDC3": ["EDCM"], "EDC4": ["EDCR"], "EDC5": ["EDCL"],
    "OP": ["OPP"], "APB": ["APB"], "FPB": ["FPB"], "AdP": ["ADPt", "ADPo"],
    "ADM": ["ADM"], "FDM": ["FDM"],
}
# The fallback set, and the grade each member carries, from
# `Findings, whether the mixed range correction can be documented responsibly 2026-09-10.md`.
FALLBACK = {
    "RI2": "B", "RI3": "B", "RI4": "B", "RI5": "B",
    "LU_RB2": "C", "LU_RB3": "C", "LU_RB4": "C", "LU_RB5": "C",
    "UI_UB2": "C", "UI_UB3": "C", "UI_UB4": "C",
    "PQ": "D", "PT": "D", "UI_UB5": "D",
}
# The force-length curve's support is 0.5 to 1.6 from `gainprm`, but at both ends of that
# interval the active force is zero, so a window filling it has a reachable posture where
# the muscle can produce nothing. That is the same fault the September 10 repair removed.
# The usable support is where active force is at least 10 percent of peak, measured from
# MuJoCo's own curve on September 12, 2026: 0.6117 to 1.4659, a width of 0.8542 rather
# than 1.100. The 10 percent figure mirrors the threshold the project already uses for
# passive force.
# The usable support, measured from MuJoCo's own force-length curve on September 12, 2026 and
# ROUNDED INWARD. The exact interval where active force is at or above a tenth of peak is
# 0.611803 to 1.465836; the first build rounded it outward to 0.6117 and 1.4659, which let 18
# accepted windows sit at 9.98 percent of peak rather than at or above a tenth.
LMIN, LMAX = 0.61181, 1.46583
CURVE_SUPPORT = (0.5, 1.6)


def load(assets, side, actfile, stem):
    p = os.path.join(assets, stem + ".xml")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(PROBE.format(side=side, act=actfile))
    try:
        return mujoco.MjModel.from_xml_path(p)
    finally:
        os.remove(p)


def read_mcfarland(path):
    """Optimal fibre length and peak force per muscle, from the lab's own extract."""
    out = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or line.startswith("muscle"):
            continue
        f = line.split("\t")
        if len(f) >= 3:
            out[f[0].strip()] = {"F": float(f[1]), "L0": float(f[2])}
    return out


def moving_joints(m, d, tid, q0):
    out = []
    for j in range(m.njnt):
        if m.jnt_type[j] in (mujoco.mjtJoint.mjJNT_FREE, mujoco.mjtJoint.mjJNT_BALL):
            continue
        if not m.jnt_limited[j]:
            continue
        adr = m.jnt_qposadr[j]
        lo, hi = m.jnt_range[j]
        d.qpos[:] = q0
        mujoco.mj_forward(m, d)
        base = d.ten_length[tid]
        q = q0.copy(); q[adr] = lo
        d.qpos[:] = q; mujoco.mj_forward(m, d); a = d.ten_length[tid]
        q = q0.copy(); q[adr] = hi
        d.qpos[:] = q; mujoco.mj_forward(m, d); b = d.ten_length[tid]
        if max(abs(a - base), abs(b - base)) > 1e-6:
            out.append((adr, lo, hi))
    return out


def admissible(d):
    """No two of the hand's own geoms interpenetrate. Strict: margin proximity is allowed."""
    for c in range(d.ncon):
        if d.contact[c].dist < 0.0:
            return False
    return True


def window(m, d, tid, js, q0, nrand, grid, seed=0):
    """The reachable length window, over the whole box and with interpenetration excluded."""
    adrs = [a for a, _, _ in js]
    los = np.array([l for _, l, _ in js])
    his = np.array([h for _, _, h in js])
    rng = np.random.default_rng(seed)
    samples = []
    if len(adrs) <= 14:
        samples += list(itertools.product(*[(l, h) for l, h in zip(los, his)]))
    if len(adrs) <= 3 and grid:
        samples += list(itertools.product(*[np.linspace(l, h, grid)
                                            for l, h in zip(los, his)]))
    samples += [tuple(rng.uniform(los, his)) for _ in range(nrand)]
    fmin, fmax = np.inf, -np.inf
    cmin, cmax = np.inf, -np.inf
    nok = 0
    for combo in samples:
        q = q0.copy()
        for adr, v in zip(adrs, combo):
            q[adr] = v
        d.qpos[:] = q
        mujoco.mj_forward(m, d)
        L = d.ten_length[tid]
        fmin = min(fmin, L); fmax = max(fmax, L)
        if admissible(d):
            nok += 1
            cmin = min(cmin, L); cmax = max(cmax, L)
    return fmin, fmax, cmin, cmax, nok, len(samples)


def solve_range(lr0, lr1, target, rest=None):
    """range[0] and range[1] for a target optimal fibre length. Millimeters in, unitless out.

    THE FOUR CONDITIONS, and what happens when they cannot all hold.
      1. the derived optimal fibre length equals the target:  range[1] - range[0] = span / target
      2. the derived tendon slack length is not negative:     range[0] <= lengthrange[0] / target
      3. the muscle stays where it can produce force:         LMIN <= range[0], range[1] <= LMAX
      4. the model's default posture maps to a normalised length at or just below 1.0, the peak
         of the force-length curve, falling back to centring the window where the travel makes
         that impossible

    WHERE 2 AND 3 CANNOT BOTH HOLD, CONDITION 2 WINS AND THE COST IS RECORDED. Elizabeth
    Schumann, September 10, 2026, answering D2: "find a solution so that we don't continue to
    be impossible." So the muscle keeps a physically possible tendon and the row says that its
    window starts below the usable support, meaning that at its most contracted reachable
    posture it produces under a tenth of its peak force. `AdP` is the only muscle in this model
    in that position, and its wrapping surface is what removes the trade.

    `lengthrange` is quantised to the precision the file carries, 1e-6 m, before anything is
    solved, because the model loads the quantised value.
    """
    lr0 = round(lr0, 3)
    lr1 = round(lr1, 3)
    span = lr1 - lr0
    w = span / target                      # condition 1
    r0_cap_tendon = lr0 / target           # condition 2
    r0_cap_curve = LMAX - w                # condition 3, upper end
    hi = min(r0_cap_tendon, r0_cap_curve)
    lo = LMIN
    TOL = 1e-9
    reasons = []
    notes = []

    if w > (LMAX - LMIN) + TOL:
        reasons.append("travel exceeds the usable support, a window %.4f wide cannot fit "
                       "inside %.4f to %.4f" % (w, LMIN, LMAX))

    # condition 4, and it is a preference rather than a constraint
    if rest is not None and span > 0:
        anchored = 1.0 - (rest - lr0) / target
    else:
        anchored = None
    centred = (LMIN + LMAX) / 2.0 - w / 2.0
    want = centred if anchored is None else anchored
    if anchored is not None and anchored < lo - TOL:
        notes.append("the default posture sits %.3f of the way up this muscle's own travel, so "
                     "no window puts it at or below the force peak; the window is centred "
                     "instead" % ((rest - lr0) / span if span > 0 else float("nan")))
        want = centred

    below_support = False
    if hi >= lo - TOL:
        r0 = float(np.clip(want, lo, min(hi, LMAX - w)))
    else:
        # Conditions 2 and 3 conflict. Condition 2 wins, per her ruling of September 10, 2026.
        r0 = float(min(hi, r0_cap_tendon))
        below_support = True
        reasons.append("no window is both physically possible and inside the usable support: "
                       "keeping the derived tendon non-negative caps range[0] at %.4f and the "
                       "support starts at %.4f. THE PHYSICALLY POSSIBLE SIDE IS TAKEN, on her "
                       "ruling of September 10, 2026 that the model must stop being impossible. "
                       "THE COST: at its most contracted reachable posture this muscle produces "
                       "under a tenth of its peak force" % (r0_cap_tendon, LMIN))

    # The file carries five decimals, so round both ends to it and then verify the derived
    # tendon on the ROUNDED pair, because that is the pair the model loads. Rounding r1 down
    # shrinks the window, which raises the derived optimal fibre length and can push the tendon
    # just below zero; that is how APB came out at minus 0.0016 mm and then minus 0.0011 mm.
    # STEP DOWN, which lowers range[0] and therefore RAISES the derived tendon. The earlier
    # version floored first and then required range[0] to have risen back to the support's lower
    # bound, a test that stepping down can never satisfy, so it ran its full 200 steps and left
    # LU_RB2 and LU_RB5 0.00200 below the bound and wrongly refused.
    r0 = round(r0, 5)
    for _ in range(400):
        ra, rb = round(r0, 5), round(r0 + w, 5)
        if rb <= ra:
            break
        L0r = (lr1 - lr0) / (rb - ra)
        if lr0 - ra * L0r >= 0.0:
            break
        r0 = round(r0 - 1e-5, 5)
    r0, r1 = round(r0, 5), round(r0 + w, 5)
    L0 = span / (r1 - r0)
    LT = lr0 - r0 * L0

    # A refusal must always carry its reason.
    if LT < -1e-9 and not reasons:
        reasons.append("after rounding to the file's five decimals the derived tendon slack "
                       "length is %.4f mm, which is negative" % (LT,))
    if r0 < LMIN - 1e-9 and not below_support:
        notes.append("after rounding, range[0] is %.5f, %.5f below the usable support's %.4f"
                     % (r0, LMIN - r0, LMIN))

    # FEASIBLE means the file gets a `range`. A muscle below the support is still corrected, and
    # its cost travels with it; only a negative derived tendon is a refusal now.
    feasible = LT >= -1e-9
    return dict(r0=r0, r1=r1, w=w, L0=L0, LT=LT, lr0=lr0, lr1=lr1,
                feasible=feasible, below_support=below_support,
                reasons=reasons + notes,
                r0_cap_tendon=r0_cap_tendon, r0_cap_curve=r0_cap_curve)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--mcfarland", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--nrand", type=int, default=1200)
    ap.add_argument("--grid", type=int, default=17)
    ap.add_argument("--repair", default=None,
                    help="folder holding the six muscle repair files, copied in before "
                         "measuring, because that is the tree the lab will run")
    args = ap.parse_args()

    mcf = read_mcfarland(args.mcfarland)
    os.makedirs(args.out, exist_ok=True)
    if args.repair:
        n = 0
        for side, sub in (("right", "right_assets"), ("left", "left_assets")):
            src_dir = os.path.join(args.repair, f"{side}_assets")
            if not os.path.isdir(src_dir):
                continue
            for f in sorted(os.listdir(src_dir)):
                if f.endswith(".xml"):
                    shutil.copy(os.path.join(src_dir, f),
                                os.path.join(args.scratch, "assets", sub, f))
                    n += 1
        print(f"copied {n} muscle repair files into the scratch tree before measuring. "
              f"THE SCRATCH TREE IS NOT THE WORKSPACE.")
    print(f"MuJoCo {mujoco.__version__}. McFarland units read: {len(mcf)}.")
    print(f"The force-length curve's support is {LMIN} to {LMAX}, from `gainprm`.\n")

    rows_by_side = {}
    for side in ("right", "left"):
        p = side[0].upper()
        assets = os.path.join(args.scratch, "assets")
        m = load(assets, side, f"{side}_hand_actuators_muscle.xml", f"_rc_{side}")
        d = mujoco.MjData(m)
        q0 = m.qpos0.copy()
        rows = []
        for aid in range(m.nu):
            if m.actuator_trntype[aid] != mujoco.mjtTrn.mjTRN_TENDON:
                continue
            full = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, aid)
            name = full.split(":")[-1]
            tid = m.actuator_trnid[aid][0]
            js = moving_joints(m, d, tid, q0)
            if not js:
                continue
            fmin, fmax, cmin, cmax, nok, n = window(m, d, tid, js, q0,
                                                    args.nrand, args.grid)
            d.qpos[:] = q0
            mujoco.mj_forward(m, d)
            rest = round(d.ten_length[tid] * 1000.0, 3)
            declared = m.actuator_lengthrange[aid] * 1000.0
            # Quantise to the precision the file carries, 1e-6 m, ONCE and here, so that
            # the target, the solved range, the written attribute and every later check all
            # rest on the same number. Doing it later left the two hands disagreeing in the
            # fifth decimal and made a window exactly as wide as the support look too wide.
            lr0, lr1 = round(cmin * 1000.0, 3), round(cmax * 1000.0, 3)
            if name in MAP:
                keys = MAP[name]
                tot = sum(mcf[k]["F"] for k in keys)
                target = sum(mcf[k]["L0"] * mcf[k]["F"] for k in keys) / tot
                grade, src = "A", "+".join(keys)
            else:
                target = (lr1 - lr0) / (LMAX - LMIN)
                grade = FALLBACK.get(name, "?")
                src = "fallback, span over %.4f" % (LMAX - LMIN,)
            sol = solve_range(lr0, lr1, target, rest=rest)
            # THE THIRD CASE, AND IT IS THE ONE THE FOUR DOCUMENTATION REQUIREMENTS EXIST FOR.
            # A muscle can have a published optimal fibre length that the model cannot honour,
            # because the model's reachable travel is wider than 1.10 times that figure and no
            # window of that width fits inside the force-length curve's own support. Honouring
            # the published figure would put the muscle off the bottom of its curve, which is
            # the fault the September 10 repair existed to remove. Such a muscle takes the
            # geometric fallback and its grade records that it did.
            # THE ORDER OF PREFERENCE, and getting it wrong pushed six muscles below the
            # curve's declared support on the eleventh build. Try the published target first.
            # If that cannot be honoured cleanly, meaning it is either infeasible or it only
            # works by letting condition 2 override condition 3, try the fallback target, which
            # is a wider optimal fibre length and therefore a narrower window in normalised
            # units and more room. Only if the fallback also fails does the trade get taken.
            if grade == "A" and (not sol["feasible"] or sol["below_support"]):
                published = target
                target = (lr1 - lr0) / (LMAX - LMIN)
                sol = solve_range(lr0, lr1, target, rest=rest)
                grade = "A-f"
                src = ("fallback, span over %.4f, because %s's published %.2f mm needs a window "
                       "%.3f wide and the usable support is %.4f" %
                       (LMAX - LMIN, "+".join(keys), published,
                        (lr1 - lr0) / published, LMAX - LMIN))
            rows.append(dict(name=name, actuator=full, aid=aid, grade=grade, source=src,
                             target=target, declared=tuple(declared),
                             full=(fmin * 1000, fmax * 1000), lr=(lr0, lr1),
                             nok=nok, n=n, njoint=len(js), **sol))
        rows_by_side[side] = rows
        print(f"{side} hand: {len(rows)} tendon-driven muscles measured")

    # ---- the provenance table, generated rather than typed
    for side, rows in rows_by_side.items():
        path = os.path.join(args.out, f"PROVENANCE, every muscle's range and where its target "
                                      f"came from, {side} hand 2026-09-12.tsv")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# Generated by build_range_correction_2026-09-12.py from the built model.\n")
            fh.write("# Not typed. Requirement 1 of the four Elizabeth Schumann accepted on "
                     "September 12, 2026.\n")
            fh.write("# lengthrange is measured over postures with no interpenetration of the "
                     "hand's own geoms.\n")
            fh.write("# grade A: McFarland's published optimal fibre length under a matching name. "
                     "A-f: a published figure exists and the model cannot honour it, so the "
                     "fallback was used and the reason is in why_not. B: naming inferred. "
                     "C: lumped unit, no single figure can be right. D: no counterpart.\n")
            fh.write("muscle\tgrade\ttarget_L0_mm\tsource\tlengthrange_lo_mm\tlengthrange_hi_mm"
                     "\trange_lo\trange_hi\tderived_L0_mm\tderived_tendon_mm\tfeasible"
                     "\tdeclared_lo_mm\tdeclared_hi_mm\twhy_not\n")
            for r in rows:
                fh.write("\t".join([
                    r["name"], r["grade"], f"{r['target']:.3f}", r["source"],
                    f"{r['lr'][0]:.4f}", f"{r['lr'][1]:.4f}",
                    f"{r['r0']:.5f}", f"{r['r1']:.5f}",
                    f"{r['L0']:.4f}", f"{r['LT']:.4f}",
                    "yes" if r["feasible"] else "NO",
                    f"{r['declared'][0]:.3f}", f"{r['declared'][1]:.3f}",
                    "; ".join(r["reasons"]),
                ]) + "\n")
        print(f"wrote {os.path.basename(path)}")

    # ---- the drop-in actuator files
    for side, rows in rows_by_side.items():
        src = os.path.join(args.scratch, "assets", f"{side}_assets",
                           f"{side}_hand_actuators_muscle.xml")
        text = open(src, encoding="utf-8").read()
        n = 0
        for r in rows:
            pat = re.compile(r'(<muscle\s+name="%s"[^>]*?)(\s*/>)' % re.escape(r["actuator"]))
            mm = pat.search(text)
            if not mm:
                print(f"  WARNING: {r['actuator']} not matched in {side} actuator file")
                continue
            head = mm.group(1)
            head = re.sub(r'\s+range="[^"]*"', "", head)
            head = re.sub(r'\s+lengthrange="[^"]*"',
                          ' lengthrange="%.6f %.6f"' % (r["lr"][0] / 1000.0,
                                                        r["lr"][1] / 1000.0),
                          head)
            if not r["feasible"]:
                # NOT CORRECTED. The muscle keeps its measured `lengthrange`, which is a
                # measurement, and carries NO `range`, so it falls back to MuJoCo's default
                # and the provenance table says why. Writing a window the construction
                # itself rejects would be the quiet mixing the requirements exist to stop.
                text = text[:mm.start()] + head + mm.group(2) + text[mm.end():]
                continue
            head += ' range="%.5f %.5f"' % (r["r0"], r["r1"])
            text = text[:mm.start()] + head + mm.group(2) + text[mm.end():]
            n += 1
        hdr = ("<!-- RANGE CORRECTION, all 44 muscles, mixed target. Schumann Lab, "
               "September 12, 2026.\n"
               "     Built by build_range_correction_2026-09-12.py. Every `range` and every\n"
               "     `lengthrange` in this file is generated, and the provenance table beside\n"
               "     it says where each target came from and what grade it carries.\n"
               "     DO NOT hand-edit. Rebuild instead. -->\n")
        out = os.path.join(args.out, f"{side}_hand_actuators_muscle.xml")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(hdr + text)
        print(f"wrote {side}_hand_actuators_muscle.xml, {n} muscles rewritten")

    # ---- report
    print("\n  muscle     grade   target      lengthrange measured        range          "
          "derived L0   tendon   verdict")
    for r in rows_by_side["right"]:
        print(f"  {r['name']:10s} {r['grade']:^5s} {r['target']:8.2f}  "
              f"{r['lr'][0]:8.3f} {r['lr'][1]:8.3f}   "
              f"{r['r0']:6.3f} {r['r1']:6.3f}   {r['L0']:8.2f} {r['LT']:8.2f}   "
              f"{'ok' if r['feasible'] else 'NOT FEASIBLE: ' + '; '.join(r['reasons'])}")
    bad = [r for r in rows_by_side["right"] if not r["feasible"]]
    print(f"\n  feasible: {len(rows_by_side['right']) - len(bad)} of "
          f"{len(rows_by_side['right'])}")
    for r in bad:
        print(f"    {r['name']}: {'; '.join(r['reasons'])}")

    # how far the declared windows move, which is the change of instrument made visible
    print("\n  where the measured window differs from the declared one by more than 1 mm:")
    for r in rows_by_side["right"]:
        d0 = r["lr"][0] - r["declared"][0]
        d1 = r["lr"][1] - r["declared"][1]
        if abs(d0) > 1.0 or abs(d1) > 1.0:
            print(f"    {r['name']:10s} declared {r['declared'][0]:8.3f} {r['declared'][1]:8.3f}"
                  f"   measured {r['lr'][0]:8.3f} {r['lr'][1]:8.3f}"
                  f"   moves {d0:+8.3f} {d1:+8.3f}")


if __name__ == "__main__":
    main()
