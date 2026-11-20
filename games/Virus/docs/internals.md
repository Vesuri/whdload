# Internals

## How it loads

A WHDLoad v4 direct slave (`ws_Flags` Disk and NoError, no Kickstart). It clears
`$1000-$3b7ff`, loads the whole disk image `Disk.1` (184320 bytes) to `$3b800`, so a
`Disk.1` offset is its address minus `$3b800`, loads the highscores, applies two patches,
turns the instruction cache on (`resload_SetCACR`) and jumps to the game's entry,
`Disk.1` offset `$286c8` (`$63ec8`).

## Memory

`ws_BaseMemSize` is `$88000` (544 KB). The ReadMe's reason: the render routines write past
the 512 KB border. The game itself uses fixed chip addresses up to at least `$78000`
(`$70000` and `$78000` stored at its entry), so no part moves to fast memory.

## Slave patches

Offsets are into `Disk.1`.

| `Disk.1` offset | Original | Patch |
|---|---|---|
| `$250c0` (level 2 interrupt, after reading CIA-A SDR into d0) | `bset #6,$bfee01` | `nop; jsr _keyboard`: does the same `bset`, then quits on F10 (`ws_keyexit`) or the reset-warning code `$78` through `resload_Abort` |
| `$2b916` (highscore entry) | `move.w #3000,d7; cmp.w #127,d0` | `nop; jsr _savehi`: on key 13 (return) saves the table, then does the replaced instructions |

The highscore table is 280 bytes at `$2b62e` (`$66e2e`). `Virus.hi` holds it nibble-swapped
and inverted (`_crypt`, its own inverse); it is loaded at start when its size is 280.

`_clamp` (slave offset `$130` in the code hunk) is never called: it would clamp `a3` below
`$78b40` before an offset add, apparently an unfinished fix for the render writes past
512 KB that the larger `ws_BaseMemSize` covers instead.

The game handshakes the keyboard with a CIA-A timer B one-shot, so the handshake does not
depend on CPU speed.

## Limitations

- Needs more than 512 KB of chip memory (above).
- No blitter-wait, cache or game-speed fixes: the slave enables the instruction cache only.
