# biomech

Corrections and patches for the piano hand model `MUSIC-Hand-v0.15`, built on MyoHand by Pei Xu, Yufei Ye and Ruocheng Wang. Every artifact here replaces a file in the shipped model rather than adding geometry. **Applied and verified on a fresh unpacking of `piano.tar.gz`, three times independently, on September 28, 2026. Not yet applied to a working copy or to a cluster.**

**Who built this, and how much weight it carries.** Built by Elizabeth Schumann working with Claude between September 6 and September 12, 2026. None of it has been reviewed by anyone who works on this model, and that review is what we are asking for. Where a choice was made, the reasoning is written out so it can be disagreed with rather than accepted. Every number below was measured by building the model and reading it, not by inspecting the files.

```
patches/     the five drop-in corrections
checks/      the standing check, and the script behind each number claimed below
```

**Naming, and the one exception.** Directories and documents use plain repo names, and git carries supersession rather than a date in a filename. **Filenames that a script writes or reads are untouched**, because the apply and build scripts construct them by name: every `*_hand_*.xml`, the keyboard files whose names carry their own measured octave span, and the provenance tables that `build_range_correction` regenerates. Renaming those would break reproduction, so they keep the names the tooling expects.

---

## The patches

| | Path | Trust | Cost to apply |
|---|---|---|---|
| 1 | **`patches/step1/`** | High | None. **This is the muscle work to apply. Six files** |
| | `patches/muscle-repair/` | High | **A component of step1.** Usable alone, deliberately. Never on top of step1 |
| | `patches/range-correction/` | High | **A component of step1.** Never on top of step1 |
| 2 | `patches/root-ceiling-patch/` | High | One retraining run |
| 3 | `patches/calibrated-key/` | Medium, never run | Belongs with gravity |
| 4 | `patches/keyboard-series/` | High | None |

**Why step1 is six files and not nine.** The range correction's actuator file already carries every
actuator change the muscle repair made, recomputed on the wrapped geometry: of the 22 actuators the
repair alters against pristine, **zero are left unchanged by the range correction.** So the set is
the correction's two actuator files and the repair's four definition files, and `patches/step1/`
holds exactly those.

**What goes wrong if you apply both components.** Whichever lands second wins. Apply the repair
second and its actuator files overwrite the correction's, **every corrected `range` value reverts,
and the copy looks changed because the definition files are still there.** The standing check passes
on it.

**So do not rely on reading this.** Run

```
python3 checks/which_version_is_this.py <your copy>/assets
```

It reads the six files and names which of four versions the copy is: unchanged, repair only, step1,
or the mixed copy above, which it refuses. It needs nothing but the standard library and it takes no
measurable time.

### 1. `patches/muscle-repair/` — six files, three per hand

Corrected forces and `lengthrange` values for the affected muscles, `APL` recomputed at 216.562 to 242.392 mm, and the five commented-out wrap pairings uncommented. Measured by building the model: muscles reaching zero active force 9 to 0, muscles carrying passive force above a tenth of declared peak 6 to 0. It costs one muscle on a third count, agreement with McFarland's force-length figures, which goes 16 to 17.

Nothing in the wrap part is invented: all ten lines already existed in the shipped model, commented out. Both hands are identical to the millimeter, measured separately. Six checksums, verified three times independently, are in `APPLY.md` with the copy and verification commands. `evidence/` holds the measured output behind each figure.

**No retraining is owed.** This touches none of the three files the joint-driven assembly loads, so every existing checkpoint stands.

### 2. `patches/range-correction/` — per-muscle `range`, all 44

Replaces MuJoCo's default `range` of 0.75 to 1.05 so muscles lose strength as they stretch. Ships with a provenance table generated from the built model giving each muscle's target, source, grade and the reason for any fallback.

**The criterion.** Widening the windows puts passive tension back: 41 of 44 muscles carry passive force above a tenth of peak somewhere in their travel, 1 of 44 at the median reachable posture, 17 of 44 at the model's default posture, which is a flat fully extended hand. The tension sits at the ends of reach and at full extension rather than where the hand works, so the criterion is read at the median reachable posture with a named exception for the flexors and interossei at full extension. The reasoning, the proposed external check against Wagner 1988, and the two places we are unsure, are in `patches/range-correction/CRITERION.md`.

`AdP` is the one muscle admitting no window that is both physically possible and inside the usable support. The physically possible side was taken, and the cost is that at its most contracted reachable posture it produces under a tenth of its peak force.

**What this correction costs, measured September 28, 2026 and not hidden.** The corrected model
**cannot hold its own default posture.** With every muscle activation free, 15 of 23 muscle-actuated
hand degrees of freedom carry torque no activation balances, totalling **6.59 Nm** against the
shipped model's 0.0032. They are all finger flexors: `mcp3_flexion` at -1.84 Nm, `pm3_flexion` at
-0.93, `mcp2_flexion` at -0.82, `mcp4_flexion` at -0.51, `mcp4_abduction` at -0.42. **Do not measure
anything at the default posture on a corrected copy**, and expect
`checks/check_hand_can_hold_itself_2026-09-28.py` to report FAIL at 6.5921 Nm, which is the correct
result rather than a sign of a bad apply.

**Why the correction is worth having anyway, and this is the case for it.** Passive torque opposing
the hand opening: the shipped model and the muscle repair alone both give 0.0000 Nm at a fifth and
0.0079 Nm at an octave, which says a relaxed hand holds an octave open for nothing. The corrected
model gives 0.0730 and **0.2412 Nm**, and 0.2412 is within four percent of the **0.25 Nm probe
Wagner applied to 238 pianists**. **It is the only version with that behaviour at all.** Its fault is
the onset rather than the size: it resists at a fifth, where there should be nothing. **The thumb
abduction window is calibrated and correct; the finger flexor windows are what fail, and rebuilding
them is the next piece of work.**

### 3. `patches/root-ceiling-patch/` — three lines per hand

Beneath the ulna sit six degrees of freedom named in the files for the elbow and functioning as an unrestricted floating base. In the joint-driven configuration they are position servos clamped at plus or minus 50 N m, against a measured generalized inertia of 8.01e-3 kg m squared about the forearm's long axis, permitting 357,644 degrees per second squared. This patch gives the three rotational clamps the muscle-driven root's own values of 12, 8 and 12 N m, bringing that to 57,223.

**This one costs a retraining run,** because a policy trained against the shipped ceilings has learned to use a root it could accelerate at 357,644 degrees per second squared. Two things to report from that run: whether F1 holds against 0.893, and whether the unrealistic elbow motion changes. If the motion is unchanged, the root ceiling is not the account of it.

Two recorded dead ends: a reward term will not fix this, because the root is driven directly by these actuators and the only naturalness term in training is a discriminator whose reference motions are hand reconstructions; and swapping in the alternative six degree of freedom root file changes the degree of freedom count, which invalidates the motion library and every pretrained checkpoint.

### 4. `patches/calibrated-key/` — one file

The shipped key has a down-weight of 2.8 grams-force against about 48 on a grand, an up-weight of 85.8 against about 22, and no Coulomb friction at all, which is why those two numbers do not sit together. This sets down-weight, up-weight and friction against published measurements of a grand action.

**Never run.** The figures come from published measurements rather than from this instrument. **One trap:** MuJoCo's joint friction does nothing unless `noslip_iterations` is set, and it fails silently rather than with an error. This belongs in the same pass as gravity, since up-weight and down-weight mean nothing in a weightless model.

### 5. `patches/keyboard-series/` — thirteen keyboards

5.50 to 6.70 inches per octave in 0.10 inch steps, generated by a script that measures what it writes, with the measured octave span in each filename.

These replace two shipped files whose contents are swapped: `piano_ds5.1.xml` measures an octave span of 139.94 mm and `piano_ds5.5.xml` measures 129.77.

---

## `checks/` — how to disbelieve any number above

`check_model_state.py` is the standing check: it compares a copy against recorded settled values and fails with its reasoning rather than a number. It does not inspect tendon wrapping, length ranges or where a file came from, so passing it is not evidence that a copy is what it should be. The checksums establish that.

**Three checks added September 28, 2026.**

| script | what it answers | on a correct step1 copy |
|---|---|---|
| `which_version_is_this.py` | which of the four versions this copy is | names it, and refuses the mixed copy |
| `check_passive_at_median_2026-09-28.py` | the passive force criterion in force | **PASS**, 41 / 1 / 17, both hands |
| `check_hand_can_hold_itself_2026-09-28.py` | can any activation hold the posture | **FAIL at 6.5921 Nm**, which is expected |

`check_passive_at_median` imports `passive_where_it_actually_sits_2026-09-12.py` rather than
reimplementing the sampler, and needs `--measurer` pointed at it. **There is one sampler on
purpose:** the first version of that check reimplemented it and reported 7 at the median against the
established 1, and the disagreement was caught only by running both on one copy.

**`patches/range-correction/check_range_correction_2026-09-12.py` has been deleted.** It counted
passive force over each muscle's whole travel and **returned REFUSED on a correctly applied copy**,
because it tested a criterion retired on September 18, 2026, six days after it was written. Anyone
who cloned this repository before today has a copy: **do not run it.** Git carries it if the
reasoning is ever wanted, and `patches/range-correction/Measured output, the refusing check
2026-09-12.txt` stays as the record of what it said.

**The sampler is at `patches/range-correction/passive_where_it_actually_sits_2026-09-12.py`**, which
is where `check_passive_at_median` expects to be pointed with `--measurer`.

Each remaining script produces one claim made above or in the write-up.

| Claim | Script |
|---|---|
| Muscles reaching zero active force, 9 as shipped | `diagnose_zero_force_2026-09-07.py` |
| Six muscles carrying uncommanded passive force, worst `LU_RB5` at 251.8 percent of declared | `passive_force_across_all_44_2026-09-08.py` |
| Derived tendon slack goes negative when the span exceeds 40 percent of where the window begins | `implied_tendon_slack_across_all_44_2026-09-07.py` |
| Shipped forces out by 0.42 to 3.68 times against nine cadaver hands | `test_jacobson_forces_2026-09-07.py` |
| Five of six reconcile to within a tenth of a percent against McFarland | `test_mcfarland_forces_2026-09-07.py` |
| Ten tendons with no wrapping surface, five pairings commented out | `audit_commented_out_wrapping_2026-09-07.py`, `measure_wrapping_condition_2026-09-07.py` |
| The `FDS4` confirmation, a 52 mm correction landing within one percent of the shipped window | `test_wrapping_offset_is_constant_2026-09-07.py` |
| `LU_RB` is a lumped unit rather than a lumbrical | `what_LU_RB_represents_2026-09-08.py` |
| Abductor pollicis brevis swings 2.68-fold across the abduction range | `analyse_force_loss_across_excursion_2026-09-07.py` |
| Key down-weight, up-weight and friction against a grand action | `test_key_physics_2026-09-06_run2.py` |
| The thirteen keyboards, measured as written | `make_scaled_keyboards_2026-09-06.py` |
| Generalized inertia about the forearm's long axis | `root_decomposition_2026-09-09.py` |

---

## What is deliberately not here

**Nothing with a participant in it.** The lab folder these came from also holds signed consent forms, IRB materials and 52 MIDI recordings of named performers. None of that belongs in a repository, and none of it is here.

**Not the collaborators' source.** `piano.tar.gz` is 470 MB and is theirs to distribute.

**Not the working record.** The project's state files and findings documents are a working memory containing claims that have since been withdrawn. The write-ups that accompany this repository are edited separately and will be added when they are settled.

---

## Literature these were checked against

Jacobson, Raab, Fazeli, Abrams, Botte and Lieber (1992), *Architectural design of the human intrinsic hand muscles*. The McFarland ARMS hand and wrist model, OpenSim, from SimTK. Mirakhorlo and colleagues (2016). Hirschkorn's instrumented grand action measurements, and Steinway regulation figures. Furuya, Altenmüller, Katayose and Kinoshita (2010).

If any of these has been superseded, that is a correction we would rather have than not.
