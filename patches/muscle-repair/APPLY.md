# The whole muscle repair, in one folder: what it is, what it does, and how to apply it

Schumann Lab, Stanford Department of Music. Biomechanical piano model, `MUSIC-Hand-v0.15`.
Written September 10, 2026, in `biomechanical model t9`.

**This corrects an earlier copy of this document, which is in the git history.** One claim in that copy is wrong: its section 4 said the repair is a retraining change and that the best F1 on note accuracy of 0.893 is not safe. **That is true of muscle-driven training and false of the trained checkpoints, which are joint-driven.** It was carried forward from the earlier document without asking which configuration the checkpoints belong to. Section 4 below is corrected and a new section 4a states the distinction. Nothing else changed.

**Written to be read cold, by someone who has not followed the work.** Every number here was
measured on a tree built in this session, not carried forward from a document. Where a figure
matches the earlier record that is said, because a match across two independent runs is worth
more than either run alone.

---

## 1. Why this folder exists

Elizabeth Schumann answered D1 on September 10, 2026 in three words: **"apply whole repair."**

Until now the whole repair was five separate changes filed in four places, three of them supplied
on four alternative bases, and no single set of files carried all of it. Assembling it correctly
took reading five documents and choosing the right one of four folders. **This folder is the whole
repair as six model files.** Applying it is one command.

The five parts, and where each came from:

| part | what it changes | per hand | source |
|---|---|---|---|
| the added-muscle drop-in files | 5 muscle forces, 5 length ranges, 6 root motor ceilings | 11 lines | `Model changes ready to apply 2026-09-07/` |
| the three recomputed length ranges | `LU_RB4`, `RI5`, `LU_RB5` | 3 lines | `Recomputed length ranges for LU_RB4 RI5 and LU_RB5 2026-09-07/` |
| the seven recomputed length ranges | `ECRL`, `FDS3`, `RI2`, `LU_RB2`, `UI_UB3`, `UI_UB4`, `UI_UB5` | 7 lines | `Recomputed length ranges for the seven stale originals 2026-09-08/` |
| the five wrap pairings | `APL`, `FDS4`, `FDP5`, `FDS5`, `FDP3` | 10 uncommented lines | `Tendon wrapping and stale length ranges, findings 2026-09-07.md` |
| `APL` recomputed with its wrap in place | one length range | 1 line | `The seven stale original length ranges, findings 2026-09-08.md` |

Twenty one changed actuator declarations and ten uncommented lines per hand, sixty two lines across
the two hands, and nothing else. The MyoHand license header and every value not named above are
copied byte for byte.

**Nothing in the wrap part is invented.** All ten lines already existed in the shipped model,
commented out. Restoring one is uncommenting the side site in the definition file and the wrap entry
in the tendon path.

---

## 2. What "applied" means here, stated plainly because it is easy to overread

**This repair has been applied to a scratch tree and verified there. It has not been applied to the
working copy or to the Marlowe cluster, and this session could not reach either of them.** The
Workspace copy of the model is the 470 megabyte archive `Model source code from Pei Xu 2026-03-04/piano.tar.gz`,
which is left untouched.

What was done, in order:

1. `piano.tar.gz` was extracted into a directory that did not exist before, which is the
   requirement in dead end 13 of `CLAUDE.md`. On September 7, 2026 an extraction into a reused path
   silently produced a previous session's tree and the standing check passed on it.
2. The pristine tree was confirmed against the recorded counts before anything was changed: 123
   bodies, 112 joints, 50 actuators, 44 tendons and 4.588 kg for each hand alone, 157, 136, 100, 88
   and 6.377 kg for the pair. All eight figures match.
3. Both fault counts were measured on that pristine tree and both reproduce the record exactly.
4. The repair was applied by `apply_the_whole_repair_2026-09-10.py`, in this folder, which asserts
   its own line counts at every step and refuses to write rather than reporting a number it has not
   confirmed.
5. Both fault counts were measured again.

So the standing of this folder is: **built, verified, and applied nowhere that matters yet.** The
six files are ready and applying them is a file copy.

---

## 3. What it does, measured on built trees rather than projected

| condition | at zero active force | carrying passive force above 10% of declared | off the curve on McFarland's figures |
|---|---|---|---|
| as shipped | **9** | **6** | 16 |
| the whole repair | **0** | **0** | 17 |

Both fault counts reach zero. That is the outcome D1 was answered to produce, and it is the first
time it has been measured on a tree carrying all five parts at once.

The nine that reached zero active force as shipped were `FDS4`, `FDP5`, `APL`, `FPB`, `AdP`, `APB`,
`LU_RB4`, `RI5`, `LU_RB5`. The six carrying passive spring force were `AdP`, `ECRL`, `LU_RB2`,
`LU_RB5`, `RI2`, `UI_UB5`, with `LU_RB5` worst at 120.60 N of uncommanded force against a declared
47.90, which is 251.8 percent. After the repair the largest passive force anywhere in the model is
`PT` at 2.5 percent of declared, which is inside the control band set by the six muscles whose
shipped window already matched the geometry.

Every figure in this table matches the record's own measurement of the same conditions, run on a
different day on a different extraction.

**The two hands are identical to the millimeter.** Both carry 34 wrapping tendons and 10 without,
the same 10 muscles in each, and the same seven derived tendon slack lengths to three decimal
places. The left hand was measured separately rather than assumed from the right.

---

## 4. What it costs, and none of this is hidden

**Seventeen muscles instead of sixteen would leave the force-length window in reality**, on
McFarland's optimal fiber lengths. This is the price of the wrap pairings and it was measured
before the decision was taken. `FDS4` and `FDP5` join that list, `FDP3` leaves it, and `APL` stays
inside the window while its force across its range goes from a 1.22-fold variation to a 237-fold
one. Part of that deterioration is definitional: McFarland's tendon slack length belongs to
McFarland's tendon routing, and restoring a wrap makes this model's path for `FDS4` 52 mm longer
than the path McFarland's number was measured against. Part of it is not definitional, and that is
the honest argument against the wrap pairings. It was made in full in
`Tendon wrapping and stale length ranges, findings 2026-09-07.md` and Elizabeth Schumann decided
against it.

**Seven of the 44 muscles carry a physically impossible negative derived tendon slack length**,
against four in the shipped model. `AdP` at minus 104.501 mm, `OP` at minus 19.685, `RI5` at minus
17.015, `PQ` at minus 15.640, `RI2` at minus 15.550, `FPB` at minus 11.892 and `RI3` at minus 2.003.
Elizabeth Schumann ruled on September 10, 2026 that this ships and is stated in the methods section,
and that the cause is then found. **The cause is now established and it is not what anyone
assumed.** It is in
`Findings, where the impossible tendon slack length comes from 2026-09-10.md`, in the project folder.
This document does not describe the negative values as acceptable; it records that they ship and
that the cause is known.

**This is a retraining change for muscle-driven work only, and no muscle-driven training has ever
been run.** The forces move by between 0.42 and 3.68 times, so any muscle-driven controller trained
before the change would have learned against different arithmetic. **It is not a retraining change
for the joint-driven checkpoints, which is what exists.** See section 4a. A short sanity run still
comes before any muscle-driven training, long enough to confirm the patched model trains at all.

### 4a. What it does not affect, and this is the correction to the earlier copy

**The joint-driven model loads none of the six files this repair changes.** Its assembly loads a different definition file, a different actuator file and a different root file, it has 29 actuators rather than 50, and its compiled model contains zero tendons. Built before and after on the same extraction, the joint-driven assembly is identical: 123 bodies, 117 joints, 29 actuators, 0 tendons, 4.588 kg and a force ceiling sum of 560.00 in both conditions, and twice that for the two-hand assembly.

**Every trained checkpoint in this project is joint-driven.** So the best F1 on note accuracy of 0.893 with precision 0.877 and recall 0.938 at 37,600 iterations, the rise from 0.852 after the frame rounding fix, and the frame rounding finding itself are measurements on a model this repair does not alter. **They stand and no retraining is required on account of this change.**

What the repair does affect: any muscle-driven training run, of which none has been done; and any muscle activation, tendon force or effective-strength figure computed from the model, including the preliminary muscle activation plots made for the 6.5 inch configuration.

**And a separate fault this repair does not fix.** The joint-driven root has its own ceilings, in `*_hand_actuators_joint.xml`, which this repair never touches. They sit at plus or minus 50 N m on all three rotational axes, which against a measured generalized inertia of 8.01e-3 kg m squared about the forearm's long axis permits 357,644 degrees per second squared. A three-line-per-hand patch is built and verified at `AI_Model/The joint-driven root ceiling patch 2026-09-10/`, and unlike this repair it does require a retraining run, because it changes the configuration the checkpoints belong to.

---

## 5. How to apply it

Two commands. The first backs up what is there, the second copies the six files over it. Nothing in
this lab is overwritten without a dated copy surviving.

Run in Terminal, substituting the real path to the model's `assets` directory:

```
ASSETS="/path/to/the/model/assets"
SRC="/Users/ejs/Library/Mobile Documents/com~apple~CloudDocs/Workspace/Research_Projects/AI_Model/The whole muscle repair, built and verified 2026-09-10"

for s in right left; do
  for f in actuators_muscle definition definition_tendons; do
    cp -n "$ASSETS/${s}_assets/${s}_hand_${f}.xml" \
          "$ASSETS/${s}_assets/${s}_hand_${f}.xml.before_2026-09-10"
  done
done && echo "BACKED UP"
```

```
ASSETS="/path/to/the/model/assets"
SRC="/Users/ejs/Library/Mobile Documents/com~apple~CloudDocs/Workspace/Research_Projects/AI_Model/The whole muscle repair, built and verified 2026-09-10"

for s in right left; do
  for f in actuators_muscle definition definition_tendons; do
    cp "$SRC/${s}_assets/${s}_hand_${f}.xml" "$ASSETS/${s}_assets/${s}_hand_${f}.xml"
  done
done && echo "COPIED. Now run the verification in section 6."
```

`cp -n` in the first command refuses rather than overwrites, so running it twice cannot destroy a
backup already taken.

The six files and their checksums, so a copy can be confirmed to be what it is supposed to be:

```
09e797c68e9b5073f4bed7845d5d8a76  right_assets/right_hand_actuators_muscle.xml
e43838ad33bc410bd957643c86318fee  right_assets/right_hand_definition.xml
86a48418ef151e01d3ffcbdd8c3a4138  right_assets/right_hand_definition_tendons.xml
c626c05a14901d58957e0ffdbeccb085  left_assets/left_hand_actuators_muscle.xml
bbf5213f63513648a2545ddaf3d397d8  left_assets/left_hand_definition.xml
6f8e8e6d9b53dd36a552834fca32e789  left_assets/left_hand_definition_tendons.xml
```

**If the tree being patched is a fresh extraction rather than an already patched one**, the
generator route is available instead and it checks its own arithmetic:

```
python3 "/Users/ejs/Library/Mobile Documents/com~apple~CloudDocs/Workspace/Research_Projects/AI_Model/The whole muscle repair, built and verified 2026-09-10/apply_the_whole_repair_2026-09-10.py" \
    --assets "/path/to/the/model/assets"
```

It prints `APPLY FINISHED` when it has finished, and it fails loudly rather than half applying:
it refuses unless the actuator file differs from the cumulative drop-in by exactly 21 declarations,
unless each of the ten commented side sites matches exactly once, and unless `APL` is sitting at the
shipped window when the last line is rewritten.

---

## 6. How to verify it

Three checks, and the third is necessary rather than sufficient. `mujoco` must be installed, and
**version 3.12.0 is what every number in the record was measured on**, including these.

**First, that the counts and the mass are unchanged and every window reads back correctly.**

```
ASSETS="/path/to/the/model/assets"
python3 - <<'EOF'
import mujoco, os
A = os.environ["ASSETS"]
want = {"right_hand_ds6.5_muscle_driven.xml": (123, 112, 50, 44, 4.588),
        "left_hand_ds6.5_muscle_driven.xml":  (123, 112, 50, 44, 4.588),
        "two_hands_ds6.5_muscle_driven.xml":  (157, 136, 100, 88, 6.377)}
bad = 0
for f, w in want.items():
    m = mujoco.MjModel.from_xml_path(os.path.join(A, f))
    got = (m.nbody, m.njnt, m.nu, m.ntendon, round(float(m.body_mass.sum()), 3))
    bad += got != w
    print(("ok   " if got == w else "FAIL ") + f"{f}  {got}")
WANT = {"ECRL": (316.355, 349.534), "FDS3": (312.390, 391.446), "RI2": (31.519, 50.347),
        "LU_RB2": (90.345, 105.889), "UI_UB3": (86.894, 96.486), "UI_UB4": (75.273, 85.199),
        "UI_UB5": (89.529, 103.735), "LU_RB4": (71.743, 80.033), "RI5": (27.118, 44.772),
        "LU_RB5": (90.423, 108.145), "FPB": (43.570, 65.755), "AdP": (19.504, 69.106),
        "APB": (40.461, 53.989), "FDM": (50.818, 66.062), "ADM": (61.263, 72.174),
        "APL": (216.562, 242.392)}
for side, pre in (("right", "R:"), ("left", "L:")):
    m = mujoco.MjModel.from_xml_path(os.path.join(A, f"{side}_hand_ds6.5_muscle_driven.xml"))
    for name, (lo, hi) in WANT.items():
        i = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, pre + name)
        g = m.actuator_lengthrange[i] * 1000.0
        ok = abs(g[0] - lo) < 0.01 and abs(g[1] - hi) < 0.01
        bad += not ok
        if not ok:
            print(f"FAIL {side} {name} {g[0]:.3f} to {g[1]:.3f}")
print("EVERY COUNT AND ALL THIRTY TWO WINDOWS MATCH THE RECORD" if not bad
      else f"{bad} CHECK(S) WRONG")
EOF
```

It prints `EVERY COUNT AND ALL THIRTY TWO WINDOWS MATCH THE RECORD` when it has finished.

**Second, the two fault counts, which are the point of the change.** Both scripts live in
`Biomechanical piano model, findings and plan 2026-09-06/`.

```
cd "/Users/ejs/Library/Mobile Documents/com~apple~CloudDocs/Workspace/Research_Projects/AI_Model/Biomechanical piano model, findings and plan 2026-09-06"

python3 analyse_force_loss_across_excursion_2026-09-07.py --assets "/path/to/the/model/assets" | grep -A 3 "FINDING 1"
python3 passive_force_across_all_44_2026-09-08.py --tree "patched=/path/to/the/model/assets" | tail -8
echo "FAULT COUNTS FINISHED"
```

Expect **0 of 44** on finding 1 and **0 muscles** carrying passive force above 10 percent of
declared. Expect **17** on finding 2, which is one worse than shipped and is the cost recorded in
section 4.

**Third, the added-muscle generator's own verification, and the standing check.**

```
python3 "/Users/ejs/Library/Mobile Documents/com~apple~CloudDocs/Workspace/Research_Projects/AI_Model/Model changes ready to apply 2026-09-07/make_actuator_files_2026-09-07.py" \
    --assets "/path/to/the/model/assets" --verify
echo "GENERATOR CHECK FINISHED"
```

Expect `every check passed`, and **100.4 percent** on all ten muscle checks across the two hands.
That is the figure the record predicts and it is what this session measured.

```
cd "/Users/ejs/Library/Mobile Documents/com~apple~CloudDocs/Workspace/Research_Projects/AI_Model/Biomechanical piano model, findings and plan 2026-09-06"
python3 check_model_state.py --model-root "/path/to/the/model/assets" ; echo "STANDING CHECK FINISHED"
```

**Expect exactly two flags, and expect the root motor flag to be gone.** Before this change the
check throws three: the root motors still at 100, and `piano_ds5.1.xml` and `piano_ds5.5.xml`
transposed against their own names. This change clears the first. The two keyboard flags are a
separate matter and a verified thirteen keyboard series already exists at
`Biomechanical piano model, findings and plan 2026-09-06/scaled_keyboards_2026-09-06/`.

**The standing check does not inspect tendon wrapping, length ranges or where a file came from, so
passing it is not evidence that a copy is what it is supposed to be.** The checksums in section 5
are what establishes that.

---

## 7. Population, which has to appear in any methods section

Unchanged and repeated because it travels with every file in this repair. The muscle forces rest on
nine cadaver hands of unstated age and sex, from a 1992 dissection study, by way of a reconciling
model whose authors state it represents healthy young adult males. **This lab's central result
concerns small-handed pianists and reports a systematic disadvantage for women.** A model
parameterized on young adult male cadaver architecture and a study about women's hands are not the
same population, and the mismatch belongs in the methods section rather than being discovered by a
reviewer.

`RI2`'s length range is the one hand-supplied number in the whole repair. MuJoCo's length range
computation does not converge on `RI2` and refuses to build the model when the attribute is deleted,
so `RI2`'s value is a kinematic sweep rather than the compiler. Any methods section must say so.

---

## 8. What this does not establish

- **It says nothing about whether a trained policy visits the postures where the faults were
  measured.** Every fault figure takes joints to their declared limits and ignores self-collision,
  so every figure is an upper bound on the artifact rather than a statement about a run. On the
  trained joint-driven policies inside `piano.tar.gz`, 42 percent of the counted faults survive into
  performance, which was measured separately on September 8, 2026.
- **It does not fix `AdP`.** `AdP` is a geometry problem as well as a parameter one, its excursion
  is overstated because it has no wrapping surface, and no choice of any attribute repairs that.
  Building the wrapping surfaces the five added muscles have never had is a separate item.
- **It does not touch the joint-driven root ceilings.** See section 4a.
- **It does not touch `range`**, which sits at MuJoCo's default of 0.75 to 1.05 for all 44 muscles.
  Elizabeth Schumann answered D3 on September 10, 2026 with "Do it," and what that correction now
  involves changed as a result of this repair. The measurement is in
  `Findings, where the impossible tendon slack length comes from 2026-09-10.md`.
- **It does not establish what changed under `APL`.** Restoring `APL`'s wrap overshoots its shipped
  window by 11.81 mm at the short end and 14.01 at the long end, so something else changed under
  `APL` as well and what it was is still not known.

---

## 9. What is in this folder

| | |
|---|---|
| `right_assets/` and `left_assets/` | the six model files, ready to copy |
| `apply_the_whole_repair_2026-09-10.py` | rebuilds them from a fresh extraction and asserts every count |
| `measured output/zero_shipped.txt` and `zero_repaired.txt` | the zero-force count before and after, raw |
| `measured output/passive_shipped.txt` and `passive_repaired.txt` | the passive force count before and after, raw |
| `measured output/make_verify.txt` | the generator's own verification, `every check passed` at 100.4 percent |
| `measured output/check_repaired.txt` | the standing check, two flags |
| `measured output/tendon_slack_all_44.txt` | the derived tendon slack length for all 44, before and after |
| `measured output/range_feasibility_all_44_2026-09-10.txt` | which muscles admit a `range` that keeps the derived tendon non-negative |
| `measured output/wrap_census.txt` | which tendons wrap and which do not, read from the built tree |
| `measured output/peak_force_all_44.txt` | a null result, filed so nobody repeats it, and why it is not the 100.4 percent figure |

The one British spelling in this document is `analyse_force_loss_across_excursion_2026-09-07.py`,
which is a file name already on disk and is left as it is.

