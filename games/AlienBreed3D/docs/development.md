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

`tools/ab3d.py` is the shared game server with this game's commands (its docstring has them
all). A repeatable run:

    INSTANCE=agent WARP=1 WINDOW=none DETERMINISTIC=1 JOY0=none python3 tools/ab3d.py serve &
    python3 tools/ab3d.py wait 20        # the main menu, from a warp boot on the a1200-030
    python3 tools/ab3d.py level          # RETURNs into level 1, then M (mouse control)
    python3 tools/ab3d.py play walk      # the scripted walk; or steps: '100 my -10; 50 mx 20'
    python3 tools/ab3d.py frames 500     # frames shown over 500 fields, fps, fields a frame
    python3 tools/ab3d.py full 1         # full screen (0: the small view)
    python3 tools/ab3d.py quit

The commands run whole fields (`monitor fields`), so with `DETERMINISTIC=1` a run repeats.
Game time follows the frame rate, so an input script ends in the same place only on the
same machine. Keys need holding for 10 fields: at 3 the game misses them.
`frames` counts swaps of `drawPt` ([internals](internals.md#display)), which happen at
most once a field. `base` prints where the hunks were loaded and `peek OFF N` reads by game
offset.

By hand: in the menu RETURN (raw `44`) selects PLAY GAME; RETURN again on the text screen
starts the level. In the game M (`37`) switches to mouse control: mouse left/right turns,
up/down moves, the left button fires (`gdb monitor mouse DX DY`, `gdb monitor input
JOY1_FIRE_BUTTON 1`). Keypad Enter (`43`) switches the view; F10 quits.

## Finding routines

`python3 tools/srcmatch.py tmp/ab3d1-src/*.s` matches the published AB3D I source's labels
to game offsets by instruction shape. The source is personal-use only and lives in an
ignored `tmp/ab3d1-src/` (from `Agrigaatti/Alien-Breed-3D-I` on GitHub). The renderer's
routines it found are in [internals](internals.md#renderer-routines).
