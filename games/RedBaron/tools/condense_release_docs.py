from pathlib import Path
root=Path('docs')
intro='''
The normal release enables its verified CPU-specific bundle by default. Its
player selector is On=0, Off=1; developer/VERIFY values below remain bit masks.
Only sim v1 receives performance patches. Current measurements and final release
checks live in [profiling.md](profiling.md), the single results record.
The full pre-condensation ledger is preserved at commit `dd9e8b4`.
'''
def write(name,body,tests):
    commands='\n'.join("python3 -B -m unittest discover -s tools -p '"+t+"'" for t in tests)
    (root/name).write_text(body+'''
## Reproduce

From the game directory, using the shared environment:

```sh
. ../../common/env.sh
'''+commands+'''
VERIFY=1 bash tools/build.sh
```

Native rechecks require the ignored development game installation, one owned
emulator, a fresh output directory and the corresponding VERIFY options below.
Use the shared machine definitions in `tools/completion_machines.py`; historical
A500 drivers that still select slow RAM must be updated to the approved minimum
before reuse. These commands are for intentional rechecks, not additional
release validation rounds.
''')
write('w1-verification.md','# W1 dashboard mirrors\n'+intro+'''
## Retained implementation and evidence

Developer bits 0/1 select the exact table mirror and cached chip mirror.
The table hook is sim:304d0, with WaitBlit on entry; cached drawing hooks
sim:30412 and invalidates at sim:303c6. The cache has allocation fallback and
keeps DMA data in chip RAM. The normal policy retains original table mirroring
on 030/040/060 while retaining the separate mirror cache.

The table model, original/optimized twins and corrected bank/dense checks passed
on A500/020. Corrected cached-030 bank checks also passed. The fallback invalidation
bug was fixed before those captures. Disabled-range and bounded display checks
are recorded in the scoreboard; they are not an all-scenes tearing guarantee.
The dashboard is event-driven, not a per-frame 3D maths cost.

Evidence families: `w1-*` in the local capture collection; the corrected scene
build and its exact hashes are identified in the retained profiling history.
Do not treat unfinished cached-030 dense directories as completed evidence.

Further cached-030 dense/cache-only extension, return-flag write-up and additional
lifecycle refinements were deferred by the user to prioritize larger costs.
They are not required by the accepted release scope.
''',['test_mirror*.py'])
write('w2-verification.md','# W2 geometry\n'+intro+'''
## Retained implementation and evidence

Developer bits 2–5 select G1 projection, G2 trivial clipping, G3 32-bit vertex
cache misses and G4 low-long back-face products. G1 is excluded on 030/040/060
by the normal policy; the other verified paths remain available. Completion C3
also retains the face-loop bit 6 on 68000 only.

Independent projection, clipping, transform and dot models were checked against
original traces. Combined native twins passed across A500/020/cached-030 bank
and dense scenes. Edge checks cover signs, overflow, normalization and matrix
forms. Same-build performance pairs and hook audits are in the scoreboard.
The whole 3D-pass cost includes raster drawing; it is not a pure maths cost.

The remaining G1/G3 refinements and G5–G9 were deferred by the original cost
threshold. Completion C1/C2 were implemented, measured and dropped below the
later 2% threshold. No unimplemented refinement is represented as shipped.
Native reproduction driver: `tools/w2_combined_twins.py --machine 020 --scene bank`
from the development directory, using a fresh output location in that driver.
''',['test_projection_model.py','test_clip_model.py','test_transform_model.py','test_dot_model.py','test_face_model.py'])
write('w3-verification.md','# W3 exact-output sound\n'+intro+'''
## Retained implementation and evidence

Developer bits 10/11/12 select S1 queue access, S9 no-op call removal and S3
bounded volume division. The normal policy keeps original S3 on 030/040/060.
The loader handles both observed sound-driver loads; sound: offsets are relative
to the driver code entry convention documented in the hook tools.

Queue and exhaustive/live division twins passed on A500/020/cached-030.
Ordered Paula/control writes and per-channel fetch observations agreed in the
bounded cached-CPU windows. These support the local exact-output proofs, not
arbitrary wall-time-aligned audio equality after a frame-rate change.
Sample data, buffer sizes, service ownership and tick/envelope timing are unchanged.

S2/S3-prime/S4–S8 were deferred below the original cost threshold. The broader
B-series sound/OS behavior changes are not part of this release.
Saved native evidence includes `w3-div-twin-a500-r2`, `w3-div-twin-020` and
`w3-div-twin-030`. The live checker is `tools/w3_twin_check.py ENTRY --step 8`
from the development directory after a matching fresh VERIFY twin boot.
''',['test_sound_model.py','test_sound_hooks.py'])
write('w4-verification.md','# W4 solid rectangle fills\n'+intro+'''
## Retained implementation and evidence

Developer bit 7 selects D1 at sim:2fd2c. When both edge masks are full, the
blitter can omit the destination read channel; masked edges retain the original
read/modify/write path. Clipping, plane order, pointers, pitch, BLTSIZE, wait and
BLTPRI policy are unchanged. This is still a blitter renderer, not C2P.

Independent fill models, three-CPU pixel twins and disabled-byte checks passed.
The completion E3 work also fixed VERIFY's pre-flight h3 pointer initialization;
the retained D1 path passed its native pixel comparisons afterward.
Its CPU rectangle and polygon replacements were separately measured and dropped;
the Fast RAM full-scene backend was also dropped. Their models remain, while
none of those rejected runtime implementations ships.

Overlay queueing was deferred below the original threshold. The later standalone
gauge cache is retained only on 020/040; complete cockpit composition was dropped.
See the E2/E3 scoreboard for measurements and scope.
The live checker is `tools/w4_twin_check.py ENTRY --step 8` from the development
directory after a matching VERIFY fill-twin boot.
''',['test_fill_model.py','test_cpu_span_model.py','test_fast_blitter.py'])
write('w5-verification.md','# W5 display pacing and player policy\n'+intro+'''
## Retained implementation and evidence

Bit 8 changes the flight swap argument at sim:00b06 to select the native beam
wait. Bit 9 wraps the flight calls at sim:00b08 and observes native VBlank at
sim:2d34e. The original publication at sim:3154a, blitter wait and copper data
remain in place. Non-flight callers are unchanged.

The normal bundle uses a two-field minimum between actual publications. First
publication has no predecessor; slow drawing does not accumulate cap debt.
Developer W6 bit 13 forces bits 8/9 and changes the minimum to one field.
The normal build does not enable W6, so it does not promise independent world
speed or 50 FPS. NTSC pacing has not been measured.

The independent modular-clock model and native compiled wrap/fast-draw fixture
passed. The fixture deliberately omits drawing, and cannot establish game FPS,
interpolation or pixel correctness. Bounded display checks and the real E4
per-field deadline failure are recorded in the scoreboard. The user accepted
measured performance on 2026-10-12; no missed deadline was relabelled a pass.

The verified mask is `0x71fff`, filtered by CPU in `perf.s`; D5 bit 13 is absent.
The normal splash list is “Faster rendering: On, Off”, with zero meaning On.
To disable the player bundle use CUSTOM2=1. Developer/VERIFY CUSTOM2=0 still
means all performance bits off. Icons remain unchanged, WHDLoad 17+ is required,
and normal/developer binaries contain no VERIFY fixtures or scripted input.

For a fresh native stress fixture from the development directory:
`python3 tools/w5_boot.py 030 768 tmp/prof/w5-recheck --stress`.
Use `publication_cadence.py` on a continuous saved field-census manifest; its
passed verdict requires every deadline, including both observation edges.
''',['test_pacing_model.py','test_publication_cadence.py'])
write('w6-verification.md','# W6 consistent-speed candidate: acceptance postponed\n'+intro+'''
## Current status

D1–D4 are implemented; the user postponed D5 on 2026-10-11. Developer bit 13
selects the candidate. It is deliberately absent from the normal verified mask.
Accepting current rendering performance on 2026-10-12 did not resume D5 or
approve this candidate for players. [game-time-plan.md](game-time-plan.md)
retains the design; the completion plan supersedes its obsolete acceptance work.

The candidate uses quantum 450 on 68000 and 225 on 020+, with interpolation only
on 020+. CIA time funds bounded catch-up debt; overload is counted and capped
at approximately one nominal second. Input, modal rebasing and presentation
remain distinct from world updates. All instruments, sabotage fixtures and
observers are VERIFY-only; the common runtime compiles in all modes.

## Accepted evidence and its limits

- The clock models, both quantum tables, stock dt=450 helper twins and deliberate
  checker failures pass. The 68000 bypass check confirms no pose capture/blend
  while retaining drawing. These are kernel/helper checks, not full gameplay proof.
- D5 rate windows cover all six configured machines. A500 passes its Time Scale 0
  sample but drops time at maximum-detail 40; 020–060 pass their sampled 40 windows.
  The scoreboard is the sole numerical rate/capacity record.
- A500/060 throttle taps and pause/rebase passed. The user found A500 steering
  predictable but maximum-detail control difficult, and 060 steering/release good.
  The 060 crash smoke test and one-flight emulated soak passed.
- Remaining catch-up input, Time Compress/mission-exit transitions, A500 Time
  Scale 60 and landing/combat outcomes were not completed. No rate sample
  substitutes for those gates or for the user's handling observations.
- E4's real 030/040/060 captures do not meet every-field cadence. The user
  accepted measured rendering performance; no 50 FPS claim remains in the release.

Cross-CPU full-state convergence and further byte-equivalence studies are not
current acceptance requirements. Rejected orientation/matrix/overlay candidates
remain historical experiments, not enabled runtime. The earlier exhaustive
ledger, raw addresses and abandoned investigations remain in Git history.

## Native reproduction after D5 is resumed

Use the current six-machine definitions and a fresh output directory. From the
development directory, `tools/completion_d5_case.py MACHINE MASK OUTPUT` performs
the native-keyboard route and rate capture. Select the documented developer
bundle plus bit 13; retain CPU policy. `tools/completion_d5_inputs.py`,
`completion_d5_pause.py` and `completion_d5_soak.py` are the retained companion
checks. Inspect their arguments before running; they may use fixed evidence paths.
Do not run these postponed checks as part of the current release.

D2's retained native checker is `tools/completion_d2_twin.py`; its original
output path is fixed, so use a fresh path before intentional reproduction.
''',['test_game_time_model.py','test_time_capacity.py','test_input_events.py','test_pose_history.py'])
(root/'open-work.md').write_text('''# Red Baron open work

The user accepted measured performance on 2026-10-12 and requested completion
of release work. The completion plan remains authoritative with that amendment.

## Required for this release

- F2: finish documentation condensation and commit it.
- F3: final builds, host tests, hook/reach audits, explicit disabled-byte check,
  and normal-build scoreboard refresh on all six machine configurations; commit.
- Replace the ReadMe's pending results with the final measured summary.

F1 is committed: Faster rendering defaults On, normal CUSTOM2=0 is On and 1 is
Off. Developer/VERIFY values remain bit masks; zero disables their patches.
The verified mask is `0x71fff` with CPU filtering. No push is authorized.

## Postponed beyond this release

D5 remains postponed by the user. W6 bit 13 stays outside the normal mask.
Remaining checks: catch-up input, Time Compress/mission-exit transitions,
A500 Time Scale 60 and remaining landing/combat outcomes. Existing rate,
input, user-flight and soak evidence is summarized in `w6-verification.md`
and measured in `profiling.md`; no further user flight test is requested now.

Earlier optional W1 cached-CPU extensions, G1/G3 refinements and G5–G9,
S2/S3-prime/S4–S8, broader sound/OS changes and overlay queueing remain deferred
unless a concrete issue justifies them. The completion plan's low-value or
regressing C/E candidates were dropped, not left as release blockers.

50 FPS and frame-independent normal-build gameplay are not release claims.
Further renderer redesign requires a new scope. Historical ledgers remain in
Git; do not revive their superseded next-work lists.
''')
