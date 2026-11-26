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
separately, the patch lists as `PL_` macros, every PC-relative and patch target a label.
With `ORIGINAL` (`make build BUILD=original`) it rebuilds `AlienBreed3D.slave` and, with
`NOMUSIC` (variant `AlienBreed3D_nomusic`), `AlienBreed3D_nomusic.slave` byte for byte as
hunk files (`VASM_FLAGS`: `-m68020 -no-opt` keeps the shipped encodings); `make check`
compares both with the installed ones (`game.sh`). Named labels are ours; `Lxxxx` labels
are the code-hunk offsets in `AlienBreed3D.slave` (the no-music slave's are lower after the
first `IFND NOMUSIC` block). The release build adds Enhanced resolution (CUSTOM5,
`src/palette.s`, `src/display.s`, `src/c2p.s`; the larger chip and ExpMem); `release/slaves.sha256` records its two slaves.

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
`copper` decodes the live copper lists: the template, the panel, or a line of the view
([internals](internals.md#display-inventory)). `frames` counts swaps of `drawPt` ([internals](internals.md#display)), which happen at
most once a field. `base` prints where the hunks were loaded and `peek OFF N` reads by game
offset.

## Measuring

`tools/baseline.sh frames|aprof MACHINE OUT` is the baseline: both views, standing and on
the walk, as [performance](performance.md) describes; MACHINE is a1200-fast, a1200-030 or
a1200-040. `frames` counts swaps on the machine's own setup; `aprof` profiles every field
(`ab3d.py aprof`) on `$FSUAE_APROF` and writes a report beside each capture with
`python3 tools/frametime.py OUT.json`: frames, work a frame (mean, p50, p95), the shares by
category and the hot routines by source label.

- aprof runs only a CPU without an MMU model, so the profile machines are the a1200-fast
  setup with `EXTRA_ARGS` (`baseline.sh` has them). The a1200-030 setup's
  `uae_uaeboard=full+indirect` also hangs the older aprof builds.
- The a1200-030 and a1200-040 setups' frame rates are not the CPUs' own (the MMU models;
  [performance](performance.md#frame-rates)): compare speed on the aprof machines.
- The shared aprof reader rejects a stop tail over one `CYCLE_UNIT`, which the 14 MHz
  68020 exceeds (6.5 colour clocks). `ab3d.py _parse` checks such a capture's accounting
  itself and accepts a tail under 16.

By hand: in the menu RETURN (raw `44`) selects PLAY GAME; RETURN again on the text screen
starts the level. In the game M (`37`) switches to mouse control: mouse left/right turns,
up/down moves, the left button fires (`gdb monitor mouse DX DY`, `gdb monitor input
JOY1_FIRE_BUTTON 1`). Keypad Enter (`43`) switches the view; F10 quits.

## The colour census and the palette

The 1x1 palette ([plan](resolution-plan.md#colour), [internals](internals.md#the-1x1-palette))
was chosen from data read at analysis time only, all in ignored `tmp/colours/`:

    tools/census.sh                         # the tables, then frames of all 16 levels
    python3 tools/colours.py census         # the report: colours, each palette's errors
    python3 tools/colours.py images A 100 tmp/colours/a100.png   # one frame, side by side

`census.sh` boots its own instance with CUSTOM1=7 (unlimited energy and shots, F1 skips the
level). `ab3d.py tables` dumps the loaded walls and floor texture. Then in each level
`ab3d.py grab` keeps every frame shown over 360 fields of walking and 720 of fighting, read
from the view list as 96x80 colour words, and `ab3d.py next` goes on.

`tools/colours.py`'s `build`, `remap` and `effects` are the slave's builder as integers. To
check the slave against them, boot with CUSTOM5=1 and dump its area:

    INSTANCE=agent WARP=1 WINDOW=none DETERMINISTIC=1 JOY0=none WHD_ARGS=CUSTOM5=1 \
      python3 tools/ab3d.py serve &
    python3 tools/ab3d.py palette tmp/pal.bin    # from the boot: the build's fields by step
    python3 tools/ab3d.py level                  # on a 68040, dump again after some play:
    python3 tools/ab3d.py palette tmp/pal.bin 1  # copyback can hold the last writes
    python3 tools/colours.py check tmp/pal.bin

`ab3d.py palette` reads memory, not the CPU's data cache, so right after the build a
68040's copyback cache can still hold its last writes (the effect tables), and they show
as differences.

## The display skeleton

Enhanced resolution's display ([internals](internals.md#the-1x1-display)) is checked by
screenshots, all in ignored `tmp/display/`:

    tools/display.sh [OUT [SETUP]]          # both slaves through the same scenes, then checks
    python3 tools/display.py check SHOT FRAME [AREA]
    python3 tools/display.py compare ORIG.png OURS.png AREA

`display.sh` boots the release slave with the option off (CUSTOM1=4: the original's
display, the same patches as Psygore's) and then on (CUSTOM5=1 too)
through level 1's start, the pause screen and a level end (`ab3d.py end`: F1, then the
last frame) in both views; with the option on also a death in both (level 2's aliens;
`ab3d.py die`) and level 2's end. Each
scene keeps a screenshot and the frame on screen (`ab3d.py frame`, and the other list:
a stop can fall between the game's pointer swap and the screen's switch). `check` renders the frame where the original shows
its view, in 12-bit colour or through the area's palette, and compares; `compare` takes
each pixel of ours as the original's or its colour through the palette, leaving out line
$ca of the small view and line $ff of full screen (internals). The deaths and level 2's
end after them are only checked against their own frames: game time follows the frame
rate, so after a fight the two runs would differ. A machine takes about 10 minutes, most
of it the two deaths, stepped a field at a time.

The release build draws both views at 1x1, 192x160 and 288x240 (plan steps 5 and 6), so
there `compare` takes the two frames instead (`display.py scale`): it counts the
original's pixels, but the border's, found among the S x S at their place in ours
(columns Sx to Sx + S - 1, lines S(y - 1) + 1 to Sy), and at least `SCALE_MIN` of them
must be. Level 1's start, pause and end find 88-95%. A build with `VASM_EXTRA=-DLORES`
draws both views at 96x80, and every scene of it is compared pixel by pixel as in step 4.

Assembling with `VASM_EXTRA=-DHOLES` fills the list the game draws next with $f0f at each
swap, so a pixel the renderer does not write in a frame shows as $f0f in `ab3d.py grab`.

## Pen bytes

`BUILD=pens` (`-DPENS`, [internals](internals.md#pen-bytes)) is checked against the
release build by still frames of the pens each shows, all in ignored `tmp/`:

    make build BUILD=refholes VASM_EXTRA=-DHOLES=2
    make build BUILD=pensholes VASM_EXTRA='-DPENS -DHOLES=2'
    BUILD=refholes tools/pencheck.sh tmp/pc-ref [LEVELS]    # default 3 levels
    BUILD=pensholes tools/pencheck.sh tmp/pc-pens
    python3 tools/pendiff.py tmp/pc-ref tmp/pc-pens [PNGDIR]

`pencheck.sh` boots its own instance (CUSTOM5=1 CUSTOM1=4) on the a1200-030 and does not
rebuild. In each level, at its start and 40 fields forward, it turns 8 times by about 45
degrees with the mouse in both views, and `ab3d.py chunky` keeps each frame's pens: the
c2p's input, the convert's output in the release build. Mouse moves place the player
exactly on any CPU and build; keys go by time. `pendiff.py` counts the differing pixels
of each frame (line 0 left out) and draws them with PNGDIR. With `HOLES=2` in both
builds, holes are pen 16 (black, exact in the palette) rather than an older frame's pixel,
so the holes, which follow the frame rate, do not differ. In a level with moving aliens
(level 4) the two builds' game time differs and so do the frames.

`display.sh`, `ab3d.py frame`, `grab` and `holes` read the lists as colour words, so they
need a build without PENS.

## Finding routines

`python3 tools/srcmatch.py tmp/ab3d1-src/*.s` matches the published AB3D I source's labels
to game offsets by instruction shape. The source is personal-use only and lives in an
ignored `tmp/ab3d1-src/` (from `Agrigaatti/Alien-Breed-3D-I` on GitHub). The renderer's
routines it found are in [internals](internals.md#renderer-routines).
