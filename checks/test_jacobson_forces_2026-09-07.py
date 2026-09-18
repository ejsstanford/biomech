#!/usr/bin/env python3
"""
Reproduce the replacement forces for the five added abductors, and the checks
that establish they can be trusted.

Schumann Lab, biomechanical piano model. 7 September 2026.

WHAT THIS IS FOR
    The companion script, test_added_muscle_parameters_2026-09-07.py, covers the
    length half and the model probe. This one covers the forces, and in
    particular the question that changed the answer twice in one day: whether a
    given cadaver dataset is on the same scale as the muscles already in the
    file. Neither is, exactly. Jacobson is nearer, and the direction of the
    error is the same in both.

    Needs no model and no MuJoCo. Pure arithmetic on published tables.

CORRECTION CARRIED IN THIS FILE, 7 September 2026
    The first version of this script asserted that Jacobson sits within 1.53 of
    the file while Mirakhorlo is out by 2.79, and it FAILED its own check, which
    is how the error was found. The two figures were not like for like. The 2.79
    came from 20 forearm EXTRINSIC muscles; the 1.53 came from 8 intrinsic and
    thumb muscles. On the same 8 muscles Mirakhorlo's median is 1.99, not 2.79.

    Recomputed and correctly labelled:
        Mirakhorlo, 20 forearm extrinsics : median 2.80, range 0.83 to 8.77
        Mirakhorlo, the 8 muscles here    : median 1.99, range 0.27 to 5.23
        Jacobson,   the 8 muscles here    : median 1.53, range 0.36 to 3.78

    So the 2.8-fold gap is a property of the FOREARM comparison, where an
    87-year-old specimen is most atrophied. It was never a statement about the
    intrinsic muscles being replaced. Jacobson is still the better basis, on
    four grounds that do not depend on that figure, and the check below now
    tests what is actually true: Jacobson's median is nearer one and its spread
    is about half as wide.

USAGE
    python3 test_jacobson_forces_2026-09-07.py

EXIT CODES
    0  every check reproduced
    1  one or more checks did not reproduce
"""

import statistics
import sys

RHO = 1.056          # g per cubic cm, Mendez and Keys. Used by Jacobson and by Mirakhorlo.
SPEC_TENSION = 50.8  # N per sq cm. Confirmed by Elizabeth Schumann, 7 September 2026.
FIVE = ["FPB", "AdP", "APB", "FDM", "ADM"]

# ---------------------------------------------------------------------------
# Jacobson, M. D., Raab, R., Fazeli, B. M., Abrams, R. A., Botte, M. J., and
# Lieber, R. L. (1992). Architectural design of the human intrinsic hand
# muscles. The Journal of Hand Surgery 17(5), 804 to 809. Table 1, n = 9.
# Read from the article's own PDF text layer, 7 September 2026.
#   key: (mass g, muscle length mm, fibre length mm)
# The pennation and printed-PCSA columns could NOT be read reliably from the
# scan, so PCSA is computed below and pennation is omitted, which makes the
# areas a slight overestimate.
# ---------------------------------------------------------------------------
JACOBSON = {
    "ADM":  (3.32,  68.4, 46.2),   # AbDM, abductor digiti minimi
    "APB":  (2.61,  60.4, 41.6),   # AbPB, abductor pollicis brevis
    "APL":  (9.96, 160.4, 58.1),   # AbPL, abductor pollicis longus
    "AdP":  (6.78,  54.6, 34.0),   # AddP, adductor pollicis
    "FDM":  (1.54,  59.2, 40.6),   # flexor digiti minimi
    "FPB":  (2.58,  57.2, 41.5),   # flexor pollicis brevis
    "OP":   (3.51,  55.5, 35.5),   # OPP, opponens pollicis
    "ODM":  (1.94,  47.2, 19.5),   # opponens digiti minimi
    "EPB":  (2.25, 105.6, 55.0),   # extensor pollicis brevis
    "DI1":  (4.67,  61.9, 31.7),   # first dorsal interosseous
}
THENAR_HYPOTHENAR = ["ADM", "APB", "AdP", "FDM", "FPB", "OP", "ODM"]

# Mirakhorlo et al. 2016, Table 2. PCSA in sq mm, two-head muscles summed.
MIRAKHORLO_PCSA = {"FPB": 37.5, "AdP": 182.6, "APB": 43.8, "FDM": 11.3,
                   "ADM": 90.4, "OP": 117.1, "ODM": 130.2, "APL": 111.4,
                   "EPB": 58.4}

# forces as right_hand_actuators_muscle.xml holds them, 7 September 2026
IN_FILE = {"FPB": 80.0, "AdP": 100.0, "APB": 42.7, "FDM": 30.0, "ADM": 12.3,
           "OP": 180.0, "APL": 116.7, "EPB": 46.0}

# reachable fraction of declared force as built, measured on the model by the
# companion script
REACHABLE = {"FPB": 0.781, "AdP": 1.058, "APB": 0.440, "FDM": 0.562, "ADM": 1.000}

fails = []


def check(ok, label, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + label + (("\n          " + detail) if detail else ""))
    if not ok:
        fails.append(label)


def pcsa_sq_mm(key):
    mass, _ml, fl = JACOBSON[key]
    return 100.0 * mass / (RHO * (fl / 10.0))


def force_n(key):
    return pcsa_sq_mm(key) / 100.0 * SPEC_TENSION


def check_reading():
    print("\n1. Was Jacobson's Table 1 read correctly?")
    print("   The paper states the fibre-to-muscle-length band for each group.")
    r = {k: JACOBSON[k][2] / JACOBSON[k][1] for k in THENAR_HYPOTHENAR}
    for k, v in sorted(r.items(), key=lambda x: x[1]):
        print(f"      {k:5s} {v:.3f}")
    lo, hi = min(r.values()), max(r.values())
    print(f"      recomputed band {lo:.2f} to {hi:.2f}")
    check(abs(lo - 0.41) < 0.005 and abs(hi - 0.73) < 0.005,
          f"thenar and hypothenar band recomputes to {lo:.2f} to {hi:.2f}, "
          "against the paper's stated 0.41 to 0.73",
          "This is the only independent check available on a scanned table, and it is\n"
          "          a strong one: it uses two columns at once and would fail on any column\n"
          "          swap or transcription slip. Two readings of Mirakhorlo's table were\n"
          "          wrong earlier the same day before a third was verified.")


def check_scale():
    print("\n2. Is each cadaver dataset on the same scale as the muscles already in the file?")
    print("   Divide the force in the file by PCSA times the specific tension.")
    print(f"      {'muscle':6s} {'in file N':>9s} {'Jacobson':>9s} {'ratio':>6s}"
          f"   {'Mirakhorlo':>10s} {'ratio':>6s}")
    jr, mr = [], []
    for k in sorted(IN_FILE):
        fj = force_n(k) if k in JACOBSON else None
        fm = (MIRAKHORLO_PCSA[k] / 100.0 * SPEC_TENSION) if k in MIRAKHORLO_PCSA else None
        rj = IN_FILE[k] / fj if fj else None
        rm = IN_FILE[k] / fm if fm else None
        if rj:
            jr.append(rj)
        if rm:
            mr.append(rm)
        print(f"      {k:6s} {IN_FILE[k]:9.1f} {(fj or 0):9.2f} {(f'{rj:.2f}' if rj else '-'):>6s}"
              f"   {(fm or 0):10.2f} {(f'{rm:.2f}' if rm else '-'):>6s}")
    mj, mm = statistics.median(jr), statistics.median(mr)
    print(f"      median ratio against Jacobson   {mj:.2f}   (n = {len(jr)})")
    print(f"      median ratio against Mirakhorlo {mm:.2f}   (n = {len(mr)})")
    sj, sm = max(jr) / min(jr), max(mr) / min(mr)
    print(f"      spread  Jacobson {sj:.1f} times   Mirakhorlo {sm:.1f} times")
    check(mj < mm and sj < sm,
          f"Jacobson's median is nearer one, {mj:.2f} against {mm:.2f}, and its spread is "
          f"about half as wide, {sj:.1f} times against {sm:.1f}",
          "Neither dataset is exactly on the file's scale. Jacobson is nearer on both\n"
          "          measures, and is preferred on four grounds that do not depend on this\n"
          "          check at all: nine hands against one; one row per muscle, matching\n"
          "          MUSIC-Hand, against two heads for FPB and AdP; it is the source\n"
          "          McFarland's lineage rests on; and its ratios are the less extreme.\n"
          "          See the correction block at the head of this file: the 2.79 figure\n"
          "          quoted in earlier drafts was a forearm comparison, not this one.")
    print("\n2b. The direction of the error, which both datasets agree on for all six")
    print(f"      {'muscle':6s} {'Jacobson':>9s} {'Mirakhorlo':>11s}   verdict")
    agree = 0
    for k in ("AdP", "APB", "FDM", "FPB", "ADM", "OP"):
        a = IN_FILE[k] / force_n(k)
        b = IN_FILE[k] / (MIRAKHORLO_PCSA[k] / 100.0 * SPEC_TENSION)
        if 0.8 < a < 1.25 and 0.8 < b < 1.25:
            v, ok = "about right", True
        elif a > 1.25 and b > 1.25:
            v, ok = "too strong in the file", True
        elif a < 0.8 and b < 0.8:
            v, ok = "TOO WEAK in the file", True
        else:
            v, ok = "the two datasets disagree", False
        agree += ok
        print(f"      {k:6s} {a:9.2f} {b:11.2f}   {v}")
    check(agree == 6,
          "two independent cadaver datasets return the same verdict on all six muscles",
          "This is the part of the finding that does not depend on choosing between them.\n"
          "          AdP is right, ADM is far too weak, and FPB, FDM, APB and OP are all too\n"
          "          strong. Unanimous across an 87-year-old single forearm and nine hands.")


def check_replacement():
    print("\n3. The replacement set")
    print(f"      {'muscle':6s} {'PCSA sq mm':>10s} {'new force N':>11s} {'in file N':>9s} {'change':>7s}")
    new = {}
    for k in FIVE:
        new[k] = force_n(k)
        print(f"      {k:6s} {pcsa_sq_mm(k):10.1f} {new[k]:11.2f} {IN_FILE[k]:9.1f}"
              f" {new[k]/IN_FILE[k]:6.2f}x")
    check(abs(new["ADM"] / IN_FILE["ADM"] - 2.81) < 0.02,
          f"ADM, the little finger abductor, is {new['ADM']/IN_FILE['ADM']:.2f} times "
          "too weak in the file",
          "It is the abductor at the far end of the span, and the end a narrow keyboard\n"
          "          relieves most.")
    check(abs(new["AdP"] / IN_FILE["AdP"] - 0.96) < 0.02,
          f"AdP is already close: {new['AdP']/IN_FILE['AdP']:.2f} times",
          "One of the five hand-entered numbers was right. 100 N against a computed 95.9.")

    print("\n4. The ratio both cadaver datasets agree is inverted")
    rf = IN_FILE["APB"] / IN_FILE["ADM"]
    rj = new["APB"] / new["ADM"]
    rm = MIRAKHORLO_PCSA["APB"] / MIRAKHORLO_PCSA["ADM"]
    print(f"      APB : ADM      in file {rf:.2f}   Jacobson {rj:.2f}   Mirakhorlo {rm:.2f}")
    check(rf > 1 and rj < 1 and rm < 1,
          f"the file makes the thumb abductor {rf:.2f} times the little finger abductor; "
          f"both cadaver sources say less than one",
          f"Jacobson puts the error at {rf/rj:.1f} times, Mirakhorlo at {rf/rm:.1f}. They\n"
          "          disagree on the size and agree on the direction.")

    print("\n5. What the two halves do together, in deliverable force")
    print(f"      {'muscle':6s} {'now N':>8s} {'after N':>8s} {'change':>7s}")
    tot_now = tot_after = 0.0
    for k in FIVE:
        now = IN_FILE[k] * REACHABLE[k]
        after = new[k] * 1.004
        tot_now += now
        tot_after += after
        print(f"      {k:6s} {now:8.2f} {after:8.2f} {after/now:6.2f}x")
    print(f"      {'total':6s} {tot_now:8.1f} {tot_after:8.1f} {tot_after/tot_now:6.2f}x")
    check(abs(tot_after / tot_now - 1.0) < 0.06,
          f"the total deliverable force barely moves: {tot_now:.1f} N to {tot_after:.1f} N, "
          f"{tot_after/tot_now:.2f} times",
          "So this is not a change in how strong the hand is. It is a redistribution,\n"
          "          from the flexors to the abductors and from the thumb side of the span to\n"
          "          the little finger side. That is what makes it worth applying.")
    apb_now, apb_after = IN_FILE["APB"] * REACHABLE["APB"], new["APB"] * 1.004
    adm_now, adm_after = IN_FILE["ADM"] * REACHABLE["ADM"], new["ADM"] * 1.004
    print(f"      APB, thumb side          {apb_now:.1f} N -> {apb_after:.1f} N")
    print(f"      ADM, little finger side  {adm_now:.1f} N -> {adm_after:.1f} N")
    print(f"      their ratio              {apb_now/adm_now:.2f} -> {apb_after/adm_after:.2f}")
    check(apb_now / adm_now > 1.0 > apb_after / adm_after,
          "the deliverable ratio between the two span-opening abductors inverts, "
          f"{apb_now/adm_now:.2f} to {apb_after/adm_after:.2f}")


def main():
    print("=" * 74)
    print("ADDED MUSCLE FORCES  ·  Jacobson 1992 at 50.8 N per sq cm  ·  7 Sep 2026")
    print("=" * 74)
    check_reading()
    check_scale()
    check_replacement()
    print("\n" + "=" * 74)
    if fails:
        print(f"{len(fails)} check(s) did not reproduce:")
        for f in fails:
            print("   " + f)
        return 1
    print("every check reproduced. Patch: added_muscle_parameters_patch_2026-09-07_run2.xml")
    print("Reasoning: 'Added muscle parameters, findings and replacement 2026-09-07.md', "
          "section 11.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
