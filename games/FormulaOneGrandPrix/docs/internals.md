# Internals

## Slave

Codetapper's v1.0 (06.12.2002), 5464 bytes, no source. Header (slave offsets):

| Field | Value |
|---|---|
| `ws_Version` | 15 |
| `ws_Flags` | `$3402`: NoError, EmulPriv, ClearMem, Examine |
| `ws_BaseMemSize` | `$80000` (512 KB chip) |
| `ws_ExpMem` | `$C0000` (768 KB, includes the 256 KB Kickstart 1.3 image) |
| `ws_GameLoader` / `ws_CurrentDir` | `$170` / `data` |
| `ws_keyexit` | `$59` (F10) |

It is a KickEmu-style OS slave on Kickstart 1.3 (`kick34005.A500` + `.RTB`). The loader at
`$174`: creates the `F1GP_Disk_#1..4` assigns, sets preferences (fast pointer), turns the
audio filter off, then

1. unless `CUSTOM1` is set or fire is held, `LoadSeg`s and runs `frontend`, which is only
   the credits intro ending at "Click to Load Main Program";
2. `LoadSeg`s `f1gp`, accepts file sizes 582992, 582988 or 582780 (one patch list each,
   at `$2A6`, `$2DC`, `$312`), `resload_PatchSeg`s it, patches the built-in driver names
   (`$3D6`), and runs it with an empty argument line; on return, quits.

### B1: reconstruction and patch lists

`tools/slave_inputs.py` verifies `manifest/game-inputs.json`, generates symbolic assembly
for the loader and helpers in `tmp/slave/original.s`, and extracts the compressed driver
names into `tmp/slave/names.rnc`. The generated source reassembles byte-for-byte to the
original 5428-byte code hunk (5464-byte HUNK executable including its wrapper). The
previous `tmp/re/slave.bin` also included the final four-byte HUNK_END marker; it is not
part of the loaded slave.

Loader code is at slave `$170–2A5`, `$358–3A3`, `$3B6–423`; strings/header, patch lists
and the names payload are data. The old KickEmu starts at `$6EC` and extends through
the trailing workspace at `$1533`. Its entry receives resload in A0; the game-specific
DOS entry is `$174`. The generated reconstruction keeps old KickEmu as literal local
bytes, separate from the symbolic loader. B2 replaces that section with shared kick13
source; this is a behavioural rebuild, not a byte-identical KickEmu rebuild.

`PatchSeg` offsets below are cumulative **allocated hunk sizes**, including BSS, not
file offsets. For the supplied 582992-byte game, hunk 2 begins at cumulative `$6F394`.
Every list contains these six operations:

| Operation | 582992 (`$2A6`) | 582988 (`$2DC`) | 582780 (`$312`) | Replacement / purpose |
|---|---:|---:|---:|---|
| long | `$982` | `$982` | `$978` | `$22116000`: load expected protection answer and branch unconditionally |
| long | `$345C4` | `$345D8` | `$345CE` | two NOPs: remove the second protection failure branch |
| subroutine | `$6F840` | `$6F856` | `$6F84A` | slave `$3B6`: decode keyboard byte and abort on F10 |
| byte | `$A79CE` | `$A79C6` | `$A791E` | `$FF`: save-directory state flag |
| long | `$A7A42` | `$A7A3A` | `$A7992` | first four characters of `saves` |
| word | `$A7A46` | `$A7A3E` | `$A7996` | final character plus terminator |

For the supplied version, the original ranges are h0+$982 (CMP.L (A1),D1 and
BEQ opcode), h0+$345C4 (BNE.W), h2+$4AC (ROR.B then EORI.B keyboard decode),
h2+$3863A (zero byte) and h2+$386AE (the six-byte `DF0:` buffer). The keyboard
replacement replays both displaced instructions before comparing the decoded key with
`ws_keyexit`; it preserves the decoder result on return. The other two game variants
are accepted by the original loader but are not supplied here: their replacement lists
are decoded; their original bytes and hunk-relative mappings remain unverified.

The driver-names routine at slave `$3D6` obtains a relocated pointer from h0+$91A
(or +$910 for 582780), adds `$900`, and checks for the eight-character prefix
`Carlos S`. Only on that match it calls `resload_Decrunch` on the RNC1 payload at
slave `$424–6EA`: 693 compressed bytes plus an 18-byte header, 1480 unpacked bytes.
Otherwise names remain unchanged. The compressed bytes are extracted locally, never
committed. The names restore is unconditional with respect to CUSTOM1; CUSTOM1 only
skips `frontend`. The loader also tests both fire-button bits, tolerates a missing
frontend, runs with an empty argument line, unloads each segment and quits on return.


## Executables

`data/game` is the original hard-disk loader (assigns, `frontend`, then `f1gp`); the slave
does not use it.

| File | Hunks (memory) |
|---|---|
| `f1gp` (582992 bytes) | 0 code `$44A54` any, file `$2C`; 1 BSS `$2A940` any; 2 code `$41C70` chip, file `$4990C`; 3 BSS `$14F84` chip |
| `frontend` (127816 bytes) | 0 code `$8` any; 1 BSS `$6F790` any; 2 code `$1EC04` chip, file `$60`; 3 BSS `$2FC58` chip |

`f1gp` holds the language dialog, the manual-protection prompt, the startup and main menus,
the race and the results screens (all their strings are in it, for example "Quick Race" at
hunk 2 `$3D8F0`). Menus and race therefore share one executable and need no handover.

## Route to gameplay

From boot (`WHD_ARGS=CUSTOM1=1` skips the intro; otherwise click at its prompt): Choose
Language → O.K.; manual protection → any key, Return (the slave accepts anything); Startup
Menu → Quick Race, O.K.; Silverstone track screen → O.K.; "Please Wait" while the race
loads. The race then runs with no input. It opens in the player's cockpit ("Riding with
Nigel Mansell", car 5, fourth on the grid) at the start lights; the player's car only
creeps (5–16 mph) and drops to 26th while the field drives away. A "Viewing" sequence and
a follow-car camera follow until "Race won by …"; the game then returns to the
Non Championship Results menu.

`tools/f1gp.py quickrace` follows this route by recognising each screen from screenshot
pixels and stops at the first polled cockpit field. Once the language dialog is up, the
intervals are fixed per machine (fields after the language dialog, 25-field polling):

| Machine | protection | startup | track | race |
|---|---:|---:|---:|---:|
| A500-equivalent | 767 | 1100 | 1373 | 2348 |
| `a1200` (no fast RAM) | 559 | 866 | 1139 | 1854 |
| `a1200-fast` | 377 | 606 | 801 | 1308 |

With the CPU held from reset (`BOOT_BREAK`), the whole route and the race repeat exactly
from boot to boot; on `a1200-fast` the language dialog appears at field 838. Without it,
host timing changed the start and the race itself: in some boots the player's car kept
driving and was never retired.

## Race main loop

During the race the game runs one loop pass per frame at hunk 0 `$3C8F6–$3CA56` (the
only one of three similar loops that executed in the green, tow and follow windows; the
others, at `$3C652` and `$3CC40–$3CD0C`, are not yet identified). One pass:

1. `$3C8F6–$3C93C`: a timer check against a 2000 × factor deadline;
2. short calls `h0+396AC`, `h0+64`, `h0+34D24`, `h0+3BBF6`, `h0+39654`, `h0+3B5DE`, then
   (unless a mode bit is set) `h0+3B346`, **`h0+2AC14`**, `h0+3BF96`, optionally `h0+3C55C`
   and `h0+34028`;
3. **`h2+280F6`**, the drawing root;
4. `h0+258A2`, `h0+39542`, `h0+2DD74`;
5. the frame pacer, `h0+1272` (below).

`h0+2AC14` walks the car records through an offset list (each record points at its
track segment) and is the per-car update. Everything else in steps 1, 2 and 4 together
takes at most about 3% of all cycles on `a1200-fast`. Which of those calls are simulation and which are
presentation is not classified yet.

Inclusive cost per frame (`tools/race_profile.py`, green window, 500 fields; work is a
frame's cycles outside the pacer's wait):

| Machine | fps | drawing `h2+280F6` | per-car update `h0+2AC14` |
|---|---:|---:|---:|
| A500-equivalent | 5.84 | 124.3 ms (72.6%) | 38.6 ms (22.6%) |
| `a1200` (no fast RAM) | 7.67 | 97.4 ms (74.7%) | 25.9 ms (19.8%) |
| `a1200-fast` | 8.00 | 58.0 ms (46.4%) | 10.4 ms (8.3%) |

On `a1200-fast` the tow and follow windows spend 63.4% and 58.7% of all cycles in
drawing and 9.8% and 4.9% in the per-car update.

## Memory and the chip bus

`f1gp`'s hunk 0 (code) and hunk 1 (BSS) are `MEMF_ANY` and load into fast RAM when there
is any (slow RAM at `$C00000` on the A500-equivalent); hunk 2 (code and data, 269 KB) and hunk 3 (BSS, 86 KB) are `MEMF_CHIP`.
`tools/dma_census.py` over 50 fields of each `a1200-fast` window (`RACE_KEEP_TRACES=1`):

- The display is 4 lores bitplanes, 320 × 200 (`BPLCON0` `$4200`, `DDFSTRT`/`DDFSTOP`
  `$38`/`$D0`, `DIWSTRT`/`DIWSTOP` `$3581`/`$FDC1`, modulos 0, `FMODE` 0): 16,000
  bitplane slots per field, 22.5%. About 52–56% of slots are free.
- The CPU takes 14,742 chip slots per field in the follow window (20.7%): 8,532
  instruction fetches, all from hunk 2's code (hottest pages `h2+23000`, `h2+29000`,
  `h2+28000`, `h2+26000`, `h2+24000`), 3,036 data reads and 3,174 data writes, most of them
  to the two screen buffers.
- The two screen buffers (four 8,000-byte planes each) and the blitter's source masks lie
  in chip RAM just above hunk 2, consistent with hunk 3. Their plane pointers are 4 mod 8:
  aligned for a 32-bit AGA fetch (`FMODE` 1 or 2), not for 64-bit (`FMODE` 3).
- DMA reads only two parts of hunk 2 in these windows: the copper list at `h2+0000–0FFF`
  and audio samples at `h2+18000–1DFFF`. The blitter (1.3–2.2% of slots) works on the
  screen buffers and reads its sources above hunk 2.
- Hunk 2 interleaves variables with its routines (for example `h2+23126–231EA`,
  `h2+28168–281A0`, `h2+1E2DC–1E65A`, each right after an `RTS`). No write landed on an
  executed instruction in the three windows.

With WHDLoad's `CACHE` option the green window's work per frame fell from 71.7 to
63.0 ms (−12%) and CPU chip slots from 11.9% to 10.0%, so the 68020's instruction cache
is off under the supplied slave by default. (That run's race differed: green came 124
fields earlier and hunk 2 loaded `$A8` lower.)

## Frame pacing

The main loop ends each frame in a busy-wait at hunk 0 `$127C–$128B` (f1gp 582992 bytes):

```
0127c  move.w h0+125E,d0      ; fields since the last frame
01282  cmp.w  h0+125A,d0      ; this frame's minimum fields
01288  bcs.w  0127c
0128c  clr.w  h0+125E
01292  addq.w #1,h0+1260      ; frame count
```

The counter's only increment is at `h0+2CC3C`, in an interrupt routine at `h0+2CC38`
that ran exactly once per field (100 times in 100 traced fields). Before waiting, `$1272` copies the field counter to `h0+125C`, so that word holds the fields
the frame's work took. The code after the loop reloads the minimum from one of two 4-entry
word tables indexed by the frame count modulo 4: `h0+1262` (6, 6, 6, 7) or `h0+126A`
(7, 8, 7, 8). Which table applies depends on a chip-hunk word compared with 60, and a frame
whose work already took at least the table value keeps the old minimum. So the game holds
its frame rate to a fixed cadence instead of running as fast as the machine allows. Both
tables average 8 frames per second: 6.25 fields at 50 Hz, 7.5 at 60 Hz (the word compared
with 60 is presumably the display rate).

## Game time

The simulation advances a fixed step per frame; elapsed real time does not enter it.

- Besides the pacer itself, the only reader of the frame's elapsed fields (`h0+125C`) is
  `h0+36288`, which scales the per-field engine-sound pitch step by
  minimum ÷ elapsed fields, so the engine sound stays smooth when a frame overruns.
- The whole Quick Race (first cockpit field to the results screen, `tools/race_clock.py`)
  takes about the same number of frames on every machine while its real duration changes
  with the frame rate, and the in-game finishing times stay near 4:51–4:54:

| Machine | race fps | frames | fields to results | winner (game time) | game clock vs real |
|---|---:|---:|---:|---|---:|
| A500-equivalent | 5.49 | 3297 | 31557 (631 s) | Senna 4:53.111 | 0.70× |
| `a1200` (no fast RAM) | 7.23 | 3194 | 22914 (458 s) | Patrese 4:50.744 | 0.93× |
| `a1200-fast` | 8.00 | 3143 | 20301 (406 s) | Berger 4:54.233 | 1.02× |

  "race fps" is measured over fields 2000–14000; the last column is race fps × 128 ms.
  Game time per frame comes from an earlier `a1200-fast` race (Patrese 5:02.229), which
  compares the game's own frame counter with its race clock: green light to the
  "Race won by" banner took 2340–2372 frames for the winner's 302.229 s, 127–129 ms of
  game time per frame (200-field sampling at both ends; where the in-game clock starts
  relative to the green light is not established), so close to the pacer's 1/8 s.
- So the in-game clocks show game time. On the A500-equivalent a race shown as 4:53
  takes about 7:00 of real time; on `a1200-fast` the pacer holds the game at about real
  time. On slower machines the pacer seldom waits (A500-equivalent: work 7–13 fields per
  frame against a minimum of 6), so the game simply runs slower.
- The races differ between machines (on one machine a run repeats exactly, checked on
  `a1200-fast`), so the frame
  counts are not directly comparable.

Consequences for the goals: on `a1200-fast` and faster machines, faster code alone cannot
raise the frame rate while the pacer holds 8 fps, and removing the pacer would speed up
the simulation with it. Higher frame rates need the simulation step decoupled from the
displayed frame (AmigaXDev `docs/playbooks/fixed-time-simulation.md`); slower machines
need it to keep game time at real time.


## Current measurements

`a1200-fast` (68020, 8 MB fast RAM, PAL), three 500-field windows (10 s each) from the
deterministic Quick Race (`tools/race_profile.py`, development doc). Times are emulated;
"work" is a frame's cycles outside the pacer's wait loop, interrupts included.

| Window (anchor) | fps | frame ms mean / p95 / max | work ms mean / p95 / max | pacer wait |
|---|---:|---|---|---:|
| green light | 8.00 | 125.1 / 140 / 140 | 71.7 / 82.1 / 85.2 | 42.7% |
| retirement and towing | 8.02 | 124.8 / 140 / 140 | 96.5 / 106.1 / 127.0 | 22.3% |
| follow camera | 8.03 | 124.6 / 140 / 140 | 84.1 / 103.2 / 128.0 | 32.0% |

- The frame rate is the pacer's cadence (6–7 fields per frame) in all three windows, not
  the machine's limit: no window's mean work fills its frame.
- The per-frame work runs under `h2+280F6` (46–63% of all cycles inclusive), which lives in
  hunk 2. That hunk is declared chip memory, so on this machine 27–34% of all cycles
  execute from chip RAM.
- DMA: about 57–62% of chip-bus slots are free; blitter 1.3–1.8%; bitplanes 22.5%.
  The CPU never stops (`STOP` 0%).
- Function names are hunk offsets of the nearest preceding call target, a heuristic; a
  large entry needs checking against the disassembly before acting on it.
