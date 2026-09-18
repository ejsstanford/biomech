#!/usr/bin/env python3
"""Audit which wrap geoms, side sites and path sites are commented out with NO
active replacement, versus commented out because a re-fitted version replaced them.

The MyoHand original coordinates were left in place as comments and re-declared
below with new values, so a bare grep for '<!--' hugely overstates how much was
disabled. Only a commented name with no active twin is a genuine disabling."""
import re, sys, collections

def split_active_commented(src):
    """Return (text_with_comments_removed, list_of_comment_bodies)."""
    comments = re.findall(r'<!--(.*?)-->', src, re.S)
    active = re.sub(r'<!--.*?-->', '', src, flags=re.S)
    return active, comments

def names(text, tag):
    return re.findall(r'<%s\b[^>]*?\bname="([^"]+)"' % tag, text)

for side, defn, tend in (("RIGHT", "right_hand_definition.xml", "right_hand_definition_tendons.xml"),
                         ("LEFT",  "left_hand_definition.xml",  "left_hand_definition_tendons.xml")):
    root = "/tmp/scratch/assets/%s_assets/" % side.lower()
    dsrc = open(root + defn).read()
    tsrc = open(root + tend).read()

    dact, dcom = split_active_commented(dsrc)
    comtext = "\n".join(dcom)

    act_sites = set(names(dact, "site")); com_sites = set(names(comtext, "site"))
    act_geoms = set(names(dact, "geom")); com_geoms = set(names(comtext, "geom"))

    dead_sites = sorted(com_sites - act_sites)
    dead_geoms = sorted(com_geoms - act_geoms)

    # tendon path entries
    tact, tcom = split_active_commented(tsrc)
    com_path = []
    for c in tcom:
        for mm in re.finditer(r'<geom\s+geom="([^"]+)"\s+sidesite="([^"]+)"', c):
            com_path.append(("geom", mm.group(1), mm.group(2)))
        for mm in re.finditer(r'<site\s+site="([^"]+)"', c):
            com_path.append(("site", mm.group(1), ""))
    # which tendon owns each commented entry
    owner = {}
    for m in re.finditer(r'<spatial[^>]*name="([^"]+)"[^>]*>(.*?)</spatial>', tsrc, re.S):
        tn, body = m.group(1), m.group(2)
        for c in re.findall(r'<!--(.*?)-->', body, re.S):
            for mm in re.finditer(r'<geom\s+geom="([^"]+)"\s+sidesite="([^"]+)"', c):
                owner.setdefault(tn, []).append(("wrap-geom", mm.group(1), mm.group(2)))
            for mm in re.finditer(r'<site\s+site="([^"]+)"', c):
                owner.setdefault(tn, []).append(("path-site", mm.group(1), ""))

    print("=" * 92)
    print(side, "HAND")
    print("=" * 92)
    print("\nA. Names declared ONLY inside a comment (genuinely removed, no active twin)")
    print("   wrap/other GEOMS:")
    for g in dead_geoms:
        print("      ", g)
    if not dead_geoms: print("       none")
    print("   SITES  (side sites end in _side; the rest are tendon path points):")
    for s in dead_sites:
        print("      ", s)
    if not dead_sites: print("       none")

    print("\nB. Commented-out entries inside a tendon path, by tendon")
    for tn in sorted(owner):
        for kind, a, b in owner[tn]:
            # is the referenced thing still declared and active?
            if kind == "wrap-geom":
                st = "geom %s" % ("ACTIVE" if a in act_geoms else "GONE")
                st += " / sidesite %s" % ("ACTIVE" if b in act_sites else "GONE")
                print(f"   {tn:22s} {kind:10s} {a:32s} {b:36s} {st}")
            else:
                st = "site %s" % ("ACTIVE" if a in act_sites else "GONE")
                print(f"   {tn:22s} {kind:10s} {a:32s} {'':36s} {st}")
    if not owner: print("   none")
    print()
