# Internals

## Loading

A direct slave (`ws_Version` 17, `WHDLF_NoError|WHDLF_ClearMem|WHDLF_EmulTrap`): 512 KB
base memory, no ExpMem, quit key F10, data from the RawDIC image `Disk.1`. It turns on the
instruction cache (`resload_SetCACR` 1, 1; the data cache stays as WHDLoad sets it), loads
the first `$B400` bytes of the image to `BASE` = `$57FE4` and identifies them by CRC16
(`$67E7`, SPS 3025; anything else `TDREASON_WRONGVER`). The image has 10 sectors a track
of which the game uses 9, so the slave packs the first nine tracks to 9 sectors each in
place. It sets CIA-A's LED bit, enables interrupts (`INTENA` `$C000`), patches the program
and jumps to `BASE+$10D4`.

Every later load goes through the game's track loader, which the slave replaces: the
parameter block at `BASE+$C98` holds the start track, the length in tracks and the
destination, and the slave reads `(track-2)*5120` bytes in from the image (tracks of 10
sectors).

## Slave patches

Offsets are into the program as loaded, from `BASE` (so the file offset into the packed
9-sector stream).

| Offset | Patch | By |
|---|---|---|
| `$A3E` | `rts`: drive motor off | Harry |
| `$A78` | `rts`: drive motor on | Harry |
| `$ADC` | `rts`: step to track 0 | Harry |
| `$B9C` | `rts`: read the protection track | Harry |
| `$669C` | jump to `Loader`, the image loader above | Harry |
| `$4B2` | `jsr CheckKeys`: stores the key at `$58C6B`, handshakes the keyboard with a 3-line delay, and quits on the quit key | Harry |
| `$51C` | `rts`: the game's CPU-timed keyboard delay | Harry |
| `$C0A` | skip to `$C6C`: the protection track check | StingRay |
| `$30C` | `jsr` a blitter wait before writing `BLTCON0` `$09F0` (not with CUSTOM1) | StingRay |
| `$6D4` | `jsr`: acknowledge the vertical blank interrupt twice, for 68040/060 and fast chipsets | StingRay |
| `$14BE` | jump to `EdgeStep` (2.0b): the edge scan converter's stepping (`$14BE`..`$165B`) without self-modification | Vesuri |
| `$47AC` | `jsr` a blitter wait before the pan step clears the field flag (2.0b, not with CUSTOM1): below | Vesuri |
| `$3C9A` | the PAL/NTSC test's mask `$1FFFF` written as `$1FF` (2.0b): [game time](#game-time) | Vesuri |
| module `$F2E` | `jsr SfxDmaWait` (2.0b), applied by `Loader` when it loads the sound module to `$20000` and the bytes match: the effect trigger's DMA-off wait, below | Vesuri |

CUSTOM1 (`C1:B:Disable Blitter Waits`) drops both blitter waits, `$30C` and `$47AC`.

`EdgeStep` keeps the step (+1 or -1) in d3 instead of writing `addq.w`/`subq.w #1,d1` into
the loops, and has a loop for each x-major mode instead of writing the `bcc.s` displacement.
It leaves registers, N, Z, V, C and memory as the game's code does; `tools/edgecheck.py`
(`make check`) compares the two under Unicorn's 68000 on random edges.

## Sound

The sound module is loaded to `$20000` (offsets below are into it). The game calls it from
wrappers that save every register and run with interrupts off (`SR` `$2700`): `$0` starts
the music, `$E9C` an effect, `$F62` is the vertical blank player.

- **The effect trigger** turns the channel's DMA off (`$EEC`), sets up the channel, waits
  (`move.w #512,d0; dbf d0,*` at `$F2E`) and sets the channel's flag (`$F36`); the next
  vertical blank player tick sets the effect's registers and turns DMA on (`$10B2`). That
  tick can come straight after the trigger returns, so the wait is the only time the DMA is
  sure to be off, and Paula restarts a channel only if it sees it off. The `dbf` is 5134
  cycles or more, 11.3 raster lines on the 68000 (more under blitter-nasty), under one line
  on the a1200-040 (beam read at entry and exit). 2.0b's `SfxDmaWait` waits for 13 changes
  of the `VHPOSR` line (12 lines or more) on every CPU; measured 13 lines on the a500 and
  the a1200-040.
- **The player's resume** (`$FE4`..`$1014`, at the end of an effect) turns DMA off, sets
  four registers and turns it on again, with no wait on any CPU; FS-UAE logs it as "DMA wait
  hack DISABLED" (under 60 instructions, so it emulates Paula not restarting) on the a500
  as on the a1200-040. It is the game's behaviour on a 68000 too, so it stays.
- The music's DMA-off and DMA-on (`$236`, `$2D2`) are on separate ticks; `$F3C` is a
  `dbf`-to-self nothing calls.

## Game time

The game's clock is the vertical blank. The VBL handler (`$570`) calls the game's tick
(`$2D36`) every field; unless one of the flags `$1876`, `$17C8`, `$17EC` or `$185F` is negative
(none was in any run below) it calls `$3768`, which adds `$9A` (154) to the byte at `$3765`
and, on each field that does not carry, counts the 24 object timers at `$179A`..`$17B1` down
to 1: 102 ticks in 256 fields, 19.9 a second on PAL. CIA-A timer B (`$3900`, 48.6 Hz, the
level 2 interrupt's `$82`) times only the music and the sound; CIA-B timer B is set but its
interrupt is not enabled. There is no boot benchmark and no task of its own.

**PAL and NTSC.** At start (`$3C7A`) the game reads `VPOSR`/`VHPOSR` as a long 100000 times
and keeps the highest `(long >> 8) & $1FFFF`, meaning the line; at 288 or under it sets the
NTSC flag `$5C3FA` and the rate `$AB` (171: 85 ticks in 256 fields, 19.9 a second at 60 Hz).
Bit 16 of that value is `VPOSR` bit 8, the lowest bit of the chip ID: 0 on OCS and ECS, 1 on
AGA (`$23` PAL, `$33` NTSC). So every AGA machine read as PAL, and on an NTSC A1200 the game
ran at 23.9 ticks a second, 20% fast. 2.0b masks with `$1FF` (V8 to V0), which changes
nothing on OCS and ECS. MEASURED (`NTSC=1`, the highest line, the rate, the Sentinel's turns
with no input): the a1200 with V1.01 `$18106`, `$9A`, every 505 fields (8.4 s); with 2.0b
`$106`, `$AB`, every 605 (10.1 s, as on PAL: 504 fields, 10.1 s); the a500 `$106`, `$AB`, and
PAL `$138`, `$9A` on the a500, a1200 and a1200-040. The loop is CPU-timed but bound by its
chip register reads; it saw line 312 on the a1200-060 too.

The timers are acted on by the main loop. Each pass (`$46D0` calls `$3630`, which calls the
enemy update `$233E`) serves one of eight enemy slots, `$170A` counting 7 to 0: a slot whose
timer is at 1 acts and reloads it. The Sentinel's turn (`$25BC`: the heading at `$77C0`+object
by `$183A`+object, the timer `$17A2` reloaded with 200 ticks, 502 fields) is one such action;
the energy drain once the Sentinel sees the player is another. So an action waits for its
slot after its timer runs out: idle, a pass is about a field; while the view is drawn or
panned a pass is a strip render. Faster drawing therefore shortens that wait, and can never
make the game faster than its ticks. The random number at `$17F4`..`$17F8` also steps once a
pass, so runs on different CPUs make different random choices.

In landscape 0000 the enemies start with the player's first action: left alone, nothing but
`$170A`, the random number and the field counter changes (1300 fields on the a500 and the
a1200-040); after a boulder the Sentinel turns every 504 or 505 fields, and once it sees the
player (about 2900 fields later) drains a unit of energy at a time until it absorbs the
player.

MEASURED (2.0b, `tools/gametime.sh`, 4000 fields after the boulder; fields):

| Machine | Turns, no input | Turns, panning | Its timer waited, panning | Drain 7 to 0, no input | Drain, panning |
|---|---|---|---|---|---|
| a500 | 504, 505 | 498 to 516 | 3 to 17 (63 in a 3000-field pan) | 765 (86 to 140 a unit) | 796 |
| a1200 | 504, 505 | 498 to 526 | 12 to 26 | 593 | 728 |
| a1200-030 | 504, 505 | 503 to 540 | 5 to 42 | 585 | 679 |
| a1200-040 | 504, 505 | 501 to 507 | 2 to 9 | 580 (81 to 90 a unit) | 648 |

With no input the timer waited 5 fields at every turn on every machine. On the a500 every
other unit of the drain took about 50 fields more, and the whole drain 32% longer than on the
a1200-040; INFERRED: a pass that redraws the view after a drain. The slave changes none of
this code, so V1.01 is the same.

## Rendering and panning

Offsets are from `BASE`, as above; the addresses below `$8000` are the game's absolute
low-memory variables and tables.

- **Display**: 320x200, 4 bitplanes (`BPLCON0` `$4200`), planes 8000 bytes apart, two
  buffers at `$60000` and `$78000`; `$58C76` holds the back buffer, so its changes count
  frames. The view is 192 lines.
- **The blitter** is used only for the scroll step at `$2E2`: four A-to-D plane copies (19
  words by 192 lines, or 20 by 184 for a vertical step), with blitter-nasty set (`DMACON`
  `$8440` at `$342`). Everything else is drawn by the CPU. The pan step (`$4868`) starts the
  four plane blits, then copies the strip's column into the words they leave out: with four
  more blits (1 word by 192 lines) for a horizontal step, with the CPU (`$493E`, 8 lines of
  20 words) for a vertical one. Then the loop clears the field flag (`$47AC`), waits for the
  field (`$358`) and restarts the copper on the new buffer (`$7C0`). StingRay's wait at `$30C`
  covers the start of each blit; nothing in the game waits for the end of the last one. On a
  68000 none is needed: blitter-nasty holds the CPU until a blit ends, so DMACONR's BBUSY never
  reads set after a `BLTSIZE` write (0 of 4032 reads on the a500). On the a1200-030 and
  a1200-040 the CPU reads it set (all of 6208 on the 040), so it runs alongside the blit; the
  last blit is over by the copper restart only if the CPU's chip accesses after it are held
  behind it, which depends on the bus, the caches and write buffers (FS-UAE's arbitration for
  these CPUs is not the hardware's). 2.0b waits for the blitter at `$47AC`, so the field
  the new buffer is shown in starts after its last blit, as on the 68000. MEASURED before the wait
  was added (a probe slave's counters at `$3F0`, all four pan directions, 250 or 500 fields
  each): the blitter was idle at every swap on the a500 (656 swaps) and at every field wait
  and swap on the a1200-040 (944), the a1200-040 with `DCACHE` (1016) and the a1200-030 with
  `MMU DCACHE` (568). FS-UAE's 68060 setup is not cycle-exact and finishes each blit at once
  (BBUSY never read set). The blits' destinations and the CPU's column never overlap, and no
  blit writes a buffer's first 8 lines, which `$4822` copies.
- **A pan step** renders a 128-pixel strip into the strip buffer at `$70000` (160 bytes a
  row, word-interleaved planes), then scrolls it in over 8 frames: each blits the front
  buffer into the back buffer shifted by one word (or 8 lines), copies one word column from
  the strip (`$493E`, from the pointer `$5C848`) and swaps at the next field. Holding D on
  the a500 gives 8 swaps one field apart, then a 16 to 24 field pause for the next strip
  (below).
- **The polygon path**: the edge scan converter (`$1440`) writes left and right edges to the
  tables at `$7B00`/`$7D00`; the span filler (`$18B4`) fills each span with `movep.l`
  read-modify-writes, 8 pixels of each plane at a time, through pattern tables at `$56100`,
  `$56800`, `$56C00` and `$56E60`.
- **Self-modifying code** (fixed in 2.0b, `EdgeStep`): the edge scan converter rewrote its own `subq.w`/`addq.w #1,d1`
  opcodes (`$1546`, `$15BE`, `$15F6`, `$1630`) and a `bcc.s` displacement (`$15C3`) for each
  edge. On a 68040/060 with the instruction cache on, the cache keeps the old instruction,
  so edges step the wrong way: faces go missing and white triangles appear. With WHDLoad's
  `NOCACHE` the a1200-040 drew correctly, and turning off only the emulated data cache did
  not help. The 68020's 256-byte cache rarely holds the patched loop, so it drew correctly.
  A census over 4085 traced a500 fields (`tools/sentinel.py census`, `tools/smc_census.py`:
  the route, pans in all four directions, boulder, robot, transfer, U-turn, hyperspace, pause,
  the music and sound keys, ESC) found no other instruction the CPU wrote and executed.

MEASURED (2.0b, landscape 0000, D held from 40 fields after the first view, `swaps` over 250
fields): the scroll-in is always a swap a field; the pause from a step's last swap to the
next step's first (the strip render) is:

| Machine | Swaps | Strip pause (fields) |
|---|---|---|
| a500 | 72 | 16 to 24 |
| a1200 | 136 | 5 to 11 |
| a1200-030 | 147 | 4 to 10 |
| a1200-040 | 159 | 4 to 8 |
| a1200-040, `NOCACHE` | 106 | 7 to 15 |
| a1200-060 | 189 | 3 to 4 |

MEASURED (2.0b, the same pan; share of the time over 60 fields traced with the cycle profiler
on the a500, the a1200 and a 28 MHz 68020 with 32 MB of Zorro III memory, `020-z3` in the
matrix; on the a1200-040, aprof over 250 fields with `--cpu=68040-NOMMU` and 16 MB of Zorro
III memory, which keeps the slave's PCs, an instruction count more than a timing). Routines are
by the nearest call target before the PC:

| Routine | a500 | a1200 | 020-z3 | a1200-040 |
|---|---|---|---|---|
| the span filler (`$18B4`) | 32.1% | 17.3% | 19.9% | 7.5% |
| the scroll blits (`$2E2`..`$356`: set-up, the CPU held behind a blit) | 17.2% | 28.5% | 8.6% | 17.6% |
| the pan step (`$4868`, its CPU column copy and chip accesses) | 0.1% | 1.1% | 1.7% | 11.2% |
| the slave's blitter waits (`$30C`, `$47AC`) | 0.2% | 0.1% | | 11.5% |
| the field wait (`$358`) | 7.6% | 14.5% | 23.9% | 20.4% |
| EdgeStep (the slave) and the edge scanner (`$1440`) | 13.3% | 5.8% | 1.8% | 1.4% |
| the projection (`$11D8`) | 5.4% | 5.0% | 6.0% | 1.6% |
| `$6BDA` | 3.3% | 5.3% | 6.7% | 1.5% |
| `$17A2` | 3.0% | 3.2% | 4.2% | 8.0% |
| `$2814` | 1.5% | 2.2% | 2.7% | 2.7% |
| `$6240` | 1.4% | 2.1% | 2.6% | 0.6% |
| the game pass (`$3630`, `$233E`) | 1.3% | 3.3% | 4.6% | 3.6% |
| the rest of the program | 10.5% | 9.5% | 12.1% | 4.7% |
| the sound module, the VBL | 3.1% | 1.7% | 2.2% | 1.0% |
| no PC (020-z3: the slave in Zorro III memory); aprof's gap | 0.1% | 0.1% | 3.2% | 6.6% |

So on the a500 a pan is the strip render (the span filler and the edge scanner alone 45%); on
the a1200-040 the render is under a third of it, and the rest is the scroll-in: 40% waiting
for the blitter (its set-up, the CPU held, the waits) and 20% the field wait. DERIVED: the
four plane blits are 14592 words read and written, about 29000 of a PAL field's 71000 colour
clocks, so the blitter is busy for about 40% of each scroll-in field on every machine.

MEASURED (2.0b, `tools/render_check.sh`, the fields its ten key pan steps take): a500 361,
a1200 198, a 28 MHz 68020 with Zorro III memory 192, a1200-030 185 (`MMU DCACHE` 165,
`MMU NOCACHE` 230), a1200-040 167 (`CACHE` 167, `DCACHE` 128, `NOCACHE` 264), a1200-060 105
(with every cache option; 110 when it traps `movep`). FS-UAE's 68060 setup is not
cycle-exact, so its figures do not follow the caches.

## Limitations

Self-modification outside the traced paths ([open-work.md](open-work.md) B4a): the static
code map finds no store into executed code but the edge scan converter's, but a store
through a computed pointer is found only by tracing it.
