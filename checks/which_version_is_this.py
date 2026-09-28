#!/usr/bin/env python3
"""Which version of the hand model is this copy, and is it a combination nobody meant?

WHY THIS EXISTS. The muscle repair and the range correction each replace some of
the same files, and the range correction's copy of them already contains every
change the muscle repair made. So applying both gives nine files where six are
wanted, and **whichever is applied second wins.** Apply the repair last and every
corrected muscle length range quietly goes back to what it was, leaving a copy of
the model that looks right, passes the standing check, and is not the model you
think it is.

A warning in a README does not stop that. This does: it reads the six files and
tells you what you actually have.

    python3 which_version_is_this.py <your copy>/assets

Exit 0 for a known, intentional version. Exit 1 for the mixed one or for anything
it does not know. No dependencies beyond the standard library.

Every fingerprint below was measured on September 28, 2026 by unpacking each
version from piano.tar.gz and reading it, not copied out of a document.
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

VERSIONS = {
    ("3e0aeae57d09b2f1e542e04754a267e5", "10b330e02ffaa4f6c967cca9cb084ca0",
     "355be75c93ec879c4a57af6c756c8f93", "5f0fdbe45b843767008267b78a1ed6dc",
     "f31fd01fc21b528eed19b342a4b001e7", "fabd5e6e59d89c79fbcf9e4920f315b2"): "unchanged",

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
"unchanged": """  UNCHANGED. Nothing has been applied to this copy.

  This is the hand model as Pei Xu, Yufei Ye and Ruocheng Wang shipped it.
  Nine of its muscles produce no force at all at postures they are supposed to
  work at, six pull on the hand all the time when nothing has asked them to,
  and every muscle uses the simulator's default stretch limits rather than
  measured ones, which is why a fault count run on it comes back clean when it
  is not.

  Let this hand go slack and it stays put easily. Open it to an octave and it
  also stays open for almost nothing, which a real hand does not do.""",

"repair-only": """  MUSCLE REPAIR ONLY. The September 10, 2026 repair, without the range
  correction.

  Both original fault counts go to zero. Let the hand go slack and it holds
  its shape slightly better than the unchanged model, and the constant
  background pull from the muscles drops to a thirty-third of what it was.

  What it does NOT have is any resistance to the hand opening. Spread it to a
  fifth or to an octave and it stays there for essentially nothing, so it says
  a relaxed hand holds an octave open for free. That is not true of real
  hands, and it is the reason the step1 version exists.

  This is a legitimate version. Use it on purpose, not by accident.""",

"step1": """  STEP 1. The muscle repair and the September 12, 2026 range correction
  applied together, with the wrist side-to-side range set from Wagner 1988.
  This is the recommended version.

  Spread this hand to an octave and it resists with 0.2412 newton-metres,
  within four percent of the force Wagner pushed against the hands of 238
  pianists. It is the only version that resists opening at all.

  KNOWN AND WRITTEN DOWN: it cannot hold a flat, fully extended hand. In that
  shape, 15 of its 23 movable finger and thumb joints carry a twist that no
  combination of muscle effort can balance, adding up to 6.59 newton-metres.
  All of them are finger flexors. So do not measure anything with the fingers
  held flat on this version, and expect check_hand_can_hold_itself to report
  FAIL at 6.5921. A FAIL there is the correct result, not a sign you applied
  it wrong.""",

"mixed": """  *** MIXED. THIS COPY IS NOT WHAT YOU THINK IT IS. ***

  It has the range correction's versions of some files and the muscle repair's
  versions of others. That happens when both are applied and the repair goes
  second.

  The muscle repair's files are the ones that carry every corrected stretch
  limit, so applying them last has wiped the correction out. The other files
  left behind make the copy look changed. The standing check passes on it.
  Every measurement you take will be wrong in a way nothing else will warn you
  about.

  TO FIX: unpack a fresh copy into a folder that did not exist before, and
  apply the six files in patches/step1 and nothing else.""",
}


def fingerprint(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 which_version_is_this.py <your copy>/assets")
    root = sys.argv[1]
    found, missing = [], []
    for folder, name in SIX:
        p = os.path.join(root, folder, name)
        if os.path.exists(p):
            found.append(fingerprint(p))
        else:
            missing.append(os.path.join(folder, name))

    if missing:
        print("This does not look like an unpacked copy of the model. These files are missing:")
        for m in missing:
            print("   ", m)
        print(f"\nPoint this at the 'assets' folder inside your unpacked copy. You gave: {root}")
        sys.exit(1)

    version = VERSIONS.get(tuple(found))
    print(f"\n  copy: {root}\n")
    if version is None:
        print("  NOT A VERSION I KNOW. These six files match no combination on record.\n")
        for (folder, name), h in zip(SIX, found):
            print(f"    {h}  {folder}/{name}")
        print("\n  Either something else has been edited, or this is newer than this script.")
        print("  Do not measure anything on it until you know which.")
        sys.exit(1)

    print(REPORT[version])
    print()
    sys.exit(1 if version == "mixed" else 0)


if __name__ == "__main__":
    main()
