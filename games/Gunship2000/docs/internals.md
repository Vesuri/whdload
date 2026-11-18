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
| Patches by | `_cb_dosLoadSeg` (`gs...`, `gs2.run`) and `patch_main` on `Gunship 2000` | `_cb_dosLoadSeg`: `gs`, `gs2.run`, `Gunship 2000` | `_cb_dosLoadSeg` (4.0b: `gs2.run`, VERIFY `gs`), `fakepad.s` (lowlevel.library) |

`Gunship 2000` is the front end; it runs `gs` (the base and menus) and `gs2.run` (the
flight). The CD32 slave loads `lowlevel.library` and `nonvolatile.library` from disk
(`USE_DISK_LOWLEVEL_LIB`, `USE_DISK_NONVOLATILE_LIB`), saves the roster through
`nonvolatile.library` to the game drawer, and `fakepad.s` replaces lowlevel's
`ReadJoyPort` (the pad from a joystick and the function keys) and `GetLanguageSelection`
(WHDLoad's language; `CUSTOM4` forces English).

## Memory

| | BaseMem (`CHIPMEMSIZE`) | ExpMem (`FASTMEMSIZE`) | Flags | `slv_Version` |
|---|---|---|---|---|
| ECS | $100000 | $100000 | `NoError`, `Examine`, `EmulTrap` | 17 (4.0b, JOTD's 16: `slv_config`, `C1:B:Skip introduction;C2:B:Enhanced framerate`) |
| AGA | $100000 | $130000 (JOTD's $100000) | `NoError`, `Examine`, `ClearMem`; stack 13000 | 17 (4.0b: `slv_config`, `C2:B:Enhanced framerate`) |
| CD32 | $1ff000 | $130000 (4.0b; JOTD's 0) | `NoError`, `Examine` | 17 (4.0b: `slv_config`, `C2:B:Enhanced framerate`) |

ExpMem also holds the Kickstart (KickEmu's `KICKSIZE` before `FASTMEMSIZE`). With JOTD's
CD32 setup all of the game's memory was chip; the 4.0b CD32 slave's ExpMem gives the OS
fast memory, and the flight's code, data and BSS (any-memory hunks) load there.

The quit key is $5d (numeric `*`), as the ReadMe says.

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

All three 4.0b slaves set KickEmu's `CACHECHIP` where JOTD's set `CACHE`: the instruction
cache for all memory, BaseMem write-through. `CACHE` marks BaseMem non-cacheable, and without
WHDLoad's MMU (the default on a 68030) one non-cacheable area switches both caches off; on the
CD32 version's 68020 (all its memory BaseMem) the instruction cache was off too (CACR 0).

### The flight's patches in all three (`src/flight.s`, 4.0b)

The three `gs2.run` files are builds of one source; the flight's patches are one file,
`src/flight.s`, and each slave defines where its build has each place (`G_*` code, `B_*`
BSS, `D_*` data offsets, and the `gs` hunks), found by aligning the code hunks with the
relocations masked; `tools/gs2.py` has the harness's subset. The offsets below are the AGA
build's. The slave calls `flight_gs2` when `gs2.run` is loaded, by the name after any device,
assign or drawer (the ECS one has one), and in VERIFY builds `flight_gs` for `gs`. The routines
address the hunks $8000 on, so the same code runs on the ECS version's 68000.

| | ECS | AGA | CD32 |
|---|---|---|---|
| code, data, BSS | $19108, $d71c, $e114 | $19014, $d578, $e1c4 | $19750, $d858, $e200 |
| e.g. present, dt, the screen drawn | $125ca, B+$c5cc, B+$b8d4 | $129c4, B+$c67e, B+$b8dc | $12968, B+$c6ba, B+$b8dc |
| `gs` hunks: `random()`, `time()`, the mission setup | 0 $3268, 96, 21 | 0 $35c4, 97, 22 | 0 $330c, 96, 21 |

The fast stack and model data, every build:

| Offset | Original | Patch | Why |
|---|---|---|---|
| $13d52 (AGA, CD32) | `movea.l D+$2c3e,sp; lea 2000(sp),sp; move.l sp,D+$2c3e` | `jsr fast_stack` (D+$2c3e += 2000), then a branch to $13d62 | the flight stays on its process stack in ExpMem instead of moving it onto its chip work area ("Memory in flight"); the 2000 bytes are still taken, so the heap is laid out as before |
| ECS $13ac2 | the same, for the supervisor stack: the ECS flight takes the machine over (a `trap`, SR $2700, its own vectors) | `jsr fast_super_stack` | the supervisor stack in 2000 bytes of fast memory allocated when `gs2.run` loads; no memory: the work area, as before |
| $181c2 | `movea.l D+$922a,a0` (the model data, before $18b8c relocates it) | `jsr fast_models` | copies the block (up to D+$9232, at most $21000 bytes) into a fast buffer allocated when `gs2.run` first loads (the ECS flight has the OS switched off) and points D+$922a at it; the transform and object code read it there ("Memory in flight"). Larger or no memory: the chip block |

The VERIFY build pins the mission for measurements (`development.md`, "Profiling in flight"):

| File, offset | Original | Patch | Why |
|---|---|---|---|
| `gs` hunk 97, $aa | `move.l -4(a5),d0` (the `time()` result) | `moveq #1,d0; nop` | `random()` ($5c; the generator is hunk 0 $35c4, seed × 3677 + 3) seeds from the clock on its first call |
| `gs` hunk 22, $2a40 | `moveq #0,d0; move.l d0,d5; move.w d5,-18(a5)` | `jsr reseed_mission`, `nop` | the mission setup reseeds: the office animations call `random()` a timing-dependent number of times, and the setup rolls the time of day here (H78+$f6 = `random(5)` = 0, H78+$f7 = `random(100)` > 40) |
| `gs2.run`, $183e8 | `move.w VHPOSR,B+$b8fe` | `jsr seed_flight` | the flight's own generator ($12aa0) seeds from the beam position |

With `CUSTOM2=1` the slaves also apply `pl_gs2_fps` to `gs2.run` (4.0b, "Enhanced
framerate"): a frame takes at least one field instead of 6 ticks, and the simulation keeps its
rate ("Frame loop"). The slave keeps the fields since the last frame (`fps_fields`), the
remainders, and k, the 6-tick periods of game time the current step completes (`fps_k`):

| Offset | Original | Patch | Why |
|---|---|---|---|
| $28 | dt from the ticks B+$c680 | `jsr fps_dt`, branch to $4a | dt = fields × 2097152/750 (PAL) or /900 (NTSC), the remainder carried; more than 11 (PAL) or 14 fields: 32767, the game's 15-tick clamp |
| $78 | the clock's add, `dt × 15360` | `jsr fps_clock`, branch to $86 | dt × 15 / 32 with the remainder carried; also k for this step |
| $2a8 | B+$c68b flips, B+$c68c counts, per step | `jsr fps_phase`, branch to $2bc | k times |
| $2c6 | the cap: until B+$c680 is 6 | `jsr fps_wait`, branch to $2d2 | until a field since the last frame |
| $2fe | B+$c68a flips (the blink), per frame | `jsr fps_blink` | once per 6 ticks of real time |
| $608 | `addq.w #1,B+$b8fc` (the VBL client) | `jsr fps_vbl` | also counts the field, unless paused (B+$c738, which stops the ticks too) |
| $18430 | `move.w #15,B+$c680` (flight setup) | `jsr fps_start`, `nop` | the first frame's dt is 32767 as before; PAL or NTSC from the highest line of a field |
| $7716 | `bsr $7c04; bsr $7dda` | `jsr fps_speed`, `nop` | the speed moves toward its target by 1/8 (1/16 down) of the gap or 1 a call, without dt: $7c04 runs k times |
| $7950 | `asr.w #2,d1; add.w d1,B+$2cc` | `jsr fps_climb`, `nop` | the climb rate moves a quarter of the way to B+$2ca a call: k times |
| $1212, $1268 | `clr.w B+6` (keys `=` and `-`) | `jsr fps_collective` | the collective steps 1 a call while the key is held: only on steps with k > 0 |
| 84 sites | `muls.w B+$c67e,Dn; add.l Dn,Dn; swap Dn` | `jsr fps_dtm<n>; nop; swap Dn` | found by `fps_dither_sites`: x × dt is truncated every frame; the product gets a uniform fraction (a golden-ratio sequence) before the swap, so it is right on average, and 0 stays 0 |

The 4.0b builds also replace the renderer's blitter routines ("Rendering"), with the same
pixels (`tools/screens.py`), where they are faster (`open-work.md`, "P8"):

| | ECS | AGA | CD32 |
|---|---|---|---|
| rectangles ($13832) | no (the ECS build queues its rectangle blits) | every CPU | every CPU |
| spans ($fab6) | 68030+ | 68030+ | 68030+ |
| lines ($fd3c) | 68020+ (slower on the 68000) | every CPU | 68030+ (no faster on the 68020) |


| Offset | Original | Patch | Why |
|---|---|---|---|
| $13832 | a D-only blit a plane through $dda0 | `jmp cf_rect` | the rectangle by CPU long writes; leaves the registers, the blitter registers and the blit list at B+$b5b8 as the blits did (the CD32 build runs the list again after some rectangles, code $dd4a there) |
| $fab6 (68030 or later, by `_attnflags`) | a blit a scanline span | `jmp cf_fill` | the spans by CPU writes, the edge words read and masked, longs between; the B rows as the blitter's pointer would give them. On the 68020/14 the blits are faster (with the CPU rectangles, CUSTOM2=1: 12.33/11.67 fps against 12.00/10.67), so it keeps them |
| $fd3c | a line blit a plane | `jmp cl_line` | the blitter's line mode by the CPU: the game's octant and error terms, the error's sign taken before each step, the pixels of one word of a row written together; leaves the registers and the blitter registers as the last plane's blit did. Faster on both CPUs |

All three wait for the blitter first, so the game's own blits (the band, the panel) still come before.

The VERIFY build reads `CUSTOM3` as the least fields a frame takes (`fps_wait`), for the
coupling test (`development.md`).

The ECS slave's `_cb_dosLoadSeg` keeps JOTD's protection search in every `gs...` file.

`_patch_exe` tells the AGA `Gunship 2000` by `$2c79` at $512; with `$2c79` at $66c (the ECS
layout) it applies the ECS install-check patches instead.

CD32: `_patch_gs2000` returns at once, so its patch list (`$154` two `nop`, `$168` `bra`) is
not applied; apart from `fakepad.s` and the flight's patches the game runs unpatched.

## Flight (AGA `gs2.run`; the other builds by the table above)

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

Per step, without dt (frame-coupled at any other rate than the cap's): the speed's and the
climb rate's approach to their targets (code $7c04, $7950), the keyboard collective (+1 a
step, $1212), and the phases. Held keys call their routine from the table at code $7d2 (by key
code) once a step (code $768). The cyclic is real time: the stick emulation (code $13994, a
VBL client) ramps the deflection per field, and code $13cc reads it into the rate commands
B+$c6b2 (roll) and B+$c6b6 (pitch).

So the step is variable and in real time: every frame advances the simulation by the ticks
since the last, in 64ths of a second, between 6 (the cap: at most 10.67 frames a second) and
15 (below 4.27 frames a second the game slows down). dt has 91 readers, mostly
`muls.w B+$c67e`. The truncation in dt costs the mission clock 1/65536 s a frame (32 in 32 frames, measured).
What runs per frame rather than per dt: the phases B+$c68a, B+$c68b and B+$c68c (instrument
blink, alternate-frame work) and everything the loop does once a frame.

### Rendering

The view is three interleaved 320×200 4-plane screens (32000 bytes each, rows of 160 bytes).
The game draws it with the blitter; the 4.0b slave fills with the CPU ("Slave patches"). A
flight frame in the views measured: the horizon (code $db42: one-colour rectangles above and
below it by $13832, the band between by a line and area-fill blits through $dda0), then
polygons by $fab6 with lines by $fd3c between them, then a few masked blits (code $12c60).

| Offset | What |
|---|---|
| $fab6 | polygon span filler: per scanline one blit, B (the colour pattern) and C to D, minterm $ca, 4 rows (the planes); waits for the blitter before each |
| $dda0 | runs a blit list from B+$b5b8 (`btst #14` waits first) |
| $fd3c | lines: one line blit a plane, minterm $ca, B the colour bit; the colour through the table the long at code $fcf8 points to |
| $b9aa, $ba80 | the cockpit view's panel: blit lists (B+$3ce with sources from B+$3c6 and masks from B+$3ca; B+$2ee with addresses), copies ($09f0) or cookie cuts ($0fca), unshifted, ascending |
| $13832 | one-colour rectangle: a D-only blit a plane (BLTCON0 $0100 or $01ff) through $dda0 |
| $109ba | object transform: a 3×3 word matrix copied in, then CPU maths |
| $e3de | a list walk ahead of the drawing (to identify) |

$fab6: D0.w indexes the pattern table at B+$108c (its first word the count, in bytes). Below
the count an entry is a pattern, with A $ffff; from it, the address of a long of two A words
(stipples: the even lines' word, then the odd lines'), then the pattern. A pattern is two
rows of 160 bytes, each plane's 40 bytes one word repeated. The edge tables by x (longs):
D+$1ea0 the first word's mask and byte offset, D+$23a0 the end byte and the last word's
mask; a span with end <= start is skipped. Even screen lines (from the shown screen B+$b8dc,
bit 5 of the offset) set B to the pattern; odd ones take the B pointer the last blit left,
160 bytes on, so after an even line without a span, one row further. With code $fab2 not
negative it draws one span from $fab2/$fab4.

In the measured flights $fab6 made 650-760 blits a frame, each about 330 CPU cycles of setup.
The chip bus still had 37-40% free slots: the blitter time is latency (setup, start, wait),
not bandwidth. With the CPU fills (CUSTOM2=1, the 68030) the chip RAM accesses are the limit:
in fs-uae a CPU long write to chip costs about 0.6 µs, a read about 1 µs.

### Memory in flight

The front end hands `gs2.run` its work area (code $18f62: a0 base, d0 size, a1 a table of
blocks). On the a1200-030 it is in chip RAM: the heap pointer D+$2c3e and end D+$2c42 ran to
$a2580, about 600 KB, with the three screens in it, and the blocks D+$922a and D+$9232 were
also in chip (D+$8d6a in fast). ExpMem had 84 KB free.

D+$922a is the model data: a file of offsets that $18b8c turns into addresses (the
pointers D+$9222, D+$9226, D+$18e4-$18f0 and code $11928, and the tables in the block),
read by the transform ($109ba) and the object code ($e3de, $1060e, $112e2, $d5c6, $10754).
The 4.0b slave moves it into fast memory; the checked views draw the same frames with it
there, so the blitter does not read it in those. D+$9232 is copied to a screen at code
$a5a2. The heap ($13084 a block, $130a6 a cleared one; 21 calls) holds the three screens and
the blitter's images (code $12f34 reads an image's header), and stays in chip.

At $13d48 the flight saves its process stack pointer (D+$2dfc) and moves the stack onto the
first 2000 bytes of the heap (D+$2c3e moves up by 2000); the exit at $13e6a restores it.
The process stack (13000 bytes, `STACKSIZE`) is in ExpMem, about 220 bytes of it used at
that point. The 4.0b slave keeps the flight there (`Slave patches`); on the chip stack,
stack and call instructions took 9-11% of the 68030's time.
