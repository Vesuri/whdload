# Development setup

AmigaXDev supplies the shared tools and documentation. Its `make setup` installs
`~/.local` and `~/.local/share/amiga`. Source `amiga/env.sh` to use that environment;
`AMIGA_ENV` can select a different shared environment file. Shared tool, ROM and
WHDLoad paths are supplied by that file, not by copies from other projects.
The launcher uses `KICKSTART`, `KICK13`, `RTB`, `WORKBENCH_ADF`, `WHDLOAD_BINARY`,
`FSUAE_COMMON` and, for the gdb server, `FSUAE_ARM`.

`make check` verifies the retained archives against `manifest/SHA256SUMS`.
The hashes pin the downloaded inputs; they are not independently authenticated
publisher checksums. `manifest/inputs.json` records their source URLs.

Local layout:

- `tmp/archives/`: original installer and complete four-disk install archives.
- `tmp/installer/`: pristine installer extraction.
- `tmp/game/`: pristine full-install extraction.
- `tmp/extracted-files.sha256`: local extraction inventory.

To recreate the extractions, download the named archives from their manifest URLs
into `tmp/archives/`, run `make check`, then extract the installer into an empty
`tmp/installer/` and the complete install into an empty `tmp/game/` using `lha x`.
Do not merge into modified game data.

## Running

`amiga/run.sh` copies `tmp/game/FormulaOneGrandPrix4Disk` to the disposable
`amiga/.run/dh1`, boots Kickstart 3.1 with the Workbench 2.04 floppy and runs
`WHDLoad FormulaOneGrandPrix4Disk.Slave PRELOAD SPLASHDELAY=0 NOREQ`. The default machine
is the A500-equivalent: 68000, 512 KB chip, 1.5 MB slow, no fast RAM. `AMIGA_SETUP`,
`CHIP_KB`/`SLOW_KB`/`FAST_KB`, `WHD_ARGS` (for example `CUSTOM1=1`), `SLAVE`, `DEBUG`,
`WARP` and the other shared launcher variables apply.

`python3 tools/f1gp.py serve` boots with `DEBUG=1` on the native FS-UAE (`FSUAE_ARM`
unless `FSUAE` is set) and serves the shared `amigaxdev.gdbserve` commands
(`shot PNG`, `wait S`, `gdb TEXT`, `profile N BIN`, `quit`). Drive input with
`gdb monitor mouse DX DY`, `gdb monitor input JOY1_FIRE_BUTTON 1|0`,
`gdb monitor key RAW 1|0` and `gdb monitor fields N` while stopped. One mouse count
moves the game's pointer one screenshot pixel in both axes.

To reach gameplay without manual input:

```sh
. amiga/env.sh
WARP=1 DETERMINISTIC=1 JOY0=none JOY1=none python3 tools/f1gp.py serve > amiga/.run/serve.log 2>&1 &
python3 tools/f1gp.py quickrace tmp/route.jsonl   # stops at the first race field
python3 tools/f1gp.py shot "$PWD/tmp/race.png"
python3 tools/f1gp.py quit
```

`quickrace` waits for each screen (language, protection, startup, track, race) by
sampling fixed screenshot pixels every 25 fields, presses fire while waiting for the
first one (skipping the intro), homes the pointer to its top-left clamp before each
click, and fails after 6000 fields on any screen. The optional file logs every input
command and reply. `ROUTE_SHOTS=DIR` in the server's environment saves each polled
screenshot, which is how to re-derive a signature if a screen stops matching.
It works with any `AMIGA_SETUP` and with or without `CUSTOM1=1`. `tools/f1gp.py` sets
`BOOT_BREAK=0xf800d6` (the second instruction of the Kickstart 3.1 reset code), so the
server holds the CPU from reset until a command advances it; `cont` resumes free running.

## Profiling the race

`tools/race_profile.py` captures cycle-exact Barto traces of one race phase and reduces
them, through the same server (start it with `AMIGA_SETUP=a1200-fast` and the options
above):

```sh
python3 tools/f1gp.py raceprofile green tmp/prof/a1200-green 500   # or tow, follow
python3 tools/race_profile.py report tmp/prof/a1200-green          # also writes report.txt
```

The server holds the CPU from reset (`BOOT_BREAK`), and the route only advances it through
gdb commands, so a given command sequence repeats exactly: two tow captures gave identical
per-PC cycles, frame events and per-field screenshots. Different sequences diverge, even
over the same span (`monitor fields N` and `monitor profile N` do not leave identical
states), so anchor field numbers are per-command counts for that sequence, and windows
from different phases need not show one continuous race. Consecutive `monitor profile`
chunks are contiguous.

Each capture runs `quickrace` and then finds its anchor field exactly: `green` is the first
field with green start lights, `tow` the first non-cockpit field after it (the retired car
being pushed away, "Viewing Nigel Mansell") and `follow` the first field with the green
"Viewing" banner after that ("Viewing Riccardo Patrese"). It runs a lead
without polling (`LEADS`, calibrated on `a1200-fast`; `RACE_LEADS=0,0,0` polls throughout on
other machines), then checks a screenshot every field, and fails if the lead overshoots.
The window is the given number of fields after the anchor field, traced 50 fields at a time
(about 7.5 MB per field), reduced and deleted. The directory keeps `profile.pkl.gz`, the
chip and fast RAM images, anchor, first and last screenshots and `meta.json`; nothing in it
may be committed.

The reducer (`StackReduction`) follows one call stack per CPU stack, because the game's
task and its interrupts run on different stacks, and follows JSR/BSR in fast RAM. The
report locates hunks 0 and 2 and the Kickstart 1.3 image in the saved RAM and labels PCs
`h0+offset`, `h2+offset` or `kick+offset`. It gives cycle accounting, DMA slot shares,
per-frame time and work from the frame pacer (below), self time per function (each PC
charged to the nearest preceding call target), inclusive time per call target and the
call tree. Interrupts are charged to their own roots. Self time per "function" is only
as good as that nearest-call-target heuristic: check a large entry with
`python3 -m amigaxdev.disasm disd DIR/fast.bin 0x200000 <h0 base> START END`.

## Race clock across machines

```sh
AMIGA_SETUP=a500-1.5m WARP=1 DETERMINISTIC=1 JOY0=none JOY1=none python3 tools/f1gp.py serve > amiga/.run/serve.log 2>&1 &
python3 tools/f1gp.py raceclock tmp/clock/a500-1.5m
python3 tools/f1gp.py quit
```

`raceclock` runs `quickrace` and then the race to the results screen in 200-field steps,
reading the pacer's words in hunk 0 (located in RAM by its minimum-field tables and the
relocated instruction after them) and saving a screenshot per step. It opens Race
Finishing Times and saves `times.png`; `samples.json` has the frame count per step. Its
RAM regions per `AMIGA_SETUP` are listed in the tool. The 68030 cycle-exact preset timed
out in the route on a loaded host; it has no result yet.

`monitor fields N` from a stop at a vertical sync runs N + 1 fields: AmigaXDev's harness
counts the first vsync as ending a partial field even when there is none. The tools count
it that way; a one-field screenshot trace runs one field.
