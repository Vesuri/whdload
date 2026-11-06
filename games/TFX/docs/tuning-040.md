# Step 11: 68040-specific tuning

The acceptance rule is measurable fixed-window improvement. Step 11 is complete with no retained code change: all three same-build A/B
copy pairs produce 73 publications/250 vblanks. The screen-copy
experiments are retained under `tmp/step11/`, not in the release slave.

## Baseline and current costs

The unchanged step-10 slave was rebuilt before modifying source. `baseline/` is a
fresh cold boot with the strict 40 MHz 040 NOMMU observer, CUSTOM3=3, CUSTOM4=18,
32 MB fast RAM, recorded input tape, and the established [2,252) vblank window.
It produces 73 publications, with zero FPSP entries. The entire profile, counts,
final PNG and all three end-state hunk dumps match step10/final/default-profile
byte-for-byte (`baseline-repeat.json`). This is emulator A/B evidence, not Apollo
1240 throughput.

`tools/step11_report.py` anchors slave addresses to the matching assembler listing
and verifies the live swap prologue. It retains the accepted step-6 game regions.
It does not reuse step 5's hardcoded slave offsets, 57-frame assertion or expected
FPSP load/execution assumptions. All PCs are assigned; a 512-scheduler-tick
boundary residual is retained explicitly, rather than assigned to a routine or
silently rounded away. The observer surrounds instruction dispatch while debugger
start/save occur between dispatches. The residual is under 0.000006% of the window;
its exact attribution is not established. The checker rejects larger residuals.

Largest measured regions in the fresh baseline:

| Region | Share of scheduler time |
|---|---:|
| ScanFillDown | 16.13% |
| Slave screen copy/publication | 16.08% |
| CPU masked sprite merge | 11.30% |
| Project | 7.68% |
| SetColor region | 7.28% |
| Polygon region | 5.33% |

Region percentages include the emulator's synthetic instruction padding. They
are not a hardware instruction-latency model. Other regions and every executed
PC remain in each `step11-report.json`.

## Cache and FPU audit

The existing startup call to resload_SetCPU already requests WCPUF_Exp_CB and
WCPUF_Slave_CB, with IC/DC enabled and base memory write-through. Runtime CACR is
$80008000. NOMMU timing cannot independently prove physical MMU page attributes;
the source request and existing MMU functionality are distinct evidence.

The new renderer's draw_mono_image_setup replaces the self-modifying font draw
path. The old fix_smc/_flushcache remains needed by selectable original rendering.
There are zero calls to that hook, _flushcache, CacheClearU, CacheClearE or
CacheControl, and zero cache opcodes in the measured new-render window. There is
no per-frame flush to remove and no reason to weaken the original path.

All executed FPU coprocessor instructions together occupy only 0.483% of this
profile. Keeping additional FPU values in registers cannot establish a useful
win with this timing model; no arithmetic/ABI changes were made on that basis.
Native step-9 FPU replacements remain intact. Flat-fill's equivalent generic
replacement already lost in step 10 (72 versus 73); the original ScanFillDown
remains selected. Masked sprites and geometry remain possible future targets,
requiring their own focused equivalence work and measurements.

## Copy experiments

`copy-candidates.s` is the exact experimental source, preserving the source's
CRLF endings. STEP11_COPY selects one of three developer-only candidates:

1. Four MOVE16 instructions per loop (64 bytes).
2. MOVEM load/store of D1-D7/A2 (32 bytes), with destination advancement.
3. Sixteen ordinary longword moves per loop (64 bytes).

Each runs only when the existing 040 tfx.020 render-list selection is active and
both buffers are 16-byte aligned. Other cases take the original four-longword
loop. The sprite copy is unchanged because it deliberately skips sprite control
words. These are diagnostic builds, never release features. The source snapshot
is not a second editable slave.

The buffers observed in the MOVE16 run were aligned ($41a13860 and $9520).
Its four MOVE16 sites each execute 73,000 times: the candidate was exercised,
not silently bypassed. All three initial runs present 73 frames.

Same-build controls use `step11_profile.py`, COPY_LISTING and COPY_OFF=1. Before
the first swap and outside the timing window, the private debugger changes only
the candidate-selection BEQ to BRA, keeping its displacement and forcing the old
loop. The instruction byte is read back. The same HDF seed and identical slave
bytes are used on each side. No fixture writes occur inside the timing window.
`check_step11.py` checks candidate execution on and absence off, strict trapping,
zero cache/FPSP events, and both frame counts.

| Candidate | Old loop | Candidate loop | Decision |
|---|---:|---:|---|
| MOVE16, 64-byte loop | 73 | 73 | Reject |
| MOVEM, 32-byte loop | 73 | 73 | Reject |
| Longword moves, 64-byte loop | 73 | 73 | Reject |

All six runs have zero FPSP entries and zero measured cache flushes. All three
on/off final images and raw hunk comparisons differ; no equivalence is inferred
from the common frame total. The implementation is discarded without spending
further validation on a non-winning candidate.

Three negative controls in `report-negative-controls.json` reject an altered
frame count, a missing high-cost instruction and a wrong slave symbol anchor.
The last initially exposed a self-consistent anchor error; independent live-code
checks at _drawdigit, _flushcache and fix_smc now reject it. The corrected report
and the aggregate checker were rerun successfully on all retained pairs.

Timing alone does not establish pixel equivalence. No candidate has passed a
routine twin or controlled-scene equivalence gate; no candidate is retained.
Uncontrolled final screenshot/state differences are recorded and are not waived.
Raw copy-region percentages are also retained, but are not comparable per-call
costs: the window can include a partial copy and changed simulation cadence.

## Tools and reproduction

From the game directory, build and capture a fresh baseline:

```
bash tools/build.sh -L "$PWD/tmp/step11-recheck.lst"
FSUAE="$PWD/tmp/step9-emulator/fs-uae/fs-uae" \
  python3 tools/step11_profile.py "$PWD/tmp/step11-recheck"
python3 tools/step11_report.py \
  tmp/step11-recheck tmp/step11-recheck.lst
python3 tools/check_step11.py
```

The last command checks retained evidence in `tmp/step11`, including current
release-byte identity. The emulator/debugger needs local socket permissions.
Run harness sessions serially, and use new output paths. Existing seeds contain
their own slave bytes; use only a seed from the exact same build.

For the rejected candidates, reconstruct the source changes from the preserved
snapshot or diff in an experimental checkout, build with -DSTEP11_COPY=1, 2 or 3
and a matching -L listing, and use a fresh seed for each changed build.
`step11_copy_runs.py` records candidates 2/3; `step11_copy_off_runs.py` records all
three controls using the captured binaries and seeds. Those drivers assume the
retained experiment layout; they are not commands for an unchanged release tree.
Restore and rebuild the authoritative source after experiments.

The final release bytes must equal the baseline, including both FPSP files.
No 020/030/060 instruction or option changes are retained. Step 10's verified
regression artifact remains the exact release artifact; repeating its full matrix
would not test a new implementation. The next project step is palette diagnosis.
