#!/usr/bin/env python3
"""Is each wrapping repair a constant offset to the tendon path, or does it change how
the path varies with posture? A constant offset only re-registers the operating window;
a varying one changes the moment arm and therefore the mechanics."""
import os, subprocess, sys
import numpy as np, mujoco
PROBE = ('<mujoco model="probe">\n  <include file="defaults.xml"/>\n'
         '  <include file="right_assets/right_hand_definition_meta.xml"/>\n'
         '  <include file="right_assets/right_hand_definition_tendons.xml"/>\n'
         '  <include file="right_assets/right_hand_actuators_muscle.xml"/>\n'
         '  <worldbody><include file="right_assets/right_hand_freeroot.xml"/></worldbody>\n</mujoco>\n')
A = "/tmp/scratch/assets"
def build():
    p = os.path.join(A, "_p_o.xml"); open(p, "w").write(PROBE)
    m = mujoco.MjModel.from_xml_path(p); os.remove(p); return m
def apply(c):
    subprocess.run([sys.executable, "/tmp/scratch/out/patch_wrapping_2026-09-07.py",
                    "--assets", A, "--pristine", "/tmp/scratch/pristine", "--condition", c],
                   check=True, capture_output=True)
T = ["R:APL_tendon","R:FDS4_tendon","R:FDP5_tendon","R:FDS5_tendon","R:FDP3_tendon",
     "R:OP_tendon","R:LU_RB3_tendon","R:LU_RB4_tendon"]
def lengths(m, n=6000):
    d = mujoco.MjData(m)
    ids = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_TENDON, t) for t in T]
    jq = [(m.jnt_qposadr[j], m.jnt_range[j,0], m.jnt_range[j,1]) for j in range(m.njnt)
          if m.jnt_type[j] not in (mujoco.mjtJoint.mjJNT_FREE, mujoco.mjtJoint.mjJNT_BALL) and m.jnt_limited[j]]
    mujoco.mj_resetData(m, d); mujoco.mj_forward(m, d); q0 = d.qpos.copy()
    rng = np.random.default_rng(23); out = np.zeros((n, len(ids)))
    for r in range(n):
        q = q0.copy()
        for (adr, lo, hi) in jq: q[adr] = rng.uniform(lo, hi)
        d.qpos[:] = q; mujoco.mj_forward(m, d)
        out[r] = [d.ten_length[i] for i in ids]
    return out
apply("BASE"); Lb = lengths(build())
apply("ALL");  La = lengths(build())
apply("BASE")
print("Change in tendon length produced by re-enabling the wrap, over 6000 random postures, mm")
print(f"{'tendon':12s}{'mean':>10s}{'min':>10s}{'max':>10s}{'sd':>10s}  reading")
print("-"*78)
for k, t in enumerate(T):
    dd = (La[:, k] - Lb[:, k]) * 1000
    if abs(dd).max() < 1e-6: r = "no effect at all"
    elif dd.std() < 0.01:    r = "CONSTANT offset: re-registers the window, no change in mechanics"
    else:                    r = "varies with posture: changes the moment arm as well"
    print(f"{t.replace('R:','').replace('_tendon',''):12s}{dd.mean():10.3f}{dd.min():10.3f}{dd.max():10.3f}{dd.std():10.3f}  {r}")
