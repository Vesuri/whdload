# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins three archives, which `make unpack` installs side by side in
`tmp/game/`:

| Archive | Installs | Game executable | Slaves |
|---|---|---|---|
| `AlienBreed3D_v1.3_AGA_0624.lha` (Retroplay) | `AlienBreed3DAGA/`: `data/`, icons, ReadMe | `data/ABD.PK`: the Aminet 8-channel version, $c4dc | `AlienBreed3DAGA.slave`, the same bytes as `AlienBreed3D.slave` |
| `AlienBreed3D_v1.3_CD32.lha` (Retroplay) | `AlienBreed3DCD32/`: the same, with `data/abd` | `data/abd`: the CD32 version, $fd78 | `AlienBreed3DCD32.slave`, the same bytes as `AlienBreed3D.slave` |
| `AlienBreed3D.lha` (whdload.de) | `AlienBreed3DHD/`: installer, box icons, ReadMe, `src/AlienBreed3DHD_src.lzx` | none | `AlienBreed3D.slave`, `AlienBreed3D_nomusic.slave` (1.3) |

Both `data/` drawers hold `abd8ch` (the $c4dc version again), `HackAB3D` (the end part's
music), `credpic`, `team`, `includes/`, `levels/` and `sounds/`; the slave loads `abd.pk`
before `abd`, so the AGA drawer runs $c4dc and the CD32 drawer $fd78. No archive holds the
floppy version ($23d2); the original disks through `Install-AlienBreed3D` would. Retroplay's
`AlienBreed3D_v1.3_NoMusic_AGA_0624.lha` and `..._NoMusic_CD32.lha` add nothing: the same
executables, and slaves equal to `AlienBreed3D_nomusic.slave`.

The runs boot the AGA drawer; both variants replace its `AlienBreed3DAGA.slave`. The CD32
version: `make run GAME_DIR=AlienBreed3DCD32 SLAVE_FILE=AlienBreed3DCD32.slave`.
`python3 tools/exe.py [FILE [OUT]]` unpacks a game executable into `OUT/abd` and
`OUT/abd.flat` (default the AGA drawer's into `tmp/exe`; the CD32 one into `tmp/exe-cd32` by
convention).

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
