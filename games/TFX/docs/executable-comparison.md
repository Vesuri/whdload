# FPU-equipped executable comparison

Task: compare plain TFX with the 1997 tfx.020 on each CPU; change automatic choice
only where the latter wins. Evidence is under `tmp/exe-compare/` relative to this
harness. All runs use DEBUG_PORT=2611 and execute sequentially. The source baseline
is 1affd2be (production code 83323382). The initial unchanged 030 action baseline
is base-030-action: 894 publications/2,000 PAL fields.

## Renderer audit

The common list is now pl_fpu_new_render. A full 040 chains its small
pl_fpu_new_render_040 rotation-cache list into it. Original rendering (C4 bit 2)
continues to skip both. Merged data/BSS use the existing DMA-only chip relocation
on every CPU with new rendering; the DMA ranges and relocation tables are unchanged.
Delta shadows allocate on 030/040/060 only. Rotation table allocation and its
DoRotPt0 hook remain full-040-only. Allocation failure retains the existing full
copy / original multiplication fallbacks.

No MOVE16 or cache-control instructions occur in the shared renderer. Its integer
operations are 020-compatible except the Gouraud reciprocal's 64-bit MULU.L: the
existing gr_start AttnFlags branch chooses gr_body_div on 060. Projection uses
memory FMOVEM for FP/control state and register/word operands for FDIV/FMOVE; it
uses no extended-immediate EA. CUSTOM1 selects integer projection; CUSTOM5 leaves
the original projection. The 6888x CPUs keep original native game FPU instructions
(no FPSP installation, so no native_fpu_patches list applied). Full 040 keeps its
native replacements; 060 keeps FPSP, its existing FPU list, and its integer
instruction fixes. Lists apply shared base, render, FPU, then 060 integer fixes;
the relevant patch sites do not overlap.

## Reproduce and interpret

`tools/exe_compare_profiles.sh` runs cpu_profile.py for integer/newfpu on 030,
060 and 020+68882, action and follow tapes. PROFILE_SLAVE and DELTA_LISTING freeze
the candidate; each CPU/executable/tape gets a separate fresh seed because CUSTOM3
is baked into the boot disk. No cross-CUSTOM seed reuse. PROFILE=0 collects the
publication counter, since per-PC profiling is implemented only on the 040 NOMMU
core. The extra 020 option explicitly enables the 68882.

AUDIT_RENDER enables tools/exe_compare_audit.py: check live hooks, data/BSS
placement, CPU/FPU identity, rotation/shadow allocation, projection, and native
FPU sites. CPU settings and build/input hashes are recorded with every run.
Compare only within a CPU; 060 timing is not cycle exact and ignores chip writes.
These are executable/renderer comparisons, not exact-output microbenchmarks:
different executable versions and frame-dependent input/scene progression can
change the work drawn. Small margins need repeat measurements; routine-level
cycle evidence is required for small exact-code changes.

## Current status

Renderer support committed as 3802cfd5. Normal and CHIP_ONLY builds have no HUNK
relocations; shipped FPSP files are unchanged. Frozen render.slave is the support
build used by all performance and native equivalence tests. Frozen auto.slave is
the final automatic-selection build (c4e56b93); it changes only selection and the
CUSTOM1 label. Final executable/option and startup regressions pass.

| CPU | Action (TFX -> tfx.020) | Follow (TFX -> tfx.020) |
|---|---|---|
| 020 + 68881, 14.19 MHz | 128 -> 165 | 93 -> 108 |
| 020 + 68882, 14.19 MHz | 128 -> 165 | 93 -> 108 |
| 030 + 68882, 50 MHz | 899 -> 1,000 | 567 -> 641 |
| 060 + FPU, 50 MHz | 502 -> 625 | 327 -> 380 |

All counts use 2,000 PAL fields. comparison.json records hashes/settings checks.
The 68881 and 68882 are identical in these emulator measurements, not a hardware
FPU-speed equivalence claim. All 16 saved performance images were visually checked.

Native tests on 020+68882, 030+68882 and 060: 275 full projection cases against the
original, independent integer oracle, four negative controls. Gouraud: 18 synthetic
streams / 2,496 rows, full planes/registers/CCR against prior chunky+C2P, independent
pixel model, six negative controls. No recorded probe streams were supplied to
this repeat; these are synthetic tests. On 060, the tested entry selects DIVU.L.
Support gates: new 040 and 020 paths plus original rendering on all four CPUs.

Final regression tooling: exe_compare_regression.sh (all four FPU-equipped CPUs,
no-FPU 020, and 68881 automatic choices); exe_compare_startup.sh (intro/menu/config/
action-intro); check_exe_comparison.py verifies coverage, source-build identity,
FPSP bytes, CPU/FPU and patch gates, and 040 FPU sites. Native suites and comparison
scripts are adjacent. Use separate new output directories for fresh suites.

Pitfall found in this run: step13_matrix.py's former 4 MB discovery window started
at $41a00000, but TFX.FPU on 040 placed an auxiliary hunk at $419fdcb8. The unchanged
hunk-chain validator correctly rejected it before flight testing. Discovery now
covers the upper 8 MB ($41800000..$41ffffff). The failed capture is preserved as
selection/040-fpu-discovery-rejected; rerun passes with the same option-specific
seed. These absolute addresses describe a local harness capture, not game patch
addresses. The live renderer checker uses the unconditional joystick hook to find
the slave, because original rendering without FPS does not patch the swap entry.

A second retained harness rejection, selection/020-fpu-enrolment-rejected, timed
out before the first swap with a blank enrolment form. TFX.FPU on 020 had not
accepted the short boot inputs. The 020 legacy FPU executables (TFX.FPU/TFX.040)
now use the existing slow-original-renderer waits: 3,000 boot fields, 40-field
key holds, 80-field transitions. The same-option seed then passes; no game/slave
patch was needed. This affects regression boot input only, not the performance
tapes or their 2,000-field measurement windows.


## Final handoff

check_exe_comparison.py passes: 68 flight cases (56 on four FPU-equipped CPUs,
ten no-FPU 020, two 68881 automatic choices), 20 startup cases and exact final
slave/FPSP identity throughout. Flight gates check each data/BSS hunk individually:
fast with new rendering, chip with original rendering. All 16 performance images,
68 flight images and 60 startup images reviewed; visual-review.json records scope.
validation.json is the final machine-readable result. No game state or cross-
executable pixel identity is claimed. Native helpers retain their separate exact
oracles and negative controls.

Automatic selection now chooses tfx.020 on every detected FPU, retaining the
existing 040 FPU and 060 PCR checks; no-FPU CPUs use TFX. Explicit CUSTOM3 choices
are unchanged. C1 is labelled integer projection because the shared renderer
supports it on all CPUs. Canonical tmp/build/release/TFX.Slave matches auto.slave. Source
snapshots, exact listings, normal/CHIP_ONLY builds and rejected harness captures
are retained under tmp/exe-compare. No emulator remains running from this suite.

No next executable-comparison task remains. Hardware calibration/real Apollo
measurements, release work and the unreproduced palette issue remain as listed
in open-work.md. No hardware 20 fps claim follows from this comparison.

Both commits are pushed to origin/tfx: 3802cfd5 (renderer), c4e56b93 (selector/plan).
