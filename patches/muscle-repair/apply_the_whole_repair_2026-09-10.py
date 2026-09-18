#!/usr/bin/env python3
"""Apply the WHOLE muscle repair to a SCRATCH copy of the model, both hands.

Schumann Lab, biomechanical piano model, September 10, 2026. Written for
`biomechanical model t9`, on Elizabeth Schumann's D1 answer of September 10, 2026,
"apply whole repair".

The whole repair is five things, and it is the only combination the record has
measured to zero on BOTH fault counts:

  1. the added-muscle drop-in actuator files      11 changed lines per hand
  2. the three recomputed length ranges            3 changed lines per hand
  3. the seven recomputed length ranges            7 changed lines per hand
  4. the five commented-out wrap pairings         10 uncommented lines per hand
  5. `APL` recomputed with its wrap in place       1 changed line per hand

Items 1 to 3 arrive together in one cumulative actuator file per hand, already
built and verified, at 21 changed lines against the shipped original. Item 4 is
five side sites in the definition file and five wrap entries in the tendon file,
each already present and commented out, so nothing is invented. Item 5 is one
attribute, and it exists because restoring `APL`'s wrap lengthens its path by
17.9 to 45.9 mm while its declared window was computed before the wrap was
disabled, which leaves `APL` carrying 34.7 per cent of its declared force as
passive spring.

Writes only into --assets, which must be a scratch tree extracted into a
directory that did not exist before. That requirement is dead end 13 in
CLAUDE.md: on September 7, 2026 an extraction into a reused path silently
produced a previous session's tree, and the standing check passed on it.

Every step asserts its own line count and refuses to write rather than
reporting a number it has not confirmed.
"""
import argparse
import os
import re
import shutil
import sys

CUMULATIVE = ("/Users/ejs/Library/Mobile Documents/com~apple~CloudDocs/Workspace/"
              "Research_Projects/AI_Model/Model changes ready to apply 2026-09-07/"
              "Recomputed length ranges for the seven stale originals 2026-09-08/"
              "on top of the added-muscle drop-in files and the three recomputed")

# The five tendons whose wrap entry already sits commented inside the tendon path,
# with the side site that entry aims at. Restoring one is uncommenting two lines.
FIVE = [
    ("APL",  "APL_torus_wrap",        "APL_torus_site_APL_side"),
    ("FDS4", "4thmcp_ellipsoid_wrap", "4thmcp_ellipsoid_site_FDS4_side"),
    ("FDP5", "5thmcp_ellipsoid_wrap", "5thmcp_ellipsoid_site_FDP5_side"),
    ("FDS5", "5thmcp_ellipsoid_wrap", "5thmcp_ellipsoid_site_FDS5_side"),
    ("FDP3", "3rdmcp_ellipsoid_wrap", "3rdmcp_ellipsoid_site_FDP3_side"),
]

APL_SHIPPED_WINDOW = "0.204756 0.228384"
APL_RECOMPUTED_WINDOW = "0.216562 0.242392"

HANDS = (("right", "R:"), ("left", "L:"))


def uncomment_site(src, name):
    """<!-- <site name="X" .../> --> becomes <site name="X" .../>. Exactly one hit."""
    pat = re.compile(r'<!--\s*(<site\s+name="%s"[^>]*?/>)\s*-->' % re.escape(name))
    new, n = pat.subn(r"\1", src)
    if n != 1:
        raise SystemExit("uncomment_site: %s matched %d times, expected 1" % (name, n))
    return new


def uncomment_path(src, tendon, geom, sidesite):
    """Uncomment one <geom geom=... sidesite=.../> inside one named tendon path.

    FDS4's entry is commented twice in its path, an evident duplicate, and only
    the first is restored. That is what the September 7 measurement was made on.
    """
    m = re.search(r'(<spatial[^>]*name="%s"[^>]*>)(.*?)(</spatial>)' % re.escape(tendon),
                  src, re.S)
    if not m:
        raise SystemExit("uncomment_path: tendon %s not found" % tendon)
    body = m.group(2)
    pat = re.compile(r'<!--\s*(<geom\s+geom="%s"\s+sidesite="%s"\s*/?>)\s*-->'
                     % (re.escape(geom), re.escape(sidesite)))
    new_body, n = pat.subn(r"\1", body, count=1)
    if n != 1:
        raise SystemExit("uncomment_path: %s/%s matched %d, expected at least 1"
                         % (tendon, geom, n))
    return src[:m.start(2)] + new_body + src[m.end(2):]


def set_apl_window(src, prefix):
    """Replace APL's lengthrange with the value recomputed with the wrap in place."""
    pat = re.compile(r'(<muscle\s+name="%sAPL"[^>]*lengthrange=")%s(")'
                     % (re.escape(prefix), re.escape(APL_SHIPPED_WINDOW)))
    new, n = pat.subn(r"\g<1>%s\g<2>" % APL_RECOMPUTED_WINDOW, src)
    if n != 1:
        raise SystemExit("set_apl_window: %sAPL at the shipped window matched %d times, "
                         "expected 1" % (prefix, n))
    return new


DECL = re.compile(r'<(?:muscle|motor)\s+[^>]*name="([^"]+)"[^>]*>')


def declarations(path):
    """Every actuator declaration in a file, keyed by actuator name.

    Compared this way rather than line for line, because the cumulative file
    carries a nineteen-line header comment the shipped original does not, and a
    line-for-line diff counts that header as a change.
    """
    out = {}
    for line in open(path).read().splitlines():
        m = DECL.search(line)
        if m:
            out[m.group(1)] = line.strip()
    return out


def changed_declarations(path_a, path_b):
    a, b = declarations(path_a), declarations(path_b)
    if set(a) != set(b):
        raise SystemExit("changed_declarations: the two files declare different "
                         "actuators, %d against %d" % (len(a), len(b)))
    return sum(1 for k in a if a[k] != b[k])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True,
                    help="scratch assets tree to modify in place")
    ap.add_argument("--cumulative", default=CUMULATIVE,
                    help="folder holding the cumulative actuator files")
    a = ap.parse_args()

    log = []

    # 1 to 3. The cumulative actuator files, 21 changed lines per hand.
    for side, prefix in HANDS:
        live = os.path.join(a.assets, "%s_assets" % side,
                            "%s_hand_actuators_muscle.xml" % side)
        drop = os.path.join(a.cumulative, "%s_hand_actuators_muscle.xml" % side)
        keep = live + ".before_2026-09-10"
        if not os.path.exists(keep):
            shutil.copy(live, keep)
        n = changed_declarations(live, drop)
        if n != 21:
            raise SystemExit("%s actuator file differs by %d declarations, expected 21"
                             % (side, n))
        shutil.copy(drop, live)
        log.append("  %-5s actuator file replaced, %d changed declarations "
                   "(11 added-muscle, 3 recomputed, 7 recomputed)" % (side, n))

    # 4. The five wrap pairings, ten uncommented lines per hand.
    for side, prefix in HANDS:
        dpath = os.path.join(a.assets, "%s_assets" % side,
                             "%s_hand_definition.xml" % side)
        tpath = os.path.join(a.assets, "%s_assets" % side,
                             "%s_hand_definition_tendons.xml" % side)
        d = open(dpath).read()
        t = open(tpath).read()
        for muscle, geom, site in FIVE:
            d = uncomment_site(d, prefix + site)
            t = uncomment_path(t, prefix + muscle + "_tendon",
                               prefix + geom, prefix + site)
        open(dpath, "w").write(d)
        open(tpath, "w").write(t)
        log.append("  %-5s five wrap pairings restored: %s"
                   % (side, ", ".join(m for m, _, _ in FIVE)))

    # 5. APL recomputed with the wrap in place.
    for side, prefix in HANDS:
        live = os.path.join(a.assets, "%s_assets" % side,
                            "%s_hand_actuators_muscle.xml" % side)
        src = set_apl_window(open(live).read(), prefix)
        open(live, "w").write(src)
        log.append("  %-5s APL lengthrange %s becomes %s"
                   % (side, APL_SHIPPED_WINDOW, APL_RECOMPUTED_WINDOW))

    print("THE WHOLE REPAIR IS APPLIED to %s" % a.assets)
    for line in log:
        print(line)
    print("APPLY FINISHED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
