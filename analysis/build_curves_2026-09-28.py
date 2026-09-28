#!/usr/bin/env python3
"""Build the force and geometry curves against thumb abduction, reproducibly.

WHY THIS EXISTS. On September 28, 2026 the four curve CSVs in this folder were
found to have no generator anywhere on the Workspace: a search of every .py
under Research_Projects/AI_Model/ for `roll_Nm_per_N`, `strength_N_mu0.5` and
"three channels" returned nothing. So no curve could be reproduced, and the
carry-over of strength and agility into
`curve, three channels at a holdable playing posture 2026-09-28.csv` could not
have been caught by rerunning, because there was nothing to rerun.

EVERY DEFINITION BELOW IS STATED, AND EACH ONE SAYS WHETHER IT REPRODUCES THE
RECORD'S OWN NUMBERS. Two do, exactly. One is close in shape and not exact. One
does not, and is a fresh definition rather than a recovery.

    python3 build_curves_2026-09-28.py <assets_dir> [--hand right] [--out FILE]
                                       [--mcp DEG --pip DEG --dip DEG] [--points N]

WHAT EACH COLUMN IS

  span_mm
      Distance between the body origins of THtip and LFtip.
      REPRODUCES THE RECORD. Matches the span_mm column of
      `curve, three channels on the REPAIRED model 2026-09-28.csv` to seven
      significant figures at the flat default. Span is kinematic and is
      identical across the pristine, repair-alone and Step 1 trees, so it does
      not identify which tree a curve was run on.

  effMass_g
      Effective mass at the thumb tip along world -z, THE RIGID RUNG: every hand
      joint locked, only the six root degrees of freedom free.
          1000 / (d . (J Minv J^T) . d),  J and M restricted to the root dofs.
      REPRODUCES THE RECORD EXACTLY, four points checked to four decimals:
      395.6723, 306.1976, 254.0402, 321.1194 g.
      Locking the hand is what makes it the rigid rung, and it is why defect 7,
      the unscaled armature, moves this figure by under one percent here and by
      17 to 33 percent on the yielding rung, where all 117 dofs carry armature.

  roll_Nm_per_N
      Moment about Ortmann's forearm rotation axis per newton pressed down at
      the thumb tip.  |(r x d) . u|, with r from a point on the axis to the tip,
      d = world -z, u the axis unit vector.
      ORTMANN'S AXIS IS THE LINE FROM THE ULNA BODY ORIGIN TO RFtip, the ring
      fingertip. Ortmann 1929: "The axis of fore-arm rotation extends through
      the head of the ulna in a line with the fourth finger of the extended
      hand, not the third finger."
      REPRODUCES THE RECORD EXACTLY. At the default extended posture it gives
      thumb 0.0833, index 0.0513, middle 0.0262, ring 0.0000, little 0.0118
      Nm/N, which is the record's per-digit table to four decimals. The
      superseded ulna-to-capitate axis, also implemented below for the
      comparison, gives the thumb 0.0549, which is the record's figure for it.

  strength_N_mu0.5
      Maximum downward force at the thumb tip. A linear program: maximise f over
      activations in [0,1] for all 44 muscles, subject to static equilibrium at
      the thumb's own four degrees of freedom, with the key's reaction on the
      fingertip inside a friction cone of mu = 0.5, linearised to 16 facets.
      Muscle force is taken linear in activation between the all-zero and
      all-one forces, which is the approximation
      `check_hand_can_hold_itself_2026-09-28.py` already makes.
      DOES NOT REPRODUCE THE RECORD EXACTLY. Four points agree to within 0.14 to
      1.81 N, which is 0.5 to 6.7 percent, with the same peak position and the
      same fall at full abduction. The sign of the disagreement is mixed across
      the four, so it is a different formulation and not a discretisation error.
      THE RECORD'S OWN FORMULATION IS NOT RECOVERED.
      Equilibrium is enforced at the thumb alone because requiring it at all 23
      muscle-actuated hand dofs is INFEASIBLE at every posture, which is L28's
      finding. Enforcing it at the thumb plus pro_sup, or at the thumb plus the
      whole wrist, gives the identical answer: only the thumb's dofs bind.
      "The rest of the hand is braced" is doing real work in this number and it
      stands in for passive structure the model does not have.

  agility_mps2
      Maximum downward acceleration of the thumb tip, maximising over activations
      in [0,1], with the root free.
      DOES NOT REPRODUCE THE RECORD. It is two to three and a half times the
      record's agility_mps2 and the ratio is not constant, so the record's
      quantity is something else. THIS COLUMN IS A FRESH DEFINITION, not a
      recovery, and it is not comparable with any agility figure already on
      record. It is written here because a stated definition that can be rerun
      is worth more than an unstated one that cannot.

  residual_Nm, passive_Nm, overlap_mm
      Whether the posture holds itself, and whether the fingers interpenetrate,
      so no row can be read without knowing whether its posture is valid.
      residual_Nm is the minimum unbalanceable joint torque with every
      activation free, the quantity of
      `check_hand_can_hold_itself_2026-09-28.py`, and it reproduces that script.
      overlap_mm is the deepest hand-to-hand interpenetration. P28's criterion is
      interpenetration deeper than 0.5 mm, NOT contact: real adjacent fingers
      touch, and 7 of 10 contacts at a measured human resting posture sit inside
      the 1 mm geom margin without overlapping.

POSTURE, AND IT IS THE LARGEST THING ON THIS PAGE. --mcp, --pip and --dip are
degrees of flexion applied to all four fingers, measured FROM THE FLAT DEFAULT,
which is qpos0 and is zero at every finger joint.

**Posture is not a detail in this model and no curve should be quoted without
it.** Curling the finger that is pressing takes what the key feels from 261.6 to
580.6 grams at the index and 255.6 to 618.0 at the middle. Holding the hand firm
rather than letting the joints give is a further factor of 4.9, 53.9 grams
against 261.6 at one posture. Both are larger than the 35.8 percent the whole
thumb abduction sweep produces. Every CSV this writes carries its posture and
this warning in its header, so the number cannot be separated from the condition
it was measured under. They are NOT the "curl" fraction of earlier scripts: that
parameterised each joint as `lower limit + curl x range`, so curl 0.00 put every
joint at its lower limit, which is 30 degrees of hyperextension at the knuckle,
and that was misread as the default. R28 withdrew the claim that followed.

TRAPS, each of which cost a day.
  d.ctrl alone produces exactly 0.0 N of muscle force. Activation is a state
      variable, d.act, na = 44. Set both.
  mj_fullM in MuJoCo 3.13 and later is (m, d, dst), and d.qM is now d.M and
      sparse.
  Do not measure anything at the flat default on a tree carrying the September
      12 range correction. It cannot hold that posture: 15 of 23 joints carry
      torque no activation balances, totalling 6.59 Nm. On the muscle repair
      alone the same posture sits at 0.0029 Nm and is fine.

Requires mujoco>=3.13, numpy, scipy. Written by Claude, September 28, 2026.
"""
import argparse, os, sys
import numpy as np, mujoco
from scipy.optimize import linprog

NMUS = 44
MCP = ["mcp2_flexion", "mcp3_flexion", "mcp4_flexion", "mcp5_flexion"]
PIP = ["pm2_flexion", "pm3_flexion", "pm4_flexion", "pm5_flexion"]
DIP = ["md2_flexion", "md3_flexion", "md4_flexion", "md5_flexion"]
THUMB = ["cmc_abduction", "cmc_flexion", "mp_flexion", "ip_flexion"]
DOWN = np.array([0.0, 0.0, -1.0])


class Hand:
    def __init__(self, assets, hand):
        self.xml = os.path.join(assets, f"{hand}_hand_ds6.5_muscle_driven.xml")
        if not os.path.exists(self.xml):
            sys.exit(f"no model at {self.xml}")
        self.m = mujoco.MjModel.from_xml_path(self.xml)
        self.d = mujoco.MjData(self.m)
        self.p = "R:" if hand == "right" else "L:"

    def jid(self, n):
        return mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_JOINT, self.p + n)

    def bid(self, n):
        return mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, self.p + n)

    def pose(self, mcp, pip, dip, abduction):
        m, d = self.m, self.d
        mujoco.mj_resetData(m, d)                      # qpos0, the flat default
        for names, deg in ((MCP, mcp), (PIP, pip), (DIP, dip)):
            for n in names:
                j = self.jid(n)
                if j >= 0:
                    lo, hi = m.jnt_range[j]
                    d.qpos[m.jnt_qposadr[j]] = float(np.clip(np.radians(deg), lo, hi))
        j = self.jid("cmc_abduction")
        lo, hi = m.jnt_range[j]
        d.qpos[m.jnt_qposadr[j]] = float(np.clip(np.radians(abduction), lo, hi))
        return d.qpos.copy()

    def measure(self, mcp, pip, dip, abduction):
        m, d = self.m, self.d
        q = self.pose(mcp, pip, dip, abduction)
        rj = self.jid("root_joint")
        rootd = list(range(m.jnt_dofadr[rj], m.jnt_dofadr[rj] + 6))

        d.act[:] = 0.0; d.ctrl[:NMUS] = 0.0
        mujoco.mj_forward(m, d)

        span = 1000.0 * np.linalg.norm(d.xpos[self.bid("THtip")] - d.xpos[self.bid("LFtip")])

        overlap = 0.0
        for k in range(int(d.ncon)):
            c = d.contact[k]
            n1 = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[c.geom1]) or ""
            n2 = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[c.geom2]) or ""
            if n1.startswith(self.p) and n2.startswith(self.p) and c.dist < 0:
                overlap = min(overlap, c.dist)
        overlap = 1000.0 * abs(overlap)

        jacp = np.zeros((3, m.nv)); jacr = np.zeros((3, m.nv))
        mujoco.mj_jacBody(m, d, jacp, jacr, self.bid("THtip"))
        Mf = np.zeros((m.nv, m.nv)); mujoco.mj_fullM(m, d, Mf)

        Jr = jacp[:, rootd]
        Mir = np.linalg.pinv(Mf[np.ix_(rootd, rootd)])
        eff_rigid = 1000.0 / (DOWN @ (Jr @ Mir @ Jr.T) @ DOWN)

        free = [k for k in range(m.nv) if k not in rootd]
        Jf = jacp[:, free]
        Mif = np.linalg.pinv(Mf[np.ix_(free, free)])
        eff_yield = 1000.0 / (DOWN @ (Jf @ Mif @ Jf.T) @ DOWN)

        ulna = d.xpos[self.bid("ulna")].copy()
        u = d.xpos[self.bid("RFtip")] - ulna                  # Ortmann's axis
        u = u / np.linalg.norm(u)
        rolls = {}
        for nm, bn in (("thumb", "THtip"), ("index", "IFtip"), ("middle", "MFtip"),
                       ("ring", "RFtip"), ("little", "LFtip")):
            rolls[nm] = abs(np.dot(np.cross(d.xpos[self.bid(bn)] - ulna, DOWN), u))
        uc = d.xpos[self.bid("capitate")] - ulna               # superseded axis
        uc = uc / np.linalg.norm(uc)
        roll_capitate = abs(np.dot(np.cross(d.xpos[self.bid("THtip")] - ulna, DOWN), uc))

        M = np.zeros((m.nu, m.nv))
        mujoco.mju_sparse2dense(M, d.actuator_moment, d.moment_rownnz,
                                d.moment_rowadr, d.moment_colind)
        Fp = d.actuator_force[:NMUS].copy()
        hand_dofs = [j for j in range(m.nv)
                     if np.abs(M[:NMUS, j]).sum() > 0 and j not in rootd]
        thumb_dofs = [m.jnt_dofadr[self.jid(n)] for n in THUMB if self.jid(n) >= 0]

        mujoco.mj_resetData(m, d); d.qpos[:] = q
        d.act[:] = 1.0; d.ctrl[:NMUS] = 1.0
        mujoco.mj_forward(m, d)
        Fa = d.actuator_force[:NMUS].copy() - Fp

        residual, passive = self._residual(M, Fp, Fa, hand_dofs)
        strength = self._strength(M, Fp, Fa, thumb_dofs, jacp)
        agility = self._agility(M, Fp, Fa, free, Mif, Jf)

        return dict(deg=abduction, span_mm=span, effMass_g=eff_rigid,
                    effMass_yielding_g=eff_yield, strength_N_mu0p5=strength,
                    agility_mps2=agility, roll_Nm_per_N=rolls["thumb"],
                    roll_index=rolls["index"], roll_middle=rolls["middle"],
                    roll_ring=rolls["ring"], roll_little=rolls["little"],
                    roll_capitate_axis=roll_capitate,
                    residual_Nm=residual, passive_Nm=passive, overlap_mm=overlap)

    @staticmethod
    def _residual(M, Fp, Fa, dofs):
        tp = (M[:NMUS, dofs] * Fp[:, None]).sum(0)
        R = (M[:NMUS, dofs] * Fa[:, None])
        n = len(dofs)
        A = np.hstack([R.T, np.eye(n), -np.eye(n)])
        c = np.r_[np.zeros(NMUS), np.ones(n), np.ones(n)]
        r = linprog(c, A_eq=A, b_eq=-tp,
                    bounds=[(0, 1)] * NMUS + [(0, None)] * (2 * n), method="highs")
        return (r.fun if r.success else float("nan")), float(np.abs(tp).sum())

    @staticmethod
    def _strength(M, Fp, Fa, dofs, jacp, mu=0.5, nfacet=16):
        tp = (M[:NMUS, dofs] * Fp[:, None]).sum(0)
        R = (M[:NMUS, dofs] * Fa[:, None]).T
        Jt = jacp[:, dofs].T
        Aeq = np.hstack([R, Jt[:, 2:3], Jt[:, 0:1], Jt[:, 1:2]])
        c = np.zeros(NMUS + 3); c[NMUS] = -1.0
        Aub = []
        for k in range(nfacet):
            th = 2 * np.pi * k / nfacet
            row = np.zeros(NMUS + 3)
            row[NMUS + 1] = np.cos(th); row[NMUS + 2] = np.sin(th); row[NMUS] = -mu
            Aub.append(row)
        r = linprog(c, A_ub=np.array(Aub), b_ub=np.zeros(nfacet), A_eq=Aeq, b_eq=-tp,
                    bounds=[(0, 1)] * NMUS + [(0, None), (None, None), (None, None)],
                    method="highs")
        return r.x[NMUS] if r.success else float("nan")

    @staticmethod
    def _agility(M, Fp, Fa, free, Mif, Jf):
        w = DOWN @ Jf @ Mif
        base = w @ (M[:NMUS, free] * Fp[:, None]).sum(0)
        coef = (M[:NMUS, free] * Fa[:, None]) @ w
        return base + float(np.sum(np.clip(coef, 0, None)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("assets")
    ap.add_argument("--hand", default="right", choices=["right", "left"])
    ap.add_argument("--mcp", type=float, default=0.0)
    ap.add_argument("--pip", type=float, default=0.0)
    ap.add_argument("--dip", type=float, default=0.0)
    ap.add_argument("--points", type=int, default=25)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    h = Hand(a.assets, a.hand)
    lo, hi = np.degrees(h.m.jnt_range[h.jid("cmc_abduction")])
    rows = [h.measure(a.mcp, a.pip, a.dip, dg)
            for dg in np.linspace(lo, hi, a.points)]

    cols = list(rows[0].keys())
    out = a.out or f"curve_{a.hand}_mcp{a.mcp:g}_pip{a.pip:g}_dip{a.dip:g}.csv"
    flat = (a.mcp == 0 and a.pip == 0 and a.dip == 0)
    with open(out, "w") as f:
        f.write(f"# FINGER POSTURE: MCP {a.mcp}, PIP {a.pip}, DIP {a.dip} degrees of flexion "
                f"from the flat default. Hand: {a.hand}. Assets: {a.assets}\n")
        f.write("# POSTURE IS NOT A DETAIL IN THIS MODEL. Curling the finger that is pressing\n"
                "# takes what the key feels from 261.6 to 580.6 g at the index and 255.6 to\n"
                "# 618.0 at the middle, measured September 28, 2026. Holding the hand firm\n"
                "# rather than letting the joints give is a further factor of 4.9. So a curve\n"
                "# measured at one posture is a curve at that posture and nothing more.\n")
        if flat:
            f.write("# THIS SWEEP IS AT THE FLAT DEFAULT, which is a fully extended hand and is\n"
                    "# not a posture anyone plays from. It is defensible only where the finger\n"
                    "# being measured is the one being moved. Say so wherever these are quoted.\n")
        f.write(",".join(cols) + "\n")
        for r in rows:
            f.write(",".join(f"{r[c]:.18e}" for c in cols) + "\n")

    print(f"{a.hand} hand, {a.points} points, thumb abduction {lo:.4f} to {hi:.4f} deg")
    print(f"finger posture: MCP {a.mcp}, PIP {a.pip}, DIP {a.dip} degrees from the flat default")
    print(f"{'deg':>9}{'span':>9}{'effMass':>10}{'strength':>10}{'roll':>9}{'resid':>9}{'overlap':>9}")
    for r in rows:
        print(f"{r['deg']:>9.2f}{r['span_mm']:>9.2f}{r['effMass_g']:>10.2f}"
              f"{r['strength_N_mu0p5']:>10.3f}{r['roll_Nm_per_N']:>9.5f}"
              f"{r['residual_Nm']:>9.4f}{r['overlap_mm']:>9.3f}")
    worst = max(r["residual_Nm"] for r in rows)
    ov = max(r["overlap_mm"] for r in rows)
    print(f"\nworst residual across the sweep {worst:.4f} Nm, deepest interpenetration {ov:.3f} mm")
    if worst > 0.15:
        print("CAUTION: this posture is not holdable on this tree. Every force column "
              "inherits an equilibrium the model cannot satisfy.")
    if ov > 0.5:
        print("CAUTION: fingers interpenetrate deeper than P28's 0.5 mm criterion.")
    if flat:
        print("CAUTION: this sweep is at the FLAT DEFAULT, a fully extended hand, which nobody\n"
              "         plays from. Curling the pressing finger more than doubles what the key\n"
              "         feels, and holding the hand firm rather than letting it give is a further\n"
              "         factor of 4.9. Quote these as figures at one posture, never as the figure.")
    print(f"written: {out}")


if __name__ == "__main__":
    main()
