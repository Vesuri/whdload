# Original/development loader equivalence

Project status: Phases A–E are complete within the agreed scope, with steady A500 handling and natural-weather validation deferred by the user. Neither deferred gate is counted as passed. Phase F is stopped at the stock-A1200 throughput gate; release validation is incomplete.
See the [current handoff](open-work.md) for completed checks, open gates and resume priorities.

The Copylock D2 question is resolved: its different return value has no effect on the
supported game's successful startup path. No registration-tag compatibility patch is
needed. Matched original/development captures pass on 68000 and 68EC020 with `CUSTOM1=0`.
The normal development binary is unchanged by this work.

This establishes the tested startup, name-entry and Practice-state compatibility. It does
not establish identical OS execution, elapsed time, random trajectories or all gameplay
paths. The WHDLoad 20 KickEmu rebase has different allocation and timing behavior from the
original custom Kickstart patches. Performance comparisons must continue to use the same
development loader on both sides.

## Copylock register lifetime

The original replacement reads the legacy registration result through tag `$88000005`
(now named `WHDLTAG_Private3`), returns it in D2, and returns `$766cc95c` in D0. With the
installed WHDLoad 20 this tag is 2001. The development replacement only sets D0; its D2 is
256 at this call in both tested configurations.

The game calls the wrapper at `$8380` from `$895e`. On the successful path, `$8962` stores
D0 and `$8968` compares it with the expected key; the equal branch returns through `$89ac`.
The retry at `$8982` is not entered. After returning to `$11d58`, the game processes name
entry through `$13732` and `$13650`. Keyboard polling at `$581e`/`$5838` does not consume D2.
The text-window clear overwrites D2's low word at `$173b2` before using it. Subsequent
coordinate operations use that word; `$16c4c` sets the entire register with `MOVEQ #4,D2`.
Interrupt save/restore does not turn the old registration result into a game input.

Read-only checkpoints produced the same values on both CPUs:

| Game checkpoint | Original D2 | Development D2 | Meaning |
| --- | ---: | ---: | --- |
| `$8962` | 2001 | 256 | Copylock returned; both D0 values are `$766cc95c` |
| `$173b2` | 2001 | 256 | Immediately before the first low-word overwrite |
| `$173b6` | 18 | 18 | Window coordinate loaded |
| `$16c4c` | 64 | 64 | Font coordinate calculation complete |
| `$16c4e` | 4 | 4 | Whole-register overwrite complete |
| `$11d70` | 68 | 68 | Empty pilot name accepted |

The runtime comparison verifies the overwrite instructions, matching return key,
converged D2, clear protection-failure flag and matching stored/expected key. It does not
query an obsolete private registration tag in the development slave or hard-code 2001.

## Comparison boundaries and results

`make -C whdload original` still rebuilds the installed slave byte-identically.
`original-verify` builds a separate input-only reference: a position-independent launch
wrapper saves/restores the original launch registers and installs the same six input
hooks as the development VERIFY build. Its original Copylock replacement, allocator and
OS patches remain in use. `whdload/verify_input.s` supplies both builds' Enter, Practice
and Space responses. The original reference always takes this Practice route.

`tools/compare_loaders.py ORIGINAL_CAPTURE DEVELOPMENT_CAPTURE` checks:

- Matched CPU/memory/launch configuration and retained slave hashes.
- Correct PCs for every register checkpoint.
- All game bytes from `$4fc0` through the end of the code hunk at Copylock return, after
  name entry and at first pit motion, after undoing file relocations and accounting for
  only the Copylock jump and six named input hooks. Both loaders agree exactly.
- The complete main-state block `$a6e..$f95`. Explicit pointer fields must have identical
  allocation-relative values. Each stored code checksum must equal the sum of its actual
  relocated game bytes. The remaining differences are limited to the RNG seed at
  `a6+$62`, clock samples at `a6+$206/$218/$47e`, and the native frame delta at `a6+$21c`.
  Every other state byte agrees at name completion and first pit motion.
- Both 32,000-byte planar bitmaps. Name-entry images agree exactly. At pit departure,
  differences are confined to the `ET: mm:ss` digits (plane 1, rows 5–11, x=144–183).
  The 68000 pair differs in seven bytes in each bitmap; the 68020 pair differs in seven
  bytes in one bitmap and zero in the other. The comparator retains those counts and
  rejects pixels outside that clock area.
- Native performance-hook bytes remain intact with `CUSTOM1=0`, checked separately by
  `tools/check_disabled.py` against the supported executable.

The checksum differences follow from relocation; the game's checksum covers relocated
instruction operands and input-hook targets. The RNG uses the existing elapsed clock and
pilot name. These fields are reported explicitly, not presented as identical raw state.
The comparison does not force clock values, seed the RNG or modify game timing.

## Timing is not equivalent

Each run continues for 500 PAL fields from first ship motion at `$14764`. Read-only
breakpoints count normal driving presentations at `$bc7c`, excluding the pit animation.
Fields are zero-based. These are emulator observations for the tested configurations,
not an acceleration benchmark between different loaders.

| Configuration | Loader | First driving field | Complete driving intervals / fields |
| --- | --- | ---: | ---: |
| 68000, 512 KiB chip + 1,536 KiB slow | Original | 195 | 68 / 302 |
| Same | Development | 387 | 25 / 111 |
| 68EC020, 2 MiB chip + 4 MiB fast | Original | 144 | 116 / 355 |
| Same | Development | 139 | 118 / 359 |

In particular, the tested 68000 development loader takes substantially longer through the
pit/departure sequence. This is a real limitation of claiming end-to-end equivalence, not
a D2 failure or a reason to mask rendered-frame timing. The game instruction bytes match;
the OS implementations do not. Shared KickEmu also replaces graphics-library waits,
including WaitBlit, but these captures do not isolate the cause of the full timing gap.
A separate development run without the extra pre-departure checkpoints reproduces the
entire 500-field presentation sequence exactly (`equivalence-development-000-repeat`).
No change to those shared routines is made here. The 68020 pair is close but still not
field-identical. Different clock samples and seeds can produce different later trajectories.

The development loader also intentionally reserves an additional 128 KiB expansion arena
and supplies a valid empty DOS command line. The original passes its segment address as
both argument pointer and length; it happens not to select the game's `1` argument branch
in these runs. Recreating that invalid launch contract is not part of compatibility.
Physical-board tests are outside scope. Long races, opponents, views, collisions and
pit re-entry remain the separate `coverage` item.

## Reproduce

Run sequentially in the project; the capture server is shared by its runs. Keep all inputs,
slaves and capture bytes in ignored `tmp/`. The checkpoints do not write guest state.

```sh
source amiga/env.sh
make -C whdload original original-verify verify
export PROBE_OFFSETS='0x8962 0x173b2 0x173b6 0x16c4c 0x16c4e 0x11d70'
export WHD_ARGS='CUSTOM1=0 CUSTOM5=2 NoCache'
export ANCHOR=0x14764 FIELDS=500 SWAP_ONLY=1

tools/fixed_window.sh tmp/prof/equivalence-original-new tmp/build/Powerdrome-original-verify.slave
tools/fixed_window.sh tmp/prof/equivalence-development-new tmp/build/Powerdrome-verify.slave
python3 tools/compare_loaders.py tmp/prof/equivalence-original-new tmp/prof/equivalence-development-new
python3 tools/check_disabled.py tmp/prof/equivalence-development-new
```

For the accelerated pair, additionally export `AMIGA_MODEL=A1200 CPU=68EC020 CHIP_KB=2048
FAST_KB=4096 EXTRA_ARGS=--slow_memory=0` and `KICKSTART="$KICKSTART_A1200"`, then use new output
directories. Restore the normal build with `make -C whdload all`.

Evidence: `tmp/prof/equivalence-original-000-final`, `equivalence-development-000`,
`equivalence-original-020`, `equivalence-development-020`, and comparison summaries
`tmp/prof/equivalence-000.json` and `tmp/prof/equivalence-020.json`. Negative checks
confirmed that changing an unallowed main-state byte or a non-clock bitmap pixel makes
the comparator fail; restoring the capture passes again.
