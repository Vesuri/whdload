# In-flight profile for the 20 fps plan (2026-10-21)

Build: production e0cd1fe7 (`tmp/build/release/TFX.Slave` == `tmp/opt20/delta-eight-verified.slave`).
Run: `tmp/prof20/current` — strict 040 NOMMU observer (`opt20-project-emulator`), tfx.020,
CUSTOM4=18, action flight tape, fresh seed, fields [2,2002). Log `tmp/prof20/current.log`.

    FSUAE=$PWD/tmp/opt20-project-emulator/fs-uae/fs-uae END_FIELD=2002 \
      python3 tools/opt20_profile.py $PWD/tmp/prof20/current
    python3 tools/prof20_analyze.py tmp/prof20/current tmp/opt20/delta-eight-verified.lst
    python3 tools/prof20_cost040.py tmp/prof20/current tmp/opt20/delta-eight-verified.lst
    python3 tools/prof20_annotate.py tmp/prof20/current game 0x6c4f2 0x6cc88 0.05

Result: 608 publications / 2,000 fields = 15.2 nominal fps (balanced-eight-on: 607).
Intervals: 13 x 2 fields, 406 x 3, 189 x 4. Zero FPSP entries, zero cache flushes;
exceptions are only level 2/3/4 interrupts. No busy-wait: the CPU is 100% busy, so
throughput = 40 MHz / cycles per frame. 2,659,219 emulated cycles and 826,629
instructions per frame. 20 fps = 800/2,000 = 2.0 M cycles/frame: remove 24.8%.

## The emulator's 040 timing is an instruction counter

Per-PC charges in this profile (cycles per execution):

| Instruction | Emulator | MC68040 (UM, cache hit) |
|---|---:|---:|
| almost everything (move, cmpm, bfins mem, muls.l, divsl.l, fdiv, fmove) | 2.84 (pure padding) | 1-2 simple; bfins mem ~10; muls.l 20; divs.l 44; fdiv ~38; fmove fp->int ~8 |
| muls.w | 20 | 16 |
| divs.w | 48 | 27 |
| chip RAM longword write | ~31 | unknown on Apollo (calibrate) |

Consequences:
- Emulator A/B ranks candidates by instruction count, with MULS.W/DIVS.W/chip penalties.
- FPU, MULS.L, DIVS.L and memory bitfield instructions are ~10x too cheap. Any change
  that trades integer DIV/MUL for FPU looks like a gain that hardware may not deliver.
- The accepted native projection (275fc83f) replaces 2 x DIVS.W (emu 96, 040 ~54 cycles)
  with 2 x (fmove.l + fdiv.w + fmove.l) (emu 8.5, 040 ~100+). Likely slower on the Apollo.
- The BFEXTU edge change (3fafdb93) trades 2 simple instructions for one 3-cycle BFEXTU:
  neutral on hardware at best.

`prof20_cost040.py` re-weights each executed PC with an approximate 040 table plus
chip penalties (W=20, R=24 cycles). Estimate: 2.07 M cycles/frame (19.4 fps if all
cache hits — real hardware will be slower; calibrate on the Apollo). Class shares
(est / emu): simple 41.8/67.7, branch 20.0/17.1, mul 11.7/8.5, FPU 8.4/1.4,
bitfield 7.3/2.4, movem 4.8/1.9, chip 3.4/-, div 2.5/0.8.

## Where the time goes (self cost; emu % / est-040 %)

| Routine | emu | est | per frame | notes |
|---|---:|---:|---|---|
| ScanFillDown `$6c4f2` | 16.9 | 16.2 | 849 calls, 4,343 lines, 3,494 spans | ~24 instr per-scanline setup; 2,794 narrow spans go to PlotColour tables; 508 wide spans run 8-plane BFINS pairs |
| _MaskSprite `$4e23c` | 11.8 | 8.2 | 17 calls, 82 plane passes, 5,285 words | CPU cookie-cut (minterm $CA). 19 instr/word/plane: mask re-read and re-shifted for every plane, first/last-word tests inside inner loop, misaligned long RMW. Callers are cockpit instrument code ($fc7c x10, $f602, $1042a, $10ecc, $117a6, $15f4e) |
| copy_changed_blocks (slave `$23f2`) | 9.1 | 9.2 | 7,987 units compared, 1,533 changed (19%) | 6 instr per unchanged 8 bytes; 3,066 chip longs |
| DoRotPt0 `$57a9c` | 9.0 | 8.3 | 1,106 two-component delta points (6 MULS.W each) + ~200 others | dispatch per point via jump table |
| project_fpu_040 (slave `$8002`) | 5.8 | 11.5 | 1,432 points (1,360 FDIV pairs) | see bias above |
| Polygon + bounds/backface `$60bfc` | 5.8 | 4.6 | 510 polys (~4.3 verts), 319 drawn | 160 off-screen, 33 back-facing |
| MakeScanTable + GenLeft + GenRight | 5.9 | 5.0 | 319 tables | vertex list doubled by copy loop, separate L/R tables |
| PlotColour `$6a4b8` | 3.0 | 3.0 | narrow-span colour tables | |
| cockpit overlay (loaded code `$41c26c4c`, from game:$3816) | 1.9 | 1.6 | 1 call, 601 longword columns x 8 planes | static RLE cockpit drawn every frame: 310 opaque + 291 masked columns (~30% of the screen, ~15% fully opaque) |
| terrain loop game:$38500 (DrawLevel area) | 1.8 | 1.3 | 256 cells | compiled C |
| draw_line_new / plot / draw_rect (slave) | 2.7 | 2.5 | | |
| _DrawSpriteImage / _DrawMonoImage / scaled bob | 3.5 | 2.7 | 57 / 40 calls | |
| RGB palette blend `$249a` | 1.35 | 2.0 | ~1 call; 256 x 3 MULS.L + DIVSL.L by 50 | recomputed each frame |
| integer sqrt `$4bdca` | 1.4 | 1.1 | 62 calls | |
| xTranslate `$5fff4` | 0.6 | 2.7 | 261 objects, 9 MULS.L each | emulator undercharges MULS.L |
| ConeCheck, clipline, ViewClip, cliptop | 2.4 | 2.0 | | |

Address-space split (emu): game 77.9%, slave 19.5%, other loaded code 2.5%, low-page
stubs 0.2%. Functional split (emu, approximate): raster fill and lines 23%, polygon
setup 13%, vertex transform/projection 19%, 2D cockpit sprites/overlay 17%, screen
copy 9.6%, palette 1.5%, remainder (game logic, terrain, HUD text, C helpers) ~17%.

Tools: `prof20_analyze.py` (exact-span attribution), `prof20_analyze_lib.py`,
`prof20_annotate.py` (per-PC listing with executions/frame), `prof20_cost040.py`.
Outputs: `tmp/prof20/current-analysis.json`, `current-cost040.json`.

## Step 0: method and fixtures (2026-10-21)

- Baseline frozen: `tmp/prof20/current` (608/2,000). Same-build run-to-run noise vs
  `opt20/balanced-eight-on` (607): +1 publication, -0.17% estimated-040 cycles/frame.
- Second fixture: `tools/views.tape.json` (FLIGHT_TAPE env, new in replay_flight.py and
  baseline_matrix.py; tape events with a `key` field are sent as `monitor key`). It keeps
  the right-bank input and adds F2/F3/F5/F6 view requests (4-swap holds) at swaps
  60/160/260/360 and F1 at 460. Profile `tmp/prof20/views`: 464/2,000 (11.6 fps),
  3.48 M emu cycles/frame. External views shift the cost to paraj's Gouraud/texture
  path: c2p_32pixels_masked 13.3%, gouraud_fill 4.4%, tfill_c2p 4.2%, texture_fill 4.1%,
  ScanFillDown 13.9%, copy 9.5%, DoRotPt0 7.4%, _MaskSprite only 1.4%.
      FLIGHT_TAPE=$PWD/tools/views.tape.json FSUAE=... END_FIELD=2002 \
        python3 tools/opt20_profile.py $PWD/tmp/prof20/views
- A/B report: `tools/prof20_ab.py CONTROL LST CANDIDATE LST [OUT.json]` checks inputs
  (emulator, tape, seed, executable, FPSP, window), prints publications, intervals,
  emulator and estimated-040 cycles/frame, FPSP entries, per-region changes and the
  plan verdict (estimated cost falls, publications do not fall).
- `opt20_balanced_profile.py` has PATCH_KIND=mask ($4e400, 6 bytes). Pitfall: the hunk
  image (`hs[0]['bytes']`) is UNRELOCATED. Restoring original bytes that contain an
  absolute address must use base+offset (the mask kind does; edge/project/exp bytes
  contain no absolutes). A first mask-off run with unrelocated bytes was stopped.
- Apollo calibration: `tools/calib040.s` (build: `$VASM -Fhunkexe -nosym -m68040`,
  binary `tmp/prof20/calib040`). Run in a Shell, no WHDLoad: `calib040 >RAM:calib.txt`.
  Times add, MULS.W/L, DIVS.W/L (with reload), both projection coordinate sequences,
  FADD/FMUL/FDIV/FSQRT, BFEXTU/BFINS, fast and chip streams, CMPM, and the original and
  step-2 mask inner loops, with interrupts disabled, fewest of three runs, as cycles at
  40 MHz from the E-clock. Functional check under FS-UAE (`RUN_CMD`/`EXTRA_FILES` added
  to the run): `tmp/prof20/calib-emulator.txt`. Stock FS-UAE timings there are not
  the profiler's model and are meaningless for hardware (e.g. FDIV 3.2 cycles). Waiting
  for the Apollo; then set CHIP_W/CHIP_R and the table in prof20_cost040.py.

## Step 2 result

mask-off/mask-on-2 (balanced, matched start): 606 -> 671 (+10.7%), emu -9.7%,
est-040 -7.2% cycles/frame. Tools: opt20_mask8_test.py (192 native twins),
check_opt20_mask_scene.py, opt20_scene.py MASK_OFF=1, opt20_gate.py mask check.
Frozen: tmp/prof20/mask-verified.{slave,lst,s}; mask-final-checks.json.
New hot list is in mask-on-2/profile.csv (prof20_analyze.py with mask-verified.lst).

## Step 1 (switch built, decision pending)

project_int_040 behind CUSTOM1. 275 twins + oracle pass (intproj-tests), gates
intproj-gate-*, scenes intproj-{scene,views}-c1{0,1} (images equal; audio/interrupt bytes
$4d72e-$4d850 differ), pair intproj-fpu/intproj-int-1: 671 -> 644, emu +4.2%, est -3.9%.
Seed pitfall: dh0.hdf bakes the WHDLoad arguments at enrolment (strings shows them);
never vary CUSTOM with TEST_SEED. check_opt20_mask_scene.py takes PATCH=start:len.

## Latest production profile (b99c3ca8, 2026-10-21)

Control of the step 9 pair: `tmp/sqrt9/sqrt-off` with `tmp/sqrt9/sqrt.lst` (746/2,000,
emulator 2.17 M, estimated 040 1.69 M cycles per frame). Top estimated-040 regions:
project_fpu_040 14.0%, sfd_span_040 9.3%, copy_changed_blocks 8.6%, rot_delta2_040 6.0%,
PlotColour 4.5%, mask_sprite8_040 3.9%, xTranslate 3.3%. Step 9's tail ceilings are in
the plan.

## Follow camera (F5) profile (b99c3ca8, 2026-10-21)

Tape `tools/follow.tape.json` (flight tape plus F5 at swap 25, held 4 swaps), output
`tmp/follow/follow` (+ `-analysis`, `-cost040`). 313/2,000 publications (7.8 fps) vs 746
in the cockpit; emulator 5.17 M, estimated 040 3.44 M cycles/frame (cockpit 1.69 M).
Gouraud path = 42.7% est (1.47 M): c2p_32pixels_masked 816k, gouraud_fill 452k,
copy_linebuf_part 74k, Gouraud scan tables/polygon 115k. Per frame: 126 Gouraud polygons,
2,462 rows, 25,171 pixels (10.2 px/row), 3,114 masked + 53 plain 32-pixel c2p calls.
The interpolation loop is ~5 instructions/pixel; the cost is a full 8-plane masked c2p
(32 pixels converted, 8 plane read-modify-writes) for every ~10-pixel row: ~53 est
cycles per Gouraud pixel.

Step 11 result (7b933812): follow camera 414/2,000, est-040 2.83 M; gouraud_fill_040 689k
+ gf_or 68k replace 1.34 M. Pairs and evidence in `tmp/gouraud/`.
