# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins two archives. Both hold a `Sentinel/` drawer, so `make unpack` installs
the first and keeps it:

| Archive | Holds | Slave |
|---|---|---|
| `Sentinel_v1.01_3025.lha` (Retroplay) | `tmp/game/Sentinel/`: `Disk.1` (SPS 3025, RawDIC, 160 KB), the slave | V1.01 (15.09.2017) |
| `Sentinel.lha` (whdload.de) | installer, RawDIC imager (`Sentinel.islave`), source, ReadMe | the same bytes |

The install package is not unpacked into `tmp/game/`; extract it by hand to read it
(`$LHA xqw=tmp/pkg tmp/archives/Sentinel.lha`). The release packager reads it from
`tmp/archives/`.

## The build

`src/Sentinel.s` is the package's `Source/Sentinel.s` (the import commit has it unchanged)
with one commented edit: `cmp.w #$67e7,d0` written as `cmpi.w`, which StingRay's assembler
emits and vasm would optimise to the Dn form. Without the 2.0b version strings (the info
text and `$VER`) the build equals the shipped slave in every byte but the last word of the
code hunk, the padding to a longword after the final `rts`: vasm pads with `nop` (`$4E71`),
the shipped slave has `$CF50`, never executed. Release 2.0b adds "enhanced by Vesuri", its
version line and `$VER: Sentinel.slave 2.0b (23.11.2026)` (replacing
`$VER:Sentinel_Slave_1.01`), and the patches marked 2.0b in
[internals.md](internals.md#slave-patches). `release/slaves.sha256` records the vasm build.

`-devpac` (no optimisation) matches: the source sizes its branches. StingRay's
`INCDIR SOURCES:Include/` stays; vasm finds `whdload.i` through `-I`. `DEBUG` stays
commented out (it would set `ws_CurrentDir` to his development drawer).

## Driving it

`tools/sentinel.py` is the gdb-stub server with the game's commands (its docstring lists
them); `python3 tools/sentinel.py serve` takes `common/run.sh`'s options. With `WARP=1
DETERMINISTIC=1 JOY0=none ENTRY=1` it stops at the game's entry (`BASE+$10D4`) and every run
repeats exactly: `route` then takes the title (field 300 on), space, return for landscape
0000, its overview and return, all by field counts. The first view is drawn in about 120
fields on the a500.

The keys: D (raw `$22`) pans right, S (`$21`) left, L (`$28`) up, comma (`$38`) down. The left
mouse button enters pointer mode (`$1853` set); there the pointer at an edge pans (`$5F84A`
0..2418 and `$5F84C` 0..2996, edges tested at `$7870`), and space returns to key mode.
`swaps N` reports the fields between buffer swaps: a pan step is 8 swaps a field apart, then
the pause while the next strip is drawn.

## The render check

`tools/render_check.sh [run options]` boots, takes the route and pans right 3 steps, left 3,
up 2 and down 2, hashing the displayed buffer after each step; the hashes must equal
`tools/render_check.txt`, recorded on the a500 (`tools/render_check.sh record`). A pan step's
picture depends only on the steps taken, so the hashes hold on every CPU; it also prints the
fields the pans took. `INSTANCE=b` runs one beside another; start them a few seconds apart (several
launched in the same second failed to boot). V1.01 matched only with `WHD_ARGS=NOCACHE` on
the 68040 and 68060.

## Checks

- `tools/edgecheck.py [N]`: `EdgeStep` against the game's edge scan converter under Unicorn
  (`make check` runs it with 20000 edges; it reads the program from `tmp/game`).
- `tools/sentinel.py census N STATE` and `tools/smc_census.py STATE...`: executed bytes the
  CPU also wrote, from 68000 traces (`tmp/` holds the states: they contain game bytes).
