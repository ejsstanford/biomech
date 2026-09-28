#!/usr/bin/env python3
"""Which version of the model is this tree, and is it a combination nobody meant?

WHY THIS EXISTS. The muscle repair and the range correction each ship actuator
files, and the range correction's already carries every actuator change the
repair made. So applying both gives nine files where six are wanted, and
**whichever is applied second wins.** Apply the repair last and every corrected
`range` value reverts, leaving a tree that looks right, passes the standing
check, and is not the model you think it is.

A warning in a README does not stop that. This does: it reads the six files and
tells you what you actually have.

    python3 which_tree_is_this.py <assets_dir>

Exit 0 for a recognised, intentional tree. Exit 1 for the mixed tree or for
anything unrecognised. No dependencies beyond the standard library.

Every hash below was measured on September 28, 2026 by building each tree from
`piano.tar.gz` and reading it, not copied from a document.
"""
import hashlib, os, sys

SIX = [
    ("right_assets", "right_hand_actuators_muscle.xml"),
    ("right_assets", "right_hand_definition.xml"),
    ("right_assets", "right_hand_definition_tendons.xml"),
    ("left_assets",  "left_hand_actuators_muscle.xml"),
    ("left_assets",  "left_hand_definition.xml"),
    ("left_assets",  "left_hand_definition_tendons.xml"),
]

STATES = {
    ("3e0aeae57d09b2f1e542e04754a267e5", "10b330e02ffaa4f6c967cca9cb084ca0",
     "355be75c93ec879c4a57af6c756c8f93", "5f0fdbe45b843767008267b78a1ed6dc",
     "f31fd01fc21b528eed19b342a4b001e7", "fabd5e6e59d89c79fbcf9e4920f315b2"): "pristine",

    ("09e797c68e9b5073f4bed7845d5d8a76", "e43838ad33bc410bd957643c86318fee",
     "86a48418ef151e01d3ffcbdd8c3a4138", "c626c05a14901d58957e0ffdbeccb085",
     "bbf5213f63513648a2545ddaf3d397d8", "6f8e8e6d9b53dd36a552834fca32e789"): "repair-only",

    ("18233aa5142c58ea3b0fefb90e135aac", "27b4983d1c84c2e06dea60f1f12fadc4",
     "86a48418ef151e01d3ffcbdd8c3a4138", "55e30f7ebffa99a8ea6244df0112a3b4",
     "a98c6ec77f6df2aaa90db7cb919af971", "6f8e8e6d9b53dd36a552834fca32e789"): "step1",

    ("09e797c68e9b5073f4bed7845d5d8a76", "27b4983d1c84c2e06dea60f1f12fadc4",
     "86a48418ef151e01d3ffcbdd8c3a4138", "c626c05a14901d58957e0ffdbeccb085",
     "a98c6ec77f6df2aaa90db7cb919af971", "6f8e8e6d9b53dd36a552834fca32e789"): "mixed",
}

REPORT = {
"pristine": """  PRISTINE. Nothing has been applied.

  This is MUSIC-Hand-v0.15 as Pei Xu, Yufei Ye and Ruocheng Wang shipped it.
  Nine muscles reach zero active force inside their own window, six act as
  uncommanded springs, and the muscle length ranges are MuJoCo's default 0.75
  to 1.05, which is why the fault count looks like zero when it is not.

  It holds its default posture at 0.0032 Nm, and it offers 0.0079 Nm of
  resistance to opening the hand to an octave, which is nothing. A real hand
  does not open that far for free.""",

"repair-only": """  MUSCLE REPAIR ONLY. The September 10, 2026 repair, without the range
  correction.

  Both original fault counts go to zero and it holds its default posture at
  0.0029 Nm, better than pristine. Total passive joint torque falls by a
  factor of 33.

  What it does NOT have: any resistance to the hand opening. 0.0000 Nm at a
  fifth and 0.0079 at an octave, so it says a relaxed hand holds an octave for
  free. That is false of real hands, and it is the reason step1 exists.

  This is a legitimate tree. Use it deliberately, not by accident.""",

"step1": """  STEP 1. The muscle repair and the September 12, 2026 range correction
  applied together, with the wrist deviation range set from Wagner 1988.
  This is the recommended tree.

  It offers 0.2412 Nm against opening to an octave, within four percent of the
  0.25 Nm probe Wagner applied to 238 pianists, and it is the only version with
  that behaviour at all.

  KNOWN AND DOCUMENTED: it cannot hold its own default posture. 15 of 23
  muscle-actuated hand degrees of freedom carry 6.59 Nm that no activation
  balances, all of them finger flexors. Do not measure anything at the default
  posture on this tree. check_hand_can_hold_itself is expected to FAIL here at
  6.5921 Nm, and a FAIL is the correct result.""",

"mixed": """  *** MIXED. THIS TREE IS NOT WHAT YOU THINK IT IS. ***

  It carries the range correction's DEFINITION files and the muscle repair's
  ACTUATOR files. That happens when both patches are applied and the repair
  goes second.

  The actuator files are where every corrected muscle `range` value lives, so
  the repair's actuator files have overwritten them and THE RANGE CORRECTION IS
  GONE. The definition files left behind make the tree look changed. The
  standing check passes. Every measurement you take will be wrong in a way
  nothing else will tell you about.

  TO FIX: extract a fresh tree into a directory that did not exist before, and
  apply the six files of patches/step1/ and nothing else.""",
}


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 which_tree_is_this.py <assets_dir>")
    root = sys.argv[1]
    got, missing = [], []
    for sub, name in SIX:
        p = os.path.join(root, sub, name)
        if not os.path.exists(p):
            missing.append(os.path.join(sub, name))
        else:
            got.append(md5(p))
    if missing:
        print("Not a model assets directory. These are missing:")
        for m in missing:
            print("   ", m)
        print(f"\nExpected <assets_dir> to contain right_assets/ and left_assets/. Got: {root}")
        sys.exit(1)

    state = STATES.get(tuple(got))
    print(f"\n  tree: {root}\n")
    if state is None:
        print("  UNRECOGNISED. These six files match no combination on record.\n")
        for (sub, name), h in zip(SIX, got):
            print(f"    {h}  {sub}/{name}")
        print("\n  Either something else has been edited, or this is a version newer than")
        print("  this script. Do not measure anything on it until you know which.")
        sys.exit(1)

    print(REPORT[state])
    print()
    sys.exit(1 if state == "mixed" else 0)


if __name__ == "__main__":
    main()
