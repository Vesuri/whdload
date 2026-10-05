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

There is **no fixed gameplay window yet** (see `docs/open-work.md`): `fixed_window.sh`,
`profile_demo.sh`, `frames.py`, `swap_fields.py`, `ingame.py` and the `state_*` tools are
still Test Drive II's game-specific versions (anchors, frame marker, VBL address, pixel test)
with only the names changed.

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
