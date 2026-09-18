#!/usr/bin/env python3
"""What does `LU_RB` represent? Settle it by measurement rather than by the naming.

Schumann Lab, biomechanical piano model, MUSIC-Hand-v0.15. Written 8 September 2026.

THE QUESTION, AS THE RECORD LEFT IT
===================================
The state file of 7 September 2026 records, in section 1: "What `LU_RB` represents is not
stated anywhere. Searched 7 September 2026: the model definition files, the tendon files,
the README and the environment code." It sets out two readings and calls the choice
between them an inference:

  reading 1, from the naming     `RI` radial interosseous, `UI` ulnar interosseous,
                                 `LU` lumbrical, `RB` radial band, `UB` ulnar band, which
                                 is the extensor-mechanism convention of the An and Chao
                                 lineage. On that reading `LU_RB` is a lumbrical acting
                                 through the radial band, and its 47.9 to 98 N is
                                 indefensible against a lumbrical's cross-sectional area.

  reading 2, from the forces     `LU_RB` and `UI_UB` carry forces identical to each other
                                 on all four digits, which is the signature of one number
                                 written to two actuators, so the unit may be carrying
                                 more than one muscle's worth of force by design.

Neither reading was tested against the model's own mechanics. This script does that. It
is cheap because the answer is already in the file: what a muscle-tendon unit represents
is fixed by where it attaches and which joints it crosses, and both are measurable.

WHAT IS MEASURED, IN FOUR PARTS, EACH WITH ITS OWN CONTROL
==========================================================
0. THE SIGN CONVENTION, FIRST, BECAUSE NOTHING CAN BE READ WITHOUT IT.
   `CLAUDE.md` records under "Things that are true and easy to get wrong": "No file
   states the sign convention, so check before interpreting." So the convention is
   established here from muscles whose action nobody disputes. Flexor digitorum
   profundus and superficialis flex every joint they cross; extensor digitorum communis
   extends. Whichever sign they carry at a joint IS flexion and extension in this model.
   Abductor digiti minimi abducts the little finger and abductor pollicis brevis abducts
   the thumb, which fixes the abduction sign the same way.

1. WHERE EACH PATH SITE SITS, and which body owns it. An interosseous with a bony
   insertion stops at the proximal phalanx. A unit inserting into a lateral band of the
   extensor mechanism runs out onto the middle phalanx and, in a full representation, the
   distal one.

2. WHICH JOINTS EACH UNIT CROSSES AND IN WHICH DIRECTION, from the moment arm, taken as
   the derivative of tendon length with respect to joint angle by central difference on
   the compiled model. This is the decisive measurement. A unit inserting into a lateral
   band MUST extend the interphalangeal joint it crosses while flexing the
   metacarpophalangeal joint, because that is what the extensor mechanism does. A unit
   with a bony insertion on the proximal phalanx cannot extend an interphalangeal joint
   at all, having no path across it.

3. WHICH SIDE OF THE DIGIT EACH UNIT LIES ON, from the sign of the abduction moment arm
   read against abductor digiti minimi. `RI` and `LU_RB` should share a sign and `UI_UB`
   should oppose them on every digit if the radial and ulnar halves of the naming are
   real.

4. WHAT FORCE EACH CARRIES, against McFarland's published values for the muscles the two
   readings imply, digit by digit and side by side. Reading 1 predicts `LU_RB` is out by
   an order of magnitude. Reading 2 predicts it is out by a small factor.

WHAT IT WRITES, STATED EXACTLY
==============================
No model file is modified. Like every probe in this folder it writes one temporary XML
into the assets directory it is pointed at and deletes it in a `finally` block. That is
why it must be pointed at a scratch copy of `piano.tar.gz` and never at the Workspace.
Everything it finds it prints, including the figures that do not support the conclusion.

SOURCES
=======
- MUSIC-Hand-v0.15, `assets/` from `piano.tar.gz`, the collaborators' archive of
  4 March 2026, extracted 8 September 2026 into a fresh directory owned by this session,
  per dead end 13 in `CLAUDE.md`.
- McFarland, D. C., Binder-Markey, B. I., Nichols, J. A., Wohlman, S. J., de Bruin, M.,
  and Murray, W. M. A Musculoskeletal Model of the Hand and Wrist Capable of Simulating
  Functional Tasks. IEEE Transactions on Biomedical Engineering, 2022,
  doi 10.1109/TBME.2022.3217722. Release 4.3 from SimTK project `arms_hand_model`,
  as read into `McFarland 43 muscle parameters as read 2026-09-07.tsv`.
- An, K. N., Chao, E. Y., Cooney, W. P., and Linscheid, R. L. Normative model of human
  hand for biomechanical analysis. Journal of Biomechanics 12(10), 775 to 788, 1979, for
  the extensor-mechanism decomposition the naming follows. NOT read in this pass; named
  because it is the lineage the convention comes from and the citation should be checked
  before it is printed anywhere.

USAGE
=====
    pip install mujoco==3.12.0
    python3 what_LU_RB_represents_2026-09-08.py --assets /path/to/scratch/assets \
        --mcfarland "/path/to/McFarland 43 muscle parameters as read 2026-09-07.tsv"
"""

import argparse
import os
import sys

import numpy as np
import mujoco

DIGITS = (2, 3, 4, 5)
STEMS = ("RI", "LU_RB", "UI_UB")

PROBE = ('<mujoco model="probe">\n'
         '  <include file="defaults.xml"/>\n'
         '  <include file="{side}_assets/{side}_hand_definition_meta.xml"/>\n'
         '  <include file="{side}_assets/{side}_hand_definition_tendons.xml"/>\n'
         '  <include file="{side}_assets/{side}_hand_actuators_muscle.xml"/>\n'
         '  <worldbody><include file="{side}_assets/{side}_hand_freeroot.xml"/></worldbody>\n'
         '</mujoco>\n')

# Which McFarland muscles each MUSIC-Hand intrinsic unit would be, under each reading.
# The dorsal interossei abduct and the palmar interossei adduct, so the radial-side
# muscle of a digit is the one that pulls it toward the thumb: for the index and middle
# that is a dorsal interosseous, for the ring and little a palmar one. Every mapping in
# this table is an INFERENCE from anatomy and from the naming, and is printed as such.
RADIAL_INTEROSSEOUS = {2: ["1stDI_MC1", "1stDI_MC2"], 3: ["2ndDI"], 4: ["2ndPI"], 5: ["3rdPI"]}
ULNAR_INTEROSSEOUS = {2: ["1stPI"], 3: ["3rdDI"], 4: ["4thDI"], 5: []}
LUMBRICAL = {2: ["LUMI"], 3: ["LUMM"], 4: ["LUMR"], 5: ["LUML"]}
# The little finger's ulnar side carries no interosseous in McFarland; abductor digiti
# minimi does that work and MUSIC-Hand represents it separately.
ULNAR_EXTRA = {5: ["ADM"]}


def load(assets, side="right", stem="_lu_rb_probe"):
    p = os.path.join(assets, stem + ".xml")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(PROBE.format(side=side))
    try:
        return mujoco.MjModel.from_xml_path(p)
    finally:
        os.remove(p)


def read_mcfarland(path):
    out = {}
    if not path or not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        f = line.rstrip("\n").split("\t")
        if f[0] == "muscle":
            continue
        try:
            out[f[0]] = {"F": float(f[1]), "L0": float(f[2]),
                         "LT": float(f[3]), "pen": float(f[4])}
        except (IndexError, ValueError):
            continue
    return out


def moment_arms(m, d, q0, eps=1e-4):
    """d(tendon length)/d(joint angle) in mm per rad, at one posture, for every hinge."""
    names, out = [], {}
    for j in range(m.njnt):
        jn = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j)
        if jn is None or m.jnt_type[j] != mujoco.mjtJoint.mjJNT_HINGE:
            continue
        adr = int(m.jnt_qposadr[j])
        vals = []
        for s in (+1, -1):
            q = q0.copy()
            q[adr] += s * eps
            d.qpos[:] = q
            mujoco.mj_forward(m, d)
            vals.append(d.ten_length.copy())
        out[jn] = (vals[0] - vals[1]) / (2 * eps) * 1000.0
        names.append(jn)
    return out, names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True)
    ap.add_argument("--mcfarland", default="")
    ap.add_argument("--eps", type=float, default=1e-4)
    a = ap.parse_args()

    m = load(a.assets)
    d = mujoco.MjData(m)
    mujoco.mj_resetData(m, d)
    mujoco.mj_forward(m, d)
    q0 = d.qpos.copy()

    tid, aid = {}, {}
    for i in range(m.ntendon):
        n = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_TENDON, i)
        tid[n.replace("R:", "").replace("_tendon", "")] = i
    for i in range(m.nu):
        n = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
        if n:
            aid[n.replace("R:", "")] = i

    A, _ = moment_arms(m, d, q0, a.eps)
    mcf = read_mcfarland(a.mcfarland)

    print("=" * 104)
    print("WHAT DOES LU_RB REPRESENT?  Measured on MUSIC-Hand-v0.15, right hand.")
    print(f"MuJoCo {mujoco.__version__}   ·   assets {a.assets}")
    print(f"moment arms by central difference at {a.eps} rad, reference posture, mm per rad")
    print("=" * 104)

    # ---------------------------------------------------------------- 0. convention
    print("\n\n0. THE SIGN CONVENTION, ESTABLISHED FROM MUSCLES WHOSE ACTION IS NOT IN DISPUTE")
    print("-" * 104)
    print("A negative moment arm here means the tendon SHORTENS as the joint coordinate")
    print("increases. Which sign that is for flexion is what the controls below fix.\n")
    print(f"{'joint':22s}{'FDP':>10s}{'FDS':>10s}{'EDC':>10s}"
          f"{'flexors carry':>18s}{'extensor carries':>20s}")
    flexsign = {}
    for dig in DIGITS:
        for js in (f"mcp{dig}_flexion", f"pm{dig}_flexion", f"md{dig}_flexion"):
            j = f"R:{js}"
            if j not in A:
                continue
            v = {}
            for c in (f"FDP{dig}", f"FDS{dig}", f"EDC{dig}"):
                v[c[:3]] = A[j][tid[c]] if c in tid else 0.0
            fl = [x for k, x in v.items() if k in ("FDP", "FDS") and abs(x) >= 0.05]
            ex = [x for k, x in v.items() if k == "EDC" and abs(x) >= 0.05]
            fs = np.mean(fl) if fl else None
            flexsign[js] = fs
            print(f"{js:22s}{v['FDP']:10.2f}{v['FDS']:10.2f}{v['EDC']:10.2f}"
                  f"{('negative' if fs is not None and fs < 0 else 'positive' if fs is not None else 'n/a'):>18s}"
                  f"{('negative' if ex and np.mean(ex) < 0 else 'positive' if ex else 'n/a'):>20s}")
    abd = {}
    print()
    for c, j in (("ADM", "R:mcp5_abduction"), ("APB", "R:cmc_abduction")):
        if c in tid and j in A:
            abd[j] = A[j][tid[c]]
            print(f"  {c:5s} at {j:20s} {A[j][tid[c]]:+8.2f} mm  ->  that sign is ABDUCTION")
    abdsign = np.sign(abd.get("R:mcp5_abduction", 1.0))

    # ---------------------------------------------------------------- 1. attachments
    print("\n\n1. WHERE EACH PATH SITE SITS.  The last body in the path is the insertion.")
    print("-" * 104)
    WK = {int(mujoco.mjtWrap.mjWRAP_SITE): "site",
          int(mujoco.mjtWrap.mjWRAP_SPHERE): "sphere",
          int(mujoco.mjtWrap.mjWRAP_CYLINDER): "cylinder",
          int(mujoco.mjtWrap.mjWRAP_PULLEY): "pulley"}
    insertion, origin = {}, {}
    for dig in DIGITS:
        for stem in STEMS:
            name = f"{stem}{dig}"
            ti = tid.get(name)
            if ti is None:
                continue
            adr, num = int(m.tendon_adr[ti]), int(m.tendon_num[ti])
            print(f"\n  {name}")
            bodies = []
            for w in range(adr, adr + num):
                kind = WK.get(int(m.wrap_type[w]), "?")
                oid = int(m.wrap_objid[w])
                if kind == "site":
                    sn = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_SITE, oid)
                    bn = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, int(m.site_bodyid[oid]))
                    p = m.site_pos[oid] * 1000.0
                    bodies.append(bn)
                    print(f"      {kind:9s} {sn:38s} body={bn:14s} "
                          f"pos=({p[0]:7.2f},{p[1]:7.2f},{p[2]:7.2f})")
                else:
                    gn = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, oid)
                    bn = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, int(m.geom_bodyid[oid]))
                    print(f"      {kind:9s} {gn:38s} body={bn:14s}  (wrap surface)")
            insertion[name] = bodies[-1] if bodies else "?"
            origin[name] = bodies[0] if bodies else "?"

    print("\n  summary of origin and insertion")
    print(f"  {'unit':10s}{'origin body':16s}{'insertion body':16s}{'reaches':>28s}")
    for dig in DIGITS:
        for stem in STEMS:
            name = f"{stem}{dig}"
            if name not in insertion:
                continue
            ins = insertion[name]
            reach = ("proximal phalanx, bony insertion" if "proxph" in ins
                     else "middle phalanx, a lateral band" if "midph" in ins
                     else "distal phalanx" if "distph" in ins else ins)
            print(f"  {name:10s}{origin[name]:16s}{ins:16s}{reach:>28s}")

    # ---------------------------------------------------------------- 2. crossings
    print("\n\n2. WHICH JOINTS EACH UNIT CROSSES, AND IN WHICH DIRECTION.  THE DECISIVE TEST.")
    print("-" * 104)
    print("Read against the convention fixed in part 0. A dash is a moment arm under")
    print("0.05 mm, i.e. the joint is not crossed at all.\n")

    def sense(js, val):
        if abs(val) < 0.05:
            return "-"
        fs = flexsign.get(js)
        if fs is None:
            return "?"
        return "FLEXES" if (val < 0) == (fs < 0) else "EXTENDS"

    verdict = {}
    for dig in DIGITS:
        print(f"  --- digit {dig} ---")
        for stem in STEMS:
            name = f"{stem}{dig}"
            if name not in tid:
                continue
            row, acts = f"  {name:10s}", []
            for js in (f"mcp{dig}_flexion", f"pm{dig}_flexion", f"md{dig}_flexion"):
                j = f"R:{js}"
                if j not in A:
                    continue
                v = A[j][tid[name]]
                s = sense(js, v)
                row += f"{js.split('_')[0]:>7s} {s:8s}({v:+6.2f})   "
                if s not in ("-", "?"):
                    acts.append((js.split("_")[0], s))
            verdict[name] = acts
            print(row)
        print()

    print("  the pattern, stated plainly")
    for stem in STEMS:
        shapes = {tuple(verdict.get(f"{stem}{dig}", [])) for dig in DIGITS}
        print(f"    {stem:8s} " + ("IDENTICAL on all four digits: " if len(shapes) == 1
                                   else "NOT identical across digits: "))
        for dig in DIGITS:
            print(f"        digit {dig}: " + ", ".join(f"{j} {s}" for j, s in verdict.get(f"{stem}{dig}", [])))

    # ---------------------------------------------------------------- 3. which side
    print("\n\n3. WHICH SIDE OF THE DIGIT EACH UNIT LIES ON, from the abduction moment arm.")
    print("-" * 104)
    print(f"  abductor digiti minimi carries {abdsign:+.0f} at the little finger, so that sign is ABDUCTION,")
    print("  which for any digit means away from the hand's own midline.\n")
    print(f"  {'unit':10s}{'abduction arm mm':>18s}{'side':>12s}")
    side = {}
    for dig in DIGITS:
        j = f"R:mcp{dig}_abduction"
        if j not in A:
            continue
        for stem in STEMS:
            name = f"{stem}{dig}"
            if name not in tid:
                continue
            v = A[j][tid[name]]
            s = "abducts" if np.sign(v) == abdsign else "adducts"
            side[name] = s
            print(f"  {name:10s}{v:18.2f}{s:>12s}")
        print()
    print("  RI and LU_RB on one side and UI_UB on the other, on every digit?")
    ok = all(side.get(f"RI{d}") == side.get(f"LU_RB{d}") != side.get(f"UI_UB{d}") for d in DIGITS)
    print(f"    {'YES' if ok else 'NO'}"
          + "".join(f"\n      digit {d}: RI {side.get(f'RI{d}')}, LU_RB {side.get(f'LU_RB{d}')},"
                    f" UI_UB {side.get(f'UI_UB{d}')}" for d in DIGITS))

    # ---------------------------------------------------------------- 4. forces
    print("\n\n4. THE FORCES, AGAINST WHAT EACH READING PREDICTS.")
    print("-" * 104)
    if not mcf:
        print("  McFarland table not supplied; skipping.")
        return 0

    def F(names):
        return sum(mcf[n]["F"] for n in names if n in mcf)

    print("  Every MUSIC-Hand to McFarland mapping below is an INFERENCE from the naming")
    print("  and from anatomy. Nothing in the model files states it.\n")
    print(f"  {'unit':10s}{'declared N':>12s}{'reading 1: lumbrical':>24s}{'x':>9s}"
          f"{'reading 2: lumbrical + radial interosseous':>44s}{'x':>9s}")
    for dig in DIGITS:
        name = f"LU_RB{dig}"
        if name not in aid:
            continue
        dec = abs(m.actuator_gainprm[aid[name]][2])
        r1 = F(LUMBRICAL[dig])
        r2 = F(LUMBRICAL[dig] + RADIAL_INTEROSSEOUS[dig])
        print(f"  {name:10s}{dec:12.2f}{r1:24.2f}{dec / r1 if r1 else 0:9.2f}"
              f"{r2:44.2f}{dec / r2 if r2 else 0:9.2f}")

    print(f"\n  {'unit':10s}{'declared N':>12s}{'ulnar interosseous':>24s}{'x':>9s}")
    for dig in DIGITS:
        name = f"UI_UB{dig}"
        if name not in aid:
            continue
        dec = abs(m.actuator_gainprm[aid[name]][2])
        u = F(ULNAR_INTEROSSEOUS[dig] + ULNAR_EXTRA.get(dig, []))
        lbl = "+".join(ULNAR_INTEROSSEOUS[dig] + ULNAR_EXTRA.get(dig, [])) or "none in McFarland"
        print(f"  {name:10s}{dec:12.2f}{u:24.2f}{dec / u if u else 0:9.2f}   ({lbl})")

    print("\n  THE PAIR THAT MATTERS. If LU_RB is the lumbrical plus the radial BAND of the")
    print("  same interosseous whose BONY insertion is RI, then RI and LU_RB together should")
    print("  total one interosseous plus one lumbrical, not two of anything.")
    print(f"\n  {'digit':7s}{'RI + LU_RB N':>14s}{'McFarland radial + lumbrical':>32s}{'x':>9s}")
    for dig in DIGITS:
        if f"RI{dig}" not in aid or f"LU_RB{dig}" not in aid:
            continue
        pair = abs(m.actuator_gainprm[aid[f'RI{dig}']][2]) + abs(m.actuator_gainprm[aid[f'LU_RB{dig}']][2])
        ref = F(LUMBRICAL[dig] + RADIAL_INTEROSSEOUS[dig])
        print(f"  {dig:<7d}{pair:14.2f}{ref:32.2f}{pair / ref if ref else 0:9.2f}")

    print("\n  RADIAL SIDE AGAINST ULNAR SIDE, which is the ratio the study's own variable")
    print("  turns on, because opening the hand at the little finger is abduction and the")
    print("  radial-side muscles are what resists it.")
    print(f"\n  {'digit':7s}{'model radial':>14s}{'model ulnar':>13s}{'model ratio':>13s}"
          f"{'McF radial':>12s}{'McF ulnar':>11s}{'McF ratio':>11s}{'inverted?':>11s}")
    for dig in DIGITS:
        need = [f"RI{dig}", f"LU_RB{dig}", f"UI_UB{dig}"]
        if any(n not in aid for n in need):
            continue
        mr = abs(m.actuator_gainprm[aid[f'RI{dig}']][2]) + abs(m.actuator_gainprm[aid[f'LU_RB{dig}']][2])
        mu = abs(m.actuator_gainprm[aid[f'UI_UB{dig}']][2])
        if dig == 5 and "ADM" in aid:
            mu += abs(m.actuator_gainprm[aid["ADM"]][2])
        cr = F(LUMBRICAL[dig] + RADIAL_INTEROSSEOUS[dig])
        cu = F(ULNAR_INTEROSSEOUS[dig] + ULNAR_EXTRA.get(dig, []))
        rm, rc = (mr / mu if mu else 0), (cr / cu if cu else 0)
        inv = "YES" if rm and rc and ((rm > 1) != (rc > 1)) else "no"
        print(f"  {dig:<7d}{mr:14.2f}{mu:13.2f}{rm:13.2f}{cr:12.2f}{cu:11.2f}{rc:11.2f}{inv:>11s}")
    print("\n  The little finger row includes abductor digiti minimi on the ulnar side of both")
    print("  models, because that is where it acts and MUSIC-Hand represents it separately.")
    print("  ADM's own declared force is the shipped 12.3 N here, not the 45.21 N of the")
    print("  approved drop-in files, so this row is the model AS SHIPPED.")

    # ---------------------------------------------------------------- 5. anomalies
    print("\n\n5. ANOMALIES FOUND ALONG THE WAY, recorded because they were not looked for.")
    print("-" * 104)
    print("  a. Sign of the metacarpophalangeal flexion moment arm, unit by unit:")
    for stem in STEMS:
        vals = []
        for dig in DIGITS:
            j, name = f"R:mcp{dig}_flexion", f"{stem}{dig}"
            if j in A and name in tid:
                vals.append((dig, A[j][tid[name]]))
        print(f"     {stem:8s} " + "  ".join(f"d{d}:{v:+6.2f}" for d, v in vals)
              + ("   <- ONE DIGIT DISAGREES IN SIGN"
                 if len({np.sign(v) for _, v in vals}) > 1 else ""))
    print("\n  b. Origin site coordinates, to check for round numbers among measured ones:")
    for dig in DIGITS:
        for stem in STEMS:
            name = f"{stem}{dig}"
            ti = tid.get(name)
            if ti is None:
                continue
            w = int(m.tendon_adr[ti])
            if int(m.wrap_type[w]) != int(mujoco.mjtWrap.mjWRAP_SITE):
                continue
            oid = int(m.wrap_objid[w])
            p = m.site_pos[oid] * 1000.0
            bn = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, int(m.site_bodyid[oid]))
            print(f"     {name:10s} {bn:14s} ({p[0]:8.2f},{p[1]:8.2f},{p[2]:8.2f})")
    print("\n  c. Declared force and shipped length range, all twelve intrinsic units:")
    print(f"     {'unit':10s}{'force N':>10s}{'lengthrange mm':>28s}{'span mm':>10s}")
    for dig in DIGITS:
        for stem in STEMS:
            name = f"{stem}{dig}"
            if name not in aid:
                continue
            i = aid[name]
            lr = m.actuator_lengthrange[i] * 1000.0
            print(f"     {name:10s}{abs(m.actuator_gainprm[i][2]):10.2f}"
                  f"{lr[0]:14.3f} to {lr[1]:9.3f}{lr[1] - lr[0]:10.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
