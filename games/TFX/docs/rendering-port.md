# tfx.020 rendering and frame-limit ports

Step 10 is complete. Gouraud/texture ports are committed as `fb0137f`. Evidence and scripts are under `tmp/step10/` and `tools/`.
The authoritative source is `src/TFXHD.s`.

## Baseline and scope

The step-9 slave rebuilt unchanged and reproduced 73 publications in the strict
040 NOMMU `[2,252)` vblank window (`baseline/`). The retained instruction profile
is the pre-patch trace. All emulator performance results are A/B comparisons;
Apollo 1240 speed remains a hardware check.

The existing new-rendering path already allocates a 16-byte-aligned fast planar
buffer, changes screen/sprite pointers in `start_frame` at `$017f8`, copies planes
and sprite pixels back to chip in `do_swap_screen` at `$019fc`, and publishes via
`_SetPage` at `$4c474`. Chunky-to-planar is per fill scanline, not a second full-frame
conversion. Those components must not be duplicated. Step 8 already separated
CPU data from DMA data; the rendering port preserves that allocation.

The new patch list is selected only for 68040 without 68060. CUSTOM4 bit 2 retains
the original rendering. The Gouraud adapter translates the inline SP+4 stream and
A5 Y coordinate to the existing C-argument helper. `_TextureFill` `$4f9f8` already
has the required C arguments; `$55bec` supplies its texture pointer. `ScanFillDown`
`$6c4f2` has the existing helper's edge ABI, including returned A2/A3.

## Validation pitfalls

- `fills-test1` stopped at an undersized private fixture-area assertion.
- `fills-test2` set its final breakpoint to `$a`: the parser consumed vasm's `A:`
  address prefix. Its verified debugger was interrupted by PID; no game conclusion.
- `fills-test3` is **not valid equivalence evidence**. The test treated merged
  patch-list offset `$715fc` as a code-relative runtime address. The actual logbase
  word is data-hunk `$4930`; allocation headers invalidate simple concatenation.
  Comparing two untouched buffers can pass. The replacement fixture resolves the
  actual data hunk and adds independent pixel models of non-empty outputs.
- `original-scene` used CUSTOM4=30 and therefore enabled the FPS overlay; it cannot
  equal no-overlay screenshots. The correct comparison uses CUSTOM4=22.

The routine fixture only runs in private scratch code with interrupts masked. It
calls original entry trampolines and installed replacements, compares complete
64,000-byte bitplanes plus 32-byte leading/trailing guards, checks returned flat
edges, and saves full outputs for a separate pixel-by-pixel oracle. It is never
part of the production slave or timing window.

## Accepted fill evidence

`fills-test4` uses the correct data-hunk logbase and passes all 436 complete-buffer
comparisons (90 Gouraud, 90 texture, 256 flat), including returned flat edges.
Three full non-empty output pairs also match `render_oracle.py` independently;
958, 960 and 12 bytes actually change, respectively. The oracle writes individual
pixel bits and does not reuse the C2P permutation. Earlier tests are excluded.

Five `fills-scene` images equal `baseline-scene` byte for byte. The all-fill
candidate measures 72 publications twice, versus 73 before. Restoring only the
original flat entry before the measured window returns 73 (`original-flat-profile`).
The fixed flight does not hit Gouraud or texture; it cannot establish a speedup
for them. Keep original flat fill enabled on 040; the slower equivalent generic
port is not enabled. Its shared implementation remains available to plain TFX.

The normal and stippled CPU line replacements present before step 10
included the final endpoint, whereas the original blitter length excludes it.
The chip-buffer hardware differential results below validate the correction.
The `original-lines-scene` experiment restoring blitter entries with fast render
buffers is invalid for equivalence: the blitter cannot address fast RAM. Do not
use it as evidence for or against the line algorithm.

## Frame-limit adapters

The new 040 list ports C4 bit 5 (uncapped) and bit 6 (one-vblank minimum).
Bit 6 takes precedence when both are set, matching the integer build. `$1abfe`
is a complete `MOVEQ #2,D0` instruction, replaced with `MOVEQ #0/#1,D0`; it is not
an immediate word belonging to a comparison. `$1830/$1850` read delta time at
A4-$ba4. The model hook `$1ec38` preserves its original byte subtraction when time
advances; at zero it unwinds saved D7, FP2–FP4/FP7 and eight local bytes. Copying the
integer helper's epilogue would corrupt the stack. `$1fec4` uses the existing zoom
quotient clamp.

`options-test2` passes 41 installed-helper cases: 14 update-skip cases, 16 model
stack/register cases and 11 zoom values. The first `options-test` used an older
binary after the assembler rejected the FPU instruction under the default CPU;
that failure is excluded. The helper now explicitly selects 040 assembly only
for its FPU restore instruction; normal and CHIP_ONLY builds must both pass.
`options-uncapped-profile` reaches 73 publications with zero FPU exceptions.

The one-frame mode also reaches 73 publications with zero FPU exceptions and its
live limit opcode is `$7001`. Frame-limit adapters are committed as `94fb17c`.
They cannot raise throughput in this CPU-bound window; there is no speedup claim.

## Original rendering equivalence work

The original line comparison uses **chip** buffers for both calls, enables blitter
DMA, waits for the last plane's blit to finish, and compares all plane/guard bytes.
`lines-before` reproduces differences in 113/128 cases (64/64 normal lines).
The first endpoint fix removes all normal-line failures. Remaining stipple cases
show that the hardware starts at pattern bit zero and rotates left; the old CPU
code rotates right and also fails to duplicate the 8-bit pattern into both bytes.
The revised 040-only core corrects both. Shared 020/030/060 line cores retain their
original behavior; the 040 list is applied after the shared list so its line hooks
are not overwritten. A dedicated list pointer replaces the earlier PL_NEXT chain.

`lines-candidate2` passes 592 full guarded-buffer comparisons: normal lines,
all octants, zero length, screen boundaries and eight independent stipple patterns.
All five `lines-scene` frames (1, 10, 30, 45, 57) equal `original-clean-scene`
in both displayed bitplanes and decoded RGB; the PNG files also match. The
correction is committed as `e006c99`. This resolves the literal original-rendering
screenshot gate, rather than accepting the pre-existing pixel differences.

The narrow-box fixture (`boxes-before`) reproduces 60 failures, all width one.
The 040 wrapper now draws that column with the existing inclusive CPU line core;
other rectangles keep the shared fill. `boxes-final` passes 259 original-blitter
comparisons and an independent clipped-column pixel oracle. Committed `6ec951e`.
No other CPU's box behavior changes.

## Final measurements and state

All three final timing modes repeat **73 publications / 250 vblanks**, nominal
PAL 14.6 fps, with zero FPU exceptions. Their presentation/input events and final
images match within each pair. The fixed flight remains CPU-bound, so lowering
the two-vblank minimum does not change this measurement. This is no speed gain
against step 9 and is not an Apollo hardware fps claim.

- Default mode also repeats every captured game-hunk byte.
- Uncapped mode has a +1-vblank origin translation in all five known clocks and
  eight differing bytes in audio queue slot 7, code `$4d7c8..$4d7d1`. Queue count
  `$4d77c` is zero in both runs. Queue entries are ten bytes from `$4d782`; enqueue
  `$4d612..$4d628` writes all fields before increasing count, and insertion shifts
  only active entries. These bytes are inactive tail residue, not active audio.
- One-frame mode differs only by a -1-vblank translation of the five clocks.

The raw state comparisons remain false for the latter two modes. These explained
differences do not extend the step-2 waiver. The separate ordinary replay matrix is reported independently below.

The final normal and CHIP_ONLY builds pass. CHIP_ONLY is a build check, not a
separate performance configuration. Both FPSP binaries remain byte-identical to
the step-9 baseline. The independent pixel/scene fixtures never run in timing
windows or normal release code.

## Reproduction and next work

From the game directory, rebuild with `bash tools/build.sh`. The retained
exit checker is `python3 tools/check_step10.py`; it validates evidence under
`tmp/step10/` and reports raw-state results separately. To repeat the final
suite into a **new** directory, run:

```
python3 tools/step10_final_runs.py "$PWD/tmp/step10-recheck"
```

The driver owns one emulator/debugger at a time. It selects the retained private
step-9 backend for fixtures/profiling and the shared backend for ordinary replay.
The retained run used `step10_gate_runs.py` afterward for the four extra CPU/option
audits; those calls are now included in the final driver. Do not run suites in
parallel: the project harness has one runtime directory and debugger connection.
Fresh seeds are mandatory after changing a build. A deliberately reused baseline
seed executes the slave stored inside that HDF, not the host build copied into a
capture directory; baseline identity must follow seed provenance and live hooks.

Useful individual tools:

- `test_render_fills.py OUT`, with `SELECTED_ONLY=1` for the final two enabled fills;
  the all-three mode requires the retained all-fill candidate build.
- `test_render_lines.py OUT` and `test_render_boxes.py OUT` compare against actual
  original blitter routines in guarded chip buffers. `ALLOW_DIFFERENCES=1` is only
  for recording failing baseline evidence, never an exit-check waiver.
- `test_frame_options.py OUT` tests the installed uncapped helpers and stack ABI.
- `step10_scene.py OUT` uses fixed simulation time and resolved-latch input; set
  `SCENE_NOMMU=1`, and `CUSTOM4=22` for original rendering without an FPS overlay.
- `step10_profile.py OUT` records the strict fixed window. `CUSTOM4=18/50/82`
  selects default/uncapped/one-frame. `RESTORE_FILLS=normal` was an experiment only.
- `compare_render_frames.py LEFT RIGHT` compares all published bitplanes and RGB.

For individual private-backend calls, set
`FSUAE="$PWD/tmp/step9-emulator/fs-uae/fs-uae"`. No shared emulator changes,
new game data, or fixtures are part of the slave. Keep original inputs read-only.

Step 11 starts from `final/default-profile/profile.csv`, including chip accesses
and per-PC costs. Retained flat fill and the screen copy remain candidates to
measure. Do not run the old `report_profile.py` unchanged: its frame count, slave
symbol offsets and FPSP assertions are specific to step 5. Rebase reporting on
current assembler symbols before assigning costs. No MOVE16, cache-flush removal
or other step-11 tuning has been introduced here.

## Regression result

Two ordinary cold boots on each of 020, 030+68882, 040 and 060 match all four
checkpoint screenshots **and every captured game-hunk byte**. This is evidence for
these retained pairs, not a promise that the older clock-drift cases can never
recur. All 245 inspected 060 FPU sites equal step 9; the legacy 060 patch list and
other CPU rendering implementations are unchanged. Final CPU/combined-option
audits separately verify precedence and the original-rendering opt-out.

All four final CPU/combined-option audits pass: 040 CUSTOM4=114 uses the one-frame
limit plus zero-time safety helpers; CUSTOM4=118 retains original rendering with
those options; 030/060 CUSTOM4=114 retain their old limit and routines. The aggregate
`validation.json` passes. All finished source changes are committed individually.

C2P implementation: Gouraud uses `copy_linebuf_part` with `c2p_32pixels` and
`c2p_32pixels_masked`; texture uses transparency-aware `tfill_c2p`. These are paraj's
existing 32-pixel scanline routines in TFXHD.s. Flat fill is direct planar output;
presentation is a planar fast-to-chip copy, not a full-screen C2P conversion.
