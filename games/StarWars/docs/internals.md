# Internals

The program, its display and game time, every slave patch (as offsets into the game's code
hunk or file), current measurements and known limitations. Offsets are for SPS 0403 (V1.0),
the only version pinned here, unless marked SPS 2926.

## How it loads

A kick13 slave (KickEmu, `BOOTDOS`, `HDINIT`, `CACHE`, `IOCACHE` 4096): WHDLoad starts
Kickstart 1.3 (`kick34005.A500`) with 512 KB chip and 512 KB ExpMem, and `_bootdos` runs as
the first process with the current directory `data` (`slv_CurrentDir`). It
`LoadSeg`s `starwars`, identifies the version by a CRC16 over part of the code hunk, applies
that version's patch list with `resload_PatchSeg`, and calls the program like the CLI
would (argument `"  \n"`, the `Input()` file handle's buffer set to it). When the program
returns, the slave unloads it and quits WHDLoad. The game reads its sounds, music and
shapes from `data/shapes/` through dos.library (`list` names them) and saves its high
scores there.

`data/starwars` (SPS 0403, SHA-256
`44f2a4223f4aef8eb0333930998dea7c8816c8be35c64ef7af947d364426c32c`, 64904 bytes) has three
hunks: code $e9e8 bytes (file data at $28, 2 relocations), data $1f20 ($11cc in the file,
at $ea3c, 88 relocations) and 4 bytes of BSS. Every patch below is in the code hunk: file
offset = code-hunk offset + $28. The program is C (small-data model, globals off `a4`) with
assembly routines, as the ReadMe says.

| Version | CRC16 range (code hunk) | CRC16 | Patch list |
|---|---|---|---|
| SPS 0403 (V1.0) | $0512-$058a | $48a3 | `PLGAME403` |
| SPS 2926 (protected) | $3b5e-$3c08 | $6f40 | `PLGAME2926` |

Any other file quits with "wrong version". The ReadMe also names SPS 939, which has no
table entry.

## Display and game time

The vertical blank code at $00ea (file $0112) sets the display (four bitplanes 8000 bytes
apart, DIW $2981-$f1c1, DDF $38-$d0, BPLCON0 $4200) and increments the frame counter
`-26430(a4)`. The program paces itself on that counter: each update clears it, then busy
waits until it reaches a threshold. The original thresholds are one frame at three of the
four sites and two at the fourth, so on a fast machine those loops ran at up to 50 (or 25)
updates a second, which the ReadMe calls unplayable. StingRay's timing fix sets all four to
three frames: at most 16.7 updates a second (PAL) at each, the same on every CPU fast
enough to meet it. Which game state each site paces has not been traced.

| Site (code hunk) | File | Original | Fixed |
|---|---|---|---|
| $897e | $89a6 | `cmpi.w #1,-26430(a4)` | 3 |
| $b612 | $b63a | `cmpi.w #1,-26430(a4)` | 3 |
| $b65e | $b686 | `cmpi.w #1,-26430(a4)` | 3 |
| $d5a8 | $d5d0 | `cmpi.w #2,-26430(a4)` | 3 |

SPS 2926: $8390, $b0fe, $b14a, $ceca.

The same counter times other waits: 50 frames at $070a, 350 frames after saving the high
scores at $074c, 500 frames at $271a.

## The slave's patches (SPS 0403, `PLGAME403`)

| Code hunk | File | Patch | Why |
|---|---|---|---|
| $d750 | $d778 | `PL_PS SetStack` over `sub.l 4(a0),d0; addq.l #8,d0` | the stack bound from the slave's `STACKSIZE` (6000) instead of the process's |
| $8d36 | $8d5e | `PL_PS delay` over the `subq.l #1,-4(a5); bne` loop (2000000 iterations) | the instruction text before the game: 3 s or a mouse button (`resload_Delay` 30) instead of a CPU-dependent loop |
| $06ca | $06f2 | `PL_B $60` (`beq` to `bra`), unless CUSTOM1 | high-score saving: skip the IO size check |
| $06fa | $0722 | `PL_B $60`, unless CUSTOM1 | as above |
| $0752 | $077a | `PL_W $4e71` over `blt.s` of the 350-frame wait | no delay after saving |
| $511a | $5142 | CUSTOM1: `PL_B $4a`, `add.w d0,-25348(a4)` becomes `tst.w` | unlimited shields; `PL_GA` keeps the address for the toggle |
| $51c2 | $51ea | CUSTOM1: `PL_PSS .CheckKey,2` over `cmpi.l #$59,8(a5)` | the S key toggles the shields patch (`eor.b #$9b`, `add.w` and `tst.w`), then the original F10 test |
| $897e+2, $b612+2, $b65e+2, $d5a8+2 | +$28 | `PL_W 3`, unless CUSTOM2 | the timing fix (above) |

CUSTOM1 (the trainer) also disables the high-score patches, so a trained score is never
saved. CUSTOM2 keeps the original frame thresholds.

## SPS 2926 (`PLGAME2926`)

Not pinned here; from the source. The protected release: `PL_SA $e314,$e432` skips the
protection check and `PL_R $7184` the second one; `SetStack` at $d084, the info-text delay at
$874e; four `PL_PSS .fixDMAWait,10` at $023a, $028c, $02de and $0330 replace the sample
player's CPU-dependent DMA waits with three raster lines; high-score saving is added (it
calls the game's routine at $8d9e after name entry, $6ed4/$6eda/$6f50) unless CUSTOM1; the
shields trainer at $4ac4 with the S key at $4b56 (before the original F3 test); the timing
sites above.

## Limitations

- The game is capped at 16.7 updates a second by the timing fix; it is no faster on a fast
  machine than on one that just meets three frames per update. Not measured here.
- Quit is Del (`slv_keyexit` $46); F10 is the game's own key in one version.
