# How the original game works

What is known about the 1990 code, from cycle-exact traces and disassembly. Addresses are
`game:` hunk-0 offsets (the slave's `PL_GAME` numbering) or `intro:` addresses (loaded at 0).
Physics details for the driving model are in [simulation-feasibility.md](simulation-feasibility.md).

## Loading and memory

| Item | Value |
|---|---|
| Archive | `Indianapolis500_v3.0_0686.lha` (Retroplay): `Indianapolis500.Slave`, `Disk.1` (901 120 bytes, DIC image of the SPS 686 disk). The only supported version (the slave checks CRC16 `$B46E`) |
| Slave | StingRay v3.0 (30.04.2022), source in the installer pack `tmp/archives/Indianapolis500.lha` (`Source/Indianapolis500_WHD.s`), identical to `Games/Indianapolis500_WHD.s` in StingRay's `MK1Roxxor/WHDLoad_Patches` at `e05698e` (game.conf `UPSTREAM`), the first commit of `src/Indianapolis500_WHD.s` here. Direct game, no kickemu or OS: loads 19×`$1600` bytes of Disk.1 to 0, patches the intro, jumps to `intro:$a040` |
| Header | `ws_Version` 17, `NoError\|ClearMem\|EmulTrap`, BaseMem `$80000`, ExpMem `$80000`, KeyExit Del |
| Original intro patches (`PL_INTRO`, from `$a040`) | `PL_SA $14,$1a` keep ext. memory pointer; `PL_P $107e` track loader; `PL_R $11b0` motor off; `PL_PS $266` patch the game; `PL_PS $b90` quit key; `PL_PSS $be2/$bf6/$c6a` level-2 ack |
| Original game patches (`PL_GAME`) | `PL_SA $2d52a,$2d542`; `PL_P $2d478`/`$2d4b8` load/save; `PL_SA $2b528,$2b5c2` skip manual protection; `PL_PSS $9bb4/$9bcc/$9c48` level-2 ack; `PL_PS $9b7e` quit key |
| Game code | A hunk executable stored raw on Disk.1 at `$1A200`, relocated by the intro's loader. Hunks (`i500_report.game_hunks()`): 0 code `$2DE08`, 1 BSS `$8C0C`, 2 BSS chip `$7AEC`, 3 data `$1B10C`, 4 data chip `$15450`, 5 BSS `$10800`, 6 data `$91FC` |

Hunk 0 is hand-written assembly with absolute addressing; its variables live inside hunk 0. The
game installs its own handlers (`$64` → `game:007ee` SOFT, `$68` → `game:09b30` CIA, `$6c` →
`game:0b29c` VBL) and runs in supervisor mode on one stack below hunk 0.

On an A1200 with fast RAM only BSS hunk 2 (31 KB) is in chip RAM; hunk 4 is flagged chip but
loaded into fast RAM. All hunk-2 references are in `game:0c7ce`–`0e4c0`, none hot.

## Time

- **CIA-A timer B** (programmed at `intro:ace2`, latch 11 883) ticks at **59.70 Hz**. Its handler
  (`game:09b30` → `game:09bda`, `game:09c06`) increments `game:12388`; every fourth tick it sets
  bit 0 of `game:12397`, and raises SOFT (level 1) if the bit was already set.
- The renderer's frame end (`game:0b574`, `game:0b592..0b5a6`) also raises SOFT when ≥4 ticks
  have passed and the bit is set. So the **simulation runs at 14.9 Hz** (every 67 ms), partly
  phase-locked to frame ends. 30 SOFT interrupts per 100 fields on every CPU.
- The SOFT handler (`game:007ee`) runs the whole simulation and increments `game:09832`
  (`ticks_pending`). Its common exit is `game:03af0`. During driving it runs the player's physics
  (`game:00850..035ce`), then the field update `game:020d26`. In the demo (`game:268da == 1`) the
  director `game:27b78` replaces the player's physics.
- The main loop (`game:00152`) originally **waits until `ticks_pending ≠ 0`**, so the frame rate
  can never exceed 14.9 fps. Rendering does not feed back into the simulation: per-tick state
  (all 33 car records, camera, director, BSS hunks 2 and 5) is identical with the wait removed,
  over 1,000+ ticks on the 68000 and 68020.
- VBL (`game:0b29c`) only swaps copper lists and updates palette/sprites. JOY0DAT is read at
  `game:0b424` (mouse deltas). `game:2b4d2` reads the timer B counter as a random seed. No
  VHPOSR/VPOSR or CIA TOD reads.

Measured simulation cost per tick:
- **Driving** (`soft_timing.py`, race, cockpit):
  - 68030/25 with `DCache`: 0.81 ms. Player physics `game:00bf8..03138` takes 0.37 ms and the
    field update `game:020d26` 0.30 ms.
  - 68EC020/14 with fast RAM and `DCache`: 2.79 ms (1.60 and 0.85 ms).
- **Demo path:** 73 k cycles on the A500 (0.52 field), 0.15 field on the 68020.

## What the renderer reads from the simulation

Everything is copied once per frame with SOFT disabled:

- **Demo/external cameras:** `game:26d24` copies the tick count and the 9-word view block
  `game:26664–26675` to `game:007a6`. `game:280d4` (called from `game:26d48`) then fills the
  frame car array at `game:2326e`.
- **Cockpit:** `game:160..172` selects a separate path that copies the live camera at
  `game:9834` to `game:007a8`, then builds the visible-car list in `game:203a0` (done by
  `game:270`).
- **Camera words** (published at `game:27f22–27f4c`): 0–2 position, 3 yaw, 4 pitch or aim, 5 (0 in the TV view), 6
  the camera's track position (wrapped at 39 600), 7 lateral position (shifted right four),
  8 track tangent heading. The demo camera's track position is `game:268d2`; in the cockpit,
  distances are relative to the player car's `+6`.
- **Car array** at `game:2326e`: a count, then per car the distance, a pointer to its 86-byte
  record (table at `game:22758`, record 0 = player, 33 records) and the record's `+6` (lap
  position, wraps at 39 600), `+8` (lateral) and `+10` (heading). `game:280d4` walks the ring of
  22-byte nodes in BSS hunk 5 (offset `$E808`) both ways from the viewer's node `game:26698`, and
  keeps cars within ±2000 units. Each car's distance carries a native bias that must be kept.
  The external array takes each car's pose from its node (`+12` record pointer, `+16/+18/+20`
  pose), not from the record. In the demo the nodes hold the previous tick's record poses; in
  replays only the nodes move. The cockpit list (`game:203a0`) takes the records' poses, and
  `game:26698` is 0 there.
- **Opponents move by their own rates.** The field loop (`game:020d38..020d7a`) adds `+84` to the
  lateral rate `+14`, adds `+14` to the lateral position `+8`, adds `+16` to the heading `+10`,
  and subtracts the 8.8 speed `+12` from the 24-bit track position (`+6` word, fraction byte
  `+5`). The controllers (`game:020f4a`, four records per tick, so each car every 8 ticks)
  change rates only after that. At a SOFT exit every opponent's next pose is therefore already
  determined: 100% (track, heading) and 99.95% (lateral; the misses are contacts) of 32,256
  race car-ticks. The player's record is different: its heading rate is not its last-tick turn.
- Not interpolated: the viewer node, counters, input state (`game:09ede…`), `game:2274c–22753`
  (coordinate scratch, saved/restored by `game:031aa–031ec`).

## Renderer

- Frame: the background `game:0c0ba` (called at `game:02da`), polygons, lines, HUD, then the end
  of frame at `game:0b574`/`0b57e` (`bset #0,game:12396`). It waits at `game:0b5ae` until VBL
  swaps (`game:0b2e2` writes COP1LC). 320×200 lores, 4 planes 8000 bytes apart.
- **Background `game:0c0ba`** paints the 3D view (rows 24–147, 124 rows × 20 words per plane):
  plane 2 cleared over sky and band, a one-dot horizon line (BLTCON1 `$5F`/`$5B`), an inclusive
  fill of the band (`$09F0`), ones below it (`$01FF`); plane 3 = NOT plane 2 (`$090F`); planes 0
  and 1 all ones (`$01FF` at `0c25e`/`0c28c`). The slope branches rejoin at `0c1d4`; tail at
  `0c29a`.
- **Polygons** are one-row span blits. `game:0bb42` (solid) and `game:0bc50` (textured): BLTCON0
  `$05AC` (B and D, minterm `$AC`), A = `$FFFF` masked by FWM/LWM tables, colour per plane from
  BLTCDAT. `game:0bc50` uses `$07AC` with a C pattern advancing 1080 bytes per plane;
  `game:0bd6c` uses a dither mask, and callers can enter at `game:0bd76` with their own phase.
  Prepared loops: `game:0bbb4`, `game:0bcbc`, `game:0be04`. About 637 spans per frame × 4 planes,
  with a BBUSY wait before every blit.
- **Lines:** `game:0b8ca`, four line-mode blits per line (one per plane), start word
  `game:e84a`, BLTCON0 at `game:e830`, B = the plane's colour word (0/`$FFFF`, written by
  `game:0b830`).
- **Transform:** `game:0a908` (vertex transform and perspective, 9 `muls` and 2 `divs`), cached
  per vertex and per component. The largest CPU item (24.8% inclusive on the A500).
- Bitmap pointer at `game:e80c`. Blitter waits: `btst #6,$dff002` (78 sites) and `btst d4,(a6)`.

Original profile, demo's first 100 fields: the A500 is CPU-bound at 5.1 fps (`game:0a908` 24.8%,
`game:0bb42` 21.4%, `game:0bc50` 10.3% inclusive). On the 68020 it is 13.1 fps with 32% of
cycles polling the blitter. On faster CPUs the 14.9 Hz tick is the limit.

## Demo

Credits → about 25 s of emulated time in a table-building loop at `game:2dd06` → the demo
("DEMO / CLICK TO DRIVE"), which runs indefinitely. The director `game:27b78` changes camera
every 150 ticks (counter `game:268d0`) and resets at tick 900 (`game:27bec`). The standard
windows are the opening and director ticks 50/200/350/500/650/800. 200 and 800 are the
heaviest views.

## Sound

- The intro (loaded at 0, still resident in the game) holds the music player. `$fe00` is a hook
  vector called on every CIA tick by the intro's handler (`intro:ac4e`) and the game's
  (`game:09be4` → `game:a018`). `$fe04` is the music tick (`$fe30`), `$fe08` starts a song and
  `$fe0c` stops it. In a race the game points the hook at its engine sound (`game:a020`); when
  it stops the music it patches `$fe04`/`$fe08` to `rts` (`game:9fe2`).
- New notes and effects turn audio DMA off, set the channels and wait with 401 reads of
  address 0 (`intro:102de`, `game:a384`) before turning DMA on. The slave replaces both waits
  (slave.md "Audio DMA wait").
- Periods: music notes from the table at `intro:179da` (135–254), with octaves from shorter
  waveforms; noise drums on channel 3 at 190–672; effects up to 794 (`game:a1ac`).

## Other facts

- Mode `game:268da` (1 = demo). `game:09b2e`: bit 0 pause, bit 1 replay. Race event
  `game:7d4` (2 = race).
- View style `game:268d7`: 2 is the replay transition wipe. The CIA handler (`game:9bf4`) then
  advances the frame counter `game:9832` itself and skips the SOFT request and `game:9c06`.
- Keys: the state table at `game:9dde` is indexed by raw key code (bit 7 event, bit 0 held), for
  example Esc at `game:9e23`. In driving, the end of SOFT (`game:03aa8`) dispatches one event
  per tick, when `game:09ef4` bit 0 is set, to the handlers at `game:9556` for the 35 raw keys
  listed at `game:97ca` (ending with `$ff`; Esc, `$45`, is the menu request `game:5fde`).
- The SOFT trigger is a handshake: every 4 CIA ticks the CIA handler sets `game:12397` bit 0,
  and the end of frame (`game:0b592`) clears it and requests SOFT. If a frame has not consumed
  it by the next 4-tick boundary, the CIA handler requests SOFT itself.

## Menu and instant replay

- A menu request is `game:09b2f` bit 0. `game:5fde` sets it (Esc in a race through the key
  dispatcher, in the demo and in the replay's camera keys at `game:277a4`), all from SOFT; `game:26cf6` sets it
  when a replay ends. The end of each frame (`game:05cc`) sees it and calls the menu
  `game:2a59c`. While it is pending the CIA handler skips its tick work (`game:09bea`): no frame
  tick, no SOFT. Raised outside SOFT while the main loop waits for a tick, it deadlocks the
  original game.
- The menu's wait loop is `game:2a8c0`; the menu id is `game:2bb0e` (8 = main menu) and the
  selection `game:2bb0c`. The dispatch table at `game:2a706`: 0 resume (or leave a replay,
  `game:2aa20`), 1 Instant Replay (`game:2aa3e`: sets `game:09b2e` bit 1, calls `game:26bca`),
  2 Practice, 4 Race.
- The recorder `game:26abe` stores the 33 poses (198 bytes) per tick in a 300-record ring at the
  start of BSS hunk 5 (`[0, $E808)`); current, start and end pointers at `game:26678/2667c/26680`.
  `game:26bca` starts playback if more than two records exist (else back to the menu).
- In replay mode SOFT runs `game:26e50` (the replay camera and playback) instead of the physics
  and leaves through the common exit `game:03af0`. Playback writes the node ring, not the car
  records.
- `intro:a1d8` sets the chip-pool allocation limit (operand at `intro:a1da`); passing a smaller
  D7 does not work because the intro resets it.
