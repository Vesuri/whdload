# How duel v1 works

What is known about the original game, read from the binary and measured in traces.
Everything applies to `duel` v1 (108 868 bytes); v2 (109 248 bytes) has different offsets
and receives no new patches.

## Addresses and memory

- `duel:XXXXX` is an offset into `duel`'s root code hunk (hunk 0): the numbering of the
  slave's patch lists. A file offset is hunk offset + `$28` (`objdump -b binary` on the file
  prints file offsets). `kick:FCxxxx` is a Kickstart 1.3 ROM address; KickEmu copies the ROM
  into RAM and the tools translate.
- `duel` is an Aztec C overlay executable (`HUNK_OVERLAY` at file `$1571C`); all hot code is in
  the root hunk (`$1156C` bytes).
- Hunk 1, the data hunk, has a `$3A38`-byte file payload but a `$7A70`-byte allocation; most
  mutable state is in the zero-filled tail. Globals are addressed off a4 = hunk 1 + `$7FFE`.
  Find hunk 1 by following the BPTR at hunk 0 − 4, then add 4; do not byte-search (that can
  find WHDLoad's PRELOAD copy). Hunk 1 also holds a `jmp abs.l` jump table.

## Tasks

| Context | Exec node | Priority | Does |
|---|---|---|---|
| Simulation | the original `Initial CLI` process (type 13) | 4 | fixed-step physics, AI, clock, sound; also runs a light ~3 000-cycle slice every field (joystick, RNG) |
| Drawing | the created `Road Drawer` task (type 1, created at `duel:11264`) | −1 | renders the latest state as fast as it can |

The simulation step runs every 6 PAL fields (8.33 Hz) whatever the render rate: the
simulation preempts drawing. `tools/task_state.py` reads both nodes from a memory dump.

## Time sources

| What | Where | Notes |
|---|---|---|
| Gameplay field clock | `-17216(a4)`, long | +1 per field in the VBL callback (`duel:01abc`) |
| Step deadline | `-17212(a4)`, long | advances by the step period at `duel:05c12`; the constant 6 is the word at `-27862(a4)` |
| VBL counter | `-$30E2(a4)`, long | game VBL server `duel:0231c`, +1 at `duel:02330`; read only by audio timers |
| RNG | `duel:0e9e2`, seed `-18632(a4)` | `seed = (seed*6907 + 130253) ^ VHPOSR`: mixes the beam position. Both tasks call it |
| `WaitTOF` | stub `duel:114f2` | |
| CIA timers, timer.device, DateStamp | unused | |

The original race clock (`-10146(a4)`, nominal tenths; raw 1 shows 0:00, reset at
`duel:0bbf8`) gains one tenth per six-field step: it runs at 5/6 of real time on PAL.

Because the RNG mixes VHPOSR and drawing also consumes it, two boots differ in traffic and
scenery, and a different CPU lands in a different attract demo. The VERIFY build's `CUSTOM3`
removes the VHPOSR term (`duel:0e9f0`) to make runs reproducible.

## State map

All writers below run in the simulation step unless marked per frame (drawing).

| State | a4 offset | Size / meaning | Writer |
|---|---|---|---|
| Player position | -17238 | long, 16.16 road units | `0b2a6` (demo AI borrows and restores it at `05a88`/`05aec`) |
| Player speed | -13282 | long, 16.16; integer word drives the MPH needle | `0a8e6`, `0a754`, `0a828`, `0a8fa` |
| Race clock | -10146 | long, nominal tenths | `05b90` (+1), reset `0bbf8`, penalties `05c58`/`05eea` |
| Opponent position / increment | -13356 / -13348 | long 16.16 / per-step, player-speed scale /64 | `0de3e` / `0dd6e` |
| Same-direction / oncoming traffic origin | -13470 / -13466 | long 16.16, wraps at road length | `0e0f6` / `0e1b4` |
| Raw heading / lateral position | -13390 / -13386 | 8.8 / 16.16, updated per road segment | segment loop `0b312..0b444` |
| RPM / engine audio period | -13188 / -2792 | long 16.16 / word | `0a6f0`… / `0d156` |
| Fuel | -10822 | word, distance-derived | `0ade6` |
| Dashboard animation phases | -3008, -3006 | words | `0ae04`, `0ae34` |
| Camera snapshot (+ fraction at -13392) | -13394 | long, copy of player position | per frame, `06442` |
| View heading / lateral snapshots | -13388 / -13382 | drawing copies | per frame, latch `06474` |
| Background phases | -3120, -3116, -3112, -3108 | longs, +4000…+7000 | per frame in the original (`08cd0`…) |
| Needle caches | -24648, -24652 | sampled speed/RPM | per frame |

MILES is not a counter: the renderer derives it from road length (word at -17240) minus the
camera, ×100/4325. `tools/compare_state.py --assert-core` compares 35 core variables, including
lane, yaw, heat, gear, clutch, police counters, crash code and average-speed sums.

**Sampling trap:** inside the step the demo substitutes opponent values into the player
globals. A VBL sample can land inside that transaction (sample 0 of a capture often does).
Compare committed values, and classify an isolated mismatch by its PC.

## Frame cost (original game, A500)

A stock A500 (512 KB chip + slow RAM) draws ~7 fps in the first race. The CPU never idles:

| Share of cycles | What | Where |
|---|---|---|
| 13% | CPU span fill of five bitplanes, ~215 spans per frame | `duel:0789c` (interior `07928..0793a`) |
| 11% + ~9% | shape blitter: start one plane, poll BBUSY, next plane | `duel:0f114` |
| ~11.6% | ~150 blitter-finished interrupts per frame, mostly overlapping those waits | `kick:fc0d14` |
| ~16% | road and object projection | `duel:07370`, `duel:079c6` |
| ~7% | masked word copy | `duel:09588` |
| 3.6% | `movem.l` back-buffer clear | `duel:086c0..08768` |
| up to 18% in sign scenes | blitter line drawer, one blit per line | `duel:0f91a` |

Rendering is `duel:06c0c` under `duel:06432`; the buffer swap is `duel:05872`, where JOTD's
slave writes COP1LC (`set_copper`, `duel:0588a`) after a beam wait that prevents tearing on
fast CPUs. Projection and span loops already keep their state in registers: the remaining CPU
loop rewrites each recover under 1% of a frame.

**Fast CPUs are chip-bus bound.** A 68030 at 25 or 100 MHz and a 100 MHz 68020 all draw
exactly 25 fps with blitter priority: shape cookie-cut blits dominate (69 blits, ~4 750 words
per field), five low-res bitplanes take 28% of the bus and the CPU's DMACONR polls more. CPU
shape drawing was built and verified pixel-exact, and was slower on every machine: CPU
chip-RAM accesses cost more than blitter slots. Only less chip-bus work per frame (for
example a fast-RAM back buffer on 68030+) could pass 25 fps.

## Road renderer

- Per-frame camera distance: 16.16 at -13394, fraction F at -13392.
- Rows are 52 bytes; 44 main rows (0..43) from -5702(a4) and 24 mirror rows (0..23). Scale
  fields 18/22/26/48 (main) and 20/24/28/50 (mirror) come from immutable height, lateral and
  width tables written at race setup (`duel:06a90`).
- The complete-segment walker (`duel:073ec..0742a`, per row) adds each segment's curve byte ×2
  to the heading accumulator -14936 and its slope byte to the slope accumulator -14932 (both
  8.8, 1/256 index units). The original reads only the accumulators' high bytes from the
  table at -26166; height accumulates at -14928 and the row y is stored at 12(a3).
- The scanline table has 117 entries of 16 bytes and ends immediately before row 0.
- Mountains are drawn from the curve sum -13398 minus heading's high byte (`duel:08c90`, in
  four-pixel steps); the sum is updated at `072b8` via `08898`, and -17234 names its segment.
- Car sprites are pre-drawn at fixed sizes; size selection is discrete.

## Overlay loader and caches

The Aztec overlay manager modifies executable stubs in the data hunk. Unloading rewrites
JMPs into BSRs at `duel:0fe7e..0fe86`; loading rewrites them into JMPs at
`duel:0ff0c..0ff12`. The completed paths restore registers and return at `duel:0fe90`
and `duel:0ff1a`. KickEmu flushes caches after DOS LoadSeg, but the game's stub writes
happen afterward and need their own flush before executing the rewritten stub.

The supplied A1200/68040 hardware dump shows the startup call through `-31662(a4)` already
rewritten to JMP in RAM, while the saved overlay-loader context has consumed byte 4 of
that JMP as index 205. Its computed table entry contains `$67504879` rather than a valid
file offset, and the saved call returns to the Seek retry at `duel:0ff42`. The dump records
an ordinary quit, not an exception; its PC of `$FFFFFFFF` is not a game fault address.
The main game is loaded and patched, but the drawing task has not been created.

The fix replaces the two six-byte restore/return sequences with slave helpers
that call the official KickEmu `_flushcache` wrapper, then perform the displaced register
restore and return. WHDLoad's `resload_FlushCache` preserves all registers and flushes both
caches on 68040/68060. The user confirmed the diagnostic on the real A1200/68040.
The slave applies it to v1 independently of Enhanced framerate (upstream
[PR #25](https://github.com/jotd666/whdload_slaves/pull/25)); the diagnostic CUSTOM1 bit 2 toggle is removed.
Real 68060 hardware remains unverified.
