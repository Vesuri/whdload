# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`. Paths are
relative to `games/RobinsonsRequiem`.

## Inputs

Pinned in `inputs.sha256`; `make unpack ARCHIVES=<directory>` verifies them into
`tmp/archives/` and unpacks all three into `tmp/game/` (no `game_unpack` hook):

| Archive | Unpacks to | What |
|---|---|---|
| `RobinsonsRequiem.lha` | `RobinsonsRequiemHd/` | CFou!'s v1.2 install package (whdload.de): `RobinsonSRequiemECS.Slave`, `RobinsonSRequiemAga.Slave`, `Install`, `ReadMe`, icons, `Solution`, and the source in `.src/` |
| `RobinsonsRequiem_v1.2.lha` | `RobinsonsRequiem/` | Retroplay's installed ECS/OCS game: `data-ecs/` and the ECS slave as `RobinsonsRequiem.Slave` |
| `RobinsonsRequiem_v1.2_AGA_1866.lha` | `RobinsonsRequiemAGA/` | Retroplay's installed AGA game: `data-aga/` and the AGA slave as `RobinsonsRequiemAGA.Slave` |

The two Retroplay slaves and the ReadMes are byte-identical to the install package's.

## Variants

| Variant | Source | Drawer, slave file | Kickstart | Machine |
|---|---|---|---|---|
| `RobinsonsRequiem` (default) | `src/RobinsonSRequiemEcs.asm` | `RobinsonsRequiem/RobinsonsRequiem.Slave` | `kick34005.A500` | `custom`: A500, 68000, 1 MB chip, 2 MB fast |
| `RobinsonsRequiemAGA` | `src/RobinSonSRequiemAga.asm` | `RobinsonsRequiemAGA/RobinsonsRequiemAGA.Slave` | `kick40068.A1200` | `a1200-fast` |

The ECS slave asks for 1 MB chip, which the shared `a500` (512 KB chip) cannot give; the AGA
slave asks for 1.6 MB chip, a 256 KB ExpMem and room for the 512 KB Kickstart image, so it
runs with fast memory (the plain `a1200` was not tried). Only these two machines have been
booted.

## Builds

The default vasm build with the repository's flags (`-m68000 -x -devpac -Fhunkexe -nosym`),
`INCLUDES=src/include`. Two changes to the shipped source make it assemble:

- `INCLUDE Sources:whdload/kick13.s` (and `kick31.s`) became `INCLUDE whdload/kick13.s`:
  `Sources:` was an Amiga assign; the build's `-I$WHDLOAD/Src/sources` finds the file.
- `src/include/lvo/intuition.i` includes the NDK's `lvo/intuition_lib.i` (the AGA source
  includes `lvo/intuition.i`; `lvo/dos.i` comes from `$AMIGA_INCLUDE`).

`-devpac` is needed: without it vasm rejects the AGA source's `doslibrary.MSG`-style labels.
The source still carries its Barfly blocks (`IFD BARFLY`: `OUTPUT`, `BOPT`, the `WDate`
date), which vasm skips.

### Byte identity

The rebuilt slaves are not byte-identical to the shipped ones (shipped 4,612 and 5,860 bytes;
rebuilt 5,292 and 6,416). The differences, checked with a comparison build in `tmp/` that
put the shipped date string back and turned on vasm's optimiser (`-opt-clr`, no `-devpac`):

1. **The KickEmu.** CFou! assembled against the 2013 `kick13.s`/`kick31.s`/`kickfs.s`; the
   build uses WHDLoad 20.1's, which are longer and different. Everything before the game's
   own part (`slv_CurrentDir`) differs, and so do the header's offsets and every PC-relative
   displacement from the game part into the KickEmu (`_resload`, `_monitor`, ...).
2. **The date.** Barfly's `INCBIN "T:date"` put `(29.03.2013)` after `Version 1.2 ` in
   `slv_info`; vasm leaves it out.
3. **Barfly's optimiser** (`BOPT O+ OG+`) against vasm's: `move.l 4,a6` as `4.w`, short
   branches, `clr.l`, `moveq #-1`, `addq`/`lea` forms. With vasm's optimiser on, the game
   part has the same length as the shipped one and the remaining differences are encoding
   choices only: `cmpi.w #$dd8e,d0` (Barfly `0c40`) against vasm's `cmp.w #` (`b07c`),
   `addi.l` against `add.l #`, and the `beq .versionok` to the next instruction, which
   Barfly assembled as a `nop` and vasm drops (a two-byte shift, made up by the final
   alignment).

The game patches, their offsets and their compare values are the same. A byte-identical
rebuild would need the 2013 KickEmu, which the shared WHDLoad tree does not keep;
`release/slaves.sha256` records the vasm builds as the baseline for later changes.

## Running

### Straight into the game (developer build)

The AGA developer build boots into the jungle start without input, with level of detail
and 3D window at HIGH, in about 15 s under `WARP=1` (no logo, flags, intro or options menu;
English):

```sh
make run BUILD=developer VARIANT=RobinsonsRequiemAGA SETUP=a1200-030
BUILD=developer VARIANT=RobinsonsRequiemAGA SETUP=a1200-030 WARP=1 python3 tools/rr.py serve &
python3 tools/rr.py ingame direct   # waits until the game is up
```

`_directstart` (`IFD DEVELOPER` in the AGA source) changes two branches of the MAIN script
as it runs; `docs/internals.md`, "Direct start", has what it patches. The release build is
unchanged by it. The music, sound and difficulty settings are the boot values the menu would
start from, not `CONFIG.INF`'s.

### Through the intro and menu (any build)

`tools/rr.py` is the gdb-stub server (`python3 tools/rr.py serve` with `VARIANT`, `WARP=1
WINDOW=none`, ...; its docstring lists the commands). For the AGA game, `ingame` goes from the
boot to the jungle start in about 20 s under `WARP=1` on `a1200-030`:

```sh
VARIANT=RobinsonsRequiemAGA SETUP=a1200-030 WARP=1 python3 tools/rr.py serve &
python3 tools/rr.py ingame          # `ingame low` leaves detail and window at LOW
```

It logs every file the game opens (breakpoints on `START`'s open wrapper, `opens`) and waits
on those loads, not on time:

1. Esc until `flags.DO` opens: an Esc during the Silmarils logo also skips the whole intro
   (the flags then go straight on to `baratinu.DO`, `param.DO`, `init3d.DO`, `prefsu.DO`).
   Pressed later, Esc ends only the running part: the video (`introag` ... `introj`), then
   the title (`present`, `musique2`) and the credits (`authors`) one by one.
2. The British flag, then Esc until the options menu (`prefsu.DO`) reads `CONFIG.INF`.
3. A click on the laptop (level of detail) and on the monitor (3D window size) turns each
   from LOW to HIGH; then Start. The game is up once `avion.DO` has loaded.

The pointer moves one shot pixel per mouse count; larger steps than about 10 counts per two
fields wrap the game's counters, so `point` homes it to the top-left corner in small steps.
Every boot starts from a fresh `DH1`, so both settings start at LOW.
