#!/usr/bin/env python3
"""Bring the joint-driven forearm root ceilings down to physiological torques.

Schumann Lab, biomechanical piano model, MUSIC-Hand-v0.15.

WHAT THIS CHANGES. Three lines per hand, six across the two files, and nothing else.
The joint-driven configuration drives the forearm root through six position servos
named for an elbow. The three rotational servos ship with their force clamped at
plus or minus 50 N m, which against the model's own measured generalized inertia
about the forearm's long axis permits about 357,600 degrees per second squared.
Adult pronation and supination is of the order of 5 to 10 N m and wrist flexion,
extension and deviation of the order of 10 to 15, so the clamp is between four and
ten times any torque a forearm can produce.

The three translational servos are left alone at plus or minus 50 N. Against a
generalized inertia of 1.789 kg that permits 28 meters per second squared, about
2.9 g, which is not the fault. Note and do not silently change: the muscle-driven
root was given 78 N on the reasoning of hand weight plus the loudest measured key
force, and 50 N is below that. Whether the joint-driven side should also read 78 is
a question rather than a repair, and raising a ceiling is not a fault fix.

WHAT IT COSTS. This changes the joint-driven model, which is the configuration every
trained checkpoint belongs to, so a policy trained against the shipped ceilings has
learned to use a root it could accelerate at 357,600 degrees per second squared.
Applying this requires retraining. That is the whole reason it is a decision rather
than a correction.

Writes only into --assets, which must be a scratch tree extracted into a directory
that did not exist before. Asserts its own line count and refuses to write rather
than reporting a number it has not confirmed.
"""
import argparse
import os
import re
import shutil
import sys

# New rotational clamps, matching the muscle-driven root ceilings decided for the
# same three axes: 12 N m about x, 8 about the forearm long axis y, 12 about z.
NEW = {"rx": 12.0, "ry": 8.0, "rz": 12.0}
SHIPPED = "-50 50"
HANDS = (("right", "R:"), ("left", "L:"))


def patch(src, prefix):
    changed = 0
    for axis, val in NEW.items():
        name = "%selbow_%s" % (prefix, axis)
        pat = re.compile(r'(<position\s+name="%s"[^>]*forcerange=")%s(")'
                         % (re.escape(name), re.escape(SHIPPED)))
        new_range = "-%g %g" % (val, val)
        src, n = pat.subn(lambda m: m.group(1) + new_range + m.group(2), src)
        if n != 1:
            raise SystemExit("REFUSED: %s at the shipped clamp matched %d times, expected 1"
                             % (name, n))
        changed += n
    if changed != 3:
        raise SystemExit("REFUSED: changed %d lines, expected 3" % changed)
    return src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True, help="scratch assets tree to modify in place")
    a = ap.parse_args()

    for side, prefix in HANDS:
        path = os.path.join(a.assets, "%s_assets" % side,
                            "%s_hand_actuators_joint.xml" % side)
        keep = path + ".before_the_root_ceiling_patch"
        if not os.path.exists(keep):
            shutil.copy(path, keep)
        # Read fully, patch, then open for writing. Doing it in one expression
        # truncates the file before the read argument is evaluated.
        original = open(path).read()
        patched = patch(original, prefix)
        with open(path, "w") as fh:
            fh.write(patched)
        print("  %-5s three rotational clamps: 50 N m becomes 12 about x, "
              "8 about the forearm long axis, 12 about z" % side)
    print("JOINT-DRIVEN ROOT CEILING PATCH APPLIED to %s" % a.assets)
    print("PATCH FINISHED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
