# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins two archives, which `make unpack` installs side by side in `tmp/game/`:

| Archive | Installs | Slaves |
|---|---|---|
| `AlienBreed3D_v1.3_AGA_0624.lha` (Retroplay) | `AlienBreed3DAGA/`: `data/` (the game, unpacked), icons, ReadMe | `AlienBreed3DAGA.slave`, the same bytes as `AlienBreed3D.slave` |
| `AlienBreed3D.lha` (whdload.de) | `AlienBreed3DHD/`: installer, box icons, ReadMe, `src/AlienBreed3DHD_src.lzx` | `AlienBreed3D.slave`, `AlienBreed3D_nomusic.slave` (1.3) |

The runs boot the Retroplay drawer; both variants replace its `AlienBreed3DAGA.slave`.
Its `data/` holds `ABD.PK` (the game; `abd8ch` is the same bytes), `HackAB3D` (the end
part's music), `credpic`, `team`, `includes/`, `levels/` and `sounds/`.

## The build

The package's `src/AlienBreed3DHD_src.lzx` is not an LZX archive but XPK `IDEA`
(encrypted) data, so the source cannot be read; neither JOTD's nor StingRay's repository
holds the slave. `src/AlienBreed3D.s` is a reconstruction: each code region disassembled
separately, the patch lists as `PL_` macros, every PC-relative and patch target a label. It
rebuilds `AlienBreed3D.slave` and, with `NOMUSIC` (variant `AlienBreed3D_nomusic`),
`AlienBreed3D_nomusic.slave` byte for byte as hunk files (`VASM_FLAGS`: `-m68020 -no-opt`
keeps the shipped encodings). Named labels are ours; `Lxxxx` labels are the
code-hunk offsets in `AlienBreed3D.slave` (the no-music slave's are lower after the first
`IFND NOMUSIC` block). `release/slaves.sha256` records both.

## Driving it

`make serve INSTANCE=<name> WARP=1 WINDOW=none &` reaches the main menu in about 25 s
on the a1200-030. In the menu RETURN (`gdb monitor key 44 1`, then `... 44 0`) selects
PLAY GAME; RETURN again on the text screen starts the level. In the game M (`37`)
switches to mouse control: mouse left/right turns, up/down moves, the left button fires
(`gdb monitor mouse DX DY`, `gdb monitor input JOY1_FIRE_BUTTON 1`). F10 quits.
