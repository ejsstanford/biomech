#!/usr/bin/env python3
"""
Throw a flag if the model has drifted from settled state, or if a known dead
end has been re-entered.

Schumann Lab, biomechanical piano model. Written 6 September 2026.

WHAT THIS IS FOR
    Several claims about this model were made confidently and later refuted,
    and several repairs were attempted along paths that are now known not to
    work. This script is the machine-readable half of that memory. CLAUDE.md
    is the half a person or an assistant reads; this is the half that fails a
    build.

    Run it before reporting anything, and run it in CI if this lives in a
    repository.

USAGE
    python3 check_model_state.py --model-root /path/to/assets
    python3 check_model_state.py --model-root /path/to/assets --expect calibrated
    python3 check_model_state.py --list-dead-ends
    python3 check_model_state.py --list-refuted

    --expect as-built    the key should still carry the original values
    --expect calibrated  the key should carry the run 2 calibrated values
    --expect either      accept either, but flag anything in between (default)

EXIT CODES
    0  no flags
    1  one or more flags thrown
    2  could not read the model or the state file
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "model_state.json")

RED = "\033[31m" if sys.stdout.isatty() else ""
YEL = "\033[33m" if sys.stdout.isatty() else ""
OFF = "\033[0m" if sys.stdout.isatty() else ""

flags = []
notes = []


def flag(title, detail, pointer):
    flags.append((title, detail, pointer))


def note(text):
    notes.append(text)


def load_state():
    with open(STATE, encoding="utf-8") as fh:
        return json.load(fh)


def read_defaults(model_root):
    path = os.path.join(model_root, "defaults.xml")
    if not os.path.exists(path):
        return None, path
    with open(path, encoding="utf-8") as fh:
        return fh.read(), path


def attr(block, name):
    m = re.search(r'%s\s*=\s*"([^"]*)"' % re.escape(name), block)
    return m.group(1) if m else None


def key_block(text, cls):
    m = re.search(r'<default\s+class="%s">(.*?)</default>' % cls, text, re.S)
    return m.group(1) if m else None


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def close(a, b, rel=0.02):
    if a is None or b is None:
        return False
    if b == 0:
        return abs(a) < 1e-12
    return abs(a - b) / abs(b) <= rel


def check_option(text, state):
    opt = re.search(r"<option[^>]*>", text)
    if not opt:
        flag("No <option> element found",
             "The solver configuration could not be read, so the friction and "
             "gravity checks below could not run.",
             "defaults.xml")
        return
    opt = opt.group(0)

    # noslip, required for frictionloss to do anything
    ns = attr(opt, "noslip_iterations")
    wants_friction = False
    for cls in ("white_key", "black_key"):
        blk = key_block(text, cls)
        if blk and num(attr(blk, "frictionloss")):
            wants_friction = True
    if wants_friction and not ns:
        flag("frictionloss is set but noslip_iterations is not",
             "MuJoCo's joint friction silently does nothing without the no-slip "
             "solver pass. Measured on this key: the default solver held 33.7 gf, "
             "with noslip_iterations=\"10\" it held 47.9 gf. The calibration will "
             "appear to be present and have no effect.",
             "CLAUDE.md, dead end 3; model_state.json settled_parameters.option")
    elif wants_friction:
        note("frictionloss is set and noslip_iterations=%s is present" % ns)

    g = attr(opt, "gravity")
    if g:
        vals = [num(x) for x in g.split()]
        if any(v is not None and abs(v) > 1e-9 for v in vals):
            flag("Gravity has been turned on",
                 "This is not a one-line change. The key body's centre of mass "
                 "sits on the playing side of its hinge, so gravity drives the key "
                 "DOWN by about 60 gf equivalent. With the calibrated spring and "
                 "gravity on, and no finger force at all, the key falls to the "
                 "bottom and stays there. Holding it up needs stiffness near "
                 "0.14650 rather than 0.05080, which works but makes the spring do "
                 "a counterweight's job. The policy also learned in zero gravity, "
                 "so retraining is required.",
                 "CLAUDE.md, dead end 4; key_physics_patch_2026-09-06_run2.xml")

    ts = num(attr(opt, "timestep"))
    if ts and ts > 5e-4:
        note("timestep is %.6g s. Fine for training, but any offline "
             "peak-velocity probe must converge the timestep to about 1.3e-4 s, "
             "because a fortissimo keystroke lasts only about seven steps at "
             "480 Hz and the force required comes out 2 to 5 per cent high."
             % ts)


def check_keys(text, state, expect):
    settled = state["settled_parameters"]
    built = settled["as_built_for_contrast"]
    for cls, skey in (("white_key", "white_key"), ("black_key", "black_key")):
        blk = key_block(text, cls)
        if blk is None:
            flag("Default class %s not found" % cls,
                 "The key parameters could not be read.", "defaults.xml")
            continue
        got = {k: num(attr(blk, k)) for k in
               ("stiffness", "springref", "frictionloss", "damping", "armature")}
        got["mass"] = num(attr(blk, "mass"))
        cal = settled[skey]
        asb = built[skey]

        is_cal = all(close(got[k], cal[k]) for k in
                     ("stiffness", "frictionloss", "damping", "armature", "mass")) \
            and close(got.get("springref") or 0.0, cal["springref"])
        is_asb = all(close(got[k] if got[k] is not None else 0.0,
                           asb[k]) for k in
                     ("stiffness", "frictionloss", "damping", "armature", "mass"))

        if is_cal:
            note("%s carries the run 2 calibrated values" % cls)
            if expect == "as-built":
                flag("%s is calibrated but as-built was expected" % cls,
                     "Values match key_physics_patch_2026-09-06_run2.xml.",
                     "run with --expect calibrated")
        elif is_asb:
            note("%s carries the original as-built values" % cls)
            if expect == "calibrated":
                flag("%s has not been calibrated" % cls,
                     "As built this key has a down-weight of 2.8 gf and an "
                     "up-weight of 85.8 gf, so it cannot sound a soft note and "
                     "cannot separate down-weight from up-weight at all. A real "
                     "grand is 48 and about 22, with roughly 13 gf of friction.",
                     "apply key_physics_patch_2026-09-06_run2.xml")
        else:
            diffs = []
            for k in ("stiffness", "springref", "frictionloss", "damping",
                      "armature", "mass"):
                if not close(got.get(k), cal[k]):
                    diffs.append("%s is %s, calibrated value is %s"
                                 % (k, got.get(k), cal[k]))
            flag("%s matches neither the as-built nor the calibrated values" % cls,
                 "Someone has changed these by hand. Differences from the "
                 "calibrated set: " + "; ".join(diffs) + ". The calibrated set "
                 "was fitted to Steinway New York grand regulation, down-weight "
                 "48 gf and up-weight 20 gf or more, and passes eleven checks "
                 "against published values. If the change was deliberate, add a "
                 "dated entry to plan.html and update model_state.json.",
                 "key_physics_patch_2026-09-06_run2.xml; log.html")


def check_root_motors(model_root, state):
    for name in ("right_hand_actuators_muscle.xml",
                 os.path.join("right_assets", "right_hand_actuators_muscle.xml")):
        path = os.path.join(model_root, name)
        if os.path.exists(path):
            break
    else:
        note("root actuator file not found, skipped the root ceiling check")
        return
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    prop = state["settled_parameters"]["root_motors"]
    worst = None
    for m in re.finditer(r'<motor[^>]*name="R:(force|torque)_([xyz])"[^>]*>', text):
        blk = m.group(0)
        fr = attr(blk, "forcerange")
        if not fr:
            continue
        hi = max(abs(num(x) or 0.0) for x in fr.split())
        kind, axis = m.group(1), m.group(2)
        want = prop["force_N"] if kind == "force" else prop["torque_%s_Nm" % axis]
        if hi > want * 1.05:
            worst = (kind, axis, hi, want)
    if worst:
        kind, axis, hi, want = worst
        flag("The forearm root motors are still at their original ceiling",
             "R:%s_%s allows %g, against a proposed %g. The root is a free "
             "floating base with no joint limits at all, and its rotational "
             "inertia about the forearm's long axis is 7.11e-3 kg m^2, so a "
             "ceiling of 100 N m permits 806000 deg/s^2. Maximum voluntary wrist "
             "torque in adults is of order 10 to 15 N m. This is a sufficient "
             "mechanical account of the unrealistic elbow motion recorded on "
             "7 November 2025. Do NOT try to fix it with a reward term: the root "
             "is driven directly and the naturalness discriminator does not "
             "observe it." % (kind, axis, hi, want),
             "root_force_ceiling_patch_2026-09-06.xml; CLAUDE.md dead ends 1 and 2")
    else:
        note("root motor ceilings are at or below the proposed values")


def check_keyboard_octaves(model_root, state):
    """Any keyboard file whose octave span does not match its own name is a flag.
    This is the June 2026 failure mode."""
    White = re.compile(r'<body\s+name="P:white_key_(\d+)"\s+pos="([-\d.eE]+)')
    for root, _dirs, files in os.walk(model_root):
        for fn in sorted(files):
            if not (fn.startswith("piano") and fn.endswith(".xml")):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding="utf-8") as fh:
                txt = fh.read()
            xs = sorted(float(m.group(2)) for m in White.finditer(txt))
            if len(xs) < 8:
                continue
            gaps = sorted(abs(xs[i + 1] - xs[i]) for i in range(len(xs) - 1))
            octave_mm = gaps[len(gaps) // 2] * 7 * 1000
            m = re.search(r"ds(\d+(?:\.\d+)?)", fn)
            if not m:
                continue
            claimed_in = float(m.group(1))
            claimed_in = claimed_in / 10 if claimed_in > 20 else claimed_in
            claimed_mm = claimed_in * 25.4
            if abs(octave_mm - claimed_mm) > 0.05:
                sev = flag if abs(octave_mm - claimed_mm) > 1.0 else None
                msg = ("%s measures an octave span of %.4f mm, which is %.4f in, "
                       "but its name claims %.2f in (%.4f mm). Difference %.4f mm."
                       % (fn, octave_mm, octave_mm / 25.4, claimed_in,
                          claimed_mm, octave_mm - claimed_mm))
                if sev:
                    sev("A keyboard file does not have the octave span its name claims",
                        msg + " In June 2026 two of four queued configurations were "
                        "built with a tenth span where an octave span belonged. "
                        "Regenerate with make_scaled_keyboards_2026-09-06.py, which "
                        "measures what it writes.",
                        "make_scaled_keyboards_2026-09-06.py --selftest")
                else:
                    note(msg + " Known and small; the four original keyboards are "
                         "wide by about 0.29 mm.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-root", help="folder containing defaults.xml")
    ap.add_argument("--expect", default="either",
                    choices=["as-built", "calibrated", "either"])
    ap.add_argument("--list-dead-ends", action="store_true")
    ap.add_argument("--list-refuted", action="store_true")
    args = ap.parse_args()

    try:
        state = load_state()
    except Exception as exc:
        print("could not read %s: %s" % (STATE, exc))
        sys.exit(2)

    if args.list_dead_ends:
        print("DEAD ENDS ALREADY EXPLORED. Do not repeat these.\n")
        for k, v in state["dead_ends"].items():
            print("  [%s]  %s" % (k, v["do_not"]))
            print("      because: %s" % v["because"])
            if v.get("do_instead"):
                print("      instead: %s" % v["do_instead"])
            print()
        sys.exit(0)

    if args.list_refuted:
        print("CLAIMS ALREADY REFUTED. Do not resurrect these.\n")
        for r in state["refuted_claims"]:
            print("  claim:      %s" % r["claim"])
            print("  correction: %s\n" % r["correction"])
        for u in state["unlocatable_citations"]:
            print("  UNLOCATABLE CITATION, attributed to %s" % u["attributed_to"])
            print("    %s" % u["claim"])
            print("    %s" % u["result"])
            print("    %s\n" % u["instruction"])
        sys.exit(0)

    if not args.model_root:
        ap.error("--model-root is required unless listing")

    text, path = read_defaults(args.model_root)
    if text is None:
        print("could not find defaults.xml under %s" % args.model_root)
        sys.exit(2)

    check_option(text, state)
    check_keys(text, state, args.expect)
    check_root_motors(args.model_root, state)
    check_keyboard_octaves(args.model_root, state)

    print("=" * 72)
    print("MODEL STATE CHECK  ·  %s" % args.model_root)
    print("state file last updated %s" % state["last_updated"])
    print("=" * 72)
    for n in notes:
        print("  ok    %s" % n)
    print()
    if not flags:
        print("  no flags. %d dead ends and %d refuted claims are on record;"
              % (len(state["dead_ends"]), len(state["refuted_claims"])))
        print("  run --list-dead-ends and --list-refuted before starting new work.")
        sys.exit(0)

    for title, detail, pointer in flags:
        print("%s  FLAG  %s%s" % (RED, title, OFF))
        for line in _wrap(detail, 68):
            print("        %s" % line)
        print("%s        see: %s%s" % (YEL, pointer, OFF))
        print()
    print("  %d flag(s) thrown. Read CLAUDE.md before proceeding." % len(flags))
    sys.exit(1)


def _wrap(s, w):
    out, line = [], ""
    for word in s.split():
        if len(line) + len(word) + 1 > w:
            out.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        out.append(line)
    return out


if __name__ == "__main__":
    main()
