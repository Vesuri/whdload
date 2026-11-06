# Prince of Persia: A500 profiling

## Machine and tools

- A500: 68000/7 MHz PAL, OCS, 512 KB chip + 1.5 MB slow (`SETUP=a500-1.5m`; plain
  `a500` has 512 KB slow, too little for the slave's 0.5 MB chip + ~0.8 MB ExpMem). Kickstart 3.1 host,
  shipped v4.4 slave (the rebuilt slave was then byte-identical), PRELOAD.
- Emulator: by default the native arm64 FS-UAE in `tmp/native-emulator` (not tracked; sha256 `3627080a…`,
  4D Sports Driving's contact-write build, `source.patch` alongside; `tools/pop.py` checks the
  hash). It has `monitor key RAW 0|1`, `monitor fields N`, a whole-space profiler window and
  the explicit-frequency fix. AmigaXDev's native builds have the same once rebuilt
  (`fsuae-harness.patch`, `fsuae-cpu-frequency.patch`); select one with `POP_FSUAE=PATH`.
  A build without the frequency fix runs the A500 10.8% fast (157481 cycles per field).
- Captures boot with `WARP=1 DETERMINISTIC=1 JOY0=none` (port 1 keeps a joystick: with
  nothing in port 1 the slave's CD32 pad reader sees Play held and pauses the game).

## Driving the game

- The game starts paused: two Returns get into level 1 (field ~1400).
- Ctrl-K selects keyboard control. Movement is the numeric keypad (raw `2d/2f/3e/1e` =
  4/6/8/2); cursor keys do nothing.
- `tools/route.py OUT STEPS...` runs a step list (`f:N`, `t:KEY[:N]`, `d:`/`u:`, `s:NAME`,
  `S:N:EVERY`); `tools/sheet.py` makes contact sheets.
- `tools/spikes_route.sh OUT`: the level-1 route (run right, drop, fall with the loose plate,
  run left, climb, run left into the spikes). Two boots give identical per-PC cycles, field
  totals and frame timestamps.

## Profiling

`tools/profile_run.py` traces `P:N` steps in chunks of at most 100 fields, reduces each chunk
with AmigaXDev's `amigaxdev.callprofile` (self cycles per PC, cycles per call stack rebuilt
from JSR/BSR and the SP, per-field DMA slots, frame-wait marks with a running tally of the
STOP blitter waits) into `profile.pkl.gz` + `meta.json`, and deletes the trace. ~1000 fields
take ~25 s and ~3 MB.
- Game PCs are reported as original addresses (`g:$xxxxx`, the slave's patch-list numbering):
  `pc - reloc_base + $1000`. `reloc_base` is read from the live slave (`_reloc_base`, slave
  offset `$194`; `$d25000` on this machine).
- Reports: `tools/report.py PROF`, `tools/tree.py PROF [MIN%] [DEPTH]`, `tools/frames.py PROF`,
  `tools/dis.sh PROF START END` (disassembly by original address).

## Game structure found so far

- Frame pacing: the VBL handler (`g:$19f9a` → `g:$1a0c2`) counts `$49d14` down, reloaded from
  `g:$7aba` = 4, and swaps the display when the main loop has set `$49d18`. The main loop's
  frame wait is `g:$1bd46` (busy `tst.l (a0)` loop). Minimum frame time is 4 fields (12.5 fps).
- Blits are serial: `g:$053a2` and `g:$053d6` start a blit, then `STOP #$2000` until the level-3
  blitter interrupt clears `$1a24`. The STOP time is booked to the STOP PCs
  (`g:$053be/$053c8/$053ee/$053f8`).
- `g:$1bd5e` → `g:$1975c` copies 20000 words (a whole 320×200×5 screen) with the blitter every
  frame, in `$1000`-word blits, each followed by STOP.
- `g:$107d0`: compiled C tile-type lookup, ~127 calls per frame.
- Room change: `g:$0aba0` → `g:$0bafa` → `g:$116a2` → `g:$1173e` → `g:$11904` → `g:$1c29c`
  redraws the room tile by tile through `g:$1cb94` → `g:$05686` (asm shape blitter, STOP waits).

## Baseline: spikes route, A500 (tmp/prof-a500, 990 fields)

- 206 frames, 10.4 fps. Frame periods: 137 × 4 fields, 38 × 5, 13 × 6, 12 × 7–9 (the spike
  death), 2 room changes of 31 and 35 fields.
- Per frame: work 4.26 fields mean (3.73 median), of which 0.95 is STOP waiting for the blitter;
  frame-wait slack 0.54. 60 frames overrun 4 fields; 22 would without the STOP waits.
- CPU time: blitter STOP waits 21.6% (`$053be` 15.2%, `$053ee` 4.0%, others), frame wait
  10.2%, tile lookup `$107d0` 9.4% self, VBL handler 4.5%.
- Call tree (inclusive): `$0ba56` 39% (room/actor drawing `$116a2` 21%, full-screen restore
  `$094e4` 17%), `$1156a` 25% (game logic, tile lookups), `$0c0ac` 16%, frame wait 10.6%,
  `$0aba0` 6.5% (room change).
- DMA slots: bitplane 28.1%, CPU 31.8%, blitter 14.4%, free 23.8%.
- Room changes (tmp/prof-room1, prof-room2): 62–75% in `$0aba0`, mostly the tile redraw
  (`$1c29c` 34–43%); `$053d6` STOP waits plus one blitter interrupt per small blit.
