# Internals

How each version loads, memory, and every slave patch. Offsets are into the named file's
first code hunk (its data starts at the file offset given) unless another hunk is named.

## Loading

All three slaves are JOTD's KickEmu slaves with `BOOTDOS`: WHDLoad boots the Kickstart image,
the slave's `_bootdos` makes the assigns and runs the game's program from `data/` through
`dos.library` `LoadSeg`, and quits with `TDREASON_OK` when it returns. `PRELOAD` holds the
files.

| | ECS | AGA | CD32 |
|---|---|---|---|
| KickEmu | `kick13.s` (`kick34005.A500`), `SETPATCH`, `BLACKSCREEN` | `kick31.s` (`kick40068.A1200`), `INITAGA` | `kick31.s`, `INITAGA`, `FORCEPAL`, `DEBUG` |
| Assigns | `gs_dsk1`-`gs_dsk4` | `gs_dsk1`-`gs_dsk4`, `ENV:` to `RAM:` | `CD0`, `Gunship_2000`, `ENV:` to `RAM:` |
| Runs | `Gunship 2000 Intro` (unless `CUSTOM1`), then `Gunship 2000` | `Gunship 2000` | `Gunship 2000` |
| Patches by | `_cb_dosLoadSeg` (name `gs...`) and `patch_main` on `Gunship 2000` | `_cb_dosLoadSeg`: `gs`, `gs2.run`, `Gunship 2000` | `fakepad.s` (lowlevel.library) |

`Gunship 2000` is the front end; it runs `gs` (the base and menus) and `gs2.run` (the
flight). The CD32 slave loads `lowlevel.library` and `nonvolatile.library` from disk
(`USE_DISK_LOWLEVEL_LIB`, `USE_DISK_NONVOLATILE_LIB`), saves the roster through
`nonvolatile.library` to the game drawer, and `fakepad.s` replaces lowlevel's
`ReadJoyPort` (the pad from a joystick and the function keys) and `GetLanguageSelection`
(WHDLoad's language; `CUSTOM4` forces English).

## Memory

| | BaseMem (`CHIPMEMSIZE`) | ExpMem (`FASTMEMSIZE`) | Flags | `slv_Version` |
|---|---|---|---|---|
| ECS | $100000 | $100000 | `NoError`, `Examine`, `EmulTrap` | 16 |
| AGA | $100000 | $100000 | `NoError`, `Examine`, `ClearMem`; stack 13000 | 16 |
| CD32 | $1ff000 | 0 | `NoError`, `Examine` | 16 |

The quit key is $5d (numeric `*`); the ReadMe says F10 and gives the older memory figures.

## Slave patches

ECS, `data/Gunship 2000` (code hunk $800 bytes at file offset $28), by `patch_main`:

| Offset | Original | Patch | Why |
|---|---|---|---|
| $66c | `movea.l $2a,a6; jsr ...` (the install check) | `jmp move1d0rts` (`moveq #1,d0; rts`) | the check passes |
| $78e | `suba.l a1,a1; movea.l $2a,a0` (the second check) | likewise | likewise |

ECS, `data/gs`: `_cb_dosLoadSeg` searches the first 500 bytes of each hunk for
`$43edfffa12d866fc` (`lea -6(a5),a1; move.b (a0)+,(a1)+; bne.s`), the manual-protection
code entry. It is in hunk 98 (code, $cbc bytes at file offset $2a730), at $d0:

| Offset | Patch | Why |
|---|---|---|
| $d0 | `jsr $c0.w`, a `jmp _crackit_1` there | writes the right code for the asked word into the entry buffer (`compute_correct_code`), then the `lea` it replaced |
| $55c | `jsr $de.w`, a `jmp _crackit_2` there | the same for the second prompt (`lea -42(a5),a1`) |

AGA, `_cb_dosLoadSeg` first clears long 0 (`clr.l 0`) on every `LoadSeg`, then by name:

| File, offset | Original | Patch | Why |
|---|---|---|---|
| `gs` (code $5ee0 at file $228), $4970 | `move.l -4(a5),d0` (the code entered) | `jsr $d0.w`, a `jmp crack` there | once five digits are in, replaces the entry with the right code (protection removed) |
| `gs2.run` (code $19014 at file $30), $12780 | `jsr -270(a6)` (`WaitTOF` before `LoadView`) | two `nop` | |
| `gs2.run`, $12834 | `lea $dff000,a5` | `jsr set_copperlist` | writes the copper end `$fffffffe` to address 0 (the game's `COPJMP2` to 0), sets `COP1LC` from the game's copper-list variable |
| `Gunship 2000` (code $6a4 at file $28), $122 | the `Install Gunship 2000` test | skip to $13e | |
| `Gunship 2000`, $16c | an `OpenLibrary` and the test after it | skip to $1f4 | |

`_patch_exe` tells the AGA `Gunship 2000` by `$2c79` at $512; with `$2c79` at $66c (the ECS
layout) it applies the ECS install-check patches instead.

CD32: `_patch_gs2000` returns at once, so its patch list (`$154` two `nop`, `$168` `bra`) is
not applied; the game runs unpatched apart from `fakepad.s`.

## Flight (AGA `gs2.run`)

`gs2.run` has five hunks: code $19014 (offsets below), data $d578 (D+), BSS $e1c4 (B+), all
three any-memory, and the chip hunks data $2c2c and BSS $18. On the a1200-030 the first three
load into ExpMem. `tools/gs2.py` finds them in a running game and reads the clocks below.

### Frame loop

| Offset | What |
|---|---|
| $1c | `jsr $13d48`: moves the stack onto the work area ("Memory in flight") |
| $28 | takes the 64 Hz ticks B+$c680 and clears them; dt B+$c67e = ticks × 32768 / 15, 32767 from 15 ticks up (`divs` overflow) |
| $4a | B+$c698 = the time acceleration B+$c696 - 1: the frame's work from $52 repeats that many times (`dbf` at $2c2) |
| $78 | mission clock: B+$c684 += dt × 15360 / 32768 (1024 per tick, 65536 a second); on the carry B+$c682 (seconds) + 1 and `bsr $308`, the once-a-second work |
| $2a8-$2b4 | per-frame phases: B+$c68b flips, B+$c68c counts 0-3 |
| $2c6-$2d0 | **the frame cap**: spins until B+$c680 is 6 ticks |
| $2d2, $2e6 | `jsr $9e78`, `jsr $9614` (not yet identified) |
| $2ec | `jsr $129c4`, present: rotates the three screens (B+$b8e4/$b8e8/$b8ec; shown B+$b8dc) and writes `COP1LC` from the chip BSS |
| $2fe | B+$c68a flips (a blink phase, read at $1c7c) |

The ticks come from a CIA-B timer server (code $133b2; the latch is 11084 E-clocks, 64.0 Hz
on PAL, 64.6 on NTSC) that adds 1 to B+$c680 unless B+$c738 is set (pause). The VBL server
(code $133f4) counts fields in B+$b8fc (code $608).

So the step is variable and in real time: every frame advances the simulation by the ticks
since the last, in 64ths of a second, between 6 (the cap: at most 10.67 frames a second) and
15 (below 4.27 frames a second the game slows down). dt has 91 readers, mostly
`muls.w B+$c67e`. The truncation in dt costs the mission clock 1/65536 s a frame (32 in 32 frames, measured).
What runs per frame rather than per dt: the phases B+$c68a, B+$c68b and B+$c68c (instrument
blink, alternate-frame work) and everything the loop does once a frame.

### Rendering

The view is three interleaved 320×200 4-plane screens (32000 bytes each, rows of 160 bytes),
drawn by the blitter one span at a time:

| Offset | What |
|---|---|
| $fab6 | polygon span filler: per scanline one blit, B (the colour pattern, D+$1ea0/D+$23a0 the edge masks) and C to D, minterm $ca, 4 rows (the planes); waits for the blitter before each |
| $dda0 | general blit (`btst #14` waits) |
| $fd3c | lines |
| $13832 | rectangle clear |
| $109ba | object transform: a 3×3 word matrix copied in, then CPU maths |
| $e3de | a list walk ahead of the drawing (to identify) |

In the measured flights $fab6 made 650-760 blits a frame, each about 330 CPU cycles of setup.
The chip bus still had 37-40% free slots: the blitter time is latency (setup, start, wait),
not bandwidth.

### Memory in flight

The front end hands `gs2.run` its work area (code $18f62: a0 base, d0 size, a1 a table of
blocks). On the a1200-030 it is in chip RAM: the heap pointer D+$2c3e and end D+$2c42 ran to
$a2580, about 600 KB, with the three screens in it, and the blocks D+$922a and D+$9232 were
also in chip (D+$8d6a in fast). Which allocations the blitter or the display needs, and
which only the CPU touches, is not yet sorted out. ExpMem had 84 KB free.

At $13d48 the flight saves its process stack pointer (D+$2dfc) and moves the stack onto the
first 2000 bytes of the heap (D+$2c3e moves up by 2000). The process stack (13000 bytes,
`slv_` stack size) is in ExpMem; the flight's stack is chip.
