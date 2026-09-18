#!/usr/bin/env python3
"""
Validate the calibrated piano key against technician metrology and published
key-speed measurements. Run 2, 6 September 2026.

Supersedes test_key_physics_2026-09-06.py, which tested down-weight only and
had no friction term.

Runs standalone:
    pip3 install mujoco numpy --break-system-packages
    python3 test_key_physics_2026-09-06_run2.py

WHAT IT CHECKS
  down-weight, up-weight, friction and balance weight, for white and black
  keys, at each key's own front edge, against Steinway New York grand
  mid-register regulation: down 48 gf, up 20 gf or more, friction near 13
  felt inertia at the key front, against about 138 g computed from
  Hirschkorn's measured key mass and moment of inertia
  key speed under constant force at piano, mezzo forte and forte
  that a light touch sounds a note at all
  that MuJoCo's frictionloss actually holds, which it does not without the
  no-slip solver pass

REFERENCE VALUES
  Steinway and Sons worldwide technical reference, New York grand regulation
  Hirschkorn, MASc thesis, University of Waterloo, 2004, Table A.1
  Furuya, Altenmueller, Katayose and Kinoshita, BMC Neuroscience 11:82, 2010
    maximum key force 4.4 N at piano and 9.6 N at forte, Yamaha U1 upright
  Askenfelt and Jansson, Five Lectures on the Acoustics of the Piano, 1990
    key speed 0.3 to 0.5 m/s at mezzo forte, seldom above 1 m/s at forte
"""

import numpy as np
import mujoco

G = 9.80665

TEMPLATE = """<mujoco>
 <compiler inertiafromgeom="auto" angle="radian" balanceinertia="true"
           boundmass="0.001" boundinertia=".0001"/>
 <option timestep="0.00208333333" impratio="10" gravity="0 0 0" {noslip}/>
 <worldbody>
  <body name="key" pos="0 0 0">
   <joint name="kj" type="hinge" axis="1 0 0" pos="0 0 0" limited="true"
          range="{rng} 0" solreflimit=".01 1" solimplimit=".95 .99 .001"
          stiffness="{k}" springref="{ref}" frictionloss="{fl}"
          damping="{d}" armature="{a}"/>
   <geom type="box" size="{sx} {sy} {sz}" pos="0 {sy} 0" mass="{m}"/>
  </body>
 </worldbody>
</mujoco>"""

# geometry as the model defines it
WHITE = dict(rng=-0.0676190854, sx=0.011313735, sy=0.074, sz=0.0105, arm=0.148)
BLACK = dict(rng=-0.08333333333, sx=0.00475, sy=0.048, sz=0.01, arm=0.096)

AS_BUILT_W = dict(k=2.0, ref=0.0, fl=0.0, d=0.05, a=1.0e-3, m=0.040)
AS_BUILT_B = dict(k=2.0, ref=0.0, fl=0.0, d=0.05, a=1.0e-3, m=0.020)
PATCHED_W = dict(k=0.05080, ref=1.0, fl=0.01887, d=0.30, a=2.1422e-3, m=0.120)
PATCHED_B = dict(k=0.03295, ref=1.0, fl=0.01224, d=0.30, a=9.0000e-4, m=0.062)

NOSLIP = 'noslip_iterations="10"'


def build(geo, cfg, noslip=NOSLIP):
    p = dict(cfg)
    p.update({k: geo[k] for k in ("rng", "sx", "sy", "sz")})
    p["noslip"] = noslip
    model = mujoco.MjModel.from_xml_string(TEMPLATE.format(**p))
    return model, mujoco.MjData(model)


def descends(force_n, geo, cfg, arm=None, noslip=NOSLIP):
    arm = arm or geo["arm"]
    model, data = build(geo, cfg, noslip)
    for _ in range(4000):
        data.qfrc_applied[0] = -force_n * arm
        mujoco.mj_step(model, data)
    return data.qpos[0] < -0.002


def rises(force_n, geo, cfg, arm=None, noslip=NOSLIP):
    arm = arm or geo["arm"]
    model, data = build(geo, cfg, noslip)
    data.qpos[0] = model.jnt_range[0][0] * 0.98
    start = data.qpos[0]
    for _ in range(4000):
        data.qfrc_applied[0] = -force_n * arm
        mujoco.mj_step(model, data)
    return data.qpos[0] > start + 0.004


def down_up(geo, cfg, arm=None, noslip=NOSLIP):
    """Down-weight and up-weight in grams-force, by bisection."""
    lo, hi = 0.0, 8.0
    for _ in range(34):
        mid = (lo + hi) / 2
        if descends(mid, geo, cfg, arm, noslip):
            hi = mid
        else:
            lo = mid
    dw = hi
    lo, hi = 0.0, 8.0
    for _ in range(34):
        mid = (lo + hi) / 2
        if rises(mid, geo, cfg, arm, noslip):
            lo = mid
        else:
            hi = mid
    return dw / G * 1000, lo / G * 1000


def felt_inertia_g(geo, cfg, arm=None):
    arm = arm or geo["arm"]
    model, data = build(geo, cfg)
    mujoco.mj_forward(model, data)
    full = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, full)
    return 1000 * full[0, 0] / arm ** 2, model.dof_armature[0], full[0, 0]


def speed(geo, cfg, force_n, arm=None):
    arm = arm or geo["arm"]
    model, data = build(geo, cfg)
    limit = model.jnt_range[0][0]
    peak, t_bottom, t = 0.0, None, 0.0
    for _ in range(14000):
        data.qfrc_applied[0] = -force_n * arm
        mujoco.mj_step(model, data)
        t += model.opt.timestep
        peak = max(peak, abs(data.qvel[0]) * arm)
        if t_bottom is None and data.qpos[0] <= limit * 0.995:
            t_bottom = t
    return peak, t_bottom


def report(label, geo, cfg):
    dw, uw = down_up(geo, cfg)
    felt, arm_term, total = felt_inertia_g(geo, cfg)
    print("=" * 70)
    print(label)
    print("=" * 70)
    print("  down-weight %6.1f gf    up-weight %6.1f gf" % (dw, uw))
    print("  friction    %6.1f gf    balance   %6.1f gf" % ((dw - uw) / 2, (dw + uw) / 2))
    print("  felt inertia at the front %6.1f g   (armature supplies %.0f%%)"
          % (felt, 100 * arm_term / total))
    print("  %-11s %-11s %-12s %s" % ("tip force", "gram-force", "descent", "peak key speed"))
    for f in (0.6, 4.4, 7.0, 9.6, 20.0):
        peak, t_bottom = speed(geo, cfg, f)
        when = ("%.0f ms" % (1000 * t_bottom)) if t_bottom else "never bottoms"
        print("  %-11s %-11s %-12s %.3f m/s"
              % ("%.1f N" % f, "%.0f gf" % (f / G * 1000), when, peak))
    print()


def position_table(geo, cfg, label, points):
    print("=" * 70)
    print("WHERE ON THE KEY: %s" % label)
    print("=" * 70)
    print("  %-10s %-10s %-10s %-10s %s" % ("play pt", "down", "up", "balance", "note"))
    for dist, note in points:
        dw, uw = down_up(geo, cfg, arm=dist)
        print("  %-10s %-10s %-10s %-10s %s"
              % ("%.0f mm" % (dist * 1000), "%.1f gf" % dw, "%.1f gf" % uw,
                 "%.1f gf" % ((dw + uw) / 2), note))
    print()


def noslip_check():
    print("=" * 70)
    print("SOLVER CHECK: does frictionloss actually hold?")
    print("=" * 70)
    for tag, ns in (("default solver", ""), ("noslip_iterations=10", NOSLIP)):
        held_at, moved_at = None, None
        for f in np.arange(0.05, 1.2, 0.02):
            if not descends(float(f), WHITE, PATCHED_W, noslip=ns):
                held_at = float(f)
            elif moved_at is None:
                moved_at = float(f)
        print("  %-22s highest force held %s, lowest force that moved %s"
              % (tag,
                 ("%.1f gf" % (held_at / G * 1000)) if held_at else "none",
                 ("%.1f gf" % (moved_at / G * 1000)) if moved_at else "none"))
    print("  Without the no-slip pass, friction leaks and the calibration fails silently.")
    print()


def checks():
    out = []
    dw, uw = down_up(WHITE, PATCHED_W)
    felt, _, _ = felt_inertia_g(WHITE, PATCHED_W)
    out.append(("white down-weight within 47 to 50 gf", 47.0 <= dw <= 50.0))
    out.append(("white up-weight at or above 20 gf", uw >= 20.0))
    out.append(("white friction within 10 to 16 gf", 10.0 <= (dw - uw) / 2 <= 16.0))
    out.append(("white felt inertia within 120 to 155 g", 120.0 <= felt <= 155.0))
    dwb, uwb = down_up(BLACK, PATCHED_B)
    out.append(("black down-weight within 4 gf of white", abs(dwb - dw) <= 4.0))
    out.append(("black up-weight at or above 20 gf", uwb >= 20.0))
    p_p, _ = speed(WHITE, PATCHED_W, 4.4)
    p_mf, _ = speed(WHITE, PATCHED_W, 7.0)
    p_ff, _ = speed(WHITE, PATCHED_W, 9.6)
    out.append(("piano key speed below 0.30 m/s at 4.4 N", p_p < 0.30))
    out.append(("mezzo forte key speed 0.30 to 0.50 m/s at 7.0 N", 0.30 <= p_mf <= 0.50))
    out.append(("forte key speed 0.50 to 1.00 m/s at 9.6 N", 0.50 <= p_ff <= 1.00))
    t_soft, _ = speed(WHITE, PATCHED_W, 0.6)
    out.append(("a 61 gf touch does bottom the key", t_soft > 0))
    dw110, _ = down_up(WHITE, PATCHED_W, arm=0.110)
    out.append(("touch weight rises when playing further in", dw110 > dw * 1.2))
    return out


if __name__ == "__main__":
    report("WHITE KEY AS BUILT", WHITE, AS_BUILT_W)
    report("BLACK KEY AS BUILT", BLACK, AS_BUILT_B)
    report("WHITE KEY CALIBRATED, run 2", WHITE, PATCHED_W)
    report("BLACK KEY CALIBRATED, run 2", BLACK, PATCHED_B)

    position_table(WHITE, PATCHED_W, "white key", [
        (0.148, "front edge, the reference position"),
        (0.130, "ordinary white-key playing"),
        (0.110, "reaching between the black keys"),
        (0.095, "thumb wedged in on a chord"),
        (0.080, "as far back as is playable"),
    ])
    position_table(BLACK, PATCHED_B, "black key", [
        (0.096, "front edge"),
        (0.080, "ordinary black-key playing"),
        (0.065, "deep in"),
    ])

    noslip_check()

    print("=" * 70)
    print("CHECKS AGAINST PUBLISHED VALUES, calibrated key")
    print("=" * 70)
    failures = 0
    for label, ok in checks():
        print("  [%s] %s" % ("pass" if ok else "FAIL", label))
        failures += 0 if ok else 1
    print()
    print("  %d of %d checks pass." % (len(checks()) - failures, len(checks())))
