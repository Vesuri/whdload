# Ferrari Formula One baseline validation

The release rebuild is suitable as the baseline for subsequent Ferrari work
within the SPS 0481 A500 configuration described below. Its normal game source
has no performance modifications. Natural demo differences are explained by the
pre-race random state; a separate controlled comparison reproduces the race
state and game image. This is a bounded rebuild-equivalence result, not a speed
benchmark or full-game compatibility certification.

## Inputs and reproducible build

Both archives, all 63 manifested extracted files and the authoritative source
pass SHA-256 verification. The pristine game drawer is never mounted writable.
Source SHA-256 remains
`88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761`.

| Artifact | Bytes | SHA-256 |
| --- | --- | --- |
| Shipped v1.01 | 5148 | `2896594727029771eef93e53069e39f9fa161f3214be733e62cb1dfd34322be9` |
| Imported configuration with DEBUG | 5696 | `4aebcefb34662cc2e1e671dae500c69843d7d0093049baa12a3d4990a2f8d26f` |
| Release rebuild | 5476 | `b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f` |
| Normal VERIFY build | 5476 | `b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f` |

Release and VERIFY were rebuilt again with identical hashes. VERIFY is currently
identical because the authoritative source contains no VERIFY instrumentation.
The input and RNG fixtures below have their own separate artifacts.

The exact imported source fails vasm because its BOOTDOS conditional is not
terminated. Only disposable build copies receive the closing ENDC. Shared Amiga
assigns and short LVO include names are mapped locally. Release additionally
comments out DEBUG, removing the development directory, banner and RMB wait.
Nothing in `src/FerrariFormulaOne_WHD.s` or the shared SDK is changed.

The shipped slave and rebuild are not byte-identical: the rebuild incorporates
the installed KickEmu/toolchain and is 328 bytes larger. `baseline-build.json`
records 48 resolved source/include dependencies, tool and ROM hashes, build
hashes and the installed emulator revision. The two existing SPS repairs and
CUSTOM1 behavior are checked in loaded memory, rather than inferred from a
successful build. Missing/invalid SLAVE selections are rejected before launch.

## Configuration and methods

- SPS 0481 `racemenu`, 199368 bytes; shipped v1.01 slave and release rebuild.
- A500/68000, 512 KiB chip, 1536 KiB slow, no Fast RAM, PAL.
- Host Kickstart 3.1; shared WHDLoad 20.0; KickEmu Kickstart 1.3 with its RTB.
- Native ARM FS-UAE, installed Barto revision recorded in the dependency manifest.
- CUSTOM1=0 and CUSTOM1=1 tested separately. No new performance option.
- Disposable DH0/DH1 per launch, isolated PID/port/socket, host inputs disabled.
- Warp for the long automatic no-input demo startup and correctness checks.
  No FPS, cycles-per-frame or real-hardware speed claim is made from these runs.

This clarifies the plan's initial warp instruction: these are correctness
captures, for which the shared playbook permits warp. Benchmark capture must
use the later calibrated timing workflow. Switching the emulator's warp setting
through the desktop could not be tested because computer control was not
approved for the emulator. That does not enter the state/pixel equality claim.

The debugger silently ignores writes to both guest memory and registers. A
readback check exposed this; those exploratory runs are explicitly invalidated.
Accepted controls execute in appended diagnostic slave code. They do not rely
on debugger writes, and they do not modify the normal slave artifacts.

## Loaded code comparison

`map_loaded.py` identifies 74 file-backed code segments totaling 73332 bytes at
the first race timing checkpoint. Mapping requires multiple unique signature
votes plus at least 98% agreement over non-relocated bytes with the original
file. It is deliberately partial; it does not claim every overlay is mapped.
The game loads at the same addresses in the shipped/rebuilt A500 runs, so game
relocations already agree. Only verified slave call operands are normalized.

For both CUSTOM1 values, every byte in those mapped ranges agrees after
normalizing the three differing slave pointers: the loader overlay hook,
`fixdelay`, and the SPS screen-pointer repair. Separately, the wrong-blit repair
is `$9240` at `race:+$6652`, the screen repair is installed at `race:+$0ab0`, and
the timing site at `race:+$589c` is patched only when CUSTOM1=0. The timing call's
slave pointer is normalized in comparisons that include that site.

The runtime library reached through Exec `$9c` identifies itself as
`graphics.library`; the shared NDK defines vector -270 as WaitTOF. Thus the
existing timing hook calls WaitTOF twice. Its relationship to full frames and
simulation cadence is still a step-2/step-4 question.

## Race state and image comparison

The read-only captures start at the first execution of `race:+$589c` and record
1, 10 and 100 subsequent visits. These are timing-hook visits, not yet a validated
frame or physics counter. Data is under `tmp/baseline/{shipped,release}-c{0,1}-valid`.

At the first checkpoint, the natural CUSTOM1=0 runs have different RNG state and
a different random start countdown (14 versus 35). The native title/menu loop
calls the RNG, and race setup derives that countdown from another RNG result.
Comparing visit 100 without controlling those values therefore compares
different progress. Aligning only the end of the countdown does not align the
remaining RNG state. Neither difference is classified as a renderer regression.

A local diagnostic copy of each slave adds the same one-shot control at the
first timing call. It restores the 120-byte RNG table/pointer region, the saved
pre-race random value and the countdown from the shipped reference. It then
executes the displaced instructions and the original timing fix. Both ordinary
slaves remain available and unmodified; this control is not evidence that the
uncontrolled demos are identical.

At visits 1, 10 and 100 in those controlled runs:

- The entire 42168-byte race region compares equal after normalization of its
  two verified slave call pointers.
- The 120-byte RNG state compares exactly.
- A deliberate changed byte inside race state is rejected by the comparator.
- At visit 100, all 256000 pixels in the displayed 640-by-400 game area compare
  exactly. Whole capture images differ only in the emulator's far-right strip,
  at x=752..753, outside the game area x=54..693.

The reference region includes race code, data and workspace. It is not yet a
semantic inventory of player/AI physics. Full state decoding, field-aligned
snapshots and completed-simulation-step comparisons remain in step 2. The
controlled sequence is CUSTOM1=0; CUSTOM1=1 has the separate loaded-code/gate and
functional checks. Results are recorded in `tmp/baseline/comparison.json`.

## Functional checks

Fresh diagnostic input copies run the same sequence on both slaves with both
CUSTOM1 values. They preserve normal game instructions and feed test values
through the native keyboard consumer and mouse sampling paths. The sequence
covers title, automatic demo/race entry, takeover, ESC pause/resume, acceleration
and sustained steering, K tow, race results, clicking Accept, the pit screen,
and the native F10 decoder/abort back to the AmigaDOS shell.

The click uses native mouse deltas and button sampling. It does not jump directly
to the pit or write a race-state flag. Test state stays in the fixture; all game
and save writes remain in the disposable mounted drawer. Inputs deliberately
include aggressive steering to exercise the off-course rendering path.

Evidence is retained in `tmp/baseline/{shipped,release}-c{0,1}-accepted-pit/`:
checkpoint screenshots, memory dumps, event/readback logs and a result manifest.
The final automated verifier requires every case to have completed and checks
title/pit/shell images, not just process exit. Earlier shorter captures that stop
at the tow message or results screen do not establish pit return.

These are emulator-level input-consumer and quit-dispatch checks. Physical host
keyboard/mouse delivery, end-to-end device IRQ delivery and a human play-test
were not performed. The F10 test enters the normal decoder with the encoded
F10 byte and observes a clean shell return; it is not a claim that a physical
F10 press was delivered. The imported DEBUG build is an assembly check only;
normal gameplay uses the release-equivalent build.

## Scope for the next step

The reproducible build, isolated runner and explicit equivalence evidence are
ready. Keep the same rebuilt loader on both sides of future performance A/Bs.
Do not use the larger diagnostic copies for acceptance FPS. No gameplay patch,
cache change, new time controller or renderer optimization has been introduced.

Irek, other CPUs/memory layouts, MMU/cache behavior, real hardware, full laps,
season save/load, timing correctness and performance remain unvalidated. The
next work is the step-2 overlay map, real presentation marker, deterministic
input tapes and semantic state inventory. Harness addresses are currently fixed
to the measured SPS/A500 layout and must not be reused blindly on another one.

## Step 2 correction to input-fixture evidence

The old input fixture saved d1/a0-a1 but restored d1-d2/a0-a1. Its generator
now saves the matching set, but the former captures do not establish register
preservation or reliable input equivalence. Its left-button acceleration comment
also described braking. The build and controlled demo comparisons are separate;
use the step-2 no-input demo evidence in `game.md` for performance preparation.
