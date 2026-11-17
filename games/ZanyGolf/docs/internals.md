# Internals

How the game loads, memory, and every slave patch. Offsets are into the loader `data/Zany`
(its first code hunk, $664 bytes, at file offset $58) or into `data/files/FILE1` (the main
program, loaded whole).

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
to $15ca2, the strokes left (absolute: OSEmu loads the program at a fixed address). Then it
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
