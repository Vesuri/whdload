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
x 0..2418 and `$5F84C` y 0..2996, larger is up; edges tested at `$7870`), and space returns
to key mode. A mouse count moves x by 4 and y by -8; `pointer X Y` steers through the
emulator's mouse input until the game's pointer is there or stops at an edge, so a pan with
the pointer is `pointer 9999 1536` (right), `0 1536`, `1280 9999` (up) or `1280 0`.
`swaps N` reports the fields between buffer swaps: a pan step is 8 swaps a field apart, then
the pause while the next strip is drawn.

Two commands bound what the shared ones leave open: `waitfor ADDR HEX MAX` runs field by
field until memory holds a value and says `timeout` after MAX fields; `brk ADDR SECONDS` is a
breakpoint with a wall-time limit (`monitor fields` ignores breakpoints, and the shared
`until` waits up to 30 minutes), stopping there or interrupting gdb.

## The render check

`tools/render_check.sh [run options]` boots, takes the route and pans right 3 steps, left 3,
up 2 and down 2 with the keys, then the same with the pointer at each screen edge, hashing
the displayed buffer after each step; the hashes must equal `tools/render_check.txt` (lines
`22 1 ...` for keys, `p22 1 ...` for the pointer), recorded on the a500 (`tools/render_check.sh
record`). A step's picture depends on the steps before it (the same view reached on the way
back has other bytes), not on the CPU or on keys against pointer: from the first view the
pointer's steps equal D's. It prints the fields each half took. `INSTANCE=b` runs one beside
another; start them a few seconds apart (several launched in the same second failed to
boot).

The reference is V1.01's picture: V1.01 matches it on the a500 (`SLAVE=original`), and the
control `SLAVE=original SETUP=a1200-040` must fail (it differs in 43 diff lines).

## The play check

`tools/play_check.sh [run options]` plays landscape 0000 through the emulator's keyboard and
mouse, and each step waits a bounded number of fields for its own record in the game's state:

| Step | Record |
|---|---|
| the route | energy (`$1784`) 10, the player is object `$3E` (`$1685`) |
| B: a boulder on the visible square in front (`pointer 1984 272`) | energy 8 |
| R: a robot on it (`1984 352`, the boulder's top) | energy 5 |
| A: absorb that robot (`1984 600`) | energy 8 |
| R again, Q: transfer | the player leaves `$3E` (to `$2C`) |
| U: U-turn | the object's heading (`$77C0`+object) turns by 128 |
| H: hyperspace | energy 2, a new object |
| H with 2 energy | the player dies (object 0), the landscape restarts (energy 10, `$3E`) |
| return | the first view is drawn again, the same picture as the first time |
| ESC, then the route from the title | object 0, then energy 10 and the same first view |
| F10 | WHDLoad ends with OK (`VERIFY_EXIT=1`) |

The game absorbs only an object whose square the player sees: a tree behind a ridge, the
boulder (it hides its own square) and the old body after the transfer (its square is below
the view) are refused, the robot on the boulder is not. After each action the view is
redrawn and keys pressed meanwhile are lost, so the check lets it settle for 200 fields.

On the way it checks the sound module's patch (`internals.md`, Sound): the `jsr` and `nop`
at module `$F2E`, and the boulder's effect trigger from the `jsr` to `$F36` lasting at least
12 raster lines (13 on the a500, 040 and 060), read from `VPOSR`/`VHPOSR` at two `brk`s.

Not covered: completing a landscape, the Sentinel absorbing the player, entering a landscape
code.

## The matrix

`tools/matrix.sh [FILTER]` runs the render check and the play check over the machines and
WHDLoad's cache options (`NoCache`, `Cache`, `DCache`, `ChipNoCache`, `BranchCache`; `MMU` on
the 030), a 28 MHz 68020 with Zorro III memory and a 68060 that traps `movep`
(`--uae_cpu_no_unimplemented=true`), two at a time; the list is in the script. Two controls
must fail: V1.01's render check on the a1200-040, and V1.01's play check (the sound patch
missing). A line whose result is not its expected one fails the run; `tmp/matrix/summary.txt`
lists them. The whole list takes about an hour of warp emulation; FILTER (a grep pattern)
runs part of it.

## Checks

- `tools/edgecheck.py [N]`: `EdgeStep` against the game's edge scan converter under Unicorn
  (`make check` runs it with 20000 edges; it reads the program from `tmp/game`).
- `tools/render_check.sh`, `tools/play_check.sh` and `tools/matrix.sh` above: minutes each,
  so not in `make check`; run the render and play checks on the a500 and a1200-040 for any
  change to the slave, and the matrix before a release.
- `tools/sentinel.py census N STATE` and `tools/smc_census.py STATE...`: executed bytes the
  CPU also wrote, from 68000 traces (`tmp/` holds the states: they contain game bytes).
