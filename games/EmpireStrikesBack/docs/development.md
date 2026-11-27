# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins two archives, both installed by `make unpack`:

| Archive | Drawer under `tmp/game/` | What |
|---|---|---|
| `EmpireStrikesBack.lha` | `EmpireStrikesBackHD` | Codetapper's v1.2 install package from whdload.de: the slave, the Install script (RawDIC with `EmpireStrikesBack.islave`), icons, a high-score file; no source. `make dist` repacks it |
| `EmpireStrikesBack_v1.2_1235.lha` | `EmpireStrikesBack` | the Retroplay install: `Disk.1` (440320 bytes) and the same slave; the run's drawer |

The two archives' slaves are the same file (SHA-256
`aeea2c6ba89739e8d94c6a609b222fbf15aee159afc4228ee50a91f2097daf7e`, 1044 bytes).
The Retroplay `Disk.1` is the second version the slave knows (title picture at $2800).

## The build

The v1.2 slave shipped without source. `src/EmpireStrikesBack.s` is a reconstruction from
its disassembly that built it byte for byte (commit "Reconstruct the Empire Strikes Back
slave source"): the labels and comments are new, the instructions are the slave's. `-devpac` (no optimisation)
matches; the slave has no relocations.

## Driving it

`make serve WARP=1 WINDOW=none INSTANCE=<name> &`, then `make server INSTANCE=<name> CMD=...`
(give the server a few seconds to come up). `wait 45` reaches the attract's high-score page.
`tools/esb.py` adds `fire`, `mouse`, `sweep` (the crosshair swept, firing on and off:
play goes on to the waves' later phases), `frames` (fields between swaps, from a trace;
the trace records no PCs on the 68030 and up, so use `sm` there), `cover`, `calls`,
`incl`, `mem`, `hits`, `gdb` and `sm` (the enhanced framerate's statistics, SmV, read by
the build's listing: `sm release`; also the fields a tick). The trigger is the
joystick's fire button (`JOY1_FIRE_BUTTON`); a game starts from the wave select (state
$0b, about 1.5 s with its countdown), firing at a planet: move the mouse at once (about
6, -5 a field for 20 fields reaches wave 3).

## Enhanced framerate builds

`make run` on a 68020 or better setup passes `CACHE` and `CUSTOM1=1`, as the installed
icon does (`ENHANCED=0` leaves CUSTOM1 out). game.conf defines:

| BUILD | What |
|---|---|
| `verify` | hits cost no shield; each exact replay is compared with what the tick drew (`sv_stn`/`sv_stbad` by state; the last mismatch's two screens are kept in ExpMem at `em_tick`, `em_rep`), and each frame drawn by bands with the same frame drawn whole (`sv_pbad`) |
| `check` | as `verify`, for every state, exact frames only (the game keeps its speed), never direct: for states not yet enabled (`SM_STATES`) |
| `timing` | colour clocks per op type and for the stages (`sv_tcost`, `sv_tcnt`: slot 0 SmPrep, 4 the whole frame in lines, 6 the band clears) |
| `direct` | every tick direct, hooks installed: the speed baseline for `sm`'s fields a tick |

In the verify builds the cannons' crosshair words are recorded like any other (in the
release they are read live), so a moving mouse does not show as a mismatch.
