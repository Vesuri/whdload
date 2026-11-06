# Validated frame counter (step 3)

Step 3 is complete for the target 040 and current default tfx.020 renderer.
`tools/count_frames.py` counts read-only debugger stops at the actual presentation
instruction and the game's vblank increment. `tools/check_frames.py` compares the
ordered events against a full 040 MMU instruction-dispatch trace and checks display
DMA independently. No slave or game instruction was changed.

## Markers and window

All addresses are offsets in tfx.020's code hunk, resolved from its live LoadSeg
chain on each boot:

- `$019fc`: swap request from PlayLevel, patched to the slave's do_swap_screen.
- `$4c474`: `move.l a0,$dff080` in SetPage: selects the published copper list.
- `$4d2de`: `addq.l #1,_vblank_clock`; the clock lives at `$4d884`.

The observer asserts the publisher and increment instruction bytes, verifies each
breakpoint against the freshly read PC, counts vblank hits itself, and logs every
publication with its copper pointer and vblank ordinal. A swap request can precede
publication by a vblank, so use the publication marker for frame timing.
ThreeScreenSwap ($3f99e) remains inappropriate for this default path.

The fixed validation window is `[2,18)` vblank increments after the first flight
swap breakpoint. This is a neutral-flight prefix of the step-2 route, before its
right-input action. There are no screenshots, additional field waits, or injected
inputs within this window. It deliberately excludes the initial partial field that
`monitor profile` does not record, and the tail after the checked window. Step 4
must choose and freeze its longer performance window separately; these counts are
validation evidence, not a baseline FPS claim.

## Reproduce

From the game directory, using a NEW result root (the sample uses `step3-new`):

```
python3 tools/count_frames.py --mode observe --output tmp/step3-new/observe --seed tmp/step3-new/seed
FSUAE="$PWD/tmp/step3-emulator/fs-uae/fs-uae" python3 tools/count_frames.py --mode trace --output tmp/step3-new/trace --seed tmp/step3-new/seed
python3 tools/check_frames.py tmp/step3-new/observe tmp/step3-new/trace --output tmp/step3-new/check.json
```

The observer uses the unchanged shared native emulator. Both runs use the same
pristine hardfile seed, rebuilt slave/FPSP and exact 040/40 MHz, MMU/FPU, 32 MB Z3
configuration. Capture is sequential and owns only its project emulator/debugger.
The checker also verifies slave/FPSP/tape/seed identities and trace SHA-256.

The private trace emulator is built once with:

```
tools/build_trace_emulator.sh "$FSUAE_CONFIGURED_BUILD"
```

Set FSUAE_CONFIGURED_BUILD to AmigaXDev's existing configured native
`fs-uae-arm/fs-uae` build directory. The script copies that build into ignored
`tmp/step3-emulator/`, applies `tools/040-dispatch-trace.patch`, and builds
there. It refuses to overwrite a pre-existing destination. Shared sources and the
installed emulator remain unchanged. This requires the original build's compiler
and dependency directories, as referenced by its configured Makefile.

Base provenance and hashes are retained in
`tmp/step3-emulator/provenance.json`; source revision is b70b1180b44ab25b97cd66466c70879897d8a362
with the installed native core/frequency/harness/register/input patches. The local
patch widens the profiling PC window and emits PC/register records immediately
before every dispatch in m68k_run_mmu040, including instructions that can throw
MMU/FPU exceptions. Records are emitted before execution so exception longjmps
cannot skip a destructor and silently omit those PCs. Other CPU loops are unchanged.

**All these dispatch records have zero cost.** They provide full instruction order
and field membership, not instruction timing. They must not be used for step 5 cost
percentages. The normal shared 040 emulator still produces no instruction records;
use the private build explicitly for trace validation. The generic window expansion
also covers Z3 addresses; no fake guest task/segment, cache disabling or memory patch
is involved.

## Evidence

Accepted evidence under `tmp/step3/`:

- `trace/`: full 20-field trace, 5,225,213 instruction records, 20 clock increments,
  and nine publications in the full capture. Entry/exit hunk dumps, config, hashes,
  exact slave/FPSP and debugger transcript are retained. Last image shows cockpit flight.
- `observe-counted/`: independent shared-emulator breakpoint capture.
- `check.json`, `check.csv`: matching ordered events and per-frame timestamps in the
  fixed window; **8 publications and 16 vblanks**.

| Window frame | Swap vblank | Publication vblank | Interval from previous publication |
|---|---:|---:|---:|
| 1 | 2 | 2 | — |
| 2 | 4 | 4 | 2 |
| 3 | 6 | 7 | 3 |
| 4 | 9 | 9 | 2 |
| 5 | 11 | 11 | 2 |
| 6 | 13 | 13 | 2 |
| 7 | 15 | 15 | 2 |
| 8 | 17 | 17 | 2 |

Each request has exactly one publication, and the two copper lists alternate.
For every publication in the window, the checker decodes all eight bitplane
pointers in the selected copper list from the trace's chip snapshot and verifies
that the next field's first bitplane DMA addresses match all eight. This verifies
actual display use, not merely calls to SetPage. Lists/addresses are fixture-local;
the checker discovers them from the captured A0 values rather than hard-coding them.

The initial game clock is 1564 in the trace run and 1565 in the observer runs.
Entry game-hunk differences are confined to the five known absolute timers from
step 2. Counter comparison uses increments from flight entry, not absolute boot
time, and requires exact event ordering, relative timestamps and buffer pointers.
No extra state differences are waived. The observer repeats the same event order
in both captured boots (the first capture requires offline recounting as below).

`observe/` is the exploratory raw-clock capture, not the accepted counter output.
One swap's raw RAM read returned the preceding clock value even after the vblank
increment breakpoint had passed. The stub reads memory banks directly; this is not
a cache-coherent guest load on the 040. Counting vblank breakpoint hits removes that
measurement error; raw clock reads remain recorded as diagnostics. The corrected
observer was rerun from a cold boot, producing `observe-counted/`.

The checker rejects deliberately removed publications, shifted timestamps and
wrong buffer pointers. Python compilation and shell syntax checks pass. No game
patch, CPU-cache setting or 060 behaviour changed.

## Next

Step 4 is complete; see `baseline-matrix.md` for the longer window, executable
markers and frequency-sensitive timing configuration. The installed 599152-byte
TFX.040 beta runs and supplies a measured row; the earlier handoff conflated it
with the damaged CD/1997 candidates. No intact native-040 build has been found.
Step 5 still needs a real cost observer: this validation-only dispatch trace does
not supply costs, and the MMU core ignores the requested frequency for timing.
