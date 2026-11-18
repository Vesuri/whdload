# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`: the inputs
and how they are installed, the build, running, the in-flight profile and traps.

## Inputs

`make unpack ARCHIVES=<directory>` takes the four archives `inputs.sha256` pins and unpacks
each with the default unpacker (no `game_unpack`):

| Archive | Drawer under `tmp/game/` | What |
|---|---|---|
| `Gunship2000.lha` | `Gunship2000HD` | JOTD's v3.1 install package from whdload.de: Install script, ReadMe, Manual, icons, the three slaves and `source/` (Barfly `.asm` sources, `fakepad.s`, `Makefile`, `slave_version`); `make dist` repacks it |
| `Gunship2000_v3.1_0808.lha` | `Gunship2000` | Retroplay SPS 0808, the floppy ECS version, `Gunship2000.slave`; the `Gunship2000ECS` run's drawer |
| `Gunship2000_v3.1_AGA_0371.lha` | `Gunship2000AGA` | Retroplay SPS 0371, the floppy AGA version, `Gunship2000AGA.slave` |
| `Gunship2000_v3.1_CD32.lha` | `Gunship2000CD32` | Retroplay, the CD32 version, `Gunship2000CD32.slave` |

The Retroplay slaves are the install package's (`Gunship2000ECS.slave` installed as
`Gunship2000.slave`), and all four ReadMes are the same file:

| Slave | SHA-256 | Bytes |
|---|---|---:|
| ECS | `b8d8a83783e224312891aba946c6ec3ca0b031573cc2d001e6d4f8d1dbb371fd` | 5124 |
| AGA | `ac9caa2062574f1e9bfa6fe31e135f930afdd1729c58168fb57d7ac96fd69dff` | 4884 |
| CD32 | `d470ea765a8ff428c006a6af61fdb26cb7d53ae347c0b762ed0a57962a431e3d` | 5132 |

The Retroplay icons set only `SLAVE=`; the ECS icon has `(CUSTOM1=1)` commented out.

## Build

`src/` is `G/Gunship2000/usr/source` from whdload_slaves at 6046174e; the install package's
`.asm` files differ from it only in the KickEmu include paths (`kick13.s` against
`whdload/kick13.s`). Three changes make it assemble with vasm against the shared WHDLoad 20.1
tree, each commented in place or in game.conf:

- `Gunship2000AGAHD.s`: a `bra.b .patch` straight before `.patch` is commented out. A
  short branch to the next instruction cannot be encoded (its displacement 0 means a word
  branch); Barfly's optimiser dropped it, vasm refuses it.
- `Gunship2000CD32HD.s`: `kick31.s` by its path, `whdload/kick31.s`, as the other two do.
- `fakepad.s` includes `lvo/lowlevel.i`, which the NDK calls `lvo/lowlevel_lib.i`: the bridge
  `src/include/lvo/lowlevel.i` (`INCLUDES="src/include"`).

The sources keep `DEBUG` set in the CD32 slave, as shipped. game.conf leaves out `-devpac`,
so vasm's default optimisations stand in for Barfly's `BOPT O+`, and adds `-pic`.

The build is not byte-identical to the shipped slaves, and cannot be: they were built with
WHDLoad 16-era KickEmu (`kick13.s`, `kick31.s`), and the 20.1 ones put JOTD's code 276
(ECS), 720 (AGA) and 710 (CD32) bytes later; the shipped slaves also carry Barfly's build date (`3.1 (28-mars-06 21:27:42)`) in
their info and `$VER` strings, which vasm builds leave out. What was compared, 18.11.2026,
with the shipped date strings put back in a scratch copy of the source: the header fields
other than the string offsets are the same, and JOTD's own code and data, from the end of the
`$VER` string to the end of the slave, disassembled and diffed as instruction sequences,
differs only in equivalent encodings:

- Barfly's `bsr x; rts` and `jsr (a2); rts` as `bra x` and `jmp (a2)`;
- `cmpa.l #0,An` against vasm's `cmpa.w #0,An` (`tst.l An` in the 68020 kick31 slaves),
  `subi.l #`/`cmpi.b #` against `sub.l #`/`cmp.b #`, `movem.l (sp)+,a0` against
  `movea.l (sp)+,a0`;
- alignment padding (`nop` or zeroes after `cnop`).

Every other operand is equal, or a PC-relative target at the same KickEmu routine or the same
string. (That compares JOTD's source; 4.0b adds the patches since, and `src/flight.s`.) `release/slaves.sha256` records this build.

## Running

`make run VARIANT=Gunship2000ECS|Gunship2000AGA|Gunship2000CD32` (ECS is the default). Each
boots on its game.conf machine (`docs/internals.md`, "Memory"): ECS on a custom A500 with
1 MB chip and 2 MB fast (no named 68000 machine has the 1 MB chip BaseMem and the 1 MB ExpMem),
AGA and CD32 on `a1200-fast`. Checked 18.11.2026 with `make serve WARP=1 WINDOW=none`: ECS
(also on `a1200-fast`, with `CUSTOM1=1`), AGA and CD32 each reach the duty roster within 40
seconds of warp.

Traps:

- Without `CUSTOM1=1` the ECS slave first runs `Gunship 2000 Intro`, which holds on its
  sunset picture until input (the shipped slave the same); `WHD_ARGS=CUSTOM1=1` skips it.
- `make run SLAVE=original` runs the variant's Retroplay slave.

## Profiling in flight

`tools/` drives each version (`VARIANT`, default `Gunship2000AGA`; `gs2.py` has each
`gs2.run` build's offsets) on a native FS-UAE (`$AMIGA_SHARE/fs-uae-aprof`, which has
`monitor key`, `mouse`, `input`, `fields` and `aprof`):

| Tool | What |
|---|---|
| `gunship2000.py` | `Session`: boots `common/run.sh` as its own instance in warp, deterministic, nothing in port 0; fields, keys, mouse, clicks, screenshots, Barto traces, aprof, memory reads. `MACHINE` = `a1200-030` (default), `a1200-030-mmu`, `a1200-fast`, `a500` (game.conf's ECS machine) or `a1200-040-z3` (68040, 32 MB Zorro III fast; with `WHD_ARGS=MMU` for WHDLoad's MMU option, functional checks only); `SLAVE`, `VARIANT` pass through |
| `profile_flight.py OUT [REFERENCE]` | the front-end route to the cockpit and the profile: a window per key of `VIEWS` (default `f5 f6`, the chase and tactical views; `f1` the cockpit view, `cockpit` the view the flight starts in, without a key), each `OUT/<key>.prof` of 150 fields (`SEGMENT`); `COUNT=1` (the default on the `a500`) counts the presented frames instead, `OUT/<key>.frames`, with `OUT/route/*.png`, `layout.json` and `state.json`; `FLY=N` first takes off and flies forward N fields (7000 reach the pinned mission's enemy units); with REFERENCE (an earlier OUT) it stops unless the cockpit is the reference's |
| `aprof_report.py OUT [TOP]` | per window (`OUT/*.prof`): frames (presents at code $129c4) and fps over the window's seconds (PAL or NTSC), CACR, the chip-bus share, the time by kind (frame cap, blitter waits, stack and calls, other, outside) and the top routines |
| `gs2.py` | finds `gs2.run`'s hunks in memory (by the installed file), the memory lists, the clocks |
| `coupling.py OUT [REFERENCE...]` | the coupling test: the same flight inputs at the same game time, the player's state sampled at mission seconds 25-90 and interpolated to the second; with REFERENCEs, the quantities outside their envelope. `coupling.py compare OUT REFERENCE...` compares saved runs |
| `screens.py OUT [REFERENCE]` | the drawn frames: at every present (code $129c4) the screen just drawn (B+$b8dc), 30 frames (`FRAMES`) in each of the cockpit, F5 and F6 views; with REFERENCE, frame by frame against it. `screens.py compare OUT REFERENCE` compares saved runs |
| `route.py OUT STEP...` | a scripted input route, for exploring |

```sh
cd games/Gunship2000
make verify VARIANT=Gunship2000AGA
BUILD=verify python3 tools/profile_flight.py tmp/prof/ref     # about 25 s of wall time
python3 tools/aprof_report.py tmp/prof/ref
SLAVE=tmp/exp/x.slave python3 tools/profile_flight.py tmp/prof/x tmp/prof/ref
```

The coupling test (P4d), each run about 60 s of wall time:

```sh
make verify VARIANT=Gunship2000AGA
for d in 0 1 2 3; do INPUT_DELAY=$d BUILD=verify python3 tools/coupling.py tmp/prof/c-cap-d$d; done
WHD_ARGS=CUSTOM2=1 BUILD=verify python3 tools/coupling.py tmp/prof/c-fps tmp/prof/c-cap-d0 \
    tmp/prof/c-cap-d1 tmp/prof/c-cap-d2 tmp/prof/c-cap-d3
```

The references are the 6-tick cap with the inputs 0-3 fields later: the 1 s turn's heading
alone spreads by 4 degrees with that (8842-10283 of 65536). `WHD_ARGS="CUSTOM2=1 CUSTOM3=N"`
makes every frame at least N fields. `DUMPS=1` also saves the data and BSS hunks at each
sample (`OUT/dumps/`).

The renderer check (P5c): the same frames as the blitter build. At the cap on the a1200-030
every frame takes 6 ticks, so a capped run is deterministic; on the a1200-fast (slower than
the cap) fix the frame length instead, `WHD_ARGS="CUSTOM2=1 CUSTOM3=7"`, for both runs:

```sh
SLAVE=tmp/exp/blit.slave python3 tools/screens.py tmp/prof/s-blit
SLAVE=tmp/exp/new.slave python3 tools/screens.py tmp/prof/s-new tmp/prof/s-blit
```

Compare slaves and machines with VERIFY builds (scratch slaves with `-DVERIFY=1`): they fly the
same mission (`internals.md`, "Slave patches"), whose cockpit shots then agree to 0.01.

The route is the duty roster (the whiteboard), a right click on the first record (WOC
ERASE-ME), name `test`, Return, Return, unit `test`, Return, the record, the door, the photo,
the map, five clicks on the keypad, the red Aux Power Unit tab and the switch under it. Each
step waits for its screen by colour (`profile_flight.screen()`); after the switch the flight
loads behind a black screen for several seconds, and the cockpit is the next lit picture.

Traps:

- aprof refuses an MMU core: the profiling 68030 is the shared `a1200-030` with
  `--uae_mmu_model=0`. It makes no difference to the game: WHDLoad uses a 68030's MMU only with
  `MMU/S` (`$WHDLOAD/Docs/en/mmu.html`), and the `a1200-030-mmu` machine gave the same
  15.33 fps with the cap at 1 tick (on another mission).
- **The mission depends on timing.** Outside VERIFY builds, the front end's choice of
  mission, helicopter and time of day changes with the CPU and the cache setup (TANGO 1,
  GOLF 1 and QUEBEC 1 on three 68030 runs), so only VERIFY runs compare.
- The front end reads the buttons once per animation frame: clicks hold 10 fields. Typed
  letters hold 4 and wait 10; keys in flight hold 10 (3 was missed).
- In the coupling test the player's position table entry is B+$127a (BSS, not data), the
  player object B+$d348; entry 1 also changes, not yet identified (not compared).
- `gs2.locate` takes each hunk's base by the most common value over the code's relocations:
  the CUSTOM2 patches overwrite some, and the PRELOADed file image matches the signature too.
- `aprof_report.py` names the slave's renderer routines `slave 0xfab6` and `slave 0x13832`:
  `gs2.locate` reads the `jmp` targets the slave patched in (`layout.json`, `slave_jumps`).
- The cockpit check (REFERENCE) compares the first lit cockpit picture. Uncapped on the
  a1200-fast its HUD (the target lock, the screen in the middle) depends on the drawing
  speed, so leave out the REFERENCE there.
- The gdb stub takes about 20 software breakpoints at once.
- One frame in a 150-field window is 0.33 fps: for changes of a few percent use
  `SEGMENT=600`. A change in the flight's start-up time (a copy, a wait) moves its timing and
  so the scenes against an older run; compare against a slave with the same delay.
- **The ECS route differs**: its WOC ERASE-ME record is the last on the board, clicks hold 30
  fields (the 68000 front end reads the buttons less often), there is no tent photo, the
  crack enters the code, and each click on the safety switch the front end sees toggles its
  cover, so the route clicks until the flight loads. The board's order also varies between
  runs (once ERASE-ME was first): rerun when the route stops at the office.
- aprof profiles the 68020 and up only; on the `a500` `profile_flight.py` counts frames.
- The CD32 version's function keys are the pad's buttons (`fakepad.s`): F5 and F6 do not
  change the view, so profile it with `VIEWS=cockpit`.
- Frames compare between renderer builds only when every frame takes the same game time: at
  the cap a frame slower than 6 ticks (the ECS chase view's first, on a 68030 with the blitter)
  moves the game time on, so use `WHD_ARGS="CUSTOM2=1 CUSTOM3=10"` there.
- `NTSC=1` (`common/run.sh`) boots NTSC: the route holds, but the front end then picks
  another mission, also in VERIFY builds, so NTSC runs compare only with each other.
- The installed aprof writes `AITDPROF 1` for `APROF 1`; `aprof_report.py` reads either.
  Its returns are unpaired, so the report uses flat PC costs.
- The CPU clock in the profile header is `colorclock × CYCLE_UNIT / cycleunit` (50.4 MHz on
  the a1200-030, 14.2 on the a1200-fast).
