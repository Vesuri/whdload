# Internals

How the game loads, memory, every slave patch, how the program draws and keeps time, and
current measurements. Offsets are into the loader `data/Zany` (its first code hunk, $664
bytes, at file offset $58) or into `data/files/FILE1` (the main program, loaded whole at
$10000 on every machine tried, so its runtime address is $10000 + offset).

## Loading and memory

A WHDLoad v10 slave (flags `NoError`, `EmulTrap`, `NoKbd`), 512 KB base memory, no ExpMem,
`ws_keyexit` $59 (F10). It loads `OSEmu.400` from `data/` to $400 and initialises it, then
calls `dos.library` `LoadSeg` on `data/Zany` through OSEmu. The loader opens
`Zany:FILES/FILE1` and the other files through OSEmu's DOS emulation, all from `data/`
(`PRELOAD` holds them). The slave patches the loader's first hunk, then jumps to its start.

## Slave patches

The loader, first hunk:

| Offset | Original | Patch | Why |
|---|---|---|---|
| $48 | `jsr` (absolute, relocated) to the protection check | `bra.s *+4` ($6002) | skips the check; see below |
| $5a | `beq.w $ae` (check passed) | `bra.w $ae` (byte $60) | always takes the passed path |
| $62e | the drive routine (writes $ff, $87, $87, $ff to CIA-B PRB $bfd100) | `rts` | no disk access |
| $658 | `jsr (a3)`, a3 = `FILE1`'s address | `jmp Patch` | patch `FILE1` before it runs |

`Patch` takes WHDLoad's CRC16 over the 64 KB at a3 (`FILE1`) and aborts with
`TDREASON_WRONGVER` unless it is $9cc8. Then it patches `FILE1`:

| Offset | Original | Patch | Why |
|---|---|---|---|
| $1f38 | `move.w #300,d0; dbf d0,*` (the keyboard handshake delay, a CPU loop) | `nop; jsr FixKey` | a delay on the beam, and the trainer |

`FixKey` decodes the raw key the game pushed at $1f20 (from 4(sp)). On F10 ($59) it writes 9
to $15ca2 (`FILE1` $5ca2), the strokes left. Then it
waits for nine changes of `VHPOSR`'s line byte, about nine raster lines, in place of the
CPU loop. `Patch` then jumps to `FILE1` (with `jmp`, so the loader's `jsr` return address
is never pushed; the game does not return).

`bra.s *+4` at $48 lands at $4c, the low word of the `jsr`'s relocated address, not at
$4e after the instruction: the CPU executes that word as an instruction. It boots on a500
and a1200, so whatever that word decodes to is harmless at the address OSEmu loads to; it
has not been looked at.

## Keys

F10 is both `ws_keyexit` and the trainer key. WHDLoad checks the quit key on each interrupt
before the game sees the key, so with the default quit key F10 quits. The install package's
NewIcon sets `QUITKEY=$5D` (keypad *), which leaves F10 to the trainer; the Retroplay icon
does not. Not tested.

## The program

`FILE1` is 64 KB of code and data in one bank, addressed from a4 = $10000 (`lea $10000(pc),a4`
throughout). Most of the game logic is threaded code: a5 walks a list of 16-bit addresses in
the bank, and each primitive ends with `move.w (a5)+,d5; movea.l d5,a0; jmp (a0)` (d5's
high word is the bank's). The primitives ($0100-$0c2a) model a 6502/65816-style machine: d0
is the accumulator, d4 holds the result for the N and Z flags, d3's top bit the carry
(`roxr.b #1,d3`); `$05e8` calls a threaded subroutine, `$0602` returns, `$0492` and
`$04a0` branch on Z. Words in the data are little-endian (the native code byte-swaps them with
`ror.w #8`). All this fits a machine translation of the Apple IIGS original (an inference,
not documented anywhere seen). Native routines (the renderer, multiply and divide helpers
such as $2a04 and $2a3a, the shape drawer) are called from the threaded code and return
with `lea <next>(a4),a5; jmp $106(a4)`, the dispatcher.

The main code runs in user mode on a stack near $9570; the interrupts run in supervisor mode
on WHDLoad's stack near $7fff0, after WHDLoad's own entry in fast memory.

## Display

Four lores bitplanes, 40-byte rows, planes $2000 apart, two buffers: $40000-$47fff and
$48000-$4ffff. The copper list is in `FILE1` at $2272. Its playfield section holds the low
words of BPL1PT-BPL4PT at $231a, $231e, $2322 and $2326 (bit 15 picks the buffer), and
BPLCON1 at $2312.

The renderer ($147a, entered from the threaded code once a frame):

1. $14a8: flips bit 15 of the four pointer words, which shows the frame drawn last time, and
   writes the fine scroll to BPLCON1. There is no wait for a field: the copper list changes
   at once, so frames are not quantised to fields.
2. Draws the next frame into the other buffer from the tile map (pointer at $0eb4) at the
   view position ($0e9c x, $0e9e y, little-endian): 20 rows ($151e) of 40 tiles ($153a),
   each tile 8x8 pixels, 32 bytes at $21d0a + its map word (pointer at $146a), copied with
   32 `move.b (a2)+,d16(An)`, chip RAM to chip RAM. Then a partial 21st row ($15f2) when the
   view's y is not a multiple of 8.
3. The shape drawer ($16f2) then draws shapes into the same buffer (twice a frame in the
   measured window).

It redraws all 800 tiles every frame, whether or not the view moved.

## Interrupts and time

Every interrupt vector ($64-$78) points to one handler at $21e6. It acknowledges VERTB and
COPER, and runs twice a field: at the vertical blank and at the copper interrupt the copper
list raises mid-screen (`move #$8010,INTREQ`). It flips a toggle at $21e2 on every run and
increments the field counter at $145c (low byte, then $145d) when the toggle returns to 0,
so the counter counts fields. Each run reads the mouse (JOY0DAT, deltas into $1d54/$1d56) and polls
the keyboard ($1f0c, with the slave's FixKey patch). It calls $3642 too, and once a field the
music sequencer at $40b8.

Game time, a lead to confirm: the threaded code at $5232 copies the field counter to $0c50;
at $62b8 it subtracts the previous pass's stamp ($6426) from it (`SEC`, `SBC`) and adds the
difference to $5de4/$5de5; at $6418 it saves the stamp. That is an elapsed-fields count per
main loop pass, which suggests the game keeps time by fields, not by frames. What consumes
$5de4 has not been traced.

## Measurements

Hole 1 in play with the pointer moving and the view scrolling, NTSC (60 fields a second,
16.7 ms a field), the shipped slave, 17.11.2026. Frames are counted by `tools/zanygolf.py
frames 240 5 3` (flips of the plane pointer, no breakpoints; 240 fields, the mouse moving
5, 3 counts a field), the costs from `tools/bench.py` traces (120 fields), which need a CPU
without an MMU model: `a1200-030` with `EXTRA_ARGS=--uae_mmu_model=0`, the same 50 MHz
cycle-exact 68030 with WHDLoad running as it does with the MMU.

| Machine | WHDLoad option | Fields a frame | Frames a second |
|---|---|---:|---:|
| `a500` (68000, 7 MHz) | | 6.66 | 9.0 |
| `a1200` (68EC020, 14 MHz, chip only) | | 5.13 | 11.75 |
| `a1200-030` (68030, 50 MHz) | | 4.37 | 13.75 |
| `a1200-030`, no MMU model | | 4.42 (trace: 4.43) | 13.5 |
| `a1200-030`, no MMU model | `CACHE` | 2.84 (trace: 2.83) | 21.0 |
| `a1200-030`, no MMU model | `DCACHE` | 2.82 | 21.25 |
| `a1200-030` | `CACHE` | 2.79 | 21.5 |
| `a1200-030` | `DCACHE` | 1.77 | 34.0, not a hardware figure (below) |

The game runs entirely in chip RAM (its 512 KB BaseMem), and WHDLoad marks BaseMem
non-cacheable, which without WHDLoad's `MMU` option means both caches off. So every
instruction fetch and data access of the 68030 waits for a chip-bus slot: the 50 MHz 68030
is 17 % faster than the 14 MHz 68020. With the instruction cache (`CACHE`) the loops run from
the cache: 55 % more frames. The data cache cannot help on hardware, which refuses to cache
chip RAM; FS-UAE models that refusal only without an MMU model, so the `a1200-030` preset
with `DCACHE` caches chip data and its 34 frames a second are not a hardware figure.

Where a frame's time goes on the 68030 (fields of CPU per frame, from the traces; every
frame drew 800 tiles):

| | Caches off | `CACHE` |
|---|---:|---:|
| Frame | 4.43 (73.9 ms) | 2.83 (47.2 ms) |
| Renderer ($1400-$16ff) | 2.92 (66 %) | 1.85 |
| Threaded-code primitives ($0100-$0c2a) | 1.23 (28 %) | 0.84 |
| Everything else (native helpers, interrupts, WHDLoad) | 0.30 | 0.14 |

A tile costs 3063 cycles (61 µs) with the caches off: 32 byte copies, each a chip read,
a chip write and the code fetches (about 40 code fetches a tile on the bus). With `CACHE` it
is 1940 cycles (39 µs), the 64 data accesses alone, about 0.6 µs each. Chip-bus slots over
the window: CPU 41 %, bitplanes 22 %, free 35 % (a CPU access cannot use every free slot).
The CPU never idles: no `STOP`, no wait for a field.
