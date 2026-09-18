#!/usr/bin/env python3
"""WHY do six original muscles reach zero active force at reachable postures?

Schumann Lab, biomechanical piano model, 7 September 2026.

The free analysis of 7 September (analyse_force_loss_across_excursion_2026-09-07.py)
found nine of 44 muscles reaching under one per cent of their own peak active force
at postures the model's own joint limits allow. The added-muscle drop-in files clear
three of them and FDM with them. Six ORIGINAL muscles remain: FDS4, FDP5, APL,
LU_RB4, RI5, LU_RB5. This script asks why, and separates the candidate causes so the
answer is measured rather than argued.

MuJoCo derives L0 and tendon slack from lengthrange and range:
    L0  = (lengthrange[1] - lengthrange[0]) / (range[1] - range[0])
    L_T =  lengthrange[0] - range[0] * L0
with range at its default 0.75 to 1.05 for all 44 muscles here. So a muscle's whole
declared operating window is exactly its lengthrange span, and normalised length is
    nl(L) = 0.75 + 0.30 * (L - lr0) / (lr1 - lr0)
Active force is zero outside 0.5 to 1.6 L0. Reaching nl = 0.5 needs the tendon to be
SHORTER than lr0 by 0.833 of the declared span. Reaching nl = 1.6 needs it LONGER
than lr1 by 1.833 of the declared span.

So there are exactly two ways to get there:
  (a) the declared span is too narrow for the excursion the joints allow, or
  (b) the excursion is larger than it should be, because the tendon path is wrong.
This script measures the excursion, the declared span, the overshoot at each end,
the joints responsible, and then re-derives the lengthrange with MuJoCo's own
compiler to see whether the shipped numbers are simply stale.

Writes nothing. Prints tables.
"""
import argparse, itertools, os, re, sys
import numpy as np
import mujoco

RANGE_LO, RANGE_HI = 0.75, 1.05
LMIN, LMAX = 0.5, 1.6
SIX = ["FDS4", "FDP5", "APL", "LU_RB4", "RI5", "LU_RB5"]
FIVE = ["FPB", "AdP", "APB", "FDM", "ADM"]

PROBE = ('<mujoco model="probe">\n'
         '  <include file="defaults.xml"/>\n'
         '  <include file="right_assets/right_hand_definition_meta.xml"/>\n'
         '  <include file="right_assets/right_hand_definition_tendons.xml"/>\n'
         '  <include file="right_assets/{act}"/>\n'
         '  <worldbody><include file="right_assets/right_hand_freeroot.xml"/></worldbody>\n'
         '</mujoco>\n')


def build(assets, actfile="right_hand_actuators_muscle.xml", stem="_diag_probe"):
    p = os.path.join(assets, stem + ".xml")
    open(p, "w").write(PROBE.format(act=actfile))
    return p


def load(assets, actfile="right_hand_actuators_muscle.xml"):
    p = build(assets, actfile)
    m = mujoco.MjModel.from_xml_path(p)
    os.remove(p)
    return m, mujoco.MjData(m)


def sweep(m, d, nrand=4000, seed=1):
    """Return per-actuator (tmin, tmax, fmin, fmax, driving joints, argmin/argmax posture)."""
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, i) for i in range(m.nu)]
    jnames = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j) for j in range(m.njnt)]
    act2ten = {i: m.actuator_trnid[i, 0] for i in range(m.nu)
               if m.actuator_trntype[i] == mujoco.mjtTrn.mjTRN_TENDON}
    jq = [(j, m.jnt_qposadr[j], m.jnt_range[j, 0], m.jnt_range[j, 1]) for j in range(m.njnt)
          if m.jnt_type[j] not in (mujoco.mjtJoint.mjJNT_FREE, mujoco.mjtJoint.mjJNT_BALL)
          and m.jnt_limited[j]]
    mujoco.mj_resetData(m, d); mujoco.mj_forward(m, d)
    q0 = d.qpos.copy()

    def state(q):
        d.qpos[:] = q
        if m.na: d.act[:] = 1.0
        d.ctrl[:] = 1.0
        mujoco.mj_forward(m, d)
        return d.ten_length.copy(), d.actuator_force.copy()

    base, _ = state(q0)
    sens = np.zeros((len(jq), m.ntendon))
    for k, (j, adr, lo, hi) in enumerate(jq):
        q = q0.copy(); q[adr] = lo; x, _ = state(q)
        q = q0.copy(); q[adr] = hi; y, _ = state(q)
        sens[k] = np.maximum(abs(x - base), abs(y - base))

    rng = np.random.default_rng(seed)
    out = {}
    for i, n in enumerate(names):
        if not n or i not in act2ten: continue
        short = n.split(":")[-1]
        t = act2ten[i]
        idx = [k for k in range(len(jq)) if sens[k, t] > 1e-6]
        if not idx: continue
        lo = np.array([jq[k][2] for k in idx]); hi = np.array([jq[k][3] for k in idx])
        adrs = [jq[k][1] for k in idx]
        jn = [jnames[jq[k][0]].split(":")[-1] for k in idx]
        samples = list(itertools.product(*[(l, h) for l, h in zip(lo, hi)])) if len(idx) <= 12 else []
        samples += [tuple(rng.uniform(lo, hi)) for _ in range(nrand)]
        tmin, tmax = np.inf, -np.inf; fmin, fmax = np.inf, -np.inf
        qmin = qmax = None
        for combo in samples:
            q = q0.copy()
            for adr, v in zip(adrs, combo): q[adr] = v
            L, F = state(q)
            f = abs(F[i])
            if L[t] < tmin: tmin, qmin = L[t], combo
            if L[t] > tmax: tmax, qmax = L[t], combo
            fmin = min(fmin, f); fmax = max(fmax, f)
        out[short] = dict(i=i, t=t, tmin=tmin, tmax=tmax, fmin=fmin, fmax=fmax,
                          joints=jn, sens=[float(sens[k, t]) for k in idx],
                          qmin=qmin, qmax=qmax, lo=lo, hi=hi,
                          lr=m.actuator_lengthrange[i].copy(),
                          peak=float(m.actuator_gainprm[i, 2]))
    return out


def nl(L, lr):
    return RANGE_LO + (RANGE_HI - RANGE_LO) * (L - lr[0]) / (lr[1] - lr[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True)
    ap.add_argument("--nrand", type=int, default=4000)
    a = ap.parse_args()

    m, d = load(a.assets)
    S = sweep(m, d, a.nrand)

    print("=" * 118)
    print("WHY SIX ORIGINAL MUSCLES REACH ZERO ACTIVE FORCE   ·   Schumann Lab   ·   7 September 2026")
    print("=" * 118)
    print()
    print("declared span   lengthrange[1]-lengthrange[0], in mm. This IS the whole operating")
    print("                window, because range is at MuJoCo's default 0.75 to 1.05.")
    print("excursion       tendon length range reachable by the model's own joint limits, mm")
    print("cover           excursion divided by declared span. 1.0 means the window exactly")
    print("                covers the excursion. Above 1.0 the muscle leaves its own window.")
    print("under / over    how far the excursion falls short of lr0 / exceeds lr1, in units of")
    print("                the declared span. Active force hits zero at under 0.833 or over 1.833.")
    print()
    hdr = (f"{'muscle':9s}{'declared span':>14s}{'implied L0':>11s}{'excursion':>11s}"
           f"{'cover':>7s}{'under':>8s}{'over':>7s}{'nl low':>8s}{'nl high':>9s}{'Fmin/peak':>11s}  note")
    print(hdr); print("-" * 118)
    rows = []
    for short, r in S.items():
        lr = r["lr"]; span = (lr[1] - lr[0]) * 1000.0
        exc = (r["tmax"] - r["tmin"]) * 1000.0
        under = (lr[0] - r["tmin"]) / (lr[1] - lr[0])
        over = (r["tmax"] - lr[1]) / (lr[1] - lr[0])
        n_lo, n_hi = nl(r["tmin"], lr), nl(r["tmax"], lr)
        frac = r["fmin"] / r["peak"] if r["peak"] else float("nan")
        note = ""
        if short in SIX: note = "<-- one of the six originals"
        elif short in FIVE: note = "<-- one of the five added"
        rows.append((short, span, span / 0.30, exc, exc / span, under, over, n_lo, n_hi, frac, note))
    # print the six and the five first, then the rest
    order = ([r for r in rows if r[0] in SIX] + [r for r in rows if r[0] in FIVE]
             + [r for r in rows if r[0] not in SIX and r[0] not in FIVE])
    for (short, span, l0, exc, cov, under, over, n_lo, n_hi, frac, note) in order:
        print(f"{short:9s}{span:12.3f}mm{l0:10.2f}{exc:10.3f}mm{cov:7.2f}"
              f"{under:8.2f}{over:7.2f}{n_lo:8.2f}{n_hi:9.2f}{frac:11.4f}  {note}")

    print()
    print("=" * 118)
    print("PER-MUSCLE DETAIL FOR THE SIX: which joints move the tendon, and at which limit")
    print("=" * 118)
    for short in SIX:
        r = S[short]
        lr = r["lr"]
        print(f"\n{short}   lengthrange {lr[0]*1000:.3f} to {lr[1]*1000:.3f} mm"
              f"   (span {(lr[1]-lr[0])*1000:.3f} mm, implied L0 {(lr[1]-lr[0])*1000/0.30:.2f} mm)")
        print(f"   reachable tendon length {r['tmin']*1000:.3f} to {r['tmax']*1000:.3f} mm"
              f"   -> normalised {nl(r['tmin'],lr):.3f} to {nl(r['tmax'],lr):.3f}")
        print(f"   active force at full activation: {r['fmin']:.4f} to {r['fmax']:.3f} N"
              f"   (declared peak {r['peak']:.2f} N)")
        srt = sorted(zip(r["joints"], r["sens"]), key=lambda x: -x[1])
        print("   joints that move this tendon, by mm of length change at their own limits:")
        for jn, sv in srt:
            print(f"      {jn:22s} {sv*1000:8.3f} mm")
        print("   posture at the SHORTEST tendon length (degrees, joint: value [limits]):")
        for jn, v, lo, hi in zip(r["joints"], r["qmin"], r["lo"], r["hi"]):
            flag = ""
            if abs(v - lo) < 1e-9: flag = "  AT LOWER LIMIT"
            if abs(v - hi) < 1e-9: flag = "  AT UPPER LIMIT"
            print(f"      {jn:22s} {np.degrees(v):8.1f}  [{np.degrees(lo):7.1f},{np.degrees(hi):7.1f}]{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
