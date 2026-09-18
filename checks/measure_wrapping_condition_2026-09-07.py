#!/usr/bin/env python3
"""Measure one wrapping condition: excursion, compiler lengthrange, and zero-force count.

Schumann Lab, biomechanical piano model, 7 September 2026.
Prints one machine-readable line per muscle so conditions can be diffed.
"""
import argparse, itertools, json, os, re, sys
import numpy as np, mujoco

RANGE_LO, RANGE_HI = 0.75, 1.05
LMIN, LMAX = 0.5, 1.6
PROBE = ('<mujoco model="probe">\n'
         '  <include file="defaults.xml"/>\n'
         '  <include file="right_assets/right_hand_definition_meta.xml"/>\n'
         '  <include file="right_assets/right_hand_definition_tendons.xml"/>\n'
         '  <include file="right_assets/{act}"/>\n'
         '  <worldbody><include file="right_assets/right_hand_freeroot.xml"/></worldbody>\n'
         '</mujoco>\n')


def load(assets, actfile, stem):
    p = os.path.join(assets, stem + ".xml")
    open(p, "w").write(PROBE.format(act=actfile))
    try:
        return mujoco.MjModel.from_xml_path(p)
    finally:
        os.remove(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--nrand", type=int, default=3000)
    ap.add_argument("--compiler", action="store_true",
                    help="also recompute lengthrange one muscle at a time (slow)")
    a = ap.parse_args()

    m = load(a.assets, "right_hand_actuators_muscle.xml", "_p_meas")
    d = mujoco.MjData(m)
    act2ten = {i: m.actuator_trnid[i, 0] for i in range(m.nu)
               if m.actuator_trntype[i] == mujoco.mjtTrn.mjTRN_TENDON}
    jq = [(m.jnt_qposadr[j], m.jnt_range[j, 0], m.jnt_range[j, 1]) for j in range(m.njnt)
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
    for k, (adr, lo, hi) in enumerate(jq):
        q = q0.copy(); q[adr] = lo; x, _ = state(q)
        q = q0.copy(); q[adr] = hi; y, _ = state(q)
        sens[k] = np.maximum(abs(x - base), abs(y - base))

    rng = np.random.default_rng(1)
    res = {}
    for i in range(m.nu):
        n = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
        if not n or i not in act2ten: continue
        short = n.split(":")[-1]; t = act2ten[i]
        idx = [k for k in range(len(jq)) if sens[k, t] > 1e-6]
        if not idx: continue
        lo = np.array([jq[k][1] for k in idx]); hi = np.array([jq[k][2] for k in idx])
        adrs = [jq[k][0] for k in idx]
        samples = list(itertools.product(*[(l, h) for l, h in zip(lo, hi)])) if len(idx) <= 12 else []
        samples += [tuple(rng.uniform(lo, hi)) for _ in range(a.nrand)]
        tmin, tmax, fmin, fmax = np.inf, -np.inf, np.inf, -np.inf
        for combo in samples:
            q = q0.copy()
            for adr, v in zip(adrs, combo): q[adr] = v
            L, F = state(q)
            f = abs(F[i])
            tmin = min(tmin, L[t]); tmax = max(tmax, L[t])
            fmin = min(fmin, f); fmax = max(fmax, f)
        lr = m.actuator_lengthrange[i]
        peak = float(m.actuator_gainprm[i, 2])
        res[short] = dict(lr=[float(lr[0]*1000), float(lr[1]*1000)],
                          sweep=[float(tmin*1000), float(tmax*1000)],
                          nl=[float(RANGE_LO+(RANGE_HI-RANGE_LO)*(tmin-lr[0])/(lr[1]-lr[0])),
                              float(RANGE_LO+(RANGE_HI-RANGE_LO)*(tmax-lr[0])/(lr[1]-lr[0]))],
                          f=[float(fmin), float(fmax)], peak=peak,
                          zero=bool(fmin <= 0.01*peak))

    if a.compiler:
        apath = os.path.join(a.assets, "right_assets/right_hand_actuators_muscle.xml")
        src = open(apath).read()
        names = [x.split(":")[-1] for x in re.findall(r'<muscle name="([^"]+)"', src)]
        for k, short in enumerate(names):
            if short not in res: continue
            lines = src.splitlines(keepends=True); out = []; seen = 0
            for ln in lines:
                if "<muscle name=" in ln:
                    if seen == k: ln = re.sub(r'\s+lengthrange="[^"]*"', "", ln)
                    seen += 1
                out.append(ln)
            tmp = "right_hand_actuators_muscle_ONE.xml"
            tp = os.path.join(a.assets, "right_assets", tmp)
            open(tp, "w").write("".join(out))
            try:
                mm = load(a.assets, tmp, "_p_one")
                res[short]["comp"] = [float(mm.actuator_lengthrange[k][0]*1000),
                                      float(mm.actuator_lengthrange[k][1]*1000)]
            except Exception as e:
                res[short]["comp"] = None
                res[short]["comp_err"] = str(e).strip().splitlines()[0]
            finally:
                os.remove(tp)

    zero = sorted([k for k, v in res.items() if v["zero"]])
    print(json.dumps({"label": a.label, "nmuscle": len(res), "zero": zero, "muscles": res}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
