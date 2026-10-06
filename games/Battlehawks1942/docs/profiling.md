# Profiling Battlehawks 1942

How to run, drive and trace the original game, and the measurements so far. Method:
`Test Drive 2'sdocs/new-game-playbook.md`. Every number here names its instrument.

## TL;DR

```sh
source amiga/env.sh
make -C whdload original                 # reconstruction == shipped slave (byte compare)
tools/fixed_window.sh tmp/prof/base      # VERIFY build, calibrate-free, 100 fields from the 1st flight frame
SLAVE=tmp/prof/base/slave.slave python3 tools/bh_report.py tmp/prof/base/trace.bin tmp/prof/base/code.bin
SLAVE=tmp/prof/base/slave.slave python3 tools/frames.py tmp/prof/base/trace.bin tmp/prof/base/code.bin 0xc00000
python3 tools/compare_traces.py tmp/prof/base/trace.bin tmp/prof/base2/trace.bin
```

A capture takes about 4 minutes (one boot, ~4600 fields to the flight in warp) and ~520 MB.

## 1. The game and the slave

| | |
|---|---|
| Archive | `Battlehawks1942_v1.0_0053.lha` (Retroplay), SHA-256s in `tmp/archive.sha256` |
| Game | PAL v1.0, three AmigaDOS OFS disks: `Disk.1` "BHawk1" (boot, `BH`, sounds), `Disk.2` "BHawk2" (screens, `FDAT/` plane data), `Disk.3` "BHPilots" (pilot records) |
| Code | `BH` on `Disk.1` (167 936 bytes), Aztec C (`link a5` prologues, `jsr d16(a4)` jump table, small data `a4` = data hunk + `$7FFE`). Hunk 0 code `$1C794` bytes at file `$28` (3 relocs); hunk 1 data `$A664` file-backed / `$F1EC` allocated (2146 relocs); hunk 2 BSS 4 bytes. `Disk.1:s/startup-sequence` is just `BH`. |
| Shipped slave | Galahad of Fairlight v1.0 (12/05/03), 1512 bytes, WHDLoad v15 header, no source. `ws_BaseMemSize` `$80000`, `ws_ExpMem` `$40000` (exactly the Kickstart image), flags `NoError\|EmulPriv`, quit F10. The archive is the "SLOW" slave (no fast RAM); the ReadMe mentions a "FAST" one, not included. |
| Reconstruction | `whdload/original/Battlehawks1942.s` rebuilds the shipped slave byte-identically. Old-style Kick 1.3 boot: `resload_LoadKick` into ExpMem, a `resload_Patch` list on the Kickstart image (trackdisk → `Disk.N` via `resload_DiskLoad`, disk change, copper, a dos `LoadSeg` hook), and in the hook one patch to `BH`. Decode its list with `tools/patchlist.py SLAVE 0x206`. |
| Game patch | The manual check ("Recognition Test", shown before the first flight): `bh:025be move.b (0,a0,d1.l),d2; cmp.w d2,d0; beq.s` becomes `jsr fix; bra.s` — any answer passes, but Return must still be pressed. |
| Built slave | `whdload/Battlehawks1942.s`: WHDLoad 20 KickEmu (`whdload/whdload/kick13.s`, vendored verbatim with the 20.0 headers in `whdload/include/`). Same machine as v1.0 (512 KB chip, no other memory), `DISKSONBOOT`, `NUMDRIVES=3` (no swaps), `WPDRIVES=%1111` (as v1.0), the same `BH` patch via `_cb_dosLoadSeg` + `resload_PatchSeg`. `make verify` adds `tape.s`. |

**Memory.** Because ExpMem holds only the Kickstart, everything the OS allocates is in the
512 KB of chip RAM: `BH` loads at chip `$22F08` (code) / `$3F6A8` (data) on the A500-equivalent
machine with both slaves, and its buffers are in chip too. The Kickstart image and the slave
are in the host machine's "other" memory (slow RAM `$C00000` with no fast RAM).
`tools/bh_report.py` finds `BH` in the trace's chip snapshot (byte-match voting, then LoadSeg's
BPTR chain to the data hunk), the relocated Kickstart in the slow-RAM dump, and the *running*
slave (the copy with `WHDLOADS` and no `$3F3` hunk header in front; the other is WHDLoad's file
copy).

## 2. The machine

The A500-equivalent: `CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536`, 68000, cycle
exact, PAL, host Kickstart 3.1 + Workbench 2.04 floppy booting `DH0`, WHDLoad 20.0 on `DH1`
(`amiga/run.sh`; kick13 needs `kick34005.A500` + `.RTB`, the RTB is in
`~/.local/share/amiga/Kickstarts/`). `fixed_window.sh` sets all of this.

## 3. Driving: `tools/bh.py` and the input tape

`bh.py serve` boots (`DEBUG=1 amiga/run.sh`), attaches gdb within the stub's 20 s window,
and serves `stop/cont/gdb/shot/profile/wait/until/quit` on `amiga/.run/bh.sock`. The
profiler's PC window is fixed per capture by one lldb attach (`LLDB_FIX`, link-time
`0x32dea04`, unchanged FS-UAE binary; ~35 s).

**There is no attract demo**, and posted host key events never reach FS-UAE. Two ways were tried:

1. **FS-UAE input recordings do not replay in this build.** `RECORD=` works, and synthetic
   events can be spliced in (`tools/splice_rec.py`; `KEY_RETURN` = 164 in this binary's
   event table, 48-byte entries, `JOY2_LEFT` = 60 and `SPC_STATESAVE1` = 378 agree with
   TD2), but FS-UAE itself emits two events at startup (2263, 2272: joystick-port mode
   actions, sent whatever `JOY0/JOY1` are). During playback recording any event truncates the
   recording at the play position, so playback always ends at position 0. `PLAYBACK=` is kept
   in `run.sh` in case a fixed FS-UAE turns up. The recordings also showed that the host
   mouse feeds port 0 when `JOY0=mouse`, even with input grab off.
2. **The VERIFY input tape (`whdload/tape.s`) — used.** `_cb_dosLoadSeg` starts an Exec task
   (TCB, stack and I/O blocks inside the slave, so the game's allocations do not move) that
   counts fields with `WaitTOF` and sends `IECLASS_RAWKEY` events through `input.device`
   `IND_WRITEEVENT`: Return at fields 3000, 3505, 4010, 4515 after BH's LoadSeg. The screens:
   title, credits (both by themselves), main menu (Return: Select Training), Select Training
   Mission (Return: first mission), Ready Room (Return: Begin Flight), Recognition Test
   (Return) → the flight. The menu is up by field ~2800 (KickEmu slave, 68000); the v1.0
   slave reached the screens on a different schedule, so retime the tape when the slave or
   the boot changes. After the tape the task sits in `Wait(0)`.
   It publishes `"BHTAPE!!"`, its field count and the field of its last key; `fixed_window.sh`
   polls the count read-only.

**Anchor.** `fixed_window.sh` boots once with no breakpoint (a breakpoint armed from reset
made warp too slow to reach field ~4600 in 5 minutes), finds `BH` and the tape counter, polls
the counter until 300 fields before the last key, then runs to the first `bh:1a2c2` (the 3D
view's c2p pass: one per frame, never run by the menus). gdb holding the CPU stops emulated
time, so polling does not change the run. The window is the first 100 fields of the first
training flight (Gunnery Fundamentals, no input, the drones ahead).

## 4. Reading a trace

- `bh_report.py`: regions, contexts (SP ranges), self/inclusive time per routine (function
  starts = Aztec `link a5` prologues + traced call targets), hottest instructions, call edges.
  The game's top level was entered before the trace, so inclusive times above `bh:06eea`
  show as `[top]`.
- `frames.py`: frames, STOP idle, level-3 interrupts (through the live `$6C` vector), DMA slots.
- `swap_fields.py`: the same frame count from read-only breakpoints (`SWAP_ONLY=1`), for the
  68030 backend that records no instructions. Not yet validated against a full trace.
- `hotspots.py`, `disd.py`, `dis.sh`: instruction-level views (`HUNKBASE` = the `bh` region).
- Disassemble `BH` without a dump: `tools/adf.py tmp/game/Battlehawks1942/Disk.1 BH tmp/BH`,
  then hunk 0 is file `$28`..`$28+$1C794`.

## 5. Display and frame counting

The 3D view is rendered by the CPU into a chunky buffer and converted by **`bh:1a2c2`, a delta
chunky-to-planar pass**: it compares the new chunky frame with the previous one a long at a
time (`cmpm.l (a5)+,(a6)+; dbne d7` at `bh:1a30e`, the hottest instruction) and converts only
the changed longs into the 4 bitplanes. The two chunky buffers alternate (`$5C808`/`$5F908`
on this machine); the bitplanes do not — **there is one displayed buffer**, written while it
is shown (no swap, no beam sync). So one c2p pass is one new frame, and that is the frame
counter (`bh_report.C2P`). The renderer never touches the blitter (no `$DFF040..58`
references, no `btst #6`; one `OwnBlitter` call in BH), so there is no blitter wait.

No graphics.library calls run during flight. The game installs its own level-3 handler,
`bh:1ac26` (a per-VBL sound sequencer that drives the audio registers and then jumps into the
Kickstart handler past its prologue, `kick:fc0d18`).

## 6. Baseline (2026-10-07, A500-equivalent, KickEmu VERIFY slave, first flight, 100 fields)

`tools/fixed_window.sh tmp/prof/base` (frames.py, bh_report.py):

- **9.6 fps**: 18 frames in 94 fields, 5.22 fields/frame (c2p passes every 4–6 fields).
- CPU never stops (0.0 % STOP); 93.3 % of cycles on BH's stack, 4.4 % and 1.5 % on two OS
  task stacks (not yet identified).
- Regions: `bh` 93.7 %, Kickstart 5.8 %, slave 0.2 % (the tape task's `Wait`), `bh-data` 0.2 %.
- Interrupts: 1.0 level-3 per field (VERTB only; no BLIT).
- DMA slots: free 34.9 %, CPU 40.6 %, bitplane 22.5 %, refresh 1.8 %, copper 0.2 %, audio 0.1 %.

Self time per frame-driving routine (% of all cycles; calls in 100 fields):

| % | routine | calls | note |
|---:|---|---:|---|
| 16.1 | `bh:1a2c2` | 19 | delta c2p (8.5 % + 4.7 % on the compare loop alone) |
| 8.3 | `bh:161ec` | 19 | |
| 8.1 | `bh:16bca` | 323 | |
| 7.3 | `bh:1719c` | 88 | |
| 5.4 | `bh:15cb6` | 19 | `movem.l d2-d7/a1-a2,-(a3)` fill in `bh:16114..`: probably the chunky clear |
| 5.3 | `bh:0aec8` | 19 | |
| 4.4 | `bh:11142` | 20 | |
| 3.9 | `bh:160f4` | 38 | |

Inclusive: `bh:06eea` (the per-frame 3D view driver: camera from the plane state, then the
scene) 54.3 %, `bh:0ab0e` 16.8 % (88 calls: per object?), `bh:15cb6` 14.0 %, `bh:1a2c2` 15.6 %.
Names are not yet assigned beyond the c2p.

Reproducibility: the same window captured twice gives the identical frame line and figures (§7).

## 7. Reproducibility

`DETERMINISTIC=1`, `JOY0=none JOY1=none`, the tape as the only input. BH has no
`VHPOSR`/`VPOSR`/CIA reads in hunk 0 (custom-chip references are only DMACON and the audio
registers). Its `rand()` (Aztec LCG 1103515245/12345, state `9180(a4)`, `bh:1adb6`, seeded by
`bh:1adea`) has not been traced to its seed.

Two fresh captures (`tmp/prof/base`, `tmp/prof/base2`, 2026-10-07), `compare_traces.py`:
**every field's PC sequence, cycle costs and screenshot are identical** (100/100), so all
timing figures are reproducible. Register values and DMA records differ, and 2 bytes of the
chip snapshot (`$2E74`, OS memory). The first differing record is the Kickstart's gameport
read `kick:fe5a56 move.w (10,a0,d1.w),d0` with `a0 = $DFF000`: **JOY0DAT** reads `$0000` in
one boot and `$0101` in the other, although `JOY0=none`. Indianapolis 500 saw the same port-0
counter differ between boots. Until that is removed, compare game state, not raw registers.

## 8. Traps

- `fixed_window.sh` uses `bh until`, which blocks until the anchor is hit. If the tape no
  longer reaches the flight (retimed boot, another slave), kill your own emulator by
  `amiga/.run/fsuae.pid` and check with `shot`s against the tape counter.
- Don't `pkill -f` broad patterns: other sessions' command lines can match.
