# biomech

Corrections and patches for the piano hand model `MUSIC-Hand-v0.15`, built on MyoHand by Pei Xu, Yufei Ye and Ruocheng Wang. Every artifact here replaces a file in the shipped model rather than adding geometry. **None has been applied to a working copy or to a cluster.**

**Who built this, and how much weight it carries.** Built by Elizabeth Schumann working with Claude between September 6 and September 12, 2026. None of it has been reviewed by anyone who works on this model, and that review is what we are asking for. Where a choice was made, the reasoning is written out so it can be disagreed with rather than accepted. Every number below was measured by building the model and reading it, not by inspecting the files.

```
patches/     the five drop-in corrections
checks/      the standing check, and the script behind each number claimed below
```

**Naming, and the one exception.** Directories and documents use plain repo names, and git carries supersession rather than a date in a filename. **Filenames that a script writes or reads are untouched**, because the apply and build scripts construct them by name: every `*_hand_*.xml`, the keyboard files whose names carry their own measured octave span, and the provenance tables that `build_range_correction` regenerates. Renaming those would break reproduction, so they keep the names the tooling expects.

---

## The five patches

| | Path | Trust | Cost to apply |
|---|---|---|---|
| 1 | `patches/muscle-repair/` | High | None |
| 2 | `patches/range-correction/` | High | None |
| 3 | `patches/root-ceiling-patch/` | High | One retraining run |
| 4 | `patches/calibrated-key/` | Medium, never run | Belongs with gravity |
| 5 | `patches/keyboard-series/` | High | None |

### 1. `patches/muscle-repair/` — six files, three per hand

Corrected forces and `lengthrange` values for the affected muscles, `APL` recomputed at 216.562 to 242.392 mm, and the five commented-out wrap pairings uncommented. Measured by building the model: muscles reaching zero active force 9 to 0, muscles carrying passive force above a tenth of declared peak 6 to 0. It costs one muscle on a third count, agreement with McFarland's force-length figures, which goes 16 to 17.

Nothing in the wrap part is invented: all ten lines already existed in the shipped model, commented out. Both hands are identical to the millimeter, measured separately. Six checksums, verified three times independently, are in `APPLY.md` with the copy and verification commands. `evidence/` holds the measured output behind each figure.

**No retraining is owed.** This touches none of the three files the joint-driven assembly loads, so every existing checkpoint stands.

### 2. `patches/range-correction/` — per-muscle `range`, all 44

Replaces MuJoCo's default `range` of 0.75 to 1.05 so muscles lose strength as they stretch. Ships with a provenance table generated from the built model giving each muscle's target, source, grade and the reason for any fallback, and a check that refuses rather than warns.

**The criterion.** Widening the windows puts passive tension back: 38 of 44 muscles carry passive force above a tenth of peak somewhere in their travel, 2 of 44 at the median reachable posture, 17 of 44 at the model's default posture, which is a flat fully extended hand. The tension sits at the ends of reach and at full extension rather than where the hand works, so the criterion is read at the median reachable posture with a named exception for the flexors and interossei at full extension. The reasoning, the proposed external check against Wagner 1988, and the two places we are unsure, are in `patches/range-correction/CRITERION.md`.

`AdP` is the one muscle admitting no window that is both physically possible and inside the usable support. The physically possible side was taken, and the cost is that at its most contracted reachable posture it produces under a tenth of its peak force.

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

`check_model_state.py` is the standing check: it compares a tree against recorded settled values and fails with its reasoning rather than a number. It does not inspect tendon wrapping, length ranges or where a file came from, so passing it is not evidence that a copy is what it should be. The checksums establish that.

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
