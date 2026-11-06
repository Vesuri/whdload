# tfx.020 memory placement (step 8)

Step 8 targets the new-rendering 68040 path only. `CUSTOM4` bit 2 (original
rendering) retains the old all-chip placement. The 020/030/060 paths and other
executables retain their existing placement. `CHIP_ONLY` also retains it.
Selection is unchanged: explicitly select the newest executable with `CUSTOM3=3`.

## Mapping

The intact 599152-byte `TFX.040` symbol build preserves the original memory
attributes. Complete relocation-masked function matches from step 6 give constant
merged offsets for each data/BSS hunk. Every byte of its initialized chip groups
matches `tfx.020`, except the two recorded sprite-table pointer addends.

Hunk-relative ranges below are half-open. Hunk 1 is merged DATA, hunk 2 merged BSS.

| Object | Old symbol-build hunk | tfx.020 range | Destination in chip allocation |
|---|---:|---|---|
| Tracker quiet sample, mouse sprite images and buffers | 2, 4 | 1:$d98–$24d4 | $0000 |
| Hardware sprite blocks, null sprite, copper lists/plane pointer words | 8, prefix | 1:$27e0–$4330 | $1740 |
| Paula quiet sample (200 bytes) | 10 | 1:$4938–$4a00 | $3290 |
| Two 320×200×8 bitplane buffers and alignment space | 9 | 2:$7cec–$270f4 | $3358 |

The allocation is `$22760` (141,152) bytes, including four padding bytes before
its display group. Both the allocation and video buffer offset are 8-byte aligned.
The video initializer's existing `+7; AND #-8` remains valid.

These formerly chip-marked objects are CPU-only and remain in fast RAM:

- 1:$24d4–$27e0: current RGB palette, sprite base word and two sprite pointers.
  `_SetPal`/`_DiffSetPal` read/write the palette using CPU accesses to AGA colour
  registers; it is not a copper list. The two sprite pointers are relocated to
  the copied hardware sprite buffers.
- 1:$4330–$4938: `_standardpal`, `_mypal`, `_logbase`, `_saved_logbase`,
  `_current_page`. All references to these stay in the merged fast hunk.
- The remaining ordinary initialized data and BSS.

All slave `PL_GA` addresses remain valid in their original segments. In particular,
`_sprogtab_ptr`, `_logbase_ptr` and `_current_page_ptr` point to CPU data in fast RAM.
The static checker verifies that no PL_GA object is inside a copied DMA range.

The old merged hunks consumed 258,996 chip payload bytes (plus their allocation
headers). The new DMA payload/allocation uses 141,152 bytes: 117,844 fewer payload
bytes, about 115.1 KiB. The original merged hunks remain allocated in fast RAM,
including their unused old DMA storage. This trades extra fast RAM for simpler
segment lifetime and pointer handling on the specified 32 MB machine.

## Implementation and guards

The existing loader hook recognizes the two merged allocation sizes including
their eight-byte segment headers. On 040 with new rendering it requests MEMF_FAST;
on all other paths it retains MEMF_CHIP. Before PatchSeg, the slave allocates the
DMA block, adjusts the recorded HUNK_RELOC32 operands and pointer-table entries,
then copies the objects. This precedes `resload_PatchSeg`, whose WHDLoad 20.1
autodoc guarantees a cache flush before returning, so the relocated code operands
are coherent before execution. No per-frame flush is added. No game file is
modified. Allocation failure aborts via
the existing out-of-memory message.

`tools/generate_chip_relocs.py` derives `chip_reloc_new.i` directly from the intact
executable's HUNK_RELOC32 entries: 50 code operands and 12 data pointers, 62 total.
It does not scan memory for values resembling addresses. `tools/check_chip_relocs.py`
independently reads the assembly table, compares its complete set against all hunk
relocations targeting the DMA ranges, checks bounds, and rejects a removed entry.
It also checks the PL_GA exclusion. The source Makefile tracks the include.

## Verification method

Use strict unsupported-FPU trapping throughout 040 tests. Performance remains the
existing [2,252) flight-relative vblank window, with the original recorded tape,
NOMMU frequency-sensitive 40 MHz timing and actual COP1LC publication counter.
Do not use the controlled-scene run as a speed measurement.

`tools/step8_scene.py` compares the same simulation scenes independently of speed.
Before the first simulation update, stop at the existing frame-limiter exit
`$1ac36`. A guarded private test fixture replaces its 16-byte timestep clamp with
`MOVEQ #5,D0; MOVE.W D0,-2980(A4); NOP × 5`. The following native code calculates
all derived floating-point timesteps normally. D1 is overwritten before use.
This fixture is applied identically to baseline and candidate in emulator memory;
it is absent from the normal slave and from performance measurements.

Inputs remain swap-indexed and are delivered to the native resolved right-arrow
latch (`$40ce5`, byte 79 of the key table at `$40c96`), the same latch `_ReadDJoy`
sets for right. A guarded six-byte fixture makes `_ReadDJoy`'s hardware word read
neutral, and clears its right-direction latch bit, so asynchronous polling cannot
undo the controlled key state. The tape writes `$ff` after swap 10 and zero after
swap 20. This makes the edge visible before the same next simulation update in
both builds. The fixture supports this tape only and rejects other event names.

Capture the actual COP1LC publication at `$4c474`,
single-step the COP1LC write, and hold the CPU with interrupts masked in a tiny
private fixture loop while recording two DMA fields. Use the last full field.
Verify all general registers are unchanged, restore the fixture NOP, PC and exact
SR (including the publication write's condition codes), and continue. This prevents
capture from silently running past the next swap on the faster build.
All eight bitplane DMA starting addresses must match the selected copper list. The observer
also requires every publication number 1 through 57 without a gap. Capture
publications 1, 10, 30, 45 and 57, including the banked flight.
`SCENE_NOMMU=1` uses the timing backend; otherwise the functional MMU backend.
This controlled scene test is not full-state cold-boot equivalence or a new waiver
of the earlier timer/audio mismatches.
The CPU-held capture uses `tmp/step8-emulator/fs-uae/fs-uae`, built privately by
`tools/build_scene_emulator.py`. Its only addition to the step-7 fixture backend is
SR register writes through `tfxreg 16`; the saved patch is `step8-scene-sr.patch`.
The shared emulator and the normal timing backend remain unchanged.

`tools/step8_audit.py` checks the live fast/chip domains and all 50 mapped code
operands. The game legitimately changes two initial mouse pointers during menu
setup, and the existing `start_frame` temporarily redirects the active sprite-table
pointer to its fast render buffer until `do_swap_screen` copies it back to chip.
Report those three live data-pointer differences separately. `tools/check_chip_dma.py` reads actual DMA records
from each screenshot trace and checks copper, audio, sprite, bitplane and any
blitter source/destination addresses remain below 2 MB.

## Pitfalls retained in the evidence

- The first conservative candidate copied all original chip groups, including
  CPU-only palette/selector data. It measured 70 publications and passed five MMU
  visual comparisons. It is retained only as an intermediate experiment.
- Breakpoint-only timestep writes miss updates while `monitor profile` advances
  the emulation to capture a field: the first-update fixture logged only 53 writes
  for 57 swaps, and its visual comparison failed. The persistent test-only clamp
  replaces that fixture.
- A screenshot at a swap request can display the previous frame depending on the
  current field phase and copy/publication delay. The first persistent-clamp
  comparison (`*-scene-fixed`) also differed. Capture after publication and verify
  the selected bitplanes, as in step 3. `final-scene-published` additionally caught
  missed swaps while the CPU ran during two-field capture; its consecutive-
  publication assertion failed. The final fixture holds the CPU during capture.
  Preserve all unsuccessful comparisons.
- CPU-held capture (`*-scene-held`) matches neutral flight but still differs after
  the bank: host queued joystick changes can reach `_ReadDJoy` on different updates
  when the render speed changes. The native hardware-read fixture
  (`*-scene-native`) still left a delay before the resolved key latch changed.
  Direct resolved-latch injection (`*-scene-latched`) removes both dependencies
  while retaining the same tape. All five final images match, including the bank.
- `final-scene-nommu` timed out during startup before flight. The exact same seed
  subsequently booted and completed all checkpoints in `final-scene-nommu-retry`.
  Retain the timeout log; it is not a completed test.
- Disk seeds contain their own slave. A saved baseline seed intentionally runs
  the pre-change slave, even if the host build copied into the output folder is
  newer. Confirm live segment placement and keep the baseline slave separately;
  the host launch manifest alone does not identify the executable inside the HDF.
- Raw state and the uncontrolled old/new fixed-window image need not match when
  publication speed and swap-indexed input timing change. The controlled visual
  comparison is separate from the unmodified timing measurement. No full-state
  equivalence or additional mismatch waiver is claimed.

## Normal timing and regression results

| Strict 040 NOMMU fixed window | Publications / 250 vblanks | Nominal PAL equivalent |
|---|---:|---:|
| Step-7 baseline | 57 | 11.4 fps |
| Final DMA-only candidate | 73 | 14.6 fps |
| Exact-seed candidate repeat | 73 | 14.6 fps |

The candidate improves throughput by 28.07% in this emulator comparison. It is
not an Apollo hardware FPS claim. The two candidate runs match the complete event
sequence, final screenshot and all three final hunk dumps byte-for-byte. The normal
old/new final screenshots differ because their frame cadence and swap-indexed
input timing differ. Visual equivalence uses the separate controlled fixture.

Final shared-emulator cold-boot pairs (`final-regression/`), checkpoints 1/10/20/30:

| CPU | All four paired images | Raw hunk state | Clock-relative hunk state |
|---|---|---|---|
| 040 strict MMU | equal | equal | equal |
| 020 integer TFX | equal | equal | equal |
| 030 + 68882 | equal | differs by two-vblank origin | equal |
| 060 | equal | equal | equal |

The two-vblank 030 origin difference is reported, not an extension of the user's
specific step-2 one-vblank acceptance. Relative to the older step-7 cold boots,
040/060 images match; 020/030 images at later checkpoints differ. Preserve these
cross-run comparisons rather than claiming all historical states/images match.
The 020/030/060 placement branches are unchanged; live 030/060 data/BSS addresses
remain in chip, while all three 040 candidate hunks reside in fast RAM.

`final-audit-original` verifies the original-rendering off path still loads both
merged hunks in chip RAM and retains all 50 original code operands. Both normal
and CHIP_ONLY builds assemble. The final source rebuild is byte-identical to the
tested candidate; both FPSP outputs and all three pristine executable hashes are
unchanged.

## Completed visual exit and reproduction

All five baseline/candidate images in `baseline-scene-latched/` and
`final-scene-latched/` are byte-identical. Both runs account for every publication
1–57. At all five checkpoints every bitplane fetch matches the published copper
list, and every captured copper/audio/sprite/bitplane DMA address is in chip RAM.
There are no blitter DMA records in these gameplay captures; its static mouse
image sources and destinations remain in the copied chip objects. The bank is
visible in the later checkpoints, so this is not a neutral-input-only comparison.

`tmp/step8/validation.json` records the complete passing visual, relocation and
normal-timing checks, and separately records the non-identical historical and
030 raw-state comparisons. The source feature is committed as `a539348`.

From the game directory, validate retained evidence:

```sh
python3 tools/check_step8.py
```

To reproduce the final suite into a new output directory (the private backends and
retained baseline HDF seed must already exist):

```sh
bash tools/build.sh
python3 tools/step8_final_checks.py tmp/step8-repeat
```

To rebuild only the private screenshot backend from the retained step-7 tree,
`python3 tools/build_scene_emulator.py` creates `tmp/step8-emulator` and
refuses to overwrite an existing tree. No shared backend is rebuilt or replaced.
The timing and audit tools continue to use the step-7 private backend; the CPU
regression suite uses the unchanged shared emulator.

The generated assembly relocation include can be reproduced with
`tools/generate_chip_relocs.py`; `tools/check_chip_relocs.py` independently verifies
it. Keep generated game bytes, disk seeds, images, traces and executables ignored.
For step 9, reprofile trap counts on this placement baseline before changing the
maths. The earlier six hot wrappers and static FINTRZ/FMOVECR census remain the
starting map, not a new measurement of this build.
