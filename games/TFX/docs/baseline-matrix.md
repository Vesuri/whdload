# Baseline matrix (step 4)

**Step 5 correction:** these historical rows used permissive FPU emulation.
Future target-040 runs must add `--uae_fpu_no_unimplemented=true`. Corrected
tfx.020 repeats 57/250 with 2,394 FPSP entries; other FPU rows have not yet been
remeasured under strict trapping. See `profile-040.md`. Retain the old table as
evidence of its stated configuration, not a strict-FPU ranking.

## Frozen experiment

`tools/baseline_matrix.py` uses the step-2 pilot-enrolment route and input tape,
then counts publications over **[2,252) game vblank increments after the first
flight swap request**. This is 250 PAL vblanks (five nominal seconds). Inputs are
unchanged: hold joystick right at swap request 10 and release at request 20.
Their actual vblank timestamps are retained. No screenshots or additional field
waits occur inside the measurement window. Read-only hunk snapshots at entry,
vblank 2 and vblank 252 do not advance guest time. The final screenshot/profile
is taken after the window and is excluded from its count.

A publication is the actual SetPage `move.l a0,$dff080`, not the swap request.
The observer checks its bytes and the relocated vblank increment, verifies fresh
PCs at each stop, and counts vblank hits rather than cache-incoherent clock RAM.
Every publication must have a unique swap request and change the selected chip-RAM
copper list. All variants have the same SetPage publisher opcode validated in step 3;
the original renderer reaches it through ThreeScreenSwap. Per-frame timestamps,
input events, binary hashes, CPU metadata, original snapshots and logs are retained.

| Executable | CUSTOM3 | Swap request | Publication | Vblank increment | Clock |
|---|---:|---:|---:|---:|---:|
| TFX | 1 | $018a6 | $4a9bc | $4b62a | $4bbd0 |
| TFX.FPU | 2 | $016f6 | $43d58 | $44c96 | $4523c |
| tfx.020 | 3 | $019fc | $4c474 | $4d2de | $4d884 |
| Installed TFX.040 beta | 4 | $01632 | $4a07c | $4aece | $4b474 |

Offsets are in code hunk 0, resolved from each live LoadSeg chain. CUSTOM4=18
selects skip-intro plus action mode. TFX original rendering uses CUSTOM4=22.
The FPS overlay, uncapped option and one-frame option are off.

The same swap-indexed input tape is used across versions, but slower versions
reach those inputs at later vblanks. These are whole-flight configuration
comparisons, not isolated rendering-routine speedups or cross-version state
identity claims. Keep this exact window/tape for subsequent baseline comparisons.

## Timing model and controls

All runs use A1200 AGA, PAL, 2 MB chip, 32 MB Z3 fast RAM, Kickstart 3.1 and
WHDLoad 20.1 with the unchanged rebuilt slave and FPSP. Z3 is the harness's memory
model, not a claim to reproduce the Apollo local bus. Host time is never used.

The step-2/3 MMU configuration is suitable for functional checks but **does not
scale its instruction timing with the requested CPU frequency**. A corrected
20 MHz probe reports frequency=20000000, MMU=68040 and cycleunit=32, and exactly
matches the 40 MHz shared-emulator probe's publication events (18 publications
in the short [2,52) window). Do not call these results 40 MHz performance.

The step-4 timing configuration follows the shared playbook: 68040-NOMMU,
CPU-compatible, CPU-cycle-exact and memory-cycle-exact enabled, frequency=40000000.
A read-only `monitor cpuinfo` extension records and asserts the effective settings
at flight entry and exit. The private emulator differs from the shared build only
by this metadata command; it does not change CPU execution or profiler behavior.
The installed shared emulator and AmigaXDev source/build remain unchanged.

Corrected frequency controls in `tmp/step4/`: `nommu40` produces 14 publications
in [2,52), `nommu20-corrected` produces 12. Live cycle units are 45 and 90,
respectively. Integer cycle-unit quantization gives approximately 40.356 and
20.178 MHz of modeled cycle budget. These remain emulator A/B figures, **not
Apollo 1240 hardware FPS**. The no-MMU timing core does not model all 040 cache,
MMU and bus costs. Step 14 must establish real speed and the hardware gap.

Rejected controls `probe40` (sandbox blocked debugger), `probe20` and `nommu20`
are retained. The latter two accidentally duplicated the frequency option; the
first occurrence won, leaving 40 MHz effective. Live metadata exposed this.
The harness now omits its default frequency when an explicit override is supplied,
rejects duplicate overrides, and asserts the effective CPU/frequency/FPU/MMU.

## Reproduce

From the game directory, build the metadata-only emulator once from the configured
native AmigaXDev build (the tool refuses to overwrite an existing destination):

```
tools/build_baseline_emulator.sh "$FSUAE_CONFIGURED_BUILD"
```

Then run the complete sequential two-boot matrix into a NEW output root:

```
bash tools/run_baseline_matrix.sh tmp/step4-new
python3 tools/report_baseline.py tmp/step4-new
```

The shell wrapper uses `tmp/step4-emulator/fs-uae/fs-uae` by default;
FSUAE may explicitly select another build supporting `monitor cpuinfo`.
A disposable pristine HDF seed is created per executable/option combination,
then reused across repeats and CPUs. Never reuse a seed with changed startup
options, slave/FPSP or game inputs: the seed embeds those files and startup command.
Run one capture at a time; each command has a host watchdog and the harness stops
only its own emulator. Failed cells retain diagnostic logs and are not assigned FPS.

For one cell:

```
FSUAE="$PWD/tmp/step4-emulator/fs-uae/fs-uae" \
python3 tools/baseline_matrix.py --machine 040 --variant newfpu \
  --output tmp/step4-single --seed tmp/step4-single-seed \
  --extra-args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true'
```

Evidence is under `tmp/step4-matrix/`; emulator patch/build provenance is
under `tmp/step4-emulator/`. `report.json` validates input delivery, repeated publication totals and screenshots,
effective CPU settings, and count arithmetic. It compares ordered events and
retains every timing difference, raw hunk difference and evidence hash. `frames.csv` is the per-frame log.

## Executable naming correction

The installed **599152-byte TFX.040** is the old unmerged 68881 beta with symbols,
selected by CUSTOM3=4. It is not the damaged 709968-byte CD executable or damaged
1997 tfx.strip. The slave ReadMe and `executables.md` already distinguish these.
Earlier step-3 handoff notes conflated the names when declaring the matrix row
unavailable. Testing the installed beta does not establish that an intact native
68040 build exists. The damaged candidates remain excluded.

## Results and decision

Both cold boots produce the listed totals. Rates are **nominal PAL-50 emulator
publications per second**, not measured Apollo hardware FPS. Resolution of this
250-vblank sample is 0.2 fps per publication.

| CPU / timing configuration | Executable / rendering | Publications | Rate | Live CACR |
|---|---|---:|---:|---:|
| 040 / 40 MHz requested, NOMMU | TFX, new | 59 | 11.8 | $80008000 |
| 040 / 40 MHz requested, NOMMU | TFX, original | 34 | 6.8 | $00000000 |
| 040 / 40 MHz requested, NOMMU | tfx.020, current slave | 57 | 11.4 | $80008000 |
| 040 / 40 MHz requested, NOMMU | TFX.FPU | 73 | 14.6 | $80008000 |
| 040 / 40 MHz requested, NOMMU | Installed TFX.040 beta | 73 | 14.6 | $80008000 |
| 020 / 14.18758 MHz, no FPU | TFX, new | 18 | 3.6 | $00000001 |
| 020 / 14.18758 MHz, no FPU | tfx.020 forced | — | unavailable | — |

040 new-renderer rows have instruction and data caches enabled; original rendering
has both disabled by the existing slave path. The 020 has its instruction cache on
and no data cache. These are the actual emulated control registers at both boundaries,
not just requested WHDLoad flags. The no-MMU backend reports mmu=0 even though the
guest's TC register contains $8000: do not mistake that guest request for an active
MMU backend. The original/new comparison includes the existing cache and memory
policy changes, not solely replacement drawing routines.

**Keep tfx.020 as the base:** it remains the newest intact 1997 build and the
project's selected target. In this fixture it needs two more publications per
window, or **3.5% greater throughput**, to match plain TFX's 59 (0.4 nominal fps).
It needs 28.1% greater throughput to match the older FPU builds' 73. This short
scene establishes a baseline, not a claim that these gaps hold throughout the game
or on real hardware. The older builds' higher rate does not justify discarding the
newer build or changing executable selection in step 4.

Forced tfx.020 on the no-FPU 020 exits before flight. The retained screenshot shows
WHDLoad `Line 1111 Emulator ($2C)` at game offset $50f4c; the executable contains
`f23c900000000000` there (FMOVE immediate to FPCR). The formatted fault location is
also retained in the fast-RAM dump. The report recognizes only this precise known
fault as unavailable; missing or unrelated failed cells remain incomplete. No
68882 was silently added to make this row run.

## Repeatability and limits

- All six measured rows have equal publication totals, delivered input events and
  final screenshots in two cold boots. Screenshots show active cockpit flight.
- Ordered events match completely for 040 TFX new/original, tfx.020 and TFX.FPU.
- Beta publication 55 moves from relative vblank 178 to 179 in the second boot;
  its total and final screenshot remain equal. The 020's swap request 17 moves
  from vblank 207 to 206; its actual publication timestamps all remain equal.
  These differences remain explicit in report.json, not rounded away.
- Full raw entry/start/end hunks match for 040 TFX new and TFX.FPU. Other rows have
  absolute-clock differences and some additional raw differences. For tfx.020,
  entry differs only in the five known timers, but the final snapshot also differs
  at data-hunk $fbfc/$fbfd, $fc40/$fc41 and $154a0..$154a3. Original-renderer and
  beta differences are larger; all exact offsets are in report.json.
  No additional game-state equivalence or mismatch waiver is claimed. The earlier
  step-2 acceptance does not cover these new differences. Read-only vblank snapshots
  are not guaranteed to interrupt each renderer at the same sub-frame work state.
- Input release at swap 20 is beyond the 020's five-second window; only its right
  press at swap 10 is delivered. Faster rows deliver both tape events. The per-row
  vblank times make this workload difference explicit. Future patch comparisons
  must retain the same script and also check gameplay/state separately.

The report and capture tools passed Python/shell syntax checks. Four negative
checks reject a missing publication, inconsistent timestamp, repeated buffer and
wrong effective frequency. No game/slave/FPSP bytes, selection rules or 060 code
changed. Tool snapshots accompany captures; failure-diagnostic/source-retention
handling was hardened during the matrix without changing successful capture logic.

## Step 5 handoff

Use this exact [2,252) window and input tape for the primary tfx.020 timing baseline.
Collect routine costs, FPSP entries by opcode/site, chip accesses and cache flushes.
The step-3 MMU dispatch trace has zero cost fields and cannot provide percentages;
its MMU timing also cannot be called 40 MHz. Establish and validate instruction-cost
coverage in the frequency-sensitive backend, including Z3 code, before reporting
costs. Keep the MMU functional configuration for cache/correctness regression.
Preserve separate timing and state-equivalence results; the baseline counts do not
waive the raw-state differences documented above.
