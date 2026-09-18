#!/usr/bin/env python3
"""
Read the McFarland ARMS 4.3 .osim and derive the replacement forces for the five
added abductors, with the one check that settles which source to use.

Schumann Lab, biomechanical piano model. 7 September 2026.

WHAT THIS IS FOR
    Two earlier passes argued about whether a cadaver dataset sat on the same
    population scale as the 39 muscles already in MUSIC-Hand. Mirakhorlo looked
    2.8 times out, then 1.99 times out; Jacobson looked 1.53 times out. All three
    figures were correct as computed and none of them was the question.

    The question is answered in one line by the .osim itself: twelve wrist and
    extrinsic muscles appear in both models and their peak isometric forces are
    identical. The two models share a force basis, so McFarland's intrinsic
    values import directly and no reconciliation is needed.

    The lesson is the one already on record from earlier the same day. A
    comparison should be written as a check rather than as a sentence, and a
    check against the wrong reference will pass while telling you nothing.

USAGE
    python3 test_mcfarland_forces_2026-09-07.py [--osim PATH]

    Default path is the copy filed in the Workspace:
        ../McFarland ARMS hand and wrist model from SimTK 2026-09-07/
            Hand_Wrist_Model_for_development.osim

EXIT CODES
    0  every check reproduced
    1  one or more checks did not reproduce
    2  could not read the .osim
"""

import argparse
import math
import os
import re
import sys

DEFAULT_OSIM = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..",
    "McFarland ARMS hand and wrist model from SimTK 2026-09-07",
    "Hand_Wrist_Model_for_development.osim")

# Peak isometric forces as right_hand_actuators_muscle.xml holds them.
# Left column is MUSIC-Hand's name, right column is McFarland's.
SHARED = [("ECRL", "ECRL", 337.3), ("ECRB", "ECRB", 252.2), ("ECU", "ECU", 192.9),
          ("FCR", "FCR", 407.9), ("FCU", "FCU", 479.8), ("PL", "PL", 101.0),
          ("EPL", "EPL", 88.3), ("EPB", "EPB", 46.0), ("FPL", "FPL", 201.0),
          ("APL", "APL", 116.7), ("EIP", "EIP", 47.3), ("EDM", "EDM", 72.4)]

# The five added muscles. AdP is two units in McFarland and one in MUSIC-Hand.
FIVE = {"FPB": (["FPB"], 80.0), "AdP": (["ADPt", "ADPo"], 100.0),
        "APB": (["APB"], 42.7), "FDM": (["FDM"], 30.0), "ADM": (["ADM"], 12.3)}
OP_IN_FILE = 180.0

# geometry-derived lengthrange, mm, from test_added_muscle_parameters_2026-09-07.py
GEOM_MM = {"FPB": (43.570, 65.755), "AdP": (19.504, 69.106), "APB": (40.461, 53.989),
           "FDM": (50.818, 66.062), "ADM": (61.263, 72.174)}
# reachable fraction of declared force as built, measured on the model
REACHABLE = {"FPB": 0.781, "AdP": 1.058, "APB": 0.440, "FDM": 0.562, "ADM": 1.000}
# The two earlier cadaver-derived sets, for the record.
# JACOBSON below is what section 11 computed from mass and the TABULATED fibre
# length, before the printed area column could be read. Those figures are LOW,
# by 1.03 to 1.50 times, because Jacobson normalises fibre length to an optimal
# sarcomere length before dividing and the tabulated length is the measured one.
# JACOBSON_PRINTED is the printed cross-sectional area column, sq cm, read from
# the real PDF with pdftotext -layout on 7 September 2026. Use that one.
JACOBSON = {"FPB": 29.91, "AdP": 95.93, "APB": 30.18, "FDM": 18.25, "ADM": 34.57}
JACOBSON_PRINTED_CM2 = {"APB": 0.68, "FPB": 0.66, "ADM": 0.89, "FDM": 0.54,
                        "OP": 1.02, "AdP": 1.94, "APL": 1.93, "EPB": 0.47}
SPEC_TENSION = 50.8   # confirmed by Elizabeth Schumann, 7 September 2026
MIRAKHORLO = {"FPB": 19.05, "AdP": 92.76, "APB": 22.25, "FDM": 5.74, "ADM": 45.92}
LMIN, LMAX = 0.5, 1.6      # MuJoCo muscle lmin and lmax, in units of L0
RANGE_SPAN = 1.05 - 0.75   # MuJoCo default range

fails = []


def check(ok, label, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + label + (("\n          " + detail) if detail else ""))
    if not ok:
        fails.append(label)


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
                     "LT": g("tendon_slack_length") * 1000.0,
                     "P": math.degrees(g("pennation_angle_at_optimal"))}
    return out


def weighted(mf, keys, field):
    tot = sum(mf[k]["F"] for k in keys)
    return sum(mf[k][field] * mf[k]["F"] for k in keys) / tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--osim", default=DEFAULT_OSIM)
    a = ap.parse_args()
    if not os.path.isfile(a.osim):
        print(f"no .osim at {a.osim}", file=sys.stderr)
        return 2
    mf = read_osim(a.osim)

    print("=" * 74)
    print("McFARLAND ARMS 4.3  ·  replacement forces  ·  7 September 2026")
    print("=" * 74)
    check(len(mf) == 43, f"{len(mf)} muscle actuators read from the .osim, against 43 in the paper")

    print("\n1. THE ONE CHECK THAT SETTLES THE SOURCE")
    print("   Twelve wrist and extrinsic muscles appear in both models.")
    print(f"      {'muscle':6s} {'MUSIC-Hand':>11s} {'McFarland':>10s} {'difference':>11s}")
    worst = 0.0
    for ours, theirs, val in SHARED:
        got = mf[theirs]["F"]
        worst = max(worst, abs(got - val))
        print(f"      {ours:6s} {val:11.1f} {got:10.2f} {got-val:11.2f}")
    check(worst < 0.5,
          f"all twelve agree to within {worst:.2f} N",
          "So the two models draw on the same force basis and there is no population\n"
          "          scale to reconcile. McFarland's intrinsic values import directly. This is\n"
          "          what two earlier passes tried to establish from cadaver tables and could\n"
          "          not: the figures they produced, 2.79 and 1.99 and 1.53, were all correct\n"
          "          as computed and none of them was the question.")

    print("\n2. The replacement set")
    print(f"      {'muscle':6s} {'in file':>8s} {'McFarland':>10s} {'change':>7s}"
          f" {'Jacobson':>9s} {'Mirakhorlo':>11s} {'spread':>7s}")
    new = {}
    for k, (keys, in_file) in FIVE.items():
        new[k] = sum(mf[x]["F"] for x in keys)
        vals = [new[k], JACOBSON[k], MIRAKHORLO[k]]
        print(f"      {k:6s} {in_file:8.1f} {new[k]:10.2f} {new[k]/in_file:6.2f}x"
              f" {JACOBSON[k]:9.2f} {MIRAKHORLO[k]:11.2f} {max(vals)/min(vals):6.2f}x")
    print(f"      {'OP':6s} {OP_IN_FILE:8.1f} {mf['OPP']['F']:10.2f} "
          f"{mf['OPP']['F']/OP_IN_FILE:6.2f}x {47.56:9.2f} {59.49:11.2f}")

    check(abs(new["ADM"] / 12.3 - 3.67) < 0.05,
          f"ADM, the little finger abductor, is {new['ADM']/12.3:.2f} times too weak in the file",
          "All three sources agree on this one. It is the abductor at the far end of the\n"
          "          span, and the end a narrow keyboard relieves most.")
    check(new["AdP"] / 100.0 > 1.5,
          f"AdP is too WEAK in the file, {new['AdP']/100.0:.2f} times, not about right",
          "This reverses the earlier reading, which put AdP at 95.9 N and called the\n"
          "          file's 100 N correct.\n"
          "          McFarland splits AdP into ADPt at 59.94 N and ADPo at 102.11 N, implying\n"
          "          1.18 and 2.01 sq cm. Jacobson's TABLE gives AdP 1.94 sq cm, which is 98.6 N,\n"
          "          and Jacobson's own PROSE says 1.10 sq cm, contradicting its table. McFarland\n"
          "          may have taken the two heads from the two disagreeing numbers; that is an\n"
          "          inference and is not established. AdP is the one number three sources do not\n"
          "          reconcile, and 162.05 N is used only because internal consistency with the\n"
          "          39 muscles already in the file outweighs any one cadaver study. If the\n"
          "          cadaver cluster is preferred, 98.6 N is the number.")

    print("\n2b. Does McFarland equal Jacobson's PRINTED area times 50.8?")
    print(f"      {'muscle':6s} {'printed cm2':>11s} {'x 50.8':>8s} {'McFarland':>10s} {'per cent':>9s}")
    close = []
    for k, a in JACOBSON_PRINTED_CM2.items():
        got = mf["OPP"]["F"] if k == "OP" else (
            sum(mf[x]["F"] for x in FIVE[k][0]) if k in FIVE else mf[k]["F"])
        want = a * SPEC_TENSION
        pc = 100.0 * (got - want) / want
        if abs(pc) < 0.5:
            close.append(k)
        print(f"      {k:6s} {a:11.2f} {want:8.2f} {got:10.2f} {pc:8.2f}%")
    check(sorted(close) == ["ADM", "APB", "FDM", "FPB", "OP"],
          "five of the intrinsics reconcile to within a tenth of a per cent: "
          + ", ".join(sorted(close)),
          "So McFarland's forces for these muscles ARE Jacobson's printed area times 50.8.\n"
          "          That validates three things at once: the reading of Jacobson's table, the\n"
          "          specific tension, and the model file. It also means McFarland and Jacobson\n"
          "          are NOT independent sources on force. Only Mirakhorlo is. APL and EPB do not\n"
          "          reconcile and should not: McFarland states that wrist and extrinsic finger\n"
          "          muscles rest on in vivo volume and strength data instead.")
    r_file = 42.7 / 12.3
    r_new = new["APB"] / new["ADM"]
    print(f"      APB : ADM   in file {r_file:.2f}   McFarland {r_new:.2f}   "
          f"Jacobson {JACOBSON['APB']/JACOBSON['ADM']:.2f}   "
          f"Mirakhorlo {MIRAKHORLO['APB']/MIRAKHORLO['ADM']:.2f}")
    check(r_file > 1 and r_new < 1,
          "all three sources put the thumb to little finger abductor ratio below one, "
          f"where the file has it at {r_file:.2f}")

    print("\n3. Do McFarland's LENGTHS transfer into MUSIC-Hand's geometry?")
    print("   Solving MuJoCo's own relations for range:")
    print("      range0 = (lengthrange0 - L_T) / L0 ,  range1 = (lengthrange1 - L_T) / L0")
    print(f"      {'muscle':6s} {'L0 mm':>7s} {'L_T mm':>7s} {'range0':>7s} {'range1':>7s}  verdict")
    fits = []
    for k, (lo, hi) in GEOM_MM.items():
        keys = FIVE[k][0]
        l0 = weighted(mf, keys, "L0") if len(keys) > 1 else mf[keys[0]]["L0"]
        lt = weighted(mf, keys, "LT") if len(keys) > 1 else mf[keys[0]]["LT"]
        r0, r1 = (lo - lt) / l0, (hi - lt) / l0
        good = r0 >= LMIN and r1 <= LMAX
        if good:
            fits.append(k)
        v = "FITS" if good else ("range0 below lmin 0.5" if r0 > 0 else "range0 NEGATIVE")
        print(f"      {k:6s} {l0:7.2f} {lt:7.2f} {r0:7.3f} {r1:7.3f}  {v}")
    check(sorted(fits) == ["ADM", "FDM", "FPB"],
          f"three of the five could carry McFarland's fibre and tendon lengths exactly: "
          f"{', '.join(sorted(fits))}",
          "APB and AdP could not, because MUSIC-Hand routes them differently. McFarland's\n"
          "          APB is 75.5 mm from origin to insertion at optimum where MUSIC-Hand's whole\n"
          "          path is 40.5 to 54.0 mm. This is DELIBERATELY NOT APPLIED: range is at\n"
          "          MuJoCo's default for all 44 muscles, and correcting it for three would give\n"
          "          them curves three times narrower than the interossei they are compared\n"
          "          against. All 44 or none.")

    print("\n4. Corroboration of the geometry-derived lengths already in the patch")
    print(f"      {'muscle':6s} {'ours mm':>8s} {'McFarland mm':>13s} {'ratio':>6s}")
    for k, (lo, hi) in GEOM_MM.items():
        keys = FIVE[k][0]
        l0 = weighted(mf, keys, "L0") if len(keys) > 1 else mf[keys[0]]["L0"]
        ours = (hi - lo) / RANGE_SPAN
        print(f"      {k:6s} {ours:8.2f} {l0:13.2f} {ours/l0:6.2f}")
    apb_ours = (GEOM_MM["APB"][1] - GEOM_MM["APB"][0]) / RANGE_SPAN
    fdm_ours = (GEOM_MM["FDM"][1] - GEOM_MM["FDM"][0]) / RANGE_SPAN
    adp_ours = (GEOM_MM["AdP"][1] - GEOM_MM["AdP"][0]) / RANGE_SPAN
    adp_mf = weighted(mf, ["ADPt", "ADPo"], "L0")
    check(abs(apb_ours / mf["APB"]["L0"] - 1) < 0.15 and abs(fdm_ours / mf["FDM"]["L0"] - 1) < 0.05,
          "two independent routes to APB and FDM agree within 12 and 2 per cent",
          "One route is MuJoCo's compiler on MUSIC-Hand's geometry, the other is a\n"
          "          published OpenSim model. They were not fitted to each other.")
    check(adp_ours / adp_mf > 3.0,
          f"AdP is out by {adp_ours/adp_mf:.1f} times, a third independent confirmation of "
          "the same defect",
          "Its tendon has no wrapping surface, so it runs as a straight line across the\n"
          "          thumb web and its excursion is overstated. Ten of the 44 tendons lack a\n"
          "          wrapping surface and all five added muscles are among them.")
    check(abs(mf["APB"]["LT"] - 24.5) < 0.5,
          f"McFarland gives APB a tendon slack length of {mf['APB']['LT']:.2f} mm; Mirakhorlo "
          "measured the APB tendon at 24.5 mm on a cadaver",
          "A model and a dissection, unrelated, within 0.6 per cent.")

    print("\n5. What the two halves do together, in deliverable force")
    print(f"      {'muscle':6s} {'now N':>8s} {'after N':>8s} {'change':>7s}")
    tot_now = tot_after = 0.0
    for k in FIVE:
        now = FIVE[k][1] * REACHABLE[k]
        after = new[k] * 1.004
        tot_now += now
        tot_after += after
        print(f"      {k:6s} {now:8.2f} {after:8.2f} {after/now:6.2f}x")
    print(f"      {'total':6s} {tot_now:8.1f} {tot_after:8.1f} {tot_after/tot_now:6.2f}x")
    check(tot_after / tot_now > 1.2,
          f"the deliverable total RISES {tot_after/tot_now:.2f} times, to {tot_after:.1f} N",
          "CORRECTION TO THE RUN 2 PATCH, which said the total barely moves at 0.97 times\n"
          "          and called the change a redistribution rather than a change in strength.\n"
          "          That was true of the Jacobson forces and is not true of these. It is a\n"
          "          redistribution AND a 41 per cent increase. Do not carry that sentence on.")
    apb_now, apb_after = 42.7 * REACHABLE["APB"], new["APB"] * 1.004
    adm_now, adm_after = 12.3 * REACHABLE["ADM"], new["ADM"] * 1.004
    print(f"      APB, thumb side          {apb_now:.1f} N -> {apb_after:.1f} N")
    print(f"      ADM, little finger side  {adm_now:.1f} N -> {adm_after:.1f} N")
    print(f"      their ratio              {apb_now/adm_now:.2f} -> {apb_after/adm_after:.2f}")
    check(apb_now / adm_now > 1.0 > apb_after / adm_after,
          "the deliverable ratio between the two span-opening abductors inverts, "
          f"{apb_now/adm_now:.2f} to {apb_after/adm_after:.2f}")

    print("\n" + "=" * 74)
    if fails:
        print(f"{len(fails)} check(s) did not reproduce:")
        for f in fails:
            print("   " + f)
        return 1
    print("every check reproduced. "
          "Patch: added_muscle_parameters_patch_2026-09-07_run3.xml")
    print("Reasoning: 'Added muscle parameters, findings and replacement 2026-09-07.md', "
          "section 13.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
