#!/usr/bin/env python3
"""Can the hand hold the posture, with every muscle activation free?

Elizabeth Schumann approved this as a second check alongside the passive force
criterion on September 28, 2026. It exists because the per-muscle criterion of
open item 31 PASSED the corrected model at 1 of 44 while the whole-hand statics
were broken: **a per-muscle force fraction can pass while the summed joint
torque makes the posture unholdable.** This measures the sum.

WHAT IT DOES. At a given posture, asks whether some activation vector in [0,1]^44
balances the passive muscle torque at every muscle-actuated hand degree of
freedom. If not, it reports the minimum total unbalanceable torque and which
joints carry it. Root degrees of freedom are excluded: the arm holds those.

WHAT IT FOUND, and this is the number to compare against:
    pristine tree, flat default posture   residual 0.0032 Nm   passive torque  0.125 Nm
    after Step 1, same posture            residual 6.59   Nm   passive torque 27.61  Nm

TWO THINGS RULED OUT as explanations, so do not re-test them: joint limits
supplying the residual (four to five joints do sit exactly on a limit, and
allowing them one-sided constraint forces changes nothing), and a solver
artifact (the relaxed problem below solves cleanly and localizes the residual).

    python3 check_hand_can_hold_itself_2026-09-28.py <assets_dir> [--max-residual 0.15]
                                                     [--curl F] [--abduction DEG]

Exit 0 on pass, 1 on fail. Requires mujoco>=3.13, numpy, scipy.
"""
import argparse, os, sys
import numpy as np, mujoco
from scipy.optimize import linprog

NMUS = 44
FLEX = ["mcp2_flexion","pm2_flexion","md2_flexion","mcp3_flexion","pm3_flexion","md3_flexion",
        "mcp4_flexion","pm4_flexion","md4_flexion","mcp5_flexion","pm5_flexion","md5_flexion"]


def residual(xml, curl=None, abduction=None):
    m = mujoco.MjModel.from_xml_path(xml); d = mujoco.MjData(m)
    pre = "R:" if "right" in os.path.basename(xml) else "L:"
    jid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, pre + n)
    rj = jid("root_joint")
    rootd = set(range(m.jnt_dofadr[rj], m.jnt_dofadr[rj] + 6)) if rj >= 0 else set()

    mujoco.mj_resetData(m, d)
    if curl is not None:
        for n in FLEX:
            j = jid(n)
            if j >= 0:
                lo, hi = m.jnt_range[j]
                d.qpos[m.jnt_qposadr[j]] = lo + curl * (hi - lo)
    if abduction is not None:
        j = jid("cmc_abduction")
        if j >= 0:
            d.qpos[m.jnt_qposadr[j]] = np.radians(abduction)
    q = d.qpos.copy()

    d.act[:] = 0.0; d.ctrl[:NMUS] = 0.0; mujoco.mj_forward(m, d)
    M = np.zeros((m.nu, m.nv))
    mujoco.mju_sparse2dense(M, d.actuator_moment, d.moment_rownnz, d.moment_rowadr, d.moment_colind)
    Fp = d.actuator_force[:NMUS].copy()
    dofs = [j for j in range(m.nv) if np.abs(M[:NMUS, j]).sum() > 0 and j not in rootd]

    mujoco.mj_resetData(m, d); d.qpos[:] = q
    d.act[:] = 1.0; d.ctrl[:NMUS] = 1.0; mujoco.mj_forward(m, d)   # act, not ctrl alone
    Fa = d.actuator_force[:NMUS].copy() - Fp

    tp = (M[:NMUS, dofs] * Fp[:, None]).sum(0)
    R  = (M[:NMUS, dofs] * Fa[:, None])
    n = len(dofs)
    A = np.hstack([R.T, np.eye(n), -np.eye(n)])
    c = np.r_[np.zeros(NMUS), np.ones(n), np.ones(n)]
    r = linprog(c, A_eq=A, b_eq=-tp, bounds=[(0, 1)] * NMUS + [(0, None)] * (2 * n), method="highs")
    if not r.success:
        return None, None, None, None
    s = r.x[NMUS:NMUS + n] - r.x[NMUS + n:]
    names = {}
    for j in range(m.njnt):
        if m.jnt_type[j] in (mujoco.mjtJoint.mjJNT_FREE, mujoco.mjtJoint.mjJNT_BALL):
            continue
        names[m.jnt_dofadr[j]] = (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j) or "").split(":")[-1]
    worst = sorted(((abs(s[k]), names.get(dofs[k], str(dofs[k])), s[k]) for k in range(n)), reverse=True)
    return r.fun, float(np.abs(tp).sum()), n, worst


def main():
    p = argparse.ArgumentParser()
    p.add_argument("assets"); p.add_argument("--max-residual", type=float, default=0.15)
    p.add_argument("--curl", type=float, default=None)
    p.add_argument("--abduction", type=float, default=None)
    a = p.parse_args()
    failed = False
    for hand in ("right", "left"):
        xml = os.path.join(a.assets, f"{hand}_hand_ds6.5_muscle_driven.xml")
        if not os.path.exists(xml):
            print(f"{hand}: no model at {xml}"); failed = True; continue
        res, passive, n, worst = residual(xml, a.curl, a.abduction)
        print(f"\n{hand} hand, {n} muscle-actuated hand dofs, root excluded")
        if res is None:
            print("  solver failed"); failed = True; continue
        print(f"  total passive joint torque        : {passive:9.4f} Nm")
        print(f"  minimum unbalanceable torque      : {res:9.4f} Nm   (pristine reference 0.0032)")
        bad = [w for w in worst if w[0] > 1e-9]
        print(f"  joints that cannot be balanced    : {len(bad)} of {n}")
        for mag, nm, sv in bad[:6]:
            print(f"      {nm:>16} needs {sv:+8.4f} Nm that no activation supplies")
        if res > a.max_residual:
            print(f"  FAIL: residual {res:.4f} Nm exceeds {a.max_residual}. "
                  f"The hand cannot hold this posture.")
            failed = True
        else:
            print(f"  PASS: within {a.max_residual} Nm")
    print("\n" + ("REFUSED" if failed else "PASSED"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
