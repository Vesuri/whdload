# Internals

## Loading

A direct slave (`ws_Version` 10, `WHDLF_NoError|WHDLF_ClearMem|WHDLF_EmulTrap`): 512 KB
base memory, no ExpMem, quit key F10, files from the `data` drawer. It installs its own
level 2 (keyboard) interrupt, sets the stack to `$800`, loads `Archipelagos_03FC00` (the
game's Atari ST format program, from disk offset `$3FC00`) to `$2000` and identifies it by
the CRC16 of the whole file: `$55BF` SPS 627, `$F600` SPS 628, anything else
`TDREASON_WRONGVER`. It applies the ST relocation table itself, patches the program and
jumps to its body, `$201C`, with A6 = `$DFF000`.

Every other load goes through the game's disk loader, which the slave replaces: the
loader's parameter block gives a disk offset and a destination, and the slave loads the
file `Archipelagos_<offset as six hex digits>`. A saved game is 512 bytes written to disk
offset `76*512*10` = `$5F000`, the file `Archipelagos_05F000`.

## Slave patches

Offsets are into the program body: a file offset of `Archipelagos_03FC00` minus its `$1C`
byte ST header (so at runtime `$201C` + offset).

| SPS 627 | SPS 628 | Patch |
|---|---|---|
| `$8E68`, `$8E72`, `$8E7C` | same | level 1, 5 and 6 interrupt handlers acknowledge twice and return |
| `$8D44` | same | keyboard: the slave's level 2 handler passes each key to the game, storing it at `$E33C` and jumping to `$E37E` (628 `$E390`, `$E3D2`) |
| `$8D6C`-`$8D76` | same | skip setting the level 7 vector |
| `$CEA2` | `$CECE` | the vertical blank acknowledge |
| `$A2C8`, `$A4DA`, `$A47A` | `$A2D4`, `$A4E6`, `$A486` | loader init, drive on and drive off return at once |
| `$9FD2`-`$A03E` | `$9FDE`-`$A04A` | the disk read: load the file named by the offset |
| `$12240` | `$124F8` | the protection track check returns at once |
| `$11512`-`$117CC` | `$1175A`-`$11A82` | the manual protection skipped whole |
| `$E4B8` | `$E50C` | "end level 2 interrupt code": returns at once; the slave's handler acknowledges the interrupt |
| `$C4AA` | `$C4BC` | the text writer's CPU loop: 58 times five raster lines |
| `$1118` | same | the replayer's DMA wait: five raster lines |
| `$1098C` | `$9E60` | save game to a file |
| | `$125CE` | the US "Fanfare" intro ends with the left mouse button |

## Limitations

- The DMA and writer delays wait on `VHPOSR` line changes: five lines, so they scale with
  the display, not the CPU.
