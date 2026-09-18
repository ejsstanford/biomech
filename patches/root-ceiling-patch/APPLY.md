# The joint-driven root ceiling patch: three lines per hand

Schumann Lab, Stanford Department of Music. Biomechanical piano model, `MUSIC-Hand-v0.15`.

**Written to be read cold.** Every number was measured on a built model rather than taken from a
document.

---

## 1. What this is, and why it is separate from the muscle repair

The forearm root of this model is six degrees of freedom named in the files for an elbow but
functioning as a floating base. **That naming is why ten months of looking for an elbow bug found
nothing: the question was never a question about an elbow.**

The record already establishes that the **muscle-driven** configuration shipped those six at plus or
minus 100 N and 100 N m, and that 100 N m about the forearm's long axis permits about 806,000 degrees
per second squared. The whole muscle repair brings that to 78 N and 12, 8, 12 N m.

**The joint-driven configuration has its own root, its own actuators and its own ceilings, and
nobody had looked at them.** They live in `right_hand_actuators_joint.xml` and its left-hand
counterpart, which the muscle repair never touches, because the joint-driven assembly loads a
different actuator file, a different definition file and a different root file. **So applying the
muscle repair leaves this fault exactly where it was.**

---

## 2. What was measured

Right hand, at the default posture, each figure from that configuration's own mass matrix.
MuJoCo 3.12.0.

| | ceiling about the forearm long axis | generalized inertia | permits |
|---|---|---|---|
| muscle-driven, as shipped | 100 N m | 7.11017e-3 kg m squared | 805,828 deg/s squared |
| muscle-driven, after the whole muscle repair | 8 N m | 7.11017e-3 | 64,466 deg/s squared |
| **joint-driven, as shipped** | **50 N m** | 8.01017e-3 kg m squared | **357,644 deg/s squared** |
| **joint-driven, with this patch** | **8 N m** | 8.01017e-3 | **57,223 deg/s squared** |

The same defect, at 44 percent of the magnitude, brought down by a factor of 6.25.

The other two rotational axes, on the same measurement: `elbow_rx` from 42,078 to 10,099 degrees per
second squared, and `elbow_rz` from 43,131 to 10,351.

**For scale.** Adult pronation and supination is of the order of 5 to 10 N m, and wrist flexion,
extension and deviation of the order of 10 to 15. A clamp of 50 N m is between four and ten times
any torque a forearm can produce.

---

## 3. What it changes, exactly

**Three lines per hand, six across the two files, and nothing else.** The three rotational position
servos:

| actuator | shipped | here |
|---|---|---|
| `elbow_rx` | forcerange -50 50 | **-12 12** |
| `elbow_ry`, the forearm long axis | forcerange -50 50 | **-8 8** |
| `elbow_rz` | forcerange -50 50 | **-12 12** |

The values match the three the muscle-driven root was given for the same three axes, on the same
reasoning.

**The three translational servos are left alone at plus or minus 50 N, deliberately.** Against a
generalized inertia of 1.789 kg that permits 28 meters per second squared, about 2.9 g, which is not
the fault.

**One thing flagged rather than changed.** The muscle-driven root was given 78 N on the reasoning of
hand weight plus the loudest measured key force of about 60 N, and the joint-driven translational
clamp of 50 N sits below that. **Whether the joint-driven side should also read 78 is a question
rather than a repair**, and raising a ceiling is not a fault fix, so it is left for someone to
decide rather than settled here.

The two files and their checksums:

```
aca533b051f9c8f10c938af60649650e  right_assets/right_hand_actuators_joint.xml
6dd0d7423e5cca937e2ab29ce4d33f1d  left_assets/left_hand_actuators_joint.xml
```

---

## 4. What it costs, and it is the reason this is a decision

**This changes the joint-driven model, which is the configuration every trained checkpoint in the
project belongs to.** A policy trained against the shipped clamps has learned to use a root it
could accelerate at 357,644 degrees per second squared. **So applying this requires a retraining
run**, unlike the muscle repair, which leaves the joint-driven model untouched and costs nothing.

**What to watch in that run, and the second thing is the more interesting result.** Whether note
accuracy holds against the established best F1 of 0.893, and whether the unrealistic elbow motion
changes. **If the motion is unchanged, then the root ceiling is not the account of it**, and a
mechanical explanation that has stood for months is wrong.

**Do not try to fix this with a reward term instead.** The root is driven directly by these
actuators, and the only naturalness term in training is an adversarial discriminator whose reference
motions are hand reconstructions, so it almost certainly never observes the root. That is a recorded
dead end. Nor should `right_hand_6d_root.xml` be swapped for the free-joint root as a first move: it
changes the degree-of-freedom count, which invalidates the motion library and every pretrained
checkpoint. That is the other recorded dead end.

---

## 5. How to apply it

Two commands. Run in Terminal, substituting the real path to the model's `assets` directory.

```
ASSETS="/path/to/the/model/assets"

for s in right left; do
  cp -n "$ASSETS/${s}_assets/${s}_hand_actuators_joint.xml" \
        "$ASSETS/${s}_assets/${s}_hand_actuators_joint.xml.before_the_root_ceiling_patch"
done && echo "BACKED UP"
```

```
ASSETS="/path/to/the/model/assets"
SRC="/Users/ejs/Library/Mobile Documents/com~apple~CloudDocs/Workspace/Research_Projects/AI_Model/The joint-driven root ceiling patch 2026-09-10"

for s in right left; do
  cp "$SRC/${s}_assets/${s}_hand_actuators_joint.xml" \
     "$ASSETS/${s}_assets/${s}_hand_actuators_joint.xml"
done && echo "COPIED. Now run the verification in section 6."
```

The generator route is available instead, and it asserts its own line count and refuses to write
rather than half applying:

```
python3 "/Users/ejs/Library/Mobile Documents/com~apple~CloudDocs/Workspace/Research_Projects/AI_Model/The joint-driven root ceiling patch 2026-09-10/make_joint_driven_root_ceiling_patch.py" \
    --assets "/path/to/the/model/assets"
```

It prints `PATCH FINISHED` when it has finished.

---

## 6. How to verify it

```
ASSETS="/path/to/the/model/assets"
python3 - <<'EOF'
import mujoco, numpy as np, os, math
A = os.environ["ASSETS"]
WANT = {"elbow_rx": 12.0, "elbow_ry": 8.0, "elbow_rz": 12.0}
bad = 0
for f in ("right_hand_ds6.5_joint_driven.xml", "two_hands_ds6.5_joint_driven.xml"):
    m = mujoco.MjModel.from_xml_path(os.path.join(A, f))
    d = mujoco.MjData(m); mujoco.mj_forward(m, d)
    M = np.zeros((m.nv, m.nv), dtype=np.float64, order="C"); mujoco.mj_fullM(m, d, M)
    print(f"{f}  bodies {m.nbody}  actuators {m.nu}  tendons {m.ntendon}")
    for i in range(m.nu):
        nm = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, i) or ""
        key = nm.split(":")[-1]
        if key not in WANT:
            continue
        got = float(m.actuator_forcerange[i][1])
        adr = m.jnt_dofadr[int(m.actuator_trnid[i][0])]
        acc = math.degrees(got / float(M[adr, adr]))
        ok = abs(got - WANT[key]) < 1e-9
        bad += not ok
        print(("  ok   " if ok else "  FAIL ")
              + f"{nm:12s} {got:5.1f} N m  permits {acc:>10,.0f} deg/s^2")
print("ALL SIX ROTATIONAL CLAMPS ARE AT THE PATCHED VALUES" if not bad
      else f"{bad} CLAMP(S) WRONG")
EOF
```

It prints `ALL SIX ROTATIONAL CLAMPS ARE AT THE PATCHED VALUES` when it has finished, and the
permitted accelerations should read 10,099, 57,223 and 10,351 degrees per second squared for `rx`,
`ry` and `rz`.

The standing check does not inspect these ceilings, so passing it is not evidence this patch was
applied. The checksums in section 3 and the command above are what establishes that.

---

## 7. What this does not establish

- **Which configuration the unrealistic elbow motion was observed in.** The record attributes it to
  the muscle-driven root at plus or minus 100 N m. If the run that was watched was joint-driven, that
  account names the wrong file and the wrong number. One question to whoever ran it settles this.
- **Whether the finger joint ceilings are also out of scale.** The joint-driven model gives every
  finger joint plus or minus 10 N m and the wrist plus or minus 20, where adult single-finger joint
  torque is of the order of 1 to 3 N m. **But a joint-driven model is a torque-driven abstraction
  rather than an anatomical claim**, and whether a generous ceiling there does any harm depends on
  whether the policy uses it, which was not measured.
- **The two-hand root inertia.** Only the right hand's was measured. The two-hand assembly's actuator
  count and force ceiling sum are exactly twice the single hand's, so the same clamps are present on
  both sides, but its inertia was not measured separately.
- **Whether the patched model trains at all.** Nothing has been trained against it.
