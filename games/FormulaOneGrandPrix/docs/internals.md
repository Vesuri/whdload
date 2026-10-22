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

The patch lists are not decoded yet.

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
| A500-equivalent | 688 | 983 | 1246 | 2109 |
| `a1200-fast` | 338 | 533 | 696 | 1134 |

With the CPU held from reset (`BOOT_BREAK`), the whole route and the race repeat exactly
from boot to boot; on `a1200-fast` the language dialog appears at field 930. Without it,
host timing changed the start and the race itself: in some boots the player's car kept
driving and was never retired.

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
  with the frame rate, and the in-game finishing times stay near 4:46–5:02:

| Machine | race fps | frames | fields to results | winner (game time) | game clock vs real |
|---|---:|---:|---:|---|---:|
| A500-equivalent | 5.49 | 2995 | 29088 (582 s) | Senna 4:46.260 | 0.70× |
| `a1200` (no fast RAM) | 7.18 | 3208 | 23230 (465 s) | Patrese 4:49.592 | 0.92× |
| `a1200-fast` | 8.04 | 3306 | 21210 (424 s) | Patrese 5:02.229 | 1.03× |

  "race fps" is measured over fields 2000–14000. On `a1200-fast`, green light to the
  "Race won by" banner took 2340–2372 frames for the winner's 302.229 s: 127–129 ms of
  game time per frame (200-field sampling at both ends; where the in-game clock starts
  relative to the green light is not established), so close to the pacer's 1/8 s. The
  last column is race fps × 128 ms.
- So the in-game clocks show game time. On the A500-equivalent a race shown as 4:46
  takes about 6:50 of real time; on `a1200-fast` the pacer holds the game at about real
  time. On slower machines the pacer seldom waits (A500-equivalent: work 5–14 fields per
  frame against a minimum of 6), so the game simply runs slower.
- The races differ between machines (each machine repeats its own exactly): on the
  A500-equivalent the player's car is never retired and Senna wins.

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
| green light | 8.04 | 124.3 / 140 / 240 | 72.8 / 86.2 / 120.4 | 41.8% |
| retirement and towing | 8.07 | 123.9 / 140 / 220 | 98.3 / 108.7 / 167.4 | 20.5% |
| follow camera | 8.06 | 124.1 / 140 / 220 | 85.7 / 103.0 / 145.4 | 30.8% |

- The frame rate is the pacer's cadence (6–7 fields per frame) in all three windows, not
  the machine's limit: no window's mean work fills its frame.
- The per-frame work runs under `h2+280F6` (46–62% of all cycles inclusive), which lives in
  hunk 2. That hunk is declared chip memory, so on this machine 27–36% of all cycles
  execute from chip RAM.
- DMA: about 56–62% of chip-bus slots are free; blitter 1.3–1.8%; bitplanes 22.5%.
  The CPU never stops (`STOP` 0%).
- Function names are hunk offsets of the nearest preceding call target, a heuristic; a
  large entry needs checking against the disassembly before acting on it.
