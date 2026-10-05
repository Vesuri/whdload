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


## 8. Performance patch validation (2026-10-05)

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
