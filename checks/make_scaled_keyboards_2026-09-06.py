#!/usr/bin/env python3
"""
Generate a series of scaled piano keyboard XML files, and assert that each one
has the octave span it was asked for.

Written 6 September 2026 for the Schumann Lab.

WHY THE ASSERTION MATTERS
    In June 2026 two of four queued keyboard configurations were invalid. For
    the tenth-span group, the generating script set the target to the TENTH
    span rather than to the corresponding OCTAVE span, so the files were built
    with octaves substantially wider than a standard piano. The error was
    caught by eye before any conclusion was drawn.

    The check in verify() below is what would have caught it automatically:
    it measures the octave span of the file that was actually written and
    compares it against the octave span that was intended. It does not trust
    the scale factor, the file name, or the caller.

USAGE
    python3 make_scaled_keyboards_2026-09-06.py --reference /path/to/piano_ds6.5.xml
    python3 make_scaled_keyboards_2026-09-06.py --reference REF --outdir OUT
    python3 make_scaled_keyboards_2026-09-06.py --reference REF --selftest

    Default series: 5.5 to 6.7 inches in 0.1 inch steps, thirteen keyboards.
    A standard octave is 6.5 inches; the lab's narrow instrument is 6.0.

WHAT IT DOES NOT DO
    It does not touch key mass, spring, friction, damping or armature. Those
    live in the default classes, see key_physics_patch_2026-09-06_run2.xml.
    Only key positions are scaled here.

A NOTE ON TENTHS
    A tenth span is not scaled independently. Key width is the octave over
    seven, and a tenth is nine key widths, so a tenth follows from the octave.
    If a keyboard ever needs an independently specified tenth, that is a
    different geometry and this script must not be used to fake it. The
    function tenth_span_mm() is provided so the implied tenth can be reported
    alongside the octave, never set.
"""

import argparse
import os
import re
import sys

MM_PER_INCH = 25.4
WHITE_RE = re.compile(r'<body\s+name="(P:white_key_(\d+))"\s+pos="([-\d.eE]+)\s+([-\d.eE]+)\s+([-\d.eE]+)"')
POS_RE = re.compile(r'(<body\s+name="P:(?:white|black)_key_\d+"\s+pos=")([-\d.eE]+)(\s)')


def read_white_positions(text):
    """Return {key index: x position in metres} for the white keys."""
    out = {}
    for m in WHITE_RE.finditer(text):
        out[int(m.group(2))] = float(m.group(3))
    if not out:
        raise ValueError("no white key bodies found: is this a piano XML?")
    return out


def octave_span_mm(text):
    """Measure the octave span: the distance across seven white keys.

    Measured as the mean spacing between adjacent white keys times seven,
    rather than from one pair, so a single malformed entry cannot set it.
    """
    pos = read_white_positions(text)
    idx = sorted(pos)
    xs = [pos[i] for i in idx]
    gaps = [abs(xs[i + 1] - xs[i]) for i in range(len(xs) - 1)]
    if not gaps:
        raise ValueError("fewer than two white keys found")
    gaps.sort()
    mid = gaps[len(gaps) // 2]                      # median, robust to outliers
    return mid * 7 * 1000.0


def tenth_span_mm(octave_mm):
    """The tenth span implied by an octave span. Reported, never set."""
    return octave_mm / 7.0 * 9.0


def scale_positions(text, factor):
    """Multiply every key body's x position by factor."""
    n = 0

    def repl(m):
        nonlocal n
        n += 1
        return "%s%.9g%s" % (m.group(1), float(m.group(2)) * factor, m.group(3))

    out = POS_RE.sub(repl, text)
    if n == 0:
        raise ValueError("no key positions were rewritten")
    return out, n


def generate(reference_path, target_octave_mm, outdir, label=None):
    with open(reference_path, encoding="utf-8") as fh:
        ref = fh.read()
    ref_octave = octave_span_mm(ref)
    factor = target_octave_mm / ref_octave
    scaled, n = scale_positions(ref, factor)

    inches = target_octave_mm / MM_PER_INCH
    label = label or ("piano_ds%.2fin_octave%.2fmm.xml" % (inches, target_octave_mm))
    path = os.path.join(outdir, label)
    if os.path.exists(path):
        raise FileExistsError("refusing to overwrite %s" % path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(scaled)
    return path, factor, n, ref_octave


def verify(path, intended_octave_mm, tol_mm=0.05):
    """Measure what was written and compare against what was intended.

    This is the check that would have caught the June 2026 error.
    """
    with open(path, encoding="utf-8") as fh:
        got = octave_span_mm(fh.read())
    ok = abs(got - intended_octave_mm) <= tol_mm
    return ok, got, tenth_span_mm(got)


def default_series():
    return [round(5.5 + 0.1 * i, 1) for i in range(13)]     # 5.5 to 6.7 inches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True,
                    help="path to an existing piano XML, for example piano_ds6.5.xml")
    ap.add_argument("--outdir", default=None,
                    help="where to write the generated files, default a sibling folder")
    ap.add_argument("--inches", nargs="*", type=float, default=None,
                    help="octave spans in inches, default 5.5 to 6.7 in 0.1 steps")
    ap.add_argument("--selftest", action="store_true",
                    help="run the regression tests and exit without writing a series")
    args = ap.parse_args()

    with open(args.reference, encoding="utf-8") as fh:
        ref_text = fh.read()
    ref_octave = octave_span_mm(ref_text)
    print("reference %s" % args.reference)
    print("  measured octave span %.4f mm  (%.4f in)" % (ref_octave, ref_octave / MM_PER_INCH))
    print("  implied tenth span   %.4f mm" % tenth_span_mm(ref_octave))
    print("  white keys found     %d" % len(read_white_positions(ref_text)))
    print()

    if args.selftest:
        sys.exit(selftest(args.reference))

    outdir = args.outdir or os.path.join(
        os.path.dirname(os.path.abspath(args.reference)), "scaled_keyboards_2026-09-06")
    os.makedirs(outdir, exist_ok=True)

    print("%-10s %-14s %-12s %-14s %-14s %s"
          % ("inches", "target octave", "factor", "written octave", "implied tenth", "check"))
    failures = 0
    for inches in (args.inches or default_series()):
        target = inches * MM_PER_INCH
        try:
            path, factor, n, _ = generate(args.reference, target, outdir)
        except FileExistsError as exc:
            print("  %s" % exc)
            continue
        ok, got, tenth = verify(path, target)
        failures += 0 if ok else 1
        print("%-10s %-14s %-12s %-14s %-14s %s"
              % ("%.1f" % inches, "%.4f mm" % target, "%.6f" % factor,
                 "%.4f mm" % got, "%.4f mm" % tenth, "pass" if ok else "FAIL"))
    print()
    print("wrote into %s" % outdir)
    print("%s" % ("all keyboards verified" if failures == 0
                  else "%d KEYBOARD(S) FAILED VERIFICATION, do not use them" % failures))
    sys.exit(1 if failures else 0)


def selftest(reference):
    """Regression tests, including the June 2026 failure mode."""
    import tempfile
    print("=" * 70)
    print("REGRESSION TESTS")
    print("=" * 70)
    results = []

    with open(reference, encoding="utf-8") as fh:
        ref = fh.read()
    ref_oct = octave_span_mm(ref)

    with tempfile.TemporaryDirectory() as td:
        # 1. round trip at unit scale
        p, f, n, _ = generate(reference, ref_oct, td, "unit.xml")
        ok, got, _ = verify(p, ref_oct)
        results.append(("unit scale reproduces the reference octave", ok))

        # 2. a normal target
        target = 6.0 * MM_PER_INCH
        p, f, n, _ = generate(reference, target, td, "six.xml")
        ok, got, _ = verify(p, target)
        results.append(("a 6.0 inch target is written and verified", ok))

        # 3. every key position moved, not just some
        results.append(("every key body position was rewritten", n >= 88))

        # 4. THE JUNE 2026 FAILURE MODE.
        #    Ask for a keyboard by handing in a TENTH span where an octave
        #    span belongs. The generator will happily build it; verify must
        #    reject it when checked against the intended octave.
        tenth_of_standard = tenth_span_mm(6.5 * MM_PER_INCH)      # 212.27 mm
        p, f, n, _ = generate(reference, tenth_of_standard, td, "tenth_mistake.xml")
        ok_as_octave, got, _ = verify(p, 6.5 * MM_PER_INCH)
        results.append(("a tenth span passed in as an octave is REJECTED", not ok_as_octave))
        print("  the June failure mode, reproduced: a file built to %.2f mm"
              % got)
        print("  would have been used as a %.2f mm octave. Rejected."
              % (6.5 * MM_PER_INCH))

        # 5. tolerance actually bites
        p, f, n, _ = generate(reference, target, td, "tol.xml")
        ok_tight, _, _ = verify(p, target + 1.0, tol_mm=0.05)
        results.append(("a 1 mm error is caught by the tolerance", not ok_tight))

        # 6. the implied tenth follows the octave, and is never set
        implied = tenth_span_mm(target)
        results.append(("implied tenth is octave times nine sevenths",
                        abs(implied - target / 7 * 9) < 1e-9))

        # 7. refuses to overwrite
        try:
            generate(reference, target, td, "six.xml")
            results.append(("refuses to overwrite an existing file", False))
        except FileExistsError:
            results.append(("refuses to overwrite an existing file", True))

    print()
    bad = 0
    for label, ok in results:
        print("  [%s] %s" % ("pass" if ok else "FAIL", label))
        bad += 0 if ok else 1
    print()
    print("  %d of %d tests pass." % (len(results) - bad, len(results)))
    return 1 if bad else 0


if __name__ == "__main__":
    main()
