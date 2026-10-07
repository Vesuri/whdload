# Profiling the original Legends of Valour

> **Read this before running, driving or tracing the game, or quoting any performance number.**
> Set up 2026-10-05 on this machine (macOS, x86_64 FS-UAE in `~/.local/fs-uae` with the Barto gdb
> stub), following Test Drive 2 `docs/new-game-playbook.md`. The harness is Test
> Drive II's (an OS game under kickemu, like this one) with Indianapolis 500's lldb fix.

## TL;DR

```sh
source amiga/env.sh
python3 tools/unpack.py                                   # once: decrunch AMIGA2 -> tmp/unpacked/
JOY0=none CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536 WARP=1 \
  python3 tools/lov.py serve > amiga/.run/serve.log 2>&1 &
python3 tools/lov.py shot "$PWD/amiga/.run/now.png"        # 1-field trace -> screenshot
python3 tools/lov.py gdb 'dump binary memory /tmp/lov-code.bin 0xc00000 0xd80000'
python3 tools/lov.py profile 5 "$PWD/tmp/prof/x/trace.bin"
python3 tools/lov_report.py tmp/prof/x/trace.bin tmp/prof/x/code.bin --base 0xc00000
python3 tools/lov.py quit
```

**Fixed window** (§7): `tools/fixed_window.sh OUT` builds the VERIFY slave, boots with the
`spin` tape and traces 100 fields from the tape's anchor; `frames.py` gives fps, `lov_report.py`
the profile.  `profile_demo.sh`, `swap_fields.py`, `ingame.py` and the `state_*` tools are still
Test Drive II's game-specific versions with only the names changed.

## 1. The game and the slave

| Field | Value |
|---|---|
| Archive | `LegendsOfValour_v1.0_0837.lha` (Retroplay, pre-installed): `LegendsOfValour.Slave` (4 488 bytes), `data/` (3.2 MB: `AMIGA2`, `charact`, `textfile`, pictures, maps). Hashes in `tmp/archive.sha256` |
| Slave | CFou! v1.0 (06.02.2005), **no source**. Decode it with `tools/slave_info.py [--pl OFF]` |
| Header | `ws_Version` 16, flags `$2402` (NoError, EmulPriv, Examine), `ws_BaseMemSize` `$80000`, `ws_ExpMem` `$C0000` (256 KB Kickstart + 512 KB), CurrentDir `data`, KeyExit `$59` (F10), no `slv_config` (v16) |
| Type | **OS game, kickemu Kickstart 1.3** (`ws_kickname` `34005.a500`, `$40000` bytes, CRC `$F9E3`); needs `kick34005.A500` + `.RTB` in `DEVS:Kickstarts` (run.sh copies them) |
| Kick patches | `slave+$60`: the stock kick13.s list (70 entries, `slave_info.py --pl 60`), applied with `resload_Patch` to ExpMem, then `jmp ExpMem+2` |
| `_bootdos` | `slave+$fa4`. `resload_Control` reads CUSTOM1 (`slave+$10fc`); assigns `LOV:`; opens and CRC16s the first 300 bytes of `AMIGA2` (result unused); `LoadSeg`s **`AMIGA2`**, or **`CHARACT`** (character creation) when CUSTOM1≠0; tells WHDLoad the segment list; patches; calls the program with `d0=1, a0="\n"`; `resload_Abort` on return |
| Stub patches | if the first long of hunk 0 is `$487A0178` (the PowerPacker stub): `jmp slave+$110c` over the stub's final `movem/rts` at stub `+$176`, and `bra.s` over the decrunch colour flash at stub `+$210` |
| Game patches | `slave+$110c`, run after the stub has loaded the real program: manual protection, **hunk 1** offsets. Version A: `h1:013e0` `cmp.l d7,d6; bne` → `move.l d6,d7; nop`, `nop nop` at `h1:0141e`, `nop` at `h1:01422`. **Version B (this AMIGA2)**: the same at `h1:013d8`, `h1:01416`, `h1:0141a` |

**The code.** `data/AMIGA2` (95 124 bytes) is a two-hunk file: a 548-byte PowerPacker stub and the
packed data (table 9,10,12,12). The stub decrunches in place and then **acts as its own LoadSeg**:
it AllocMems every hunk of the decrunched hunk file, copies and relocates it, chains them as a
segment list (`[size+8][next BPTR][hunk]`) and returns into hunk 0. `tools/unpack.py` is a port of
that decruncher and writes `tmp/unpacked/AMIGA2` (199 436 bytes, byte-exact) and `charact`.

| Hunk | Type | Size | | Hunk | Type | Size |
|---|---|---|---|---|---|---|
| 0 | code | `$199C` | | 9 | code | `$660` |
| 1 | code | `$2C2C` (protection) | | 10 | code | `$C4` |
| 2 | code | `$63FC` | | 11 | data | `$5E3C` file, `$A4DC` alloc |
| 3 | code | `$5BC` | | **12** | code | **`$179D0`** (asm, no `link`, reads VHPOSR) |
| 4–8 | code | `$B0`..`$2700` | | 13–16 | code | `$14`..`$184` (library stubs) |

Hunks 0–10 are **Lattice/SAS C** (`link a5` prologues, "** Stack Overflow **", "*** Break:"); hunk
12 looks hand-written. Docs name code as `hN:OFFSET`.

## 2. The machine

Same as Test Drive II: Kickstart 3.1 host + Workbench 2.04 floppy boot DH0, whose startup-sequence
runs `WHDLoad LegendsOfValour.Slave PRELOAD SPLASHDELAY=0 NOREQ` on DH1 (a fresh copy of
`tmp/game/LegendsOfValour` + WHDLoad; **save games written during a run are lost** when the next
run recreates DH1). The ReadMe asks for 0.5 MB chip + 0.5 MB other memory.

**A500-equivalent**: `JOY0=none CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536`. Observed
layout on that machine (one boot, 2026-10-05; WHDLoad memory is slow RAM at `$C00000`): Kickstart
image `$CB5000`, hunks spread over `$CFDBE8..$D5B8B8` (h12 at `$D43EE8`), live slave `$D7DD08`.
Every hunk was in the slow-RAM dump, none in chip. `lov_report.regions(dump, base, chip)` finds
them all by voting for hunk 0 and walking the segment chain (checking each AllocMem size), because
the freed decrunch buffer still holds a stale copy of every hunk.

**`JOY0=none` for every capture.** The host mouse feeds port 0 even with input grab off, and the
game is mouse-driven: the user moving the mouse over a capture window took it from the start
screen into the game.

## 3. Driving and tracing (`tools/lov.py`)

Test Drive II's server (`serve`, `stop/cont`, `gdb`, `shot`, `profile`, `wait`, `until`, `quit`;
socket `amiga/.run/lov.sock`) with Indianapolis 500's single-attach `LLDB_FIX` (same FS-UAE
binary, `BASETEXT_VM = 0x32dea04`). All the stub facts in the playbook §5 apply. A 5-field
`profile` took 48 s, most of it the lldb attach.

## 4. What the game does without input

With `JOY0=none` the boot reaches the **start screen** (a static 3D street with three buttons:
load game (green), a red button not yet identified, Amiga DOS) and stays there; there is **no attract
demo**. Clicking the load button shows the save-slot screen; loading a slot enters the game (seen
by the user, 2026-10-05).

Start-screen trace (5 fields, A500-eq., `tmp/prof/start`): 91.5% of the CPU on the main stack in
a polling loop through `h6:0076c`, `h0:01524`, `h2:00000`, `h1:01b8c`, `h12:16a4e`, `h12:0fe66`
(each called ~43 times a field), 7.6% in the Kickstart. Not a gameplay figure.

## 5. Input and time, as the game reads them

All in **h12's vertical-blank server `h12:06404`** (found statically; runs in the interrupt
context `ctx1` of the start-screen trace):

| Offset | What |
|---|---|
| `h12:06404` | `addq.l #1,h11:0602c` — **field counter** (time source). `h12:063ac` combines its low word with VPOSR into a beam-time value; `h12:063f0` waits for the next field |
| `h12:0643e` | `move.w $dff00a,d0` (**JOY0DAT**), deltas against `h12:0002c` added to the **pointer accumulators `h11:008d2` (x) / `h11:008d4` (y)** |
| `h12:06472` | optional per-field callback through `h12:0648e` |
| `h12:06480` → `h12:05298` | buttons: left = CIAAPRA bit 6 (`h12:0529a`), right = POTINP bit 10 (`h12:052ee`), each debounced over 2 fields; state bits in **`h12:05292`** (bit 0 left, bit 1 right), read by `h12:05288` |

No CIA keyboard reads in AMIGA2; the keyboard, if used, comes through the OS (intuition is opened
by h0/h11). So the game can be driven entirely by replacing the JOY0DAT read and the button call
in this server with a tape indexed by the field counter.

## 6. The rebuilt slave and the input tape

`whdload/LegendsOfValourHD.s` (`make -C whdload`, `make -C whdload verify`) rebuilds CFou!'s v1.0
on WHDLoad 20.0's `kick13.asm` example (09.11.25) and the 2025 `kick13.s`, with the example's
options: `IOCACHE = 1024` (without it every small game `Read()` was a resload call, i.e. an OS
switch unless PRELOADed — slow, with a garbled display during IO), `CACHECHIP`, `SETPATCH`,
`SEGTRACKER`, `POINTERTICKS`, `SETKEYBOARD`, `HRTMON`, `WHDCTRL`. `slv_Version` 17: the host's
WHDLoad is 19.2, so no v20 `ws_MemConfig`. PRELOAD only helps when the 3.2 MB of data fits:
interactive `run.sh` now defaults to 1 MB chip + 8 MB fast; the A500-equivalent machine cannot
preload it.

**Input tape** (VERIFY build, `CUSTOM5=1`, `whdload/tape.s`): h12:05298 (the VBL server's button
routine) jumps into the slave, which writes the tape's pointer position into the game window's
`MouseX/MouseY` (the game copies them every poll, `h1:01b8c`) and its buttons into `h12:05292`.
Script → file: `tools/tape.py` (`FIELDS X Y [L|R|A|W]` lines, window coordinates = (screenshot
x − 75) / 2, (y − 38) / 2). `tools/tape_explore.sh SCRIPT OUT [COUNT STEP]` boots it and takes
screenshots every STEP s of warp, labelled with the tape field (exploration only). Tape field 0
is the first VBL after the game installs its server.

Screens do not arrive at fixed fields (the start screen came anywhere between field 2 400 and
2 750 in different routes), so fixed waits either misfire or waste minutes. A **`W` entry** waits
on game state instead: the tape also hooks the game's button hit test `h6:0076c` (list, x, y) to
remember the list it was given; the entry holds until that list has the button with id FIELDS
(0: any) under (X,Y). It covers every screen that hit-tests through h6 (start screen, slot
screen, the game's panels once a frame) but **not the conversation panel**, which polls through
h2. An **`A` entry** marks the anchor: its first field runs `_tape_anchor`, where
`fixed_window.sh` breaks.

What the screens do (`tools/tapes/`):
- Start screen: green = load a **character** (`Charact.__N`, written by `CUSTOM1` character
  creation), red = load a **saved game** (`Legend1.__N`), Amiga DOS. The archive has neither.
- Save-slot screen (`h8:001de`): bars 1–8 select, left die loads (only an existing file), middle
  die switches save disk, **right die cancels → the game starts with the default character**.
- In game, a townsman may walk up and talk: soon after the start on a 68020, often not at all
  on the A500. His speech blocks the game (the main loop only waits for fields) until EXIT
  (75,183) in the conversation panel; clicking there with no conversation hits the status bar,
  harmlessly.
- View size: the game **starts in the medium view**; nothing is saved (and DH1 is fresh every
  run). Computer button (15,188) → options dialog → second icon from the right on the top row
  (193,52); each click cycles medium → small → large → medium (`tools/tapes/viewcycle.txt`);
  clicking outside the dialog applies it. The townsman's conversation shows the face in a
  full-frame view, which looks like the large view.
- **Benchmark route `spin.txt`**: W-driven through the start and slot screens, default
  character, two clicks → large view, 1 500 fields clicking EXIT every 100 (dismisses the
  greeting on any machine), then 250 fields turning right (143,148) and the anchor; the turn
  continues through the window. The game redraws the view continuously, also when standing still.

## 7. Fixed window, frame counter, baseline

**Window.** `tools/fixed_window.sh OUT [TAPE]` (A500-equivalent unless `CHIP_KB` etc. say
otherwise): builds the VERIFY slave and keeps it and its listing in OUT, boots with
`DETERMINISTIC=1`, finds the live slave in a dump, breaks at `slave + _tape_anchor` (from the
listing) and traces `FIELDS` fields (100; the stub caps a profile at 100). `anchor.txt` records
the tape field and the game's own field counter (`h11:0602c`) at the anchor.

**Reproducibility.** `tools/compare_traces.py A B` compares every field's instruction records
(PCs, costs, registers), DMA records and screenshot. Two fresh A500-equivalent boots of the
spin route (`tmp/prof/a500`, `a500b`, 2026-10-05): anchor at tape field 4 729 / game field
4 730 in both, **all 100 fields identical** in all three (also for the route without the EXIT
phase, `spin1`/`spin2`). **Run one capture at a time:** with a second emulator capturing in
parallel both debugger sessions failed, and a boot that survived had the Intuition pointer
elsewhere and a one-field phase shift.

**Frame counter.** The game never writes the copper. The main loop renders the view into a
chunky buffer (one byte per pixel, 192 bytes wide; `h12:027bc`) and then shows it with
`h12:05ea6`, a dispatcher on a view-size word that waits for the beam (`h12:063ce`) and
converts the buffer into the screen's 4 bitplanes (chunky-to-planar, `h12:054ce`..`055e6`
for this size: `add.b`/`addx.w` bit shuffles, 8 pixels per step, with a shortcut for 8 equal
pixels), or copies with `BltBitMap` + `WaitBlit`. `frames.py` counts entries of `h12:05ea6`.
`swap_fields.py` now watches that same display entry (validated against the trace in §8).

**Baseline, spin route, large view, 100 fields from the anchor (2026-10-05):**

| Machine | fps | fields/frame | CPU busy | Command |
|---|---|---|---|---|
| A500-eq. (68000 7 MHz, 512K chip + 1.5M slow) | **2.5** | 19.75 (4 frames in 79 fields) | 100% (no STOP) | `tools/fixed_window.sh tmp/prof/a500` |
| A1200 (68EC020 14 MHz, 2M chip + 4M fast) | **12.5** | 4.0 (24 frames in 96 fields) | 100% | `AMIGA_MODEL=A1200 KICKSTART=…/kick40068.A1200 CHIP_KB=2048 FAST_KB=4096 CPU=68EC020 EXTRA_ARGS=--slow_memory=0 tools/fixed_window.sh tmp/prof/a1200` |

Where the time goes (share of all CPU cycles in the window; inclusive unless noted):

| Work | A500-eq. | 68020 | Code |
|---|---|---|---|
| Render the 3D view | 43.8% | 53.1% | `h12:027bc` → `h12:02808` (per-column wall setup, 11.7% / 14.1% self) |
| — textured wall columns | 26.8% self | 31.8% self | `h12:04c1a`: scaled column, drawn outward from the middle both ways |
| Chunky-to-planar to the screen | 26.0% | 29.9% | `h12:05ea6` (its loop at `054ce` shows up as "h12:05288" self: no prologues in h12) |
| Game logic and objects (h5) | 15.8% | 6.2% | `h5:02358` → `h5:01f2a` → `h5:00292` |
| — scaled sprites (people, pillars) | 12.6% self | 4.9% self | `h12:05114`: masked, z-tested columns (scene-dependent, see below) |
| Interrupts and OS | ~9% | ~3% | VBL server `h12:06404` → module player in chip RAM (`?020124`), Kickstart |

No blitter waits are polled (0%); one level-3 interrupt (vertical blank) per field; DMA slots on
the A500-eq.: 42% CPU, 22.5% bitplane, 31% free. The two windows do not show the same scene: the
W steps finish earlier on the faster machine (anchor at tape field 4 729 on the A500-eq., 4 333
on the 68020), and the 68020's *last* field shows the view of the A500's *first*. So the sprite
share differs, and whether the turn and the townsman advance per field or per rendered frame is
the first game-time question (playbook §9).


## 8. Performance patch validation (2026-10-05–06)

### W0 groundwork

The slave now records the segment chain in `_hunks[17]`, shared with the VERIFY input tape,
and queries `WHDLTAG_ATTNFLAGS_GET` and CUSTOM2 in `_bootdos`. CUSTOM2 bits 0–5 are reserved
for W1–W6, respectively. Only implemented options are exposed in `slv_config`; patches remain
opt-in in the slave. The user chose to enable completed, verified patches in local preferences,
accept the existing game-time behaviour (including faster world progression below 4.2 fps),
and defer W7. No change to movement, AI timing, the beam wait, or the 25 fps cap is authorized
by this performance work.

Build outputs now live in `tmp/build/`, including the listing. Captures retain their exact
slave and listing. `tools/check_disabled.py` compares each `PERF_RANGE` declaration with the
local decrunched executable, applying its RELOC32 fixups before comparison. The W1 entry
range is ten bytes (whole `movem` and `movea` instructions), rather than a six-byte jump that
would split the second instruction.

**Original-slave behaviour check:**

```
python3 tools/behaviour_check.py tmp/prof/w0-original
make -C whdload
python3 tools/behaviour_check.py tmp/prof/w0-rebuilt --slave tmp/build/LegendsOfValour.Slave
```

Each capture calibrates h6's loaded address, then reboots with a breakpoint armed before
reset advances at the **first `h6:0076c` button poll**. Neither slave receives tape input.
At this start-screen point both have geometry 192 × 92 and byte-identical chunky colours
(high nibbles) and four-plane view bytes. The plane-byte SHA256 is
`9b8f447c8b27a0c3f93502cb1522acdcb8586546f7f16584fb9d0f7442f98db6`.
Full screenshots agree except the 18 × 18 Intuition pointer at the top-left: the rebuilt
kickemu uses a red pointer, the original a grey pointer. The first poll is at game field
2,450 (original) / 2,453 (rebuilt). This verifies the no-input start screen; it does not claim
identical IO timing or a full gameplay-state equivalence test.

**Tape/frame-counter validation:** `WHD_ARGS=CUSTOM2=0 tools/fixed_window.sh tmp/prof/w0-trace`
reaches tape field 4,729 / game field 4,730, the existing baseline anchor. The disabled-hook
checker passes for `h12:054ce` (ten original bytes). The breakpoint counter now watches
`h12:05ea6` and the VBL entry `h12:06404`, using debugger convenience variables only.

`KEEP_SLAVE=1 SWAP_ONLY=1 WHD_ARGS=CUSTOM2=0 tools/fixed_window.sh tmp/prof/w0-swaps`
(retaining the same slave/listing) gives **exactly the full trace's 100-field frame pattern**:
entries at fields 3, 21, 40, 61, 82; four intervals across 79 fields = 19.75 fields/frame,
2.5 fps. All 17 `_hunks` entries match the live segment chain. The A500 attention flags are
`$200` (no AFF_68020). The harness now refreshes its memory dump at the anchor before using
STATE_ONLY/SWAP_ONLY, rather than relying on a pre-decrunch dump.


### W1 CPU-selected Kalms C2P

**Implemented and verified.** CUSTOM2 bit 0 replaces only `h12:054ce`'s first ten bytes
with a jump and two NOPs. The adapter preserves d0–a6 and returns to the original caller.
The patch checks the relocated entry before writing and flushes caches afterwards.
The hunk relocation cross-reference has no absolute references into these ten bytes;
the h12 branch audit finds the dispatcher entry at `h12:05eb2`, with none into the middle.
CUSTOM2=0 passes `check_disabled.py` on both CPUs and both benchmark routes below.

WHDLoad attention flags select the word-writing routine on 68000/10 (`$200` observed),
the longword-writing routine on 68020+ (`$203` observed). The two Kalms files are vendored
at commit `d8ecf79a3325615305dd800ae7704b518e0d9dda`; all local changes are listed in
[the vendor README](../whdload/kalms/README.md). Both ignore the low nibble, use source
stride 192, and finish each row's pipeline before skipping to the next row. Contrary to
the initial plan, the longword routine has no upstream nibble masks: explicit masks cost
extra instructions. Measured costs below replace the original cycle estimates.

**Actual geometry**, recorded by the successful in-game twins. Plane pointers
`h12:00042..00051` are reread every call. Each is the current screen plane base plus
`y*40+x/8`; the four bases are separated by 8,000 bytes, with 40-byte row stride.
Offsets here are relative to each current plane base, not capture-specific addresses.

| View | Width × height | Origin x,y | Original plane offset | Enclosing x,width | Enclosing plane offset |
|---|---|---|---|---|---|
| Large | 192 × 92 | 64,16 | `$288` | 64,192 | `$288` |
| Medium | 112 × 64 | 104,30 | `$4bd` | 96,128 | `$4bc` |
| Small | 80 × 48 | 120,38 | `$5ff` | 112,96 | `$5fe` |

Large view reads the game buffer directly. Medium/small use a private staging buffer:
copy the active pixels at source column zero, add eight black pixels at each side, and
advance source rows by 192. Never read/write before chunky column zero. The smaller-view
enclosing destination is word aligned; large is also longword aligned.

A first medium-view twin found an important transition case: extra destination columns
still held earlier large-view pixels, rather than black. The adapter saves/restores those
extra screen bytes around conversion. Source padding is always black; surrounding screen
pixels stay exactly as the original left them, including during view-size transitions.

**Pixel-exact self-test:** VERIFY + CUSTOM2=1 + CUSTOM5=3 runs the relocated original
routine into scratch planes seeded from the screen, then the replacement into the screen.
It compares all 40 bytes of every row in all four planes, including margins/guards, and
aborts at the first differing byte. Before both routines it XORs every active low nibble
with `$0f`, restoring source bytes afterwards: duplicated colour nibbles cannot hide a
wrong nibble merge. The retained early failing run demonstrated the abort path; it is not
counted as a successful test. The host requires the completion breakpoint, not merely an
interrupted debugger session.

```
TAPE_OPTIONS=3 SELFTEST_FRAMES=300 WHD_ARGS=CUSTOM2=1 tools/fixed_window.sh tmp/prof/w1-views-a500 tools/tapes/c2p-views.txt
AMIGA_MODEL=A1200 KICKSTART="$AMIGA_SHARE/Kickstarts/kick40068.A1200" CHIP_KB=2048 FAST_KB=4096 CPU=68EC020 EXTRA_ARGS=--slow_memory=0 TAPE_OPTIONS=3 SELFTEST_FRAMES=300 WHD_ARGS=CUSTOM2=1 tools/fixed_window.sh tmp/prof/w1-views-a1200 tools/tapes/c2p-views.txt
python3 tools/c2p_check.py tmp/prof/w1-views-a500 --require-all-views
python3 tools/c2p_check.py tmp/prof/w1-views-a1200 --base 0x200000 --require-all-views
```

| CPU/converter | Medium twins | Small twins | Large twins | Total |
|---|---|---|---|---|
| 68000 / word | 37 | 104 | 389 | 530 |
| 68020 / longword | 297 | 427 | 606 | 1,330 |

All **1,860** comparisons passed. The route visits all sizes, handles the townsman's
conversation and continues turning through street/wall/sprite views; at least 300 large
frames complete after the anchor on each CPU. Performance runs use CUSTOM5=1, excluding
all twin work. Normal builds contain neither the twin nor input tape.

**100-field spin A/B**, sequential captures with the same retained VERIFY slave in all
four runs (SHA256 `1b94f390bb8e6719720ee39cde601da0db80ddb588ae44dddc9e46cbbe8bafe7`).
Only CUSTOM2 differs. Geometry is 192 × 92 in every measured window.

```
WHD_ARGS=CUSTOM2=0 tools/fixed_window.sh tmp/prof/w1-a500-off
WHD_ARGS=CUSTOM2=1 tools/fixed_window.sh tmp/prof/w1-a500-on
AMIGA_MODEL=A1200 KICKSTART="$AMIGA_SHARE/Kickstarts/kick40068.A1200" CHIP_KB=2048 FAST_KB=4096 CPU=68EC020 EXTRA_ARGS=--slow_memory=0 WHD_ARGS=CUSTOM2=0 tools/fixed_window.sh tmp/prof/w1-a1200-off
AMIGA_MODEL=A1200 KICKSTART="$AMIGA_SHARE/Kickstarts/kick40068.A1200" CHIP_KB=2048 FAST_KB=4096 CPU=68EC020 EXTRA_ARGS=--slow_memory=0 WHD_ARGS=CUSTOM2=1 tools/fixed_window.sh tmp/prof/w1-a1200-on
```

| Machine | fps off → on | Frame intervals / fields off → on | C2P completed calls off → on | Main-task cycles/call off → on | Inclusive cycles/call off → on |
|---|---|---|---|---|---|
| A500-equivalent | **2.5 → 3.0** | 4/79 → 5/82 | 5 → 6 | 748,288 → 502,191 (−32.9%) | 803,106 → 540,342 |
| 14 MHz 68020 + fast | **12.4 → 14.8** | 24/97 → 29/98 | 25 → 30 | 356,316 → 169,955 (−52.3%) | 364,280 → 175,143 |

Use this fresh paired 68020 baseline (24 intervals/97 fields); §7's earlier 12.5 fps
window had 24/96. Unrounded fps improves 20.4% / 19.6%, respectively. The faster turn
renders a different scene, most visibly on the 020. First/last screenshots of both
variants are shown in these ignored local comparison sheets (off left, on right;
first above, last below):

![A500 spin off/on first/last](../tmp/prof/w1-a500-comparison.png)
![68020 spin off/on first/last](../tmp/prof/w1-a1200-comparison.png)

**Scene-stable second A/B:** `tools/tapes/wall.txt` uses VERIFY's new H wait to stop at
heading 150, then waits 1,000 fields before the anchor. H reads `h11:08c28`; the ordinary
counting path adds no work inside the performance window. The shipping slave has no H/tape
code. Repeat the four commands above using `w1-wall-...` output names and append
`tools/tapes/wall.txt`. The retained slave is identical across all four wall captures,
SHA256 `b091177a3a85c67904d3d97d427e4a1cea950384b4ea86dc9c2a479cd52336b9`.
Its C2P code matches the spin build; only the VERIFY heading fixture was added.

| Machine | fps off → on | Frame intervals / fields off → on | C2P completed calls off → on | Main-task cycles/call off → on | Inclusive cycles/call off → on |
|---|---|---|---|---|---|
| A500-equivalent | **2.8 → 3.1** | 5/89 → 6/97 | 6 → 6 | 741,853 → 501,837 (−32.4%) | 800,207 → 541,502 |
| 14 MHz 68020 + fast | **11.9 → 14.1** | 23/97 → 27/96 | 24 → 28 | 363,379 → 169,915 (−53.2%) | 372,102 → 174,543 |

Unrounded fps improves 10.1% / 18.6%. All four viewport images per machine are
pixel-identical (physical crop 202,68–586,252 in the 754 × 576 captures). Player position
is 5216,3616 and heading 150 in all four state dumps; visible-object render records also
match. This supports the cycle savings without the spin route's changed scene.

![A500 wall off/on first/last](../tmp/prof/w1-wall-a500-comparison.png)
![68020 wall off/on first/last](../tmp/prof/w1-wall-a1200-comparison.png)

Each output retains slave/listing, code dump, trace, tape, anchor, logs, first/last images,
`frames.txt`, `profile.txt`, `blocks.txt`, `c2p.txt`, and `state.json`. Analyse with the retained slave:

```
SLAVE=tmp/prof/w1-a500-off/slave.slave python3 tools/frames.py tmp/prof/w1-a500-off/trace.bin tmp/prof/w1-a500-off/code.bin 0xc00000
python3 tools/c2p_report.py tmp/prof/w1-a500-off
python3 tools/c2p_report.py tmp/prof/w1-a1200-on --base 0x200000
SLAVE=tmp/prof/w1-a500-off/slave.slave python3 tools/check_disabled.py tmp/prof/w1-a500-off
python3 tools/lov_state.py tmp/prof/w1-a1200-on --base 0x200000
```

`c2p_report.py` pairs the unchanged entry `h12:054ce` with the original or replacement
RTS at the same stack depth. Boundary calls are excluded. Inclusive costs include IRQs;
main-task costs exclude the separate IRQ stack and include the entire adapter. Large-view
replacement costs are about 28.4 cycles/pixel on the 68000 and 9.6 on the 020, in trace-reported cycle units. The original's equal-pixel shortcut remains scene
dependent, so both routes and both measures are retained.

**Game-time check and limit.** State snapshots map heading to `h11:08c28`, player x/y to
`h11:08c1c`/`08c20` (A4 = h11 + `$8000`). A trace effective-address scan finds a movement
step reader at `h12:14b78`, `add.w -4232(a0),d0`, reading `h12:0cdd6`; it has no relocated
absolute operand. The A500 spin ends at heading 210 off / 255 on with step 48 in both;
the 020 ends at 150 off / 30 on, step 16 / 12, animation pacing 3 / 4. Position remains
5216,3616. Turning therefore remains coupled to the game's frame timing. The object
records dumped here are render records, not a mapped townsman world position; deeper
AI timing/state mapping remains open. The user accepted the existing behaviour. W1
changes no movement/AI timing instruction, 25 fps cap, beam wait, or one-shot conversion.

**Local preference:** `amiga/performance.env` (ignored) now enables only W1, mask 1.
`amiga/run.sh` builds the normal slave under `tmp/build-release` on the next interactive
boot. Explicit SLAVE/WHD_ARGS override the preference; captures always provide both.
No interactive `.run` emulator was started or modified. `make -C whdload
OUT=../tmp/build-release` assembles the normal slave with 68000/PIC checks; the VERIFY
build assembles too. W7 remains deferred; W2 is the next planned feature.

### W2 CPU-independent PUBLIC chunky allocation (2026-10-06)

CUSTOM2 bit 1 now replaces only the 20,000-byte chunky allocation with
`AllocMem(20000, MEMF_PUBLIC)`, on every CPU. Exec chooses its normal memory priority;
there is no MEMF_FAST requirement or CPU gate. Only slave-owned allocations use
`FreeMem(pointer,20000)`. Failed allocations retain the game's original pool allocator,
free and error handling. The two complete-instruction hooks are `h1:022c6` and
`h1:02760`; both signatures are checked before patching. All other allocations retain
their original paths. The [pointer/ownership audit](w2-audit.md) covers every chunky
pointer user and finds no DMA or blitter consumer of that buffer.

**Correctness.** The retained VERIFY build is SHA256
`b7484e3af7fe5628252cab342e9f3b9c18051165d356ecd8cbd75fca82cfda54`.
With CUSTOM2=3 / CUSTOM5=11, original-versus-Kalms pixel twins passed on the W2 buffer:

| Processor / physical memory | Large | Medium | Small | Total |
|---|---:|---:|---:|---:|
| 68000, 1 MB chip + 8 MB fast | 371 | 73 | 107 | 551 |
| 68EC020, 2 MB chip + 4 MB fast | 746 | 347 | 452 | 1,545 |

Both use the correct CPU-selected converter, perturb unrelated low nibbles, and cover
192×92, 112×64 and 80×48 views. Both also pass allocation/free/reallocation through the
same dispatchers used by the game, clearing ownership on free and recording PUBLIC/FAST
memory in physical fast RAM. CUSTOM5=13 forces the PUBLIC attempt to fail: the 020 reaches
the wall anchor using the original chip-memory pool and passes the same lifecycle check.
See `tmp/prof/w2-views-68000-fast-1m`, `w2-views-a1200` and
`w2-public-fallback-a1200`. The normal build excludes these test controls and counters.

**Performance protocol.** Every capture uses the identical retained slave above,
CUSTOM5=1, a 100-field window, JOY0=none and `amiga/.cap`. W1 stays enabled; only W2
changes (CUSTOM2=1 off / 3 on). Captures are sequential. The A500-equivalent is unchanged:
512 KB chip + 1.5 MB expansion slow RAM, 68000 at 7 MHz. The 020 configuration is unchanged:
A1200, 2 MB chip + 4 MB fast, 68EC020 at 14 MHz. W2 buffers on the first machine actually
land in expansion **slow** RAM, despite Exec's PUBLIC/FAST flags; on the 020 they land
in physical fast RAM. This distinction is confirmed from ownership, TypeOfMem and the
captured memory region, rather than assuming all memory flagged FAST has a fast bus.

Reproduce the captures and their analysis (`check_disabled`/`chunky_check`, `frames`, profile,
C2P, render, blocks, state) with `tools/ab_window.sh w2 1 3 "spin wall" "a500 a1200 68000-fast"`,
then `python3 tools/ab_summary.py w2` (fps, cycles/call, state, comparison sheets; summary kept
in `tmp/prof/w2-results.txt`). The capture commands alone, one at a time:

```sh
for route in spin wall; do
  for mode in off on; do
    bits=1; [ "$mode" != on ] || bits=3
    AMIGA_MODEL=A500 CPU=68000 CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536 TAPE_OPTIONS=1 WHD_ARGS=CUSTOM2=$bits tools/fixed_window.sh tmp/prof/w2-$route-a500-$mode tools/tapes/$route.txt
  done
  for mode in off on; do
    bits=1; [ "$mode" != on ] || bits=3
    AMIGA_MODEL=A1200 KICKSTART="$AMIGA_SHARE/Kickstarts/kick40068.A1200" CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 EXTRA_ARGS=--slow_memory=0 TAPE_OPTIONS=1 WHD_ARGS=CUSTOM2=$bits tools/fixed_window.sh tmp/prof/w2-$route-a1200-$mode tools/tapes/$route.txt
  done
done
```

**Turning window:**

| Machine | fps off → on | Intervals/fields | Completed C2P calls | Main-task cycles/call | Inclusive cycles/call |
|---|---|---|---|---|---|
| A500-equivalent | 3.0 → 3.0 | 5/82 → 5/82 | 6 → 6 | 502,064 → 502,198 | 540,215 → 537,349 |
| 14 MHz 68020 + fast | 14.9 → 16.0 | 28/94 → 30/94 | 29 → 31 | 169,973 → 144,062 (−15.2%) | 173,287 → 146,040 |

Unrounded 020 fps improves 7.1%. A500 first/last off/on screenshots and all state fields
match; its tiny cycle differences do not establish a speed gain. The 020 ends at heading
30 off / 135 on, with movement step 12 in both; position stays 5216,3616 but visible
objects differ. Renderer/wall comparisons on this route therefore include changed scenes.

![A500 W2 spin off/on first/last](../tmp/prof/w2-spin-a500-comparison.png)
![68020 W2 spin off/on first/last](../tmp/prof/w2-spin-a1200-comparison.png)

**Fixed wall:**

| Machine | fps off → on | Intervals/fields | Completed C2P calls | Main-task cycles/call | Inclusive cycles/call |
|---|---|---|---|---|---|
| A500-equivalent | 3.1 → 3.1 | 6/97 → 6/97 | 6 → 6 | 501,750 → 501,750 | 541,403 → 541,403 |
| 14 MHz 68020 + fast | 14.2 → 15.1 | 27/95 → 29/96 | 28 → 30 | 170,030 → 144,078 (−15.3%) | 174,070 → 147,128 |

Unrounded 020 fps improves 6.3%. All four viewports per machine are pixel-identical
(crop 202,68–586,252); position 5216,3616, heading 150 and visible-object records match.
The 020 whole screenshots match off/on. On the A500 only the far-right capture border
(x=751–753, y=0–303) differs outside the game viewport; do not claim whole-image equality.
The A500 movement step remains 48; the 020 changes 16 → 12 under the existing timing code.

| Machine / completed work | Calls off → on | Main-task cycles/call off → on | Inclusive cycles/call off → on |
|---|---|---|---|
| A500 renderer | 6 → 6 | 1,278,367 → 1,278,367 | 1,374,842 → 1,374,842 |
| A500 wall column | 1,152 → 1,152 | 4,276 → 4,276 | 4,631 → 4,631 |
| A500 sky/floor clear | 6 → 6 | 69,195 → 69,195 | 73,706 → 73,706 |
| 020 renderer | 28 → 29 | 661,428 → 629,439 (−4.8%) | 676,179 → 643,645 |
| 020 wall column | 5,443 → 5,857 | 2,361 → 2,277 (−3.6%) | 2,412 → 2,328 |
| 020 sky/floor clear | 29 → 30 | 37,228 → 19,222 (−48.4%) | 37,903 → 20,116 |

![A500 W2 wall off/on first/last](../tmp/prof/w2-wall-a500-comparison.png)
![68020 W2 wall off/on first/last](../tmp/prof/w2-wall-a1200-comparison.png)

**Additional 7 MHz 68000 with physical fast RAM:** A500 model, 1 MB chip + 8 MB
fast, no slow RAM. The smaller 512 KB chip + 4 MB fast VERIFY fixture hit the original
startup allocator failure loop before W2; the 1 MB/8 MB control boots successfully.
Both completed wall captures use the same retained build as the primary matrix.

```sh
for mode in off on; do
  bits=1; [ "$mode" != on ] || bits=3
  AMIGA_MODEL=A500 CPU=68000 CHIP_KB=1024 FAST_KB=8192 EXTRA_ARGS=--slow_memory=0 TAPE_OPTIONS=1 WHD_ARGS=CUSTOM2=$bits tools/fixed_window.sh tmp/prof/w2-wall-68000-fast-$mode tools/tapes/wall.txt
done
```

| Work | Calls off → on | Main-task cycles/call off → on | Inclusive cycles/call off → on |
|---|---|---|---|
| C2P | 6 → 7 | 496,192 → 496,679 | 533,916 → 535,026 |
| Renderer | 6 → 6 | 1,230,841 → 1,213,599 (−1.4%) | 1,319,703 → 1,303,583 |
| Wall column | 1,191 → 1,152 | 4,125 → 4,140 | 4,437 → 4,421 |
| Sky/floor clear | 6 → 6 | 73,454 → 68,878 (−6.2%) | 80,551 → 74,084 |

FPS is **3.2 → 3.2**, six intervals in 94 fields in both windows. The W2 buffer is
owned PUBLIC/FAST memory in the physical fast region. Anchor fields differ (5,483 off /
5,495 on), but heading 150, position 5216,3616, movement step 48 and object records
match; all four viewports and off/on whole screenshots match. There is no measured
FPS gain at stock 7 MHz; the small renderer/clear savings support allowing W2 on a
68000. Overclocked 68000 performance remains unmeasured.

![68000 with physical fast W2 wall off/on first/last](../tmp/prof/w2-wall-68000-fast-comparison.png)

**Analysis and limits.** Each output retains slave/listing, trace, code dump, tape,
anchor, logs, first/last screenshots, `frames.txt`, `profile.txt`, `blocks.txt`,
`c2p.txt`, `render.txt` and `state.json`. All ten VERIFY slave hashes match.
`render_report.py` pairs `h12:027bc`, the `04c1a`/`04cbe`/`04d42` column family,
and `051a2` clear with an RTS at their entry stack depth. Each routine excludes its
own partial boundary calls; column counts can include columns from partial render
frames. Inclusive costs include interrupts; main-task costs exclude the separate IRQ
stack, in the same trace-reported cycle units as W1. `blocks.py` produces the plan's
64-byte histogram with the whole-window cycle denominator.

```sh
OUT=tmp/prof/w2-wall-a1200-on
SLAVE="$OUT/slave.slave" python3 tools/frames.py "$OUT/trace.bin" "$OUT/code.bin" 0x200000
SLAVE="$OUT/slave.slave" python3 tools/lov_report.py "$OUT/trace.bin" "$OUT/code.bin" --base 0x200000
python3 tools/c2p_report.py "$OUT" --base 0x200000
python3 tools/render_report.py "$OUT" --base 0x200000
python3 tools/blocks.py "$OUT" --base 0x200000
python3 tools/lov_state.py "$OUT" --base 0x200000
python3 tools/chunky_check.py "$OUT" --base 0x200000 --expect fast
SLAVE=tmp/prof/w2-wall-a1200-off/slave.slave python3 tools/check_disabled.py tmp/prof/w2-wall-a1200-off --base 0x200000 --custom2 1
```

All five W2-off captures pass the disabled-byte check for both W2 ranges. The checker
also checks all three declared ranges with mask 0 on a retained all-off W1 capture.
The harness now stops during host memory-region discovery and rejects stops other
than the tape anchor: large dumps exposed a race that could miss the one-time anchor.
Interrupted exploratory runs and earlier explicit-FAST builds are excluded from results.

W2 changes no movement/turning, animation, AI timing, 25 fps cap or beam-wait code.
Frame-rate-independent simulation timing remains required investigation (§2.3.1 of
the performance plan). The scene-stable route controls the visible scene, not the
whole simulated world or its AI state.

**Local preference:** `amiga/performance.env` now enables W1+W2, mask 3. The tracked
example matches. The next interactive boot builds the normal slave in `tmp/build-release`;
explicit SLAVE/WHD_ARGS still override preferences. The normal slave builds with 68000/PIC
checks (28,896-byte code hunk, 28,932-byte file), and the VERIFY build also assembles.
All built files and game-derived evidence remain in ignored tmp. No `.run` emulator was
started or modified. W3 is the next performance item; simulation timing is open and W7
remains deferred.

### W3 CPU-selected wall-column unroll (2026-10-07)

CUSTOM2 bit 2 selects sixteen paired pixels with fixed destination displacements
on 68000/10. All three complete six-byte CMP/DBGE hooks are checked before writes.
Texture indexing, NOT, ADD/ADDX, clipping and material tails remain unchanged.
68020+ retain all original hook bytes: the CPU-independent candidate regressed
on the fixed wall (2,276 → 3,009 main-task cycles/column, 15.1 → 13.0 fps).
VERIFY twins can exercise the replacement on either CPU.

**Correctness:** current-source wall bodies pass 38,800 A500 and 126,576 020
pixel/register/flag comparisons, including all three replacement blocks. Those
retained verifier builds and view-geometry limits are documented in
`tmp/prof/render-current-twin-a500` and `render-current-twin-a1200`. The final
CPU-selected captures pass disabled-byte checks; on the 020, checking CUSTOM2=3
against the bit-2-on dumps also confirms all three W3 hooks remain original.

**Final measurements:** `w3-cpu`, CUSTOM2=3/7, CUSTOM5=1, 100 fields, serial
JOY0=none captures in amiga/.cap. All eight retained slave hashes are
`0edaa8925020edffe568eabe5a525f6538e674f0d4c51fb68eb8fdd20f0cb320`.
This build excludes pixel-twin costs from the window. The native capture fixture,
PC-base metadata and restoration checks are described in [native-capture.md](native-capture.md).

| Machine / route | fps off → on | Display intervals / fields | Wall calls | Wall main cycles/call | Renderer main cycles/call |
|---|---|---|---|---|---|
| A500 spin | 3.0 → 3.0 | 5/82 → 5/82 | 1,146 → 1,176 | 3,334 → 3,105 | 1,214,180 → 1,196,513 |
| A500 wall | 3.1 → 3.2 | 6/97 → 6/94 | 1,152 → 1,186 | 4,275 → 3,993 | 1,278,355 → 1,218,920 |
| 020 spin | 15.8 → 15.8 | 31/98 → 31/98 | 6,073 → 6,073 | 1,922 → 1,922 | 604,020 → 604,020 |
| 020 wall | 15.1 → 15.1 | 29/96 → 29/96 | 5,760 → 5,760 | 2,278 → 2,278 | 628,295 → 628,295 |

On the A500 fixed wall, column cost falls 6.6%, renderer cost falls 4.6%, and
unrounded fps improves 3.2%. Wall inclusive costs are 4,602 → 4,299 cycles/column;
renderer inclusive costs are 1,374,825 → 1,310,883 cycles/call. Boundary-partial calls
are excluded independently. Counts may include columns from a partial renderer call.

Off/on first and last whole screenshots match for both routes and CPUs. All four
wall viewports match; spin first/last differ as expected while turning, with each
corresponding off/on image matching. Player position, heading, movement step and
visible-object snapshots agree off/on. This does not establish equal AI world state
or frame-independent simulation. Timing code, the 25 fps cap and beam wait are unchanged.

![A500 W3 wall off/on first/last](../tmp/prof/w3-cpu-wall-a500-comparison.png)
![68020 W3 wall off/on first/last](../tmp/prof/w3-cpu-wall-a1200-comparison.png)
![A500 W3 spin off/on first/last](../tmp/prof/w3-cpu-spin-a500-comparison.png)
![68020 W3 spin off/on first/last](../tmp/prof/w3-cpu-spin-a1200-comparison.png)

Reproduce with the §7 machine settings:

```sh
FSUAE="$HOME/.local/share/amiga/fs-uae-arm/fs-uae" PROFILE_WINDOW=guest \
  tools/ab_window.sh w3-cpu 3 7
python3 tools/ab_summary.py w3-cpu
```

All outputs are retained under ignored tmp: exact slave/listing, anchor, code dump,
PC-base sidecar, first/last screenshots, FPS/profile/block/C2P/render reports and state.
Traces and large emulator logs were deleted after the reports completed, as specified
by the plan. Normal/VERIFY/guest feature-prefix builds pass the assembler's PIC checks.
W1–W3 are enabled in local preferences (mask 7); the next interactive boot builds
the normal slave. No interactive emulator was started or modified. W4–W6 remain open,
frame-independent timing remains required investigation, and W7 remains deferred.

### Revised W4–W6 correctness (2026-10-07)

W4 now counts eight rows per block instead of retaining DBF at every row. W5
uses a 1,024-slot exact-quotient cache with full divisor tags and guards the
original arithmetic and continuations. Its discarded D7/CCR state is overwritten
before use; VERIFY compares all fifteen registers and five flags after the
canonical mathematical continuation. The source/liveness audit is in
[w3-w6-audit.md](w3-w6-audit.md).

The identical retained VERIFY SHA256 on both CPUs is
`4690a396852cf44643a0f84c5b7d9fcc726ef5fbcda437ced5704418deeb7092`.
`render-rescue-twin-a500` and `render-rescue-twin-a1200` reached the completion
breakpoint after 300 large-view conversions following the anchor. All seventeen
flag snapshots use legal SR reads on the 68000 and CCR reads on the 020.

| CPU | C2P medium / large / small | Wall variants | Sprite variants | Live reciprocals | Exhaustive reciprocals | Clear widths 192 / 112 / 80 |
|---|---|---|---|---:|---:|---|
| 68000 | 34 / 331 / 42 | 23,574 / 23,573 / 23,573 | 10,181 / 1,095 / 1,094 | 70,720 | 262,140 | 662 / 68 / 84 |
| 68020 | 84 / 509 / 219 | 41,552 / 41,552 / 41,552 | 10,501 / 1,233 / 1,233 | 124,656 | 262,140 | 1,018 / 168 / 438 |

An earlier revised run missed its anchor: the stopped dump showed completed
exhaustive tests and successful live twins, but the tape remained at a later
computer-button W wait with another panel's button list active. A VERIFY-only
`VERIFY_WAIT_RESCUE` pulse resolves that wait. Normal and ordinary VERIFY binaries
compare byte-identical with the fixture excluded. Performance captures exclude it.
The timed-out runs are excluded from final validation and performance results.

Reproduce serial validation (one exact retained build, calibration then a startup
breakpoint that arms abort detection before exhaustive tests):

```sh
FSUAE="$HOME/.local/share/amiga/fs-uae-arm/fs-uae" tools/render_validate.sh render-verify 63
```

Final W4–W6 measurements follow below. Preferences now enable W1–W6 (mask 63).
Correctness counts alone establish no speed gain.

### W4 CPU-selected counted sprite rows (2026-10-07)

CUSTOM2 bit 3 selects eight sprite rows per block on 68000/10. Fixed destination
displacements replace per-row pointer stepping, with one counter update per block
and an original-style short tail. Row-to-texel lookup, transparency, palette mapping,
clipping and depth tests are unchanged. The replacement preserves all registers and
X/N/Z/V/C. All three six-byte hooks are checked before writes; the boundary audit is
in [w4-audit.md](w4-audit.md).

**Correctness:** all three replacement bodies pass pixel/register/flag twins on both
CPUs. The retained integration VERIFY SHA256 is
`4690a396852cf44643a0f84c5b7d9fcc726ef5fbcda437ced5704418deeb7092`:
A500 sprite variants 10,181 / 1,095 / 1,094; 020 variants 10,501 / 1,233 / 1,233.
Both runs cover all view sizes and complete 300 large-view C2P twins after the anchor.
The later CPU gate leaves the tested bodies unchanged; VERIFY may force them on either
CPU. Use `FSUAE="$HOME/.local/share/amiga/fs-uae-arm/fs-uae" tools/render_validate.sh w4-verify 15`.

The CPU-independent candidate changed 020 sprite-row cost by only 0.4–0.6%, with
no measured FPS gain. The final installer consequently retains the original compact
loops on 68020+. The final `w4-cpu` matrix uses CUSTOM2=7/15, CUSTOM5=1, 100 fields,
both routes and both CPUs, serial JOY0=none captures in amiga/.cap. All eight retained
slave hashes are `2aaaad468756b3090e04efe0be00b61eb8c84109398415cd26ed7a1baf4f240f`.
Other prospective patches in this retained development build are disabled.

| Machine / route | fps off → on | Intervals / fields off → on | Sprite inner main cycles/column | Main cycles/scanned pixel | Renderer main cycles/call |
|---|---|---|---|---|---|
| A500 spin | 3.0 → 3.1 | 5/82 → 5/80 | 5,619 → 5,111 | 63.03 → 57.34 | 1,196,465 → 1,190,811 |
| A500 wall | 3.2 → 3.2 | 6/94 → 5/78 | 5,714 → 5,288 | 62.11 → 57.47 | 1,218,857 → 1,197,358 |
| 020 spin | 15.8 → 15.8 | 30/95 → 30/95 | 1,637 → 1,637 | 22.23 → 22.23 | 603,849 → 603,849 |
| 020 wall | 14.9 → 14.9 | 29/97 → 29/97 | 2,034 → 2,034 | 22.11 → 22.11 | 629,541 → 629,541 |

A500 sprite-row cost falls 9.0% on spin and 7.5% on wall. Unrounded FPS improves
2.5% / 0.4%. Complete sprite-inner counts are 335/335 (29,864 scanned pixels each)
on spin, 231/198 (21,252/18,216 pixels) on wall. Inclusive inner costs are
5,968 → 5,527 and 6,124 → 5,671 cycles/column. Transparent pixels count as scanned
work. Independent boundary-partial calls are excluded from each routine.

Pose, heading, movement step and visible-object snapshots match off/on on both
routes and CPUs. All four wall viewports match on each machine. The 020 first/last
whole screenshots match off/on; A500 whole screenshots differ outside the wall
viewport, and spin frames differ in phase while turning. This is not equal-time AI
world-state proof. Existing simulation timing, the 25 fps cap and beam wait remain.
The 020 bit-3-on dumps also pass all fifteen W3–W6 disabled ranges with expected
mask 3, confirming the wall and sprite hooks remain original despite those option bits.

![A500 W4 spin off/on first/last](../tmp/prof/w4-cpu-spin-a500-comparison.png)
![68020 W4 spin off/on first/last](../tmp/prof/w4-cpu-spin-a1200-comparison.png)
![A500 W4 wall off/on first/last](../tmp/prof/w4-cpu-wall-a500-comparison.png)
![68020 W4 wall off/on first/last](../tmp/prof/w4-cpu-wall-a1200-comparison.png)

Reproduce with the §7 machine settings and native capture mode:

```sh
FSUAE="$HOME/.local/share/amiga/fs-uae-arm/fs-uae" PROFILE_WINDOW=guest tools/ab_window.sh w4-cpu 7 15
python3 tools/ab_summary.py w4-cpu
```

Exact slave/listing, dumps, PC-base/restoration metadata, images, reports and state
remain under ignored tmp; large traces/logs were deleted after analysis. W4-only
normal/VERIFY/capture builds pass 68000/PIC checks. Local preferences and their
tracked example now enable W1–W4 (mask 15). No interactive emulator was operated.
W5–W6 and frame-independent timing remain open; W7 remains deferred.

### W5 CPU-selected exact reciprocal cache (2026-10-07)

CUSTOM2 bit 4 caches the exact two-DIVU quotient at eight ray-setup sites on
68000/10. The 1,024-slot table stores Q32 and a complete divisor16 tag; collisions
are misses, never approximations. Misses execute the original arithmetic and zero
retains the original divide exception. The installer validates the entire skipped
arithmetic and each continuation's D7/CCR liveness before writing any hook.
See [w5-audit.md](w5-audit.md) and `tools/ray_liveness.py`.

**Correctness:** the retained integration VERIFY SHA256
`4690a396852cf44643a0f84c5b7d9fcc726ef5fbcda437ced5704418deeb7092` passes 262,140
exhaustive cases per CPU: every nonzero divisor, both register orders, X clear/set,
and varied coordinates. It also passes 70,720 A500 and 124,656 020 live comparisons.
All fifteen registers and five flags are compared after the canonical unchanged
continuation, which retains every quotient bit in D2. The raw optimized state is
restored so the actual game continuation executes once. The final gated build's
reciprocal core is byte-identical to this successful twin build. VERIFY can force
it on either CPU. Reproduce with `tools/render_validate.sh w5-verify 31`, using
the native FSUAE setting shown above.

The CPU-independent candidate regressed on the 020: spin quotient costs
87 → 134 main-task cycles/call; wall 86 → 105. The final installer consequently
retains all eight original divide sequences on 68020+. Its final `w5-cpu` matrix
uses CUSTOM2=15/31, CUSTOM5=1, 100 fields, both routes and CPUs, serial JOY0=none
captures in amiga/.cap. All eight retained slave hashes are
`9460c0eba3404bb0b79ecac15b17387d174b7fae346c45dca6042d2c726baf6f`.
W6 is disabled in this retained development build.

| Machine / route | fps off → on | Intervals / fields off → on | Quotient main cycles/call | Cache hit rate | Renderer main cycles/call |
|---|---|---|---|---|---|
| A500 spin | 3.1 → 3.2 | 5/80 → 6/94 | 291 → 286 | 71.0% | 1,190,811 → 1,175,668 |
| A500 wall | 3.2 → 3.2 | 5/78 → 6/93 | 282 → 222 | 90.0% | 1,197,358 → 1,202,022 |
| 020 spin | 16.0 → 16.0 | 30/94 → 30/94 | 87 → 87 | original divides | 602,309 → 602,309 |
| 020 wall | 15.1 → 15.1 | 29/96 → 29/96 | 86 → 86 | original divides | 629,475 → 629,475 |

A500 quotient cost falls 1.7% on spin and 21.3% on wall. Unrounded FPS improves
2.1% / 0.6%. The wall renderer mean rises 0.4%; this is not a claim of overall
renderer-cost improvement. Inclusive quotient costs are 302 → 324 on spin and
296 → 237 on wall; interrupt timing affects those inclusive means. Counts are
1,216/1,199 complete quotient scopes on spin, 1,309/1,195 on wall. Hit/miss totals
are 851/348 and 1,076/119. The scopes include the whole cache adapter and exclude
boundary-partial calls independently.

Player position, heading and movement step match off/on on both routes and CPUs.
Wall object snapshots and all four wall viewports match; spin visible-object snapshots
change on the A500 despite corresponding whole screenshots matching. All off/on
first/last whole screenshots match. This does not prove equal AI world state.
The 020 on dumps pass all fifteen W3–W6 original ranges with expected mask 3,
confirming that enabling the three CPU-gated bits leaves their hooks untouched.
Existing movement/AI timing, the 25 fps cap and beam wait remain unchanged.

![A500 W5 spin off/on first/last](../tmp/prof/w5-cpu-spin-a500-comparison.png)
![68020 W5 spin off/on first/last](../tmp/prof/w5-cpu-spin-a1200-comparison.png)
![A500 W5 wall off/on first/last](../tmp/prof/w5-cpu-wall-a500-comparison.png)
![68020 W5 wall off/on first/last](../tmp/prof/w5-cpu-wall-a1200-comparison.png)

Reproduce with §7 machine settings and `PROFILE_WINDOW=guest`:

```sh
FSUAE="$HOME/.local/share/amiga/fs-uae-arm/fs-uae" PROFILE_WINDOW=guest tools/ab_window.sh w5-cpu 15 31
python3 tools/ab_summary.py w5-cpu
```

Retained builds, dumps, metadata, images, reports and state remain under ignored tmp;
traces/logs were removed after analysis. W5-only normal/VERIFY/capture builds pass
68000/PIC checks. Preferences and the tracked example enable W1–W5 (mask 31).
No interactive emulator was operated. W6 measurements and frame-independent timing
remain open; W7 remains deferred.


### W6 fixed-width MOVEM chunky clear (2026-10-07)

CUSTOM2 bit 5 replaces the sky/floor row clear on every CPU. Eleven repeated-colour
registers write 44-byte predecrement MOVEM blocks with exact tails for 192, 112 and
80-byte widths. Row stride remains 192; colours, row counts, unused columns, all
fifteen registers and X/N/Z/V/C match the original. Other widths retain a general
sixteen-byte path. The mask excludes the address register. See [w6-audit.md](w6-audit.md).

**Correctness:** the shared integration VERIFY build above compares the complete
20,000-byte allocation, registers and flags against a runtime copy of the original.
Successful width-192/112/80 counts are 662/68/84 on 68000 and 1,018/168/438 on
020. The replacement body remains unchanged in the final measured build. Normal,
VERIFY and capture variants pass the 68000/PIC assembler; normal builds exclude twins.

The final `w6-movem` matrix uses CUSTOM2=31/63, CUSTOM5=1, 100 fields, both routes
and CPUs, serial JOY0=none captures in amiga/.cap. The four off controls are retained
identical-build W5-on windows, with `control-origin.txt` recording their provenance;
four new on captures complete the pairs. All eight exact retained slave hashes are
`9460c0eba3404bb0b79ecac15b17387d174b7fae346c45dca6042d2c726baf6f`.

| Machine / route | fps off → on | Intervals / fields off → on | Clear main cycles/call | Clear inner main cycles/call | Renderer main cycles/call |
|---|---|---|---|---|---|
| A500 spin | 3.2 → 3.2 | 6/94 → 6/93 | 69,077 → 43,061 | 34,398 → 21,392 | 1,175,668 → 1,150,496 |
| A500 wall | 3.2 → 3.3 | 6/93 → 6/92 | 71,217 → 43,326 | 35,465 → 21,525 | 1,202,022 → 1,160,184 |
| 020 spin | 16.0 → 16.1 | 30/94 → 31/96 | 18,935 → 15,451 | 9,400 → 7,656 | 602,309 → 601,023 |
| 020 wall | 15.1 → 15.3 | 29/96 → 30/98 | 19,229 → 15,644 | 9,547 → 7,752 | 629,475 → 623,910 |

Clear main-task cost falls 37.7% / 39.2% on A500 spin/wall and 18.4% / 18.6%
on 020. Unrounded FPS improves 1.1% / 1.1% and 1.2% / 1.3%, respectively. Complete
outer clear counts are 6/6 on each A500 pair, 32/32 on 020 spin, 30/30 on 020 wall;
inner counts are twice those. Outer inclusive costs are 73,585 → 47,574,
76,436 → 46,328, 19,721 → 15,796 and 19,754 → 15,930. Scopes include adapter costs;
interrupt work and independently incomplete boundary calls are excluded from main means.

Position, heading and visible-object snapshots match off/on for all four pairs.
Movement step matches except 020 spin (12 → 10). Wall first/last whole images and
all four wall viewports match on both CPUs. Spin differs in frame phase: A500 first
whole image matches and last differs; 020 first differs and last matches. Neither
spin pair has all four viewports identical. Pixel twins prove the replacement on
identical inputs; these captures do not establish equal-time simulation or AI state.
No movement/AI timing, 25 fps cap or beam wait was changed. Both 020-on dumps pass
all fourteen original W3–W5 hook ranges with expected mask 35 (W1/W2/W6 active).

![A500 W6 spin off/on first/last](../tmp/prof/w6-movem-spin-a500-comparison.png)
![68020 W6 spin off/on first/last](../tmp/prof/w6-movem-spin-a1200-comparison.png)
![A500 W6 wall off/on first/last](../tmp/prof/w6-movem-wall-a500-comparison.png)
![68020 W6 wall off/on first/last](../tmp/prof/w6-movem-wall-a1200-comparison.png)

Reproduce fresh pairs with §7 settings and native capture mode:

```sh
FSUAE="$HOME/.local/share/amiga/fs-uae-arm/fs-uae" PROFILE_WINDOW=guest tools/ab_window.sh w6-movem 31 63
python3 tools/ab_summary.py w6-movem
FSUAE="$HOME/.local/share/amiga/fs-uae-arm/fs-uae" tools/render_validate.sh w6-verify 63
```

Retained builds, dumps, metadata, images, reports and state remain under ignored tmp;
traces/logs were removed after analysis. Local preferences and their tracked example
enable W1–W6 (mask 63); the next interactive boot builds the normal slave. No
interactive emulator was operated. W3–W6 are complete in separate source commits.
Frame-independent simulation timing remains required investigation; W7 stays deferred.


### Simulation timing investigation, no timing patch (2026-10-07)

The VERIFY-only TIMING_STUDY wrapper can add eight PAL fields per renderer
entry after the tape anchor (CUSTOM5 bit 8). Two identical-build pairs with
CUSTOM2=63 and CUSTOM5=1/257 prove AI coupling on the A500 equivalent and
14 MHz 020: 52 of 56 decoded actor records differ at the end of each pair,
from identical initial world state. The original sampler used 100 subsequent
VBL-entry stops, ending at counter delta 99; no FPS is inferred from this.
See [timing-investigation.md](timing-investigation.md) for the exact intervals,
state comparisons, and the corrected after-increment sampler.

Separate early-game pause captures identify the greeting townsman as actor 43.
Across 100 VBL counter fields on each CPU, all 101 actor snapshots and the
paused game clock are identical. These establish the pause behavior to retain;
they do not establish a completed frame-independent simulation patch.
Normal and ordinary VERIFY builds remain byte-identical to the pre-study
builds when TIMING_STUDY is absent. All eighteen legal flag-capture sites pass
in the retained 68000 and 020 study builds.

Build with `make -C whdload verify OUT=../tmp/build-timing-study VASMFLAGS=-DTIMING_STUDY=1`.
For coupling, retain that same slave/listing in each output directory and use
§7 machine settings with KEEP_SLAVE=1, STATE_ONLY=1, STATE_FIELDS=100,
TAPE_OPTIONS=1/257, WHD_ARGS=CUSTOM2=63 and tools/tapes/wall.txt. Compare with
`python3 tools/lov_timing_compare.py NORMAL_CAPTURE DELAYED_CAPTURE`.
For pause observation use TIMING_PAUSE=1, STATE_ONLY=1, TAPE_OPTIONS=1 and an
early-game tape anchor followed by a stationary hold, as retained in
`tmp/prof/timing-pause-a500/tape.txt`. All captures were serial in amiga/.cap,
with JOY0=none; game-derived artifacts remain ignored under tmp.


### Optional one-degree turning (2026-10-07)

CUSTOM2 bit 7 changes angular precision; W7 remains deferred. The standalone
candidate excludes the unfinished simulation patch. All four captures use the
same PROFILE slave SHA256
`aa81853ff1fece05384af9536b09a61a1fde71cede0611408c5176795d4fcb2c`,
CUSTOM2=63/191, CUSTOM5=1, 100 fields, JOY0=none, serial in amiga/.cap.
The stationary route retains heading 270 and position (5216,3616), so the
new tap/hold policy cannot change the camera pose during this comparison.

| Machine | fps off → on | Intervals / fields off → on | Renderer main cycles/call | C2P main cycles/call |
|---|---|---|---|---|
| A500 equivalent | 3.4 → 3.6 | 6/88 → 7/96 | 1,165,803 → 1,162,327 | 503,544 → 500,835 |
| 14 MHz 68020 + 4 MB fast | 16.8 → 17.0 | 32/95 → 33/97 | 560,145 → 560,753 | 143,587 → 143,748 |

These are observed window costs, **not a speedup claim**: visible-object state
is different between off/on runs, especially the A500's mapped sprite work.
The four 020 viewports are identical; the A500 viewports are not. The original
simulation advances with rendered frames, and table construction also changes
startup timing. Matched-state VERIFY wall twins, rather than this A/B, establish
legacy-heading pixel equality. Renderer inclusive cycles/call are
1,257,047 → 1,250,715 (A500) and 571,232 → 572,755 (020), with 6/7 and 33/33
complete calls respectively. All six normal turning hook ranges retain their
original bytes in each off capture (the worktree checker also checks inactive
timing ranges). The on captures pass the W2 PUBLIC ownership check.

Generating a table occurs at view setup, outside these measurement windows.
The VERIFY VBL counter around the generator, excluding the oracle, reports
304/542 PAL fields for medium/large on A500 (6.08/10.84 seconds), and 50/87 on
020 (1.00/1.74 seconds). Small-view setup was not timed by this route.
The private table allocation is 144,000 bytes, MEMF_PUBLIC on every CPU.
The slave reserves an additional 144 KiB of expansion memory even with bit 7
off; with bit 7 on allocation failure retains coherent five-degree behavior.
The original game-owned table remains allocated. Normal slave code is 43,380
bytes; VERIFY buffers and fixtures are excluded.

Reproduce from the standalone turning commit using §7 machine settings:

```sh
FSUAE="$HOME/.local/share/amiga/fs-uae-arm/fs-uae" PROFILE_WINDOW=guest \
  tools/ab_window.sh one-degree-final 63 191 turning-still 'a500 a1200'
python3 tools/ab_summary.py one-degree-final
```

The retained matrix was seeded with one identical build using KEEP_SLAVE=1.
Reports, listings, state and first/last images remain in
`tmp/prof/one-degree-final-turning-still-*`; traces were removed after analysis.
An earlier stationary route stopped inside a conversation on 020 and was
rejected, not included above. Detailed correctness and input coverage is in
[the turning plan](one-degree-turning-plan.md).
