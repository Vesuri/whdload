# Fast RAM rendering and 50 FPS: plan (FR series, 2026-11-02)

Goal: on every machine where it is faster, draw each frame with the CPU into
Fast RAM and copy the finished image to Chip RAM once. Up to one new frame per
PAL field (20.03 ms, 49.92 FPS) is supported; that is the ceiling, not a
target (user decision, 2026-11-02). Game logic keeps its native
speed: the player at 20 ms and opponents at native 100 ms with the existing B8
render-pose blending. Nothing changes for the A500, the chip-only 020,
`CUSTOM2=0` or Irek's version.

This continues the H series in [RENDERING_PLAN.md](RENDERING_PLAN.md). It
supersedes H14 (CPU road) and H15 (dense cars) on machines that take the Fast
RAM path. It also covers most of H16's purpose: drawing into Fast RAM never
waits for the beam. Step IDs are FR0–FR10. Estimates are labelled; every
number not marked "measured" is to be confirmed by the step that needs it.

## 1. What is known

**Frame structure.** `FF1PresentationAfterTick` draws once it has caught up
with the 20 ms ticks, so the fine path has no 25 FPS cap. A frame shows in one
field when the work from one publication to the next fits in a field.
`B8Draw` currently does the following, in order:

1. Request `LoadView` of the previous frame (`$2428a`).
2. `OwnBlitter`, then prepare the road (H3).
3. Wait for line 256, or for a field that has passed since the request
   (`B8_65728`).
4. Clear and draw the back buffer:
   - clear `$6b050` and `$6b950`;
   - road `$6b368` and `$6bf90`;
   - cars `$69bb8`;
   - mirrors `$6ae70` and `$6af7e`, with their `$24ae0` bitmap operations;
   - pit messages;
   - cockpit `$6c0d0` and `$6ba18`, gauges `$6bbfc`, `$293d0` and `$6adf8`;
   - demo text `$239a0`, the flag and the clock.
5. `DisownBlitter`, then the instruments (`$6694e`).

The next loop's `WaitBlit` completes the last blits.

**Display.** There are two Chip banks of three planes each, used alternately.
The native view is 384 × 200 pixels with 48-byte rows. In the A500
calibration the planes are allocated 10,320 bytes apart (215 rows), and the
first visible fetch is base + 4. Some rows near the top are not cleared every
frame; the flag, clock and demo text live there. A whole three-plane bank is
28,800 bytes for 200 rows. If only 40 of the 48 bytes per row are displayed,
the visible part is 24,000 bytes; FR1 confirms this.

**Why the accelerated machines stall.** On the 040 the CPU mostly waits for
the blitter. The blitter and Chip RAM run at the same speed on every model.
Measured on 040‑40 BCE, grid scene, before H9–H13:

| Stage | ms per frame |
| --- | ---: |
| Road | 10.2 |
| Clear | 4.7 |
| Cars | 4.7 |
| `$6b950` | 3.3 |
| Cockpit, gauges and mirrors | about 11.7 |
| Text and HUD | about 2.5 |

The post-wait draw after H13 is about 36.8 ms. In dense packs the cars alone
take 33–41 ms. The current 040‑40 BCE frame rates are 24.51 (normal), 24.96
(solo), 24.92 (grid) and 12.48 FPS (dense). The 030‑50 BCE rates are similar
in common scenes.

**Sibling results.**

- **Mercenary 3 (S4/F):** staged its 3D view in Fast RAM and copied
  21,760 bytes to Chip with `movem` in 3.3 ms on the 030/50, measured. It
  reached 48 FPS on the 030/50 only after its code and scratch also moved to
  Fast RAM (F2–F5).
- **TFX:** copies only changed blocks to Chip on the 040; that does not pay
  on a cacheless 020.
- **Gunship:** draws its enhanced 3D view with the CPU in Fast RAM.

**Lessons from earlier work here.**

- A CPU cookie-cut that writes to Chip RAM lost on the 040 (H13: 36.97 to
  40.66 ms). CPU work only pays when it replaces Chip-bus work. It must not run
  alongside it.
- The 020 and 030 get no data cache. With WHDLoad's MMU option, the data cache
  crashed performance-mode startup, and HEAD crashes the same way.
- 060 is treated as 040-class and not tested separately. Real hardware
  testing is deferred, so every figure here is from the emulator.

## 2. Design

**Per-bank Fast shadows.** Each Chip bank gets a Fast RAM shadow of the same
layout (2 × 30,960 bytes for 215 rows). Every drawing write meant for bank X
goes to shadow X. One shadow per bank keeps the native semantics of
uncleared regions exactly: each bank still shows what was last drawn into
that bank. As a result, the existing exact frame gates remain valid.

**Copy point.** `B8Draw` runs a prefix of its stages into the shadow, then
copies the region the prefix owns from the shadow to the Chip bank, then runs
the remaining stages natively in Chip:

- At the start of the series the prefix is empty; that is the equal-layout
  control.
- Each FR5 step moves the copy point one stage later.
- At the end there are no blits during driving, and the copy is the only
  write to Chip.

**Publication.** Drawing into Fast RAM never conflicts with the display, so
the line-256/field wait moves from before drawing to before the copy. The copy
goes only into the bank that is not displayed. `LoadView` follows the copy.
Consequences:

- The CPU draws frame N+1 while frame N waits for its field. Lost waiting time
  shrinks without a third Chip bank.
- A frame that misses the field is shown one field later, as today.

**Software blitter.** The blitter cannot reach Fast RAM, so every blit in a
redirected stage must run on the CPU:

- **Exact reference first (FR2):** a complete software blitter, the oracle
  for everything that follows.
- **Specialized kernels second (FR6):** for the measured hot cases.

Redirection happens at the native blit sites:

- The custom-register writes go to a Fast register image.
- The `BLTSIZE` write becomes a call that executes the blit with addresses
  translated. Bank addresses go to the shadow; source addresses go to Fast
  mirrors where they exist.
- `WaitBlit`/`OwnBlitter` inside redirected stages cost nothing because the
  blits are synchronous.

The race code is already a public relocated copy with a patch ledger, so this
uses the existing patch and restore machinery.

**Activation.**

- Only in performance mode (`CUSTOM2=1`).
- Only on CPUs where it measurably beats today's path (user decision,
  2026-11-02). FR0 makes the first estimate; FR10 decides per CPU.
- Only with real Fast RAM and successful allocation of every FR buffer.
  Otherwise today's path runs unchanged, with no half-enabled state.

The 68000 and chip-only 020 payloads stay byte-identical.

## 3. Steps

Each step is one switchable, equal-layout change and one commit, unless the
step says it is analysis only. Re-measure after each accepted step, and do not
stack estimates. The gates in section 4 apply to every code step; additional
gates are listed per step.

### FR0 — Feasibility and budget (diagnostic fixtures only)

Decide whether 50 FPS is reachable and on which CPUs before writing any
production code. Run on 040‑40 BCE and 030‑50 BCE in normal, solo, grid and
dense, with 300 complete presentations and warp off.

- **FR0a. Floor without drawing.** Bypass every stage of `B8Draw` except
  publication.
  - Record the interval histogram, tick cost and road-preparation cost.
  - Record the frames that contain the 100 ms opponent update separately:
    they come once in five frames and set the worst case.
  - This is the ceiling per CPU: no drawing work can beat it. Report it;
    a ceiling below one field is not a reason to stop.
- **FR0b. CPU floor of the drawing code.** Run `B8Draw` with every `BLTSIZE`
  write and `WaitBlit` suppressed. The pixels are wrong; the purpose is the
  CPU cost of the native drawing logic alone (projection, sorting, setup and
  clipping) once the blitter waits and `WaitBlit` dispatch disappear.
- **FR0c. Copy cost.** Copy 3 × 10,320 bytes and the visible 3 × 40 × 200
  bytes from Fast to Chip with `move.l`, 12-register `movem.l` and (040)
  `move16`.
  - Time each at the start of a field and mid-display with the game's
    display DMA running.
  - Also time Chip-to-Fast reads, which FR3 needs to resync the shadows.
  - Estimate from Mercenary 3: 3.6–4.4 ms on the 030/50.
- **FR0d. Kernel micro-benchmarks in Fast RAM.** Each kernel is a rough
  prototype, not exact:
  - a 24-word × 103-row descending exclusive fill;
  - 50 road-edge lines;
  - the six background fills;
  - 37 one-row spans;
  - one car-sized and one cockpit-sized cookie-cut, with the colour
    expansion merged in.
- **FR0e. Budget and go/no-go.**
  - Budget per frame: FR0a + FR0b + FR0c + the FR0d sum, against 20.03 ms.
    Aim for at most 18 ms in the opponent-update frame.
  - Record the result in `tmp/manifest/fr0-budget.json` and a section
    here.
  - **Decided (user, 2026-11-02):** every CPU that gains takes the path;
    50 FPS is the ceiling, not a requirement. FR0 estimates the gain per
    CPU (020+Fast, 030, 040) and scene. A CPU whose budget shows no
    plausible gain over today's path is not pursued further.
  - **Stop:** if no CPU shows a plausible gain, report the shortfall and stop.

### FR0 results (measured 2026-11-02; emulator only)

Matrix: 040‑40 BCE, 030‑50 BCE and 020+Fast (`a1200-fast`) × normal, solo,
grid and dense, performance mode, warp off. FPS runs use 300 intervals. Traces
are 30 fields (60 for the benchmarks); the 030 traces run as 68EC030 because the
full-MMU 68030 loop is not instrumented (HI25 caveat M‑3). The FPS runs use the
real 68030. Diagnostic builds and tools are in the ignored harness
(`tools/fr0_*.py`, `tools/fr0_bench*.s`). The budget is in
`tmp/manifest/fr0-budget.json`. The `base` build is byte-identical to the
production slave (`597a74b9…`).

**Method change for FR0b.** Instead of suppressing `BLTSIZE`, FR0b runs the
unchanged slave with the emulator's immediate blitter
(`--uae_immediate_blits=true`, which works with the cycle-exact blitter). Each
blit completes instantly, uses no Chip bus time, and pixels stay correct. The
result is the cost of the drawing logic with blits free.

**FPS (300 intervals).**

| CPU | Scene | Today | Blits free (FR0b) | No drawing (FR0a) |
| --- | --- | ---: | ---: | ---: |
| 040‑40 | normal / solo / grid | 24.51 / 24.96 / 24.96 | 49.92 (all 1 field) | 49.92 |
| 040‑40 | dense | 12.48 | 49.92 | 49.92 |
| 030‑50 | normal / solo / grid | 24.55 / 24.96 / 24.96 | 49.92 | 49.92 |
| 030‑50 | dense | 12.48 | 49.92 | 49.92 |
| 020+Fast | normal / solo / grid | 15.34 / 16.64 / 14.95 | 33.88 / 34.91 / 30.01 | 49.92 |
| 020+Fast | dense | 8.97 | 30.01 | 49.92 |

**Work per frame, ms (CPU time excluding the beam wait, WaitBlit and idle).**

| CPU | No drawing, mean/max | Blits free, mean/max (normal … dense) |
| --- | --- | --- |
| 040‑40 | 2.1–2.5 / 3.6 | 9.5–10.2 / 11.3–12.1 |
| 030‑50 | 2.8–3.3 / 5.0 | 11.2–11.8 / 12.8–13.6 |
| 020+Fast | 8.1–10.3 / 17.4 | 22.5–26.8 / 30.8–33.8 |

Opponent-update frames add about 0.5 ms on the 040 and 030 and up to 7 ms on
the 020. The ceiling (FR0a) is one field on every CPU.

**Copy (FR0c), ms, 040 / 030 / 020.** Bank (30,960 bytes), best method:
4.32 / 4.32 / 4.57. Visible part (24,000 bytes): 3.61 / 3.73 / 4.98.
Chip→Fast read of a bank: 4.56 / 5.11 / 6.58. `move.l`, `movem` and `move16`
come within 0.3 ms of each other on the 040: the Chip bus is the limit. Early
(mid-display) and late (after line 256) copies cost the same.

**Kernel prototypes (FR0d), ms, 040 / 030 / 020.**

| Kernel | 040 | 030 | 020 |
| --- | ---: | ---: | ---: |
| Descending fill 24 × 103 | 1.42 | 0.94 | 3.31 |
| 50 lines, 5,150 one-dot rows | 3.20 | 2.91 | 10.35 |
| Six background fills (3 planes) | 0.23 | 0.58 | 2.06 |
| 37 one-row spans (24 words × 3 planes) | 0.24 | 0.21 | 0.76 |
| Car cookie-cut 6 × 40 × 3 planes | 0.41 | 0.31 | 1.12 |
| Cockpit cookie-cut 13 × 57 × 3 planes | 1.24 | 0.95 | 3.36 |

**Blitter work today (040 base traces).** Blitter DMA per frame: normal
17.9 ms, solo 14.5, grid 19.1, dense 57.7. Today the 040 spends 10–16 ms per
frame on CPU drawing and 20–55 ms in WaitBlit. CPU and blitter run almost
serially.

**Budget (FR0e).** The estimated frame is the logic with blits free, plus all
blits replaced by the prototype kernels and scaled by the per-frame blit
counts, plus a full bank copy:

| CPU | Scene | Kernels | Estimate, mean | Estimated FPS (today) | Kernels must fit in, mean / worst frame | Kernel speedup needed |
| --- | --- | ---: | ---: | --- | --- | ---: |
| 040‑40 | normal | 14.1 | 27.9 | 24.96 (24.51) | 6.9 / 5.1 | 2.0× |
| 040‑40 | solo | 8.6 | 22.6 | 24.96 (24.96) | 6.8 / 4.8 | 1.3× |
| 040‑40 | grid | 16.1 | 30.6 | 24.96 (24.96) | 6.3 / 4.4 | 2.6× |
| 040‑40 | dense | 79.3 | 93.9 | 9.98 (12.48) | 6.2 / 4.3 | 12.8× |
| 030‑50 | normal | 11.9 | 27.4 | 24.96 (24.55) | 5.1 / 3.5 | 2.3× |
| 030‑50 | solo | 7.7 | 23.2 | 24.96 (24.96) | 5.1 / 3.4 | 1.5× |
| 030‑50 | grid | 13.5 | 29.5 | 24.96 (24.96) | 4.6 / 2.8 | 3.0× |
| 030‑50 | dense | 62.0 | 78.1 | 12.48 (12.48) | 4.5 / 2.7 | 13.8× |
| 020+Fast | all | 27–220 | 56–251 | 3.8–15.4 (9.0–16.6) | none: logic + copy exceed a field | — |

"Must fit in" is the field minus the logic with blits free minus the
visible-only copy. The "speedup needed" column is how much faster than the
prototypes the kernels must run for the mean frame to fit one field.

**Findings.**

1. **The blitter is the whole bottleneck on the 030 and 040.** With blits
   free, every scene, dense included, runs at one field per frame. The logic
   costs 9.5–11.8 ms.
2. **At prototype kernel costs, no CPU gains.** On the 040 and 030 the
   estimate stays at two fields in common scenes and gets worse in dense.
   The prototype kernels are about as fast as the blitter: 16 ms against
   19 ms in grid on the 040.
3. **The 020+Fast does not gain and is not pursued.** Its logic alone, 22–27
   ms with blits free, already exceeds a field, and its kernels are about 3×
   slower than the 040's.
4. **Common scenes need kernels 1.3–3× faster than the prototypes on the 030
   and 040.** The largest prototype costs are the road: lines and fill take
   6.0 ms of the 14.1 ms on the 040 in normal. Drawing the road as spans
   directly, without lines and fill, and treating the cockpit's opaque words
   as plain copies would close much of that gap. This is not demonstrated
   yet.
5. **Dense cannot reach one field.** Its 58 ms of blitter work would need
   kernels more than 12× faster. Reaching three fields instead of four would
   need about 1.8×.
6. **An alternative is visible in the data, outside this plan.** CPU and
   blitter run serially today, and the blitter is busy only 14.5–19.1 ms per
   common-scene frame. If the CPU logic overlapped the blits, the bound
   would be about max(logic, blitter) ≈ 18–19 ms in normal, solo and grid on
   the 040. That would work without Fast shadows or a copy, but blits would
   have to be queued instead of waited for. Not measured.

**FR0e verdict.** At the measured prototype costs, no CPU shows a gain, so
the stop rule applies. The 030 and 040 come close enough in common scenes
that the verdict depends on kernel quality, which FR0 does not settle. Two
options for the user to choose between (not decided):

- **(a) Stop the FR series** here, with these results recorded.
- **(b) Extend FR0 by one diagnostic step (FR0f)** before any production
  code. Prototype a span-based road (replacing lines and fill) and an
  opaque-aware cockpit/car cookie-cut. Re-run the budget. Continue to FR1
  only if normal, solo and grid then fit a field on the 040 or 030. Dense
  stays at today's path either way.

The serial CPU/blitter finding (6) is a separate idea and would need its
own plan.

### FR0g — One real dense frame on the 030 (measured 2026-11-02)

User request: measure real code for one real dense frame on the A1200/030
instead of extrapolating from prototypes. Everything the drawing touches is
in Fast RAM: sprite and car graphics, masks, colour scratch and the back
buffer. Only the final copy would go to Chip.

**Method.**

1. **Capture.** An emulator copy (`tmp/step5-frame-observer-blitlog-build`,
   new `monitor blitlog`) logged every blit started in one dense-fixture frame
   on 030‑50 BCE. For each blit it records the registers, the pre-blit bytes
   of each channel and the D bytes afterwards.
2. **Reference check.** A Python blitter that follows the emulator's
   semantics (`tools/fr0_blits.py`) reproduces 279 of 280 blits byte for
   byte. The remaining one is overwritten by the CPU gauge strips (H13)
   before the next blit, so it cannot be compared.
3. **Fast image.** The frame needs a 117 KB Fast image: the union of every
   region read or written, in 29 segments, filled from the Chip snapshot at
   the frame's start. It is built with 280 translated blit records
   (`tools/fr0_replay_gen.py`).
4. **Replay.** 68030 code (`tools/fr0_replay.s`) executes the records with
   run-time classification. It uses specialised loops for the classes in the
   frame and an exact generic path for the rest (21 small blits per frame).
   It runs in the no-draw build every frame after the line-256 wait. A
   restore of the image runs first and is not counted.
5. **Correctness.** After a replay, the Fast image equals the Python
   sequential replay byte for byte: 0 differing bytes out of 119,744
   (`tools/fr0_replay_check.py`).
6. **Timing.** 30-field trace (68EC030, HI25 M‑3); cost charged by routine
   and averaged over 12–15 replays.

**The frame's blits.**

| Class | Blits | Words or dots |
| --- | ---: | ---: |
| ABCD cookie-cut `$CA` | 32 | 20,309 words |
| ABD colour masks `$C0`/`$FC`/`$30` | 23 | 15,488 words |
| Lines `$4A` | 122 | 2,263 dots |
| Descending fill | 10 | 3,296 words |
| Other (BCD spans, ACD, D, CD) | 93 | |

The blitter's own DMA for a dense frame is about 58 ms (040 base trace).

**Cost on 030‑50, ms per frame** (each version byte-exact):

| Version | Total | Cookie-cut | Lines | ABD | Fill | Rest |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Word loops, exact line emulation | 45.0 | 17.5 | 6.8 | 9.8 | 3.0 | 7.9 |
| + Bresenham XOR lines, 32-bit ABD, transparent/opaque skip | 35.0 | 18.6 | 2.6 | 3.1 | 3.0 | 7.7 |
| + 32-bit funnel-shift cookie-cut | **31.6** | 15.1 | 2.6 | 3.1 | 3.0 | 7.8 |

**Dense frame on the 030, assembled:**

| Part | ms |
| --- | ---: |
| Logic with blits free (FR0b, mean / max) | 11.8 / 13.6 |
| All blits by CPU in Fast RAM | 31.6 |
| Copy to Chip, visible / whole bank | 3.7 / 4.3 |
| **Total, mean / max** | **about 47 / 50** |

That is three fields (16.6 FPS) against today's four (12.48 FPS), a 1.33×
gain, with no further work.

**What this corrects in FR0e.** The prototype budget predicted 62 ms of
kernels for dense on the 030 and called it unreachable. That came from
scaling car work by blitter DMA slots. The real frame needs 31.6 ms, about
1.8× faster than the blitter's 58 ms. Drawing with the CPU in Fast RAM is
faster than the blitter on the 030 for this frame.

**Headroom not yet used, estimates only:**

- Merge the colour expansion into a single pass per car: read and shift the
  mask once for three planes instead of separate ABD and per-plane ABCD
  blits. This removes most of the 3.1 ms of ABD and roughly a third of the
  cookie-cut cost.
- Clear in Fast RAM instead of in Chip. Today's CPU clear is inside the
  logic figure.
- Two fields (40 ms) for dense needs about 7 ms less. That is plausible with
  the merged pass but not shown.

**Open.** This is one frame of one scene on one CPU. Normal, solo and grid,
and the 040, are not measured this way yet. Their blitter load is 14.5–19 ms
per frame, so one field also needs the logic (11–12 ms) to shrink. The same
pipeline (`fr0_blitcap.py` → `fr0_replay_gen.py` → `fr0_build.py replay` →
check → trace) can measure them in minutes.

### FR0 decision and plan revisions (2026-11-02)

**Go** (user and assistant agree, 2026-11-02). The real dense frame on the 030
draws in 31.6 ms of exact CPU work against about 58 ms of blitter work. That
gives 3 fields instead of 4 before any structural optimisation. This replaces
the prototype-based FR0e verdict.

**Scope and expectation.**

- **CPUs.** The 030 and 040 are pursued. The 020+Fast is excluded: its logic
  alone exceeds a field.
- **Expected win.** The measured gain is in heavy scenes: dense goes from 4 to
  3 fields, possibly 2 with the merged car pass.
- **Common scenes.** Normal, solo and grid reach one field only if the drawing
  logic also shrinks. Logic with blits free is 11–12 ms, so 20 ms leaves
  about 4–5 ms for blits and copy. Until then their expected result is "no
  slower" (2 fields).
- **The selection gate is unchanged.** A CPU takes the path if it is faster
  overall and slower in no scene.

**Revisions to the steps below.**

1. **New FR0h, the first execution step, diagnostic only.** Run the FR0g
   pipeline for normal and grid on the 030 and for normal, grid and dense on
   the 040. It confirms the 040 and sets each scene's real blit cost before
   any production code. It is small: the tools exist.
2. **All drawing data in Fast RAM** (user requirement, 2026-11-02). Only the
   final copy writes Chip.
   - FR1 must list every Chip source a blit or CPU drawing write reads, not
     only the banks.
   - FR3 allocates Fast copies of all of them. Static assets are copied at
     driving entry and on overlay reload. Dynamic data (colour scratch, the
     cockpit with its gauge writes, glyph scratch) lives only in Fast.
   - FR4 translates every source pointer, not only "where mirrors exist". A
     pointer outside the known banks and mirrors takes the production fault
     exit.
   - The FR4 VERIFY guard covers Chip reads as well as writes.
3. **FR2 is reduced to medium.**
   - `tools/fr0_blits.py` is already verified against the emulator on 280
     real blits and becomes the offline oracle.
   - `fr0_blitcap.py` supplies real register images per scene.
   - `tools/fr0_replay.s` (exact generic path plus fast paths) is the
     starting point for `FastRenderBlit.s`.
   - The in-guest Chip-versus-Fast oracle harness and generated coverage
     remain required.
4. **FR6 order, from measured costs** (030 dense, ms):
   1. Car cookie-cut with the colour expansion merged into one pass per car
      (15.1 + 3.1).
   2. Fill (3.0).
   3. Lines (2.6, already Bresenham).
   4. The remaining classes and the generic path (about 7.8).
5. **New FR11 (optional, separate decision after FR10): drawing-logic cost
   for common scenes.** Profile the 9.6–10 ms of non-blit drawing logic on
   the 030 and 040 (projection, sorting, setup, today's CPU writers). Reduce
   it towards the one-field budget. Gates as in section 4.

Revised order:

```
FR0h → FR1 → FR2 → FR3 → FR4 → FR5a…FR5f → FR6 → FR7 → FR8 → FR12 → FR10 → (FR11)
                                   ↑ checkpoints at FR5c and FR5f
FR9 any time, only if it would help the 030.
```

### FR1 — Screen write and read census (analysis only)

Attribute every access to the display banks during driving. Use the existing
trace and DMA-census tools in BCE mode (blitter DMA records). If the
instruction trace lacks store addresses, add a bank write-watch to the
measurement emulator. Cover normal, solo, grid and dense, plus pit messages,
demo text, flag blinking and the countdown.

1. **Writers.**
   - For each blit: issuing PC, channels, minterm, area or line mode, fill
     flags, shifts, masks, size and destination range.
   - For each CPU write: PC and range, including H5/H9/H10/H11/H13.
2. **Readers.**
   - Blitter C channel reads, such as the cookie-cut background.
   - CPU reads, such as the H9 pre-fill scan.
   - Confirm that nothing outside drawing reads the banks, apart from display
     DMA.
   - Check for any reader of the blitter zero flag (`DMACONR` BZERO): the
     software blitter must then produce it.
3. **Sources outside the banks.**
   - Car images and masks, colour scratch `$1c1b8`, the cockpit image (with
     its H13 gauge writers), fonts and the flag: size, writers and lifetime,
     including overlay reload.
4. **Geometry.** DDF/modulo from the live copper list: the exact displayed
   bytes and rows, which define the copy region.
5. **Persistence.**
   - Which bank regions are not rewritten every frame, and which code writes
     them outside the fine draw: race start, pause, pit, menu, tow and
     re-entry.
   - This defines when the shadows must be resynced.

Output: `tmp/manifest/fr1-census.json`, plus a section here listing the
native blit sites. Step 3 recorded 27 `WaitBlit` call sites in about ten
routines in the A500 calibration; addresses must be resolved per layout.

**Gate:** every byte written to a bank during a fine draw is attributed to a
site.

### FR1 results (2026-11-02, done)

Gate passed: every blit and every CPU write into a bank during driving is
attributed to an issuing instruction. The data is in
`tmp/manifest/fr1-census.json`; the lifecycle timelines are in
`tmp/step5/fr1-bankwatch/`. All results are from the emulator only.

**Method.**

- **Recorders.** The blit-log emulator copy gained three recorders:
  - `memlog`: every CPU data access to Chip RAM and every `DMACONR` read,
    with the instruction PC, the index of the next blit and a stack snapshot
    at every `BLTSIZE` write;
  - `bankwatch`: per-field accesses to given ranges, aggregated by PC and
    enabled by an environment variable, so the release route harness runs
    unchanged;
  - `monitor poke`, plus the `irq-state` command the release harness needs.
- **Tools.** `fr1_capture.py`, `fr1_census.py`, `fr1_report.py` and
  `fr1_bankwatch.py`.
- **Driving scenes**, 030‑50 BCE, after the 100th draw:
  - normal (12 frames) and solo, grid and dense (4 frames each);
  - start, 8 frames during the countdown (`$66f94` = 17);
  - pit messages 1 and 2, set with a presentation-only `B8PitMessage` poke.

  Demo text and the flag are drawn in all of them. normal, start and pit use
  the production slave `597a74b9…`; solo, grid and dense use the matched
  H5 fixtures.
- **Lifecycle.** The release modal route ran twice under bankwatch: once
  watching the banks and once watching the sources. It covers boot, race
  start, pause, tow, exit, pit menu, paddock, race settings and re-entry into
  qualifying driving.
- **Attribution.** The number of logged `BLTSIZE` writes equals the number of
  blits in every capture, so every blit has its instruction. On the 68030 CE
  core the logged PC is the instruction after the access. The tables below
  give the routine and that PC; the `BLTSIZE` write is the instruction
  before it.

**Display geometry (copper lists).**

- **Copper lists.** Bank 0's list is at `$ce30` and bank 1's at `$20838`;
  both are in Chip outside the banks.
- **Display registers.** BPLCON0 `$3200` (3 planes) from line `$2c` to
  `$f4`, which is 200 lines. DDFSTRT `$30` and DDFSTOP `$c8` give 20 words
  per row; BPL1MOD and BPL2MOD are 8, and BPLCON1 is `$66`.
- **Plane pointers.** They start at bank + 4, with a plane stride of 10,320
  bytes.
- **Copy region.** Bytes 4–43 of rows 0–199 in each plane:
  **24,000 bytes per bank.**
- **Banks.** Bank 0 is `$18f48`/`$1b798`/`$1dfe8` and bank 1 is
  `$528d8`/`$55128`/`$57978`, from `$66c92`.

**1. Blit sites during driving** (blits per frame: normal, solo, grid,
dense, start).

| Site (PC after `BLTSIZE`) | Per frame | Type | Destination ← sources | Callers |
| --- | --- | --- | --- | --- |
| `$24ae0`+`$138` (`$24c18`) | 39/39/39/39/15 | BCD, some descending; minterm `ca`; ASH 0–14 | bank ← Chip images (B), bank (C); also Chip scratch | `$6b950` (B8 `$65748`), cockpit `$6c106`/`$6c310`, gauges `$6bbfc`, flag `$66802` |
| `$24ae0`+`$2d8` (`$24db8`) | 34–36 | BCD; minterms `0a`/`fa`/`ca`/`3a`; BSH 0–15 | bank and mirror scratch ← glyphs, font, images | `$6b950`, B8 text `$65922`/`$65a4e`/`$65b68`/`$65c94`, mirrors `$6a6d8`, `FF1RenderDemoText`, `$6c310`/`$6c56a` |
| `$6ac4a`+`$140` (`$6ad8a`) | 97–104 | Line, `4a`, mostly EFE fill (some FCI) | bank ← bank (C) | road `$6b368` |
| `$6ac4a`+`$194` (`$6adde`) | 20–22 | Line, `4a`, EFE | bank ← bank | road `$6b368` |
| `FF1RenderFill`+`$b4` | 10–14 | CD, EFE fill, descending, `aa` | bank ← bank | road `$6b368` / `$6c958` |
| `$32d50`+`$aa` (`$32dfa`) | 9/3/10/10/9 | ABD `fc` | car-mask scratch ← car image and mask | cars `$69e44`/`$6afec`, mirrors `$6ae70`/`$6af7e`, `$6adf8` |
| `$32d50`+`$11c` (`$32e6c`) | 12/3/13/13/12 | ABD `c0`/`30` | car-mask scratch ← car image and mask | as above |
| `$32d50`+`$1b2` (`$32f02`) | 27/9/30/30/27 | ABCD `ca`, ACD `0a`; ASH/BSH 0–15 | bank ← car (A/B), bank (C) | as above |
| `$6c310`+`$24c` (`$6c55c`) | 3 | D only, `00`/`ff`, 12×55 | bank (cockpit rectangle fill) | B8 `$65cb8` |
| `$6ba18`+`$1d4` (`$6bbec`) | 6 | ABCD `ca`, ASH 3–15 | bank ← Chip `$cd30`, `$41398` (A), `$cf58`, `$41398` (B) | B8 cockpit call |
| OS `WritePixel` (graphics.library copy in Fast) | 12 | CD 1×1 `ea`/`2a` | bank, 4 pixels × 3 planes | instruments `$6694e` → `$66a08` → `$2a1b0` |

There are 11 game sites plus the OS one. The `$24ae0` bitmap routine is
reached through the public `FF1RenderBitmap` hook, and its two `BLTSIZE`
sites carry about 74 blits per frame. Redirection at these 11 instructions
and at `$2a1b0` covers every blit during driving.

**CPU writers into the banks:**
- `FF1RenderClearRows` (long writes, about 4,300 per frame);
- `FF1RenderOverlapHUD`/`FF1FlagPresentation` (bytes, 168 per frame);
- `FF1RenderBitmap`+`$14a`…`$174`, the pit-message text through the CPU
  bitmap path (bytes, 288 or 432 per frame across both banks while a message
  shows).

**2. Readers.**

- **Blitter C channel.** Every cookie-cut, line, fill and `$24ae0` site reads
  the bank it writes.
- **Blitter B channel.** `$24ae0` also reads the bank through B, about 225
  words per frame from `$6b950`, a copy from one place in the back bank to
  another.
- **CPU reads of the banks:**
  - the H9 pre-fill scan `FF1RenderFill`+`$68`, 138–877 long reads per
    frame;
  - `$24ae0`+`$3c` (`$24b1c`, `movea.l (a4),a0`). It reads the first long of
    its bitmap argument, even when that argument is a raw bank address. The
    value is then overwritten unless argument word 50(sp) is negative. FR4
    translates the pointer, so the read lands in the shadow; the VERIFY
    Chip-read guard must allow this read.
- **Nothing else reads the banks during driving.** The only readers outside
  the drawing routines appear during menus and setup.
- **`DMACONR`.** Every reader tests bit 6, BBUSY, with
  `btst #6` / `tst.b`: host `gfx_WaitBlit`/`gfx_waitblit` and the OS
  `WritePixel`. **No reader tests BZERO**, so the software blitter does not
  need to produce it.

**3. Front-bank writes.** Two writers also draw into the bank on display
while the other bank is being drawn:

- the demo label, `FF1RenderDemoText` drawing into `$226ae` then `$226b2`:
  528 bytes per frame (3 × 11 words × 8 rows at row 20);
- the pit messages (`FF1RenderBitmap`): 144 or 216 bytes per frame.

Both write identical pixels into both banks. With per-bank shadows, FR4
sends them to the front shadow. The published frames stay identical, because
the front bank receives the same pixels when it is next drawn and copied.
Natively the text appears up to one field earlier, mid-frame. The full
24,000-byte copy also covers these rows.

**4. Chip sources outside the banks.** Everything below `$c000` and the
supervisor stack at `$7ff6e`–`$80000` is OS and interrupt data. Neither is
drawing data. The drawing sources are:

| Range | Bytes | Content | Read by | Written during driving |
| --- | ---: | --- | --- | --- |
| `$cd30`–`$cd78` | 72 | small cockpit/gauge table | `$6ba18` A | CPU `$252d0`, `$6d066`, `$6d472`, `$6d4cc` |
| `$cf58`–`$d3d6` | 1,150 | glyph/text data, including the pit strings `$d0c0`/`$d0c6` | `$24ae0` B, `$6ba18` B, CPU `FF1RenderBitmap` | CPU `$252d0`, `$68d4e`, `$6bbfc` |
| `$17238`–`$17258` | 32 | small car image | `$32d50` A/B | no |
| `$18d80`–`$18e0b` | 139 | Chip hunk 46 (`$255a0`, 456 bytes; the only Chip hunk) | `$24ae0` B, CPU `FF1RenderGaugeStrip` | no |
| `$22652`–`$229ca` | 888 | flag/HUD image | `$24ae0`+`$138` B | no |
| `$23e10`–`$28e32`, `$34ba0`–`$34cf2`, `$45478`–`$459ea` | about 18,000 | car images and masks | `$32d50` A/B | no |
| `$35f70`, `$38300`, `$3a690` | 3 × 8,716 | cockpit image planes | `$24ae0` B | no |
| `$41398`–`$428fa` | 5,474 | gauge/cockpit composition scratch | `$24ae0` C, `$6ba18` A/B, CPU `FF1RenderGaugeStrip` | blit `$24ae0` D, CPU `FF1RenderGaugeStrip` |
| `$49798`–`$49a5a`, `$50188`–`$5044a` | 2 × 706 | mirror bitmaps | `$32d50`, `$24ae0` | blit `$24ae0`+`$2d8` D |
| `$4b568`, `$4b898` | 2 × 406 | HUD images | `$24ae0`+`$138` B | no |
| `$518e8`–`$527e2` | 3,834 | car-mask scratch and colour scratch `$1c1b8` | `$32d50`+`$1b2` A/B, `$24ae0` B | blits `$32d50`+`$aa`/`$11c` D, CPU `FF1RenderDemoText` |

That is about 58 KB of sources: static images about 46 KB and dynamic
tables and scratch about 12 KB. FR3 copies the static ranges and keeps the
dynamic ranges in Fast only. The dynamic ranges include the native CPU
writers listed, so those writers must be redirected too.

**Source lifetime (second lifecycle run, watching these ranges):**

- **During driving**, no static range is written. The only hits are the
  dynamic ranges marked in the table. A few line-blit hits come from
  bankwatch's deliberately wide line-mode span estimate, not from real
  writes; the exact per-word census above shows none.
- **Before each driving entry** (race start and re-entry, about 40 fields
  each), setup code rewrites every range: OS graphics code and native
  `$24e2a`/`$24e48`/`$24e62`.
- **Menus.** The menus and paddock reuse several of these ranges (for
  example `$41398` and `$45478`), and boot clears them.
- **Consequence for FR3:**
  - copy the static sources at the same point the shadows are seeded, the
    first fine draw of each driving entry;
  - overlay reload needs no separate trigger, because reload only happens
    outside driving and is followed by a new entry.

**5. Persistence.**

- **During driving**, in every scene and every frame, the drawing rewrites
  the same 21,954 of the 24,000 displayed bytes per bank. No byte is written
  in some frames and not others.
- **Never rewritten** (2,046 bytes, identical in both banks):
  - rows 0–2 entirely;
  - the top-right panel, rows 3–52, bytes 28 or 34–43.

  At the start it is 2,592 bytes. Pit messages draw into part of this panel,
  in both banks.
- **Lifecycle (bank timeline):**
  - before each driving entry (race start, and re-entry from the menus), OS
    graphics code and native `$24ae0` (`$24c18`/`$24db8`) rewrite both banks
    in the 4–6 fields before the first fine draw;
  - the menus, paddock and race settings use the bank memory continuously
    (`$24db8` in about 7,000 fields);
  - pause and pause-held write nothing to the banks;
  - tow and exit hand over to the menu code, which rewrites them.
- **Consequence for FR3:**
  - seed both shadows from Chip at the first fine draw of every driving entry;
  - treat the shadows as invalid as soon as driving exits;
  - no other resync point exists inside driving.

**Corrections to later steps.**

- **FR2:** BZERO is not needed. Line mode with EFE/IFE fill and FCI, the
  descending fill, and all 16 ASH/BSH values are required.
- **FR4:**
  - the redirection list is the 11 instructions above plus `$2a1b0`
    (`WritePixel`);
  - front-bank writes go to the front shadow;
  - the `$24b1c` read must be translated.
- **FR3:** the source list is the table above, seeded at driving entry.
  The native CPU writers of the dynamic tables (`$252d0`, `$68d4e`,
  `$6bbfc`, `$6d066`, `$6d472`, `$6d4cc`, `FF1RenderGaugeStrip`,
  `FF1RenderDemoText`) must write the Fast copies. Redirect them in FR4 the
  same way as the blit sites, or keep those tables in Chip and mirror them
  at each draw. That choice belongs to FR3.
- **FR7:** the copy is 24,000 bytes per bank, so the persistent top-right
  panel needs no special case.

### FR2 — Exact software blitter (reference)

`FastRenderBlit.s`, 68020+ code in the public fine payload. It executes one
blit from a register image:

- **Area mode:** all channel combinations and all 256 minterms (with a fast
  path for the minterms found in FR1). It also handles ASH/BSH, first- and
  last-word masks, modulos, descending mode, and inclusive or exclusive fill
  with FCI carry.
- **Line mode:** octants, SIGN, SING one-dot lines, texture with BSH,
  start pixel, and the hardware's first-pixel behaviour.
- **BZERO:** produced if FR1 finds a reader.

Speed is not a goal here.

**Oracle harness.** A VERIFY fixture runs each case twice: on the hardware
blitter into a Chip scratch area, and in software into a Fast scratch area.
It compares the complete destination plus guard bytes on both sides. Cases:

- every captured FR1 register image from normal, solo, grid and dense;
- generated coverage:
  - each minterm in use and each line octant;
  - every shift;
  - mask edges and fill modes, both directions;
  - heights 1–200 and widths 1–24 words;
  - zero-size and clipped edge cases.

Run on 040‑40 BCE and 030‑50 BCE. The emulator's blitter is the oracle until
real hardware testing.

**Gate:** zero differences.

### FR2 results (2026-11-03, done)

Gate passed: the hardware blitter and `FastRenderBlit` produce identical
bytes in all 4,479 cases on 030‑50 BCE and on 040‑40 BCE. The data is in
`tmp/manifest/fr2-oracle.json`. All results are from the emulator only.

**Code.** `FastRenderBlit.s` is included in the fine payload only when
`FF1_FAST_RENDER` is defined. Production does not define it, so the
production slave stays byte-identical (`597a74b9…`).

- **Register image.** It mirrors custom registers `$040`–`$075`
  (offset = register − `$40`), so FR4 can point a site's register base at it.
  Two words of internal blitter state follow: the previous B word and the
  shifted B hold.
- **`FastRenderBDAT`** performs the side effect of a `BLTBDAT` write. The
  blitter shifts B data at write time, using the current BSH and the
  previous B word.
- **`FastRenderBlit`** runs one blit, synchronously, on memory the CPU
  addresses directly:
  - all channel combinations and all 256 minterms, with direct evaluators
    for the 13 minterms FR1 found and a generic path for the rest;
  - ASH/BSH, first- and last-word masks, modulos and descending mode;
  - inclusive and exclusive fill with FCI;
  - line mode: octants, SIGN, SING, texture with BSH, start pixel and the
    first-pixel write to DPT;
  - the BLTSIZE encodings 0 = 64 words and 0 = 1024 rows;
  - pointer and modulo bit 0 is ignored, as in hardware;
  - afterwards the image holds the hardware's end state: pointers, the last
    words read into ADAT/BDAT/CDAT, and the line mode's updated
    ASH/BSH/SIGN. A second BLTSIZE write therefore continues correctly.
- **Not supported:** line mode with B enabled or a width other than 2. These
  return d0 = 1 and write nothing. FR1 found only width-2 lines with B off.
  The FR4 production guard must take the fault exit for them.
- **Not produced:** BZERO (FR1 found no reader).
- **Emulator semantics used.** These were read from the emulator source and
  confirmed by the oracle:
  - the A/B shift history is cleared at blit start;
  - the fill carry restarts on every row;
  - IFE together with EFE acts as EFE;
  - a disabled B channel uses the hold from the last `BLTBDAT` write or B
    read.

**Oracle harness (ignored harness).**

- **Fixture.** `tools/fr2_build.py oracle` builds the fixture. It replaces
  the drawing stages of `B8Draw` with `tools/fr2_oracle.s`, the same cut as
  FR0's no-draw build. Each draw runs 32 cases. For each case:
  1. it fills a Fast scratch from the case's xorshift32 seed and copies it to
     a Chip scratch. Bank 0 is the Chip scratch: 30,960 bytes, free because
     nothing is drawn;
  2. it runs a D-only primer blit to clear the B history, writes the
     registers with `BLTBDAT` after `BLTCON1`, then writes `BLTSIZE` and
     waits (plus an optional second `BLTSIZE`);
  3. it runs the same case through `FastRenderBDAT`/`FastRenderBlit` on the
     Fast side;
  4. it compares every byte of the case area. That area is each channel's
     span, 64-byte guards between spans, and 512 trailing bytes.
- **Scratch contents.** Pseudo-random in four densities (½, ⅛, ⅞, 1⁄32 set
  bits), not the captured pixels.
- **Captured cases.** All 10,774 blits from the FR1 captures (normal, solo,
  grid, dense, start, pit 1, pit 2). That is 2,751 distinct register images
  after rebasing, each with the channel geometry it had in the game.
- **Generated cases** (1,728):
  - every minterm with ABCD in both directions;
  - every ASH × BSH pair;
  - all 15 channel subsets, with a disabled A, B or C supplying its data
    register;
  - B disabled with every BSH;
  - 64 first/last mask combinations, including zero masks and one-word rows;
  - IFE, EFE and both, with and without FCI, both directions, for D, CD, AD
    and ABD;
  - widths 1–24 and heights 1–200, and the 64-word and 1,024-row encodings;
  - negative, row-repeating and odd modulos, and odd pointers;
  - D disabled;
  - second-BLTSIZE continuation for area and line;
  - lines at 72 angles with and without SING, every BSH texture, every start
    pixel, random lines and single dots. All 8 octant codes occur with and
    without SING.
- **Coverage.** 4,280 of the cases change memory: 275,941 changed words in
  all.

**Results.**

| Check | Result |
| --- | --- |
| Oracle, 030‑50 BCE (68030) | 4,479/4,479 cases, 0 differing bytes |
| Oracle, 040‑40 BCE (68040) | 4,479/4,479 cases, 0 differing bytes |
| Negative control in the guest: IFE treated as EFE | 121 failing cases, all of them fill cases |
| Host check (`tools/fr2_unicorn.py`, Unicorn 68020 and 68040) against the Python model (`tools/fr2_model.py`) | 4,479/4,479 equal in memory and end state; a one-instruction fault gives 1,008 mismatches |
| Production slave | unchanged, `597a74b9…` |

**Notes for later steps.**

- **FR4:**
  - each redirected `BLTBDAT` write must call `FastRenderBDAT`;
  - every other register write only stores into the image;
  - `BLTSIZE` stores into the image and then calls `FastRenderBlit`.
- **FR6:** the kernels are checked against `FastRenderBlit` and the hardware
  with the same harness (`fr2_cases.py` → `fr2_build.py` → `fr2_run.py`).

### FR3 — Shadows, copy and publication with an empty prefix

The framework, with nothing drawn in Fast RAM yet.

- **Allocation.** Allocate both shadows (and the FR7 mirrors, if accepted)
  once at driving entry, all or nothing, from the public pool. Measure its
  headroom first. If the pool is short, grow the WHDLoad reservation: a
  somewhat larger memory requirement is accepted (user decision,
  2026-11-02). Update the documented requirements and run the memory check.
  Allocation failure selects today's path.
- **Copy-point mechanism.** The prefix is empty, so the copy region is empty,
  and the arms must match exactly.
- **Wait and copy order.** Move the beam/field wait to just before the copy.
  Keep the `LoadView` request order and the H3 road preparation.
- **Resync.** Copy each Chip bank into its shadow after every route where
  native code may have drawn outside the fine draw. FR1 lists those routes;
  run them through the public lifecycle (pause, tow, pit, menu, re-entry and
  overlay reload). This costs one Chip read pass per bank, measured in FR0c,
  and only at those transitions.
- **Selection.** Selection, an immutable A/B preset and patch-ledger entries
  are restored on every exit route.

**Gate:** section 4, with all exact gates against the H6c/B8-PAL references.
The 040‑40 BCE frame rates do not change with the prefix empty.

### FR3 results (2026-11-03, done)

Gate passed: with the path active and the prefix empty, every exact gate
matches the B8-PAL references, and the frame rates equal the B arm. The data
is in `tmp/manifest/fr3-validation.json`. All results are from the
emulator only.

**Code.** `FastRender.s` (fine payload, before `public_bind` so its native
operands are bound) plus three hooks. All of it is assembled only with
`FF1_FAST_RENDER`; the release slave stays byte-identical (`597a74b9…`), and
so do the 68000 and 020 payloads of the development build. A development
build sets `FF1_FINE_DEFINES=FF1_FAST_RENDER=1` for `build.py`. Activation per
CPU stays an FR10 decision.

- **Mirror table.** One entry per Chip range: both banks (3 × 10,320 bytes
  each) and the 14 FR1 source ranges, padded to 16 bytes and merged where
  close. Each Fast mirror keeps its Chip address modulo 16.
  `FF1FastRenderMap` translates a Chip address into its mirror and reports a
  miss for anything else; FR4 uses it for every pointer.
- **Install** (every driving entry, from the barrier) qualifies:
  - the immutable preset `FF1FastRenderControl` (1 = path, 0 = today's path;
    the equal-layout B arm);
  - the CPU (030, 040 or 060 by WHDLoad's attention flags);
  - the Chip layout. The FR1 addresses are fixed because WHDLoad's
    Kickstart 1.3 environment gives the game the same 512 KiB Chip on every
    machine. The native bank table at `$66c92` and the live address of Chip
    hunk 46 anchor that layout. A different layout selects today's path.
- **Allocation and seed** happen at the first draw of each entry, in the
  copy-point hook before the field wait:
  - one `MEMF_PUBLIC|MEMF_FAST` block of 125,760 bytes, all or nothing.
    Failure keeps today's path for that entry;
  - after `WaitBlit`, every mirror is copied from Chip (125,488 bytes), once
    per entry and never on the per-frame path.
- **Copy point and publication.** The prefix hook sits after `OwnBlitter` and
  the H3 road preparation, before the line-256/field wait. The publication
  hook sits after the wait, before the first native stage. FR5 stages will
  run in the prefix hook. The FR3 prefix is empty, so publication copies
  nothing. `FF1FastRenderCopyBank` copies a bank's displayed region (bytes
  4–43 of rows 0–199 in three planes, 24,000 bytes) for FR5. `LoadView`
  order and the H3 preparation are unchanged.
- **Release.** `public_reset` (native loop exit, overlay unload and rollback)
  frees the block before the payload's zero-initialized state is cleared.
  The menus never see the allocation, and the next entry seeds again. No
  native code is patched, so FR3 adds no patch-ledger entries.
- **Diagnostics.** `FF1FastRenderStats` (tag `FR3S`) survives lifecycle
  resets: installs, activations, CPU/layout rejections, allocation failures,
  seeds, releases, publications, free Fast memory before and after.

**Memory headroom (measured).** The public pool is 512 KiB of the 768 KiB
expansion reservation; at the first draw the game's hunks and the other
allocations use about 230 KiB of it (235,760 bytes).

| Moment | Free Fast | Largest block | Free after FR3 |
| --- | ---: | ---: | ---: |
| 030‑50 BCE, and 040‑40 BCE in the lifecycle routes | 288,496 | 175,040 | 162,736 |
| 040‑40 BCE probe launch (`CUSTOM1=1`) | 175,880 | 175,040 | 50,120 |

In the second row, DOS-task allocations of about 110 KiB from race start were
still held; they are freed during the same field wait. No allocation failed
in any run. The reservation does not grow, so the memory requirements and
the memory check are unchanged.

**Checks (candidate `4f84965c…`, B arm `98186499…`).**

| Check | Result |
| --- | --- |
| Probe, 030‑50 and 040‑40 BCE: mirrors versus Chip right after the seed | all 16 ranges identical |
| Core smokes: A500, A1200, 020+Fast, 030‑50 BCE, 040‑40 BCE | passed |
| Exact gates, 040‑40 BCE, fixtures built with the path: 100-update states, 30 frames normal and grid, elapsed clock | all 0 error |
| Copy round trip (diagnostic build: every publication rereads the back bank and copies the 24,000-byte region back to Chip): 30 frames normal and grid | 0 error |
| MMU smokes: 030 with WHDLoad MMU and data cache, 040 MMU | passed |
| Lifecycle, 030‑50 and 040‑40 BCE: race control route (pause, tow, exit, pit menu, paddock, race settings) and the modal route (exit and re-entry into a fresh session) | passed; one install, allocation and seed per entry, one release per exit, none during pause, no allocation failure |
| Lifecycle, 020+Fast (path not selected): route and modal; A500 season save | passed |
| Driving controls, 040‑40 BCE | passed |

FPS, 300 presentations, warp off, path on against the B arm in the same
session:

| Machine | Path on | B arm | Field intervals on / off |
| --- | ---: | ---: | --- |
| 040‑40 BCE | 24.51084 | 24.51084 | 289×2 + 11×3 / identical |
| 030‑50 BCE | 24.59133 | 24.55102 | 291×2 + 9×3 / 290×2 + 10×3 |
| 020+Fast (path not selected) | 15.40753 | 15.40753 | identical |
| A1200 chip-only | 8.20609 | 8.20609 | identical |

The 030 difference is one interval, a phase shift from the one-time seed.

**Not covered.**

- **`reload`** (`CUSTOM2=0` overlay reloads): the harness reference
  `tmp/step3/release-original-030-50-custom1-1-clock-v2/anchor.bin` is
  missing. The release slave fails at the same step, so this is not an FR3
  result. `CUSTOM2=0` never reaches the fine payload, and the host, 68000 and
  020 payloads are byte-identical, so the legacy path is unchanged by
  construction.
- **Harness fixes.** The route and modal runners now close their live
  session after a passing replay; before, they waited for a manual `quit`.
  The smoke runner cannot check `CUSTOM2=0`, because it waits for
  performance-path breakpoints.

**Notes for later steps.**

- **FR4:** translate pointers with `FF1FastRenderMap`, and take the fault
  exit on a miss. The FR1 source ranges are the observed extents. A
  redirected site that reads outside them shows up as a miss in VERIFY, and
  the table is extended then.
- **FR5:** stages move into `FF1FastRenderPrefix`, and the publication copy
  grows with them. `FF1FastRenderCopyBank` is the full-region copy that the
  round-trip diagnostic verified.
- **FR2 harness:** `tools/fr2_build.py` now patches the new `B8_65734`
  sequence.

### FR4 — Blit redirection at native sites

For the stages inside the prefix:

- Point each native site's custom-register writes at the Fast register image
  by patching absolute and base operands in the public race copy.
- Replace each `BLTSIZE` write with a call to FR2.
- Turn `WaitBlit` calls inside redirected stages into returns.
- Retarget the existing CPU writers (H5/H9/H10/H11/H13) to the shadow
  whenever their stage is in the prefix.

**Guards.**

- **VERIFY:** no blitter DMA and no CPU write touches a Chip bank during
  prefix stages, except the copy. Checked with the BCE DMA records and the
  FR1 write-watch.
- **Production:** each redirected site checks that its destination is a bank
  or known scratch, and otherwise takes the existing production fault exit.
  It never draws into an unknown address.

**Gate:** section 4. In addition, the site table equals the FR1 census for
the redirected stages, and every patch word restores.

### FR4 results (2026-11-04, done)

Gate passed in the emulator, with one memory exception below: two qualified
small-memory setups no longer boot the Fast render builds. The data is in
`tmp/manifest/fr4-validation.json`. All results are from the emulator
only.

**Code.** All of it is in `FastRender.s` and assembled only with
`FF1_FAST_RENDER`. The release slave stays byte-identical (`597a74b9…`).

- **Sites.** The 11 redirected instructions of the FR1 census are patched
  through the barrier's patch ledger: BLTSIZE at `$24c18`, `$24db8`, `$6ad8a`,
  `$6adde`, `$32dfa`, `$32e6c`, `$32f02`, `$6bbec`, `$6c55c`, and the line
  routine's BLTBDAT at `$6ad6c`/`$6adc0`. `WritePixel` (`$2a1b0`) is
  redirected too.
  - Each thunk repeats the instructions it displaces.
  - No patched span contains a native branch target except at its first
    word. The `$6adde` patch moved to `$6add6` because `$6adde` is a branch
    target.
- **Register base.** The three base-register routines take their base from
  `FF1FastRenderRegs`: the custom chip, or `FF1FastRenderImage − $40` when
  redirected. The base convention is BLTCON0 at +`$40`.
  - The two absolute-operand routines (`$6ba18`, `$6c310`) write the Fast
    register image permanently. They flush their registers to the hardware
    before a hardware BLTSIZE.
- **Translation.** At a soft BLTSIZE, each enabled channel's whole span is
  translated, line mode included (C/D extent from the octant bits). Both
  ends must lie in one mirror, and D must lie in a writable mirror. The
  pointers return to their Chip values after the blit.
- **CPU writers** (H4 demo text, H5 bitmap, H10 clear, H11 overlap, H13
  gauges, H9 fill scan, `WritePixel`) translate their targets with
  `FF1FastRenderTarget`.
- **Faults.** A miss, an unsupported blit form, a native fallback or an
  unsupported RastPort takes the production fault exit. The reason and site
  are recorded in `FR4S`.
- **Candidate and diagnostic.** In the candidate the prefix is empty, so
  every site writes the hardware. `FF1_FAST_RENDER_FULL` redirects the whole
  draw from publication to the end of B8Draw and copies the back shadow
  (30,960 bytes) to Chip there.

**Census correction: the source mirrors cover the whole graphics region.**

- **What was missed.** The FR1 extents were what the sampled scenes touched.
  A diagnostic build (`FF1_FAST_RENDER_CHIPREAD`) logged every span outside
  the mirrors and accessed it in place. Over 300 redirected draws:
  - car, post and helmet images were read all through `$cde0`–`$51089`;
  - the rear-view mirror bitmaps are several times the FR1 extent, with
    writes at `$4857a`–`$486b7`, `$491dc`–`$4a9f8` and `$4f51a`–`$51898`.
- **New mirror table.** The 16 ranges became five, all writable:
  - both banks;
  - `$cd30`–`$d3e0`, refreshed from Chip before each redirected draw for
    the audio descriptors;
  - `$d3e0` up to bank 0;
  - the end of bank 0 up to bank 1.

  The block is 316,672 bytes. With it, the same run logs no span outside the
  mirrors.

**Memory (user decision, 2026-11-04).**

- **ExpMem.** The block does not fit the 512 KiB public pool, which has
  288 KiB free at the first draw. Fast render builds therefore set ws_ExpMem
  to 1 MiB (`build.py` `EXPMEM`), and the pool opened by `FF1PublicBoot` is
  sized from `FF1_EXPMEM_SIZE`.
  - At the first draw: 550,640 bytes free, largest block 437,184, and
    233,968 free after the allocation.
  - Production keeps `$c0000`.
- **Machines that no longer boot.** With 1 MiB, the A500 with 512 KiB Chip
  and 1.5 MiB Slow and the chip-only A1200 (2 MiB) do not boot. Their smoke,
  FPS, season and controls checks fail at boot. The A500 with 2 MiB Fast
  passes.
- **Still open.** The release memory scheme is undecided. One option is to
  load the hunks into ExpMem and move only the Chip-required data to Chip.
- **State captures.** The bigger pool moves the guest's Fast allocations by
  `$44000`. The 100-update state records therefore differ from B8-PAL, but
  only in Fast-pointer longs (2,600 bytes, all of them pointers), and the
  private fractions are equal apart from a trailing pointer. Over 1,200
  matched updates on 020+Fast, the 768 KiB and 1 MiB layouts are identical
  apart from pointers.
- **Live race.** The live FPS race on 020+Fast reaches the tow exit after
  about 257 presentations with 1 MiB, in both the candidate and the control;
  production keeps racing. The FR code is not installed on the 020, so this
  comes from the start conditions of the live run, not from FR4. That cause
  is not verified. 020+Fast FPS is not measured for FR4.

**Checks (candidate `693d4896…`, control `93a35875…`, FULL `19005479…`).**

| Check | Result |
| --- | --- |
| FULL, 040‑40 BCE probe, 300 draws | 0 faults, 0 hardware blits, 0 spans outside the mirrors; per draw about 263 software blits and 11 `WritePixel` |
| FULL: 30 frames normal and grid against B8-PAL | 0 error |
| Candidate: 30 frames normal and grid; elapsed clock | 0 error; 0.0075 % |
| Candidate: 100-update states | equal apart from Fast pointers (see above) |
| Smokes: 030‑50 BCE, 040‑40 BCE, 020+Fast, A500+Fast | passed |
| MMU: 030 with WHDLoad MMU and data cache, 040 MMU | passed |
| Route and modal: 030‑50 BCE, 040‑40 BCE, 020+Fast | passed |
| Controls: 040‑40 BCE, 020+Fast | passed |
| A500 (1.5 MiB Slow), chip-only A1200 | do not boot with 1 MiB ExpMem |

FPS, 300 presentations, warp off; candidate against the control in the same
session:

| Machine | Candidate | Control | Field intervals |
| --- | ---: | ---: | --- |
| 040‑40 BCE | 24.47079 | 24.51084 | 288×2 + 12×3 / 289×2 + 11×3 |
| 030‑50 BCE | 24.47079 | 24.55102 | 288×2 + 12×3 / 290×2 + 10×3 |

The thunks cost one or two intervals in 300 while every blit still goes to
the hardware.

**Notes for later steps.**

- **FR5:** a stage moves by turning redirection on before it and off after
  it. The FULL diagnostic shows that every stage already runs exactly in
  software.
- **Release:** the memory scheme must be decided before FR10.
- **Harness:** `ff1_gates.py` compares state records byte for byte, so it
  needs a reference with the same layout once ExpMem changes.

### Code and data placement check (2026-11-04)

Question: should the game's code and CPU data be loaded into Fast, with only
DMA data left in Chip? Measured on the production slave, 030/50 + Fast, from
the FR1 census dumps and memory logs:

- **Code is already in Fast.** The public pool is registered at priority 10
  before `LoadSeg`, so all root and race hunks load into it. The only
  exception is hunk 46, 456 bytes, the one Chip-flagged hunk, which the
  blitter reads. The overlay groups total 180 KB; root plus race are 111 KB.
- **Chip at the first draw:** 366 KB allocated. 50 KB of that is OS, and
  315 KB (`$ced8`–`$5a1c8`) is game data loaded at run time: both banks,
  images, sound and drawing scratch. The pool holds 219 KB of game
  allocations.
- **CPU Chip accesses per frame** (memlog, data accesses, scenes normal /
  dense / grid / start / solo): custom registers 9,700–15,000 (mostly
  `WaitBlit` polling), bank writes 4,600–5,400, supervisor stack 690–1,400,
  low OS memory 250–470, other game data 590–690 (the drawing sources at
  `$cd30`–`$d3e0`, the gauge strip and the composition scratch, which the
  blitter also reads).

Conclusion: the inversion already holds for everything the CPU uses heavily.
The remaining non-drawing Chip traffic is about 1,500–2,500 accesses per
frame, well under 1 ms of a roughly 40 ms frame. Of that, only the
supervisor stack could move; low OS memory is fixed by Kickstart 1.3, and the
game data is blitter data that FR already mirrors. The speed left on the table
is the blitter and the CPU's bank drawing, which is what FR5 onward targets.
The 020+Fast has the same pool policy but was not measured.

### FR5 — Move the stages to Fast RAM, in draw order

One step per stage, each switchable. Every step moves the copy point after
its stage. The order follows the native draw order, so each step keeps a
contiguous prefix:

- **FR5a. Clear and background** (`$6b050`, `$6b950`). H10's CPU fill
  targets the shadow.
- **FR5b. Road** (`$6b368`, `$6bf90`, the H3 prepared road, lines, spans and
  the H9 fills).
- **FR5c. Cars** (`$69bb8`). The colour expansion (`$32e12`) gets a Fast
  scratch, then the cookie-cut (`$32e6c`) runs. Car images and masks get Fast
  mirrors, refreshed on overlay reload.
- **FR5d. Mirrors** (`$6ae70`, `$6af7e`) and their `$24ae0` operations.
- **FR5e. Pit messages, cockpit and gauges** (`$6c0d0`, `$6ba18`, `$6bbfc`,
  `$293d0`, `$6adf8`). The cockpit image and the H13 gauge writes move to a
  Fast mirror.
- **FR5f. Demo text, flag, clock and the instruments** (`$239a0`/H4, H11,
  `$6694e` after `DisownBlitter`).

After FR5f the race draw issues no blits, and the H7 BLIT ownership becomes
irrelevant while driving.

**Decided (user, 2026-11-02):** the intermediate steps add a copy of about
4 ms while later stages still wait for the blitter, so FR5a–FR5c may not gain
on their own. Accept each step on its correctness gates and judge performance
at the FR5c and FR5f checkpoints against FR0's budget. This replaces the
H-series rule of keeping each change only for a measured gain.

### FR5a results (2026-11-04, done)

Gate passed on correctness in the emulator; frame rates drop, as the plan
allowed for (performance is judged at FR5c). The data is in
`tmp/manifest/fr5a-validation.json`.

**Code** (`FastRender.s`, assembled only with `FF1_FAST_RENDER`; the release
slave stays `597a74b9…`).

- **Prefix.** `FF1FastRenderPrefix`, before the field wait, runs the native
  clear `$6b050` and background `$6b950` redirected into the shadows, with
  B8Draw's argument from `-$30(a6)`. After the wait, `FF1FastRenderPublish`
  copies the result to Chip and returns 1, and B8Draw skips both native
  calls. The immutable preset `FF1FastRenderStages` (1, or 0 for the empty
  FR4 prefix) gives an equal-layout A/B arm.
- **Row tracking.** The shadows are exact only where the prefix drew, since
  the later native stages draw into Chip. Every prefix starts with all 645
  rows of each bank untrusted. A redirected access to an untrusted row first
  reads it from Chip, unless a CPU fill covers the whole row; writes mark rows
  dirty, and the publication copies exactly the dirty rows (full 48-byte
  rows). The blitter is idle before the first read, and nothing draws between
  the prefix and the publication, so Chip holds what the native stages would
  read.
- **Guards.** In the prefix, a blit destination outside the banks (reason 6)
  or an untracked CPU bank write (reason 7) takes the production fault exit.
  The H10 fill uses `FF1FastRenderTargetRows`, which tracks its rows.

**Checks (candidate `20f33e1c…`, empty prefix `995ce3c0…`, control
`22e7813b…`).**

| Check | Result |
| --- | --- |
| Probe, 040‑40 BCE, 300 draws | 0 faults; per draw 6 software blits (`$24ae0`), about 442 rows published, 361 filled whole, 81 read from Chip first |
| 30 frames normal and grid against B8-PAL; elapsed clock | 0 error; 0.026 % |
| Smokes: 030‑50 BCE, 040‑40 BCE, 020+Fast, A500+Fast | passed |
| MMU: 030 with WHDLoad MMU and data cache, 040 MMU | passed |
| Route and modal: 030‑50 BCE, 040‑40 BCE, 020+Fast | passed |
| Controls: 040‑40 BCE, 020+Fast | passed |

The 100-update states were not rerun: they differ from B8-PAL by the FR4
pointer shift by construction, and the exact frames cover the drawing.

FPS, 300 presentations, warp off, same session:

| Machine | FR5a | Empty prefix | Control | Field intervals (FR5a) | Mean (FR5a / control) |
| --- | ---: | ---: | ---: | --- | --- |
| 030‑50 BCE | 22.554 | 24.511 | 24.551 | 236×2 + 64×3 | 44.3 / 40.7 ms |
| 040‑40 BCE | 20.376 | 24.471 | 24.511 | 165×2 + 135×3 | 49.1 / 40.8 ms |

FR5a adds about 3.6 ms per frame on the 030 and 8.3 ms on the 040, more than
the roughly 4 ms copy the plan expected. Where the time goes is not measured
yet. The candidates are the generic FR2 software blitter running the
background blits (FR6 targets that), the 21 KB row copy after the wait, and
the 3.9 KB of row reads. Before FR5b, profile the prefix and the copy
per stage on the 040.

### FR5b results (2026-11-04, done)

Gate passed on correctness in the emulator. Frame rates drop sharply, far
beyond FR5a; the plan judges performance at FR5c, but the road's software
blits make that checkpoint meaningless without kernels (see below). The data
is in `tmp/manifest/fr5b-validation.json`.

**Code** (`FastRender.s`, `RenderFill.s`, `FerrariFormulaOne_FullPresentation.s`;
assembled only with `FF1_FAST_RENDER`; the release slave stays `597a74b9…`).

- **Prefix.** After the clear and background, `FRPrefixRoad` computes
  B8Draw's road angle `-$2c(a6)` as B8Draw does and calls the road through
  the H3 prepared entry (`FF1RenderDrawPreparedRoad`, or `$6b368`). The
  publication returns the number of staged FR5 stages; at 2 B8Draw skips the
  clear, background and road, runs the H11 clock preparation (CPU workspace
  only) and continues at `$66c7c`.
- **Road registers.** The road saves nothing and leaves D4–D7/A2–A5 changed;
  B8Draw runs on with them. The prefix records D0–D7/A0–A5 after the road and
  `FF1FastRenderRoadExit` restores them where B8Draw skips it.
- **`$6bf90` stays native.** It is a CPU sort of the car lists
  (`$6a5da`/`$6a63a`/`$6a5aa`) and draws nothing.
- **Fill scan.** The H9 scan reads rows 200 − extent … 199 of both road
  planes with the CPU; `FF1FastRenderTargetScan` tracks them as reads, so
  untrusted rows are first read from Chip.
- **Line spans.** FR4's line span assumed V − 1 steps on both axes; a
  384-pixel near-horizontal road line then reached past the bank and faulted
  (reason 1). `FRTranslate` now counts the minor-axis steps exactly from the
  error term as FRBLine steps it: with AMOD ≤ 0 ≤ BMOD and
  AMOD ≤ e0 < BMOD, k = ⌊(e0 + (V − 1)·BMOD − AMOD) / (BMOD − AMOD)⌋;
  any other form keeps the V − 1 bound.
- **Preset.** `FF1FastRenderStages` is now the stage count (2; 1 = the FR5a
  arm, 0 = the empty prefix).

**Checks (candidate `8073eb93…`, FR5a arm `c20a256b…`, empty prefix
`1eacee25…`, control `07b170ec…`).**

| Check | Result |
| --- | --- |
| Probe, 040‑40 BCE, 300 draws | 0 faults; per draw about 103 + 22 software road lines, 13 fills and 6 `$24ae0` blits; 443 rows published, 361 filled whole, 82 read from Chip first |
| 30 frames normal and grid against B8-PAL; elapsed clock | 0 error; 0.141 % |
| Smokes: 030‑50 BCE, 040‑40 BCE, 020+Fast, A500+Fast | passed |
| MMU: 030 with WHDLoad MMU and data cache, 040 MMU | passed |
| Route and modal: 030‑50 BCE, 040‑40 BCE, 020+Fast | passed |
| Controls: 040‑40 BCE, 020+Fast | passed |

The published rows barely change (443 against 442): the road draws inside
rows the clear already wrote, so the copy is not where the time goes.

FPS, 300 presentations, warp off, same session:

| Machine | FR5b | FR5a arm | Control | Field intervals (FR5b) | Mean (FR5b / FR5a / control) |
| --- | ---: | ---: | ---: | --- | --- |
| 030‑50 BCE | 14.654 | 22.419 | 24.551 | 2×1 + 13×2 + 146×3 + 139×4 | 68.2 / 44.6 / 40.7 ms |
| 040‑40 BCE | 8.587 | 20.376 | 24.511 | 68×5 + 220×6 + 12×7 | 116.5 / 49.1 / 40.8 ms |

The road costs about 24 ms on the 030 and 67 ms on the 040 in the generic
FR2 software blitter, against the blitter's 10.2 ms (§1); its line mode
steps one pixel at a time through frame variables (not yet profiled). The 040 is slower than the 030 at it, which also needs explaining
(emulator cost model or the 040's handling of this loop). Before FR5c, write
the FR6 line and fill kernels (or profile the 040 first): the FR5c
checkpoint can only judge the design once the road no longer runs through
the generic blitter.

### FR5c–FR5f results (2026-11-05, done)

Gate passed on correctness in the emulator: the whole race draw runs in the
prefix, and no hardware blit is issued while driving. Frame rates fall
further. Performance was set aside (user, 2026-11-05: "get everything
rendered with the CPU, then look at the performance"). The data is in
`tmp/manifest/fr5f-validation.json`.

**Code** (`FastRender.s`, `FerrariFormulaOne_FullPresentation.s`, and
`RenderBitmap.s`, `RenderOverlap.s`, `RenderText.s`, `RenderGauges.s`;
assembled only with `FF1_FAST_RENDER`; the release slave stays `597a74b9…`).

- **Stages 3–6 run inline.** The later stages are interleaved with B8Draw's
  own computations, so they are not called from the prefix. From preset 3
  on, `FF1FastRenderPrefix` leaves the redirection on after the road.
  B8Draw then skips its field wait (`FF1FastRenderLate`) and runs on from
  the end of the road, redirected.
- **Cut points.** `FR_B8Cut` cuts follow stage 3 (`B8_657a6`), 4 (before
  `B8PresentPit`), 5 (after `$6adf8`) and 6 (after the instruments' last
  WaitBlit). The cut matching the preset turns the redirection off, waits for
  the field as B8Draw did, including the H3/C4 field test, and publishes.
  A cut at or after the staged count ends the prefix, so no path skips the
  publication.
- **CPU writers.** `FF1FastRenderTargetSpan` tracks the span written: the
  H5 bitmap path (8 rows), the H11 clock, `WritePixel` (1 byte), the H4 demo
  scratch (192 bytes) and the H13 gauge rows. The plain `FF1FastRenderTarget`
  still faults (reason 7) on an untracked bank write in a prefix.
- **Memory outside the banks.**
  - With every stage staged (preset 6, `FF1FastRenderScratch`), the scratch
    and rear-view mirror images live in Fast alone.
  - The partial arms (1–5) track 256-byte blocks of the three non-bank
    mirrors as the bank rows are tracked. An untrusted block is read from
    Chip on its first access, and written blocks are published with the rows.
  - This was needed. Without it, arm 4 drew a stale cockpit digit: the B8
    text blits of the mirror stage write the cockpit digit bitmap, and the
    native `$6ba18` after the cut reads it in Chip.
  - The FR5a/b fault-6 guard is gone; those arms now track blocks too.
  - `FF1_FAST_RENDER_BLOCKS` is a diagnostic that tracks blocks in every arm.
- **Preset.** `FF1FastRenderStages` is 6, and `fr5_build.py` makes arms
  1–5 (`fr5-fr5a` … `fr5-fr5e`) and the empty prefix.

**Correction to FR5a and FR5b.** Their frame gates ran on fixtures built
without `FF1_FAST_RENDER` (`ff1_gates.py` builds the fixtures from the
environment, and `FF1_FINE_DEFINES` was not set), so the frame gates did not
cover the Fast path. Only the timing gate used the candidate. Rerun now with
the define: arms 1 and 2 match B8-PAL in both scenes (below).

**Checks (candidate `9461f4bf…`).**

| Check | Result |
| --- | --- |
| Probe, 040‑40 BCE, 300 draws | 0 faults, 0 hardware blits, one cut per draw; per draw about 37 + 35 `$24ae0`, 104 + 22 road lines, 13 fills, 8.5 + 10 + 26 car blits, 3 cockpit fills, 6 compositions, 11 `WritePixel` planes; 624 rows published, 361 filled whole, 263 read from Chip first; no block tracked |
| Probe, arm 4 (cars and mirrors) | 0 faults; per draw about 115 blocks read from Chip, 13.5 published |
| 30 frames normal and grid against B8-PAL, fixtures with the path, preset 6 | 0 error |
| The same frames, arms 1–5 (preset patched into the fixtures) | 0 error |
| Elapsed clock | 0.059 % |
| Smokes: 030‑50 BCE, 040‑40 BCE, 020+Fast, A500+Fast | passed |
| MMU: 030 with WHDLoad MMU and data cache, 040 MMU | passed |
| Route and modal: 030‑50 BCE, 040‑40 BCE, 020+Fast | passed |
| Controls: 020+Fast, 030‑50 BCE | passed |
| Controls: 040‑40 BCE | fails at "idle" (below) |

**Controls on the 040.**

- **The failure.** After braking to 0, the test expects speed 0 for 50
  fields with no input. It reads 371, with the player moved to the far
  lateral position.
- **The positions.** A rear-end collision fits them: car 4 was two segments
  behind the stopped car in the same lane, and at "idle" it sits where the
  player stopped.
- **Why only this build.** The frame rate decides where the player stops
  and when the traffic arrives. The same build passes on the 030, and arms 2
  and 5 and the `FF1_FAST_RENDER_BLOCKS` diagnostic pass on the 040 at
  similar rates.
- **Status.** The test is sensitive to frame rate, and this is not a render
  fault, but the collision itself is inferred from positions, not observed.
  The test needs a stop point that traffic cannot reach before it is used to
  judge changes in frame rate.

FPS, 300 presentations, warp off, same session:

| Machine | FR5f (all) | Arm 5 | Arm 4 | Arm 3 | Arm 2 | Control |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 030‑50 BCE | 10.606 | 9.625 | 11.746 | 12.833 | 13.541 | 24.551 |
| 040‑40 BCE | 6.214 | 6.034 | 7.207 | 7.788 | 8.270 | 24.511 |

- **The arms.** The partial arms now pay for reading non-bank blocks from
  Chip, so arm 2 is below its FR5b figure (13.54 against 14.65 on the 030)
  and arm 5 is below the full arm.
- **The whole draw in software.** It takes about 94 ms on the 030 and
  161 ms on the 040, against 40.7 ms natively. The road alone accounts for
  about 24 ms and 67 ms of that (FR5b).
- **Next.** Profile the 040 per stage, then write the FR6 kernels.

### FR6 — Specialized kernels for the hot blits

After FR5, profile the 040 with the measurement emulator and replace the
generic software blits at the costliest sites with exact kernels. The likely
order is set by the FR0d and FR5 measurements:

1. Car cookie-cut with the colour expansion merged, so the scratch is skipped
   (dense packs).
2. Descending exclusive road fill, using table-driven carry per byte.
3. One-row road spans.
4. One-dot road-edge lines.
5. Cockpit cookie-cut with precomputed opaque, partial and transparent word
   runs, derived from the live mask and invalidated with it.
6. Mirror road.

**Gate per kernel:** the FR2 harness compares the kernel with the generic
software blitter and with the hardware blitter on all FR1 captures, then
section 4 applies. Keep a kernel only where it gains on that CPU.

### FR6 results (2026-11-05, done)

Gate passed in the emulator. On the 030 the Fast path now runs faster than
the native draw: 35.8 FPS against 24.6. Work was focused on the 030 (user,
2026-11-05); the 040 is at 22.0, still below its native 24.5. The data is
in `tmp/manifest/fr6-validation.json`.

**Code** (`FastRenderKernels.s`, new; `FastRenderBlit.s`, `FastRender.s`;
assembled only with `FF1_FAST_RENDER`; the release slave stays `597a74b9…`).

- **Kernels.** `FRBFast` looks up (channels, minterm) and runs a
  register-resident loop, ascending or descending, with the first, middle
  and last word unrolled. Shapes: BCD with $CA, $0A, $FA, $3A; ABCD $CA; ACD
  $0A; ABD $FC, $C0, $30; D $00, $FF. ABCD $CA, ACD $0A and the ABD forms
  have unshifted variants for ASH = BSH = 0. Any other shape returns to the
  generic path, which now computes the minterm only when it is used.
- **Fill.** CD $AA fills go through a 2 × 512-word table (carry out, filled
  byte), exclusive and inclusive, built on first use.
- **Lines.** The road and edge line form (BLTCON0 $xB4A, H = 2) has four
  loops: X- or Y-major, with and without SING.
- **End state.** Every kernel leaves the pointers, the data registers, the
  shift history and the line state as FR2's `FastRenderBlit` does.
- **Owned shadows.** With every stage staged, the shadows are seeded from
  Chip once and every redirected write lands in them; every dirty row is
  published each draw, and FR1 found no other writer during driving. So each
  shadow row equals Chip when a draw starts. The prefix no longer clears the
  row states, reads need no tracking, and a write only marks its rows
  (`FRMarkSpan`, row = offset × 43691 >> 21). Publication resets the rows.
  The partial arms keep the FR5 tracking.
- **Span lookup.** `FRSpan` walks the mirror table once.

**Checks (k5, `8ec61e11…`).**

| Check | Result |
| --- | --- |
| Host check against `FastRenderBlit`, 68020/030/040 | 4,479 cases, 0 mismatches, 3,162 through kernels; seeded faults in area, fill, line and unshifted paths were caught |
| Probe, 030‑50 BCE, 300 draws | 0 faults, 0 hardware blits, one cut per draw, 625 rows published, none read from Chip |
| 30 frames normal and grid against B8-PAL | 0 error |
| Elapsed clock | 0.0075 % |
| Smokes: 030‑50 BCE, 040‑40 BCE, 020+Fast, A500+Fast | passed |
| MMU: 030 and 040 | passed |
| Route and modal: 030‑50 BCE, 040‑40 BCE, 020+Fast | passed |
| Controls: 020+Fast, 030‑50 BCE, 040‑40 BCE | passed (040 failed at FR5) |

The A500 with 512 KiB Chip and the chip-only A1200 still do not boot with
1 MiB ExpMem (FR4). The first MMU run in a session sometimes stops after
3 s because the harness finds no memory dump; reruns pass on both CPUs.

FPS on the 030‑50 BCE, 300 presentations, warp off:

| Build | Change | FPS |
| --- | --- | ---: |
| FR5f | generic software blitter | 10.61 |
| k1 | area and fill kernels (fill table at an absolute address, a bug) | 18.35 |
| k2 | the table addressed PC-relative | 22.86 |
| k3 | owned shadows | 26.65 |
| k4 | line kernel, lazy minterm, one-pass span | 34.99 |
| k5 | unshifted kernels, reads skip tracking | 35.83 |
| Native control | | 24.55 |

- **Where the time goes now.** A 030 trace of k4 puts about 22 % in
  per-blit overhead (translation, span, marking, setup), 13.7 % in the
  ABCD $CA cookie-cut, 10 % in lines, 8.7 % in publication and 6.6 % in
  fills.
- **The 040.** It went from 6.2 to 22.0 FPS but is still below native. It
  was not profiled in FR6.
- **Next.** The per-blit overhead and the cookie-cut loop, then FR7 (copy)
  and FR8 (pacing). (FR7 was done first; see its results.)

### FR7 — Copy optimization

1. Copy only the displayed region found by FR1, with the instruction chosen
   by FR0c.
2. Copy only changed data:
   - Keep a Fast mirror of what each Chip bank holds and compare the shadow
     with it.
   - Write only the longwords or rows that differ. The static cockpit and
     sky rows are the expected wins.
   - Keep it only where it gains: TFX's 040-only result.
3. Optional: copy finished bands early during drawing, only if FR1 shows
   band-ordered completion. Not expected to pay.

### FR7 results (2026-11-06, done)

Gate passed in the emulator. On the 030 the Fast path now runs at 40.0 FPS
(FR6 35.8, native 24.6). Items 1 and 2 are done; item 3 was not tried. The data
is in `tmp/manifest/fr7-validation.json`.

**Code** (`FastRender.s`, assembled only with `FF1_FAST_RENDER`; the release
slave stays `597a74b9…`).

- **Copy modes.** The immutable preset `FF1FastRenderCopy` selects the
  publication: 2 (the preset) compares, 1 copies the displayed region of the
  dirty rows, 0 is FR6 (every dirty row whole). Modes 1 and 2 apply only with
  every stage staged (owned shadows); the partial arms always use 0, because
  their native stages read Chip.
- **Displayed region.** Only bytes 4–43 of rows 0–199 of each plane reach
  Chip (FR1); a dirty row outside it is just marked clean.
- **View mirrors.** Two 24,000-byte Fast copies of what each Chip bank
  displays, placed after the mirrors in the one block (316,672 to 364,672
  bytes) and filled from the shadows right after the seed. Mode 2 compares
  each displayed longword of a dirty row with its view copy and writes Chip
  and the view only where they differ.
- **Write-back at release.** Outside the displayed region the Chip banks now
  lag their shadows. Nothing reads them during driving, so the release (every
  lifecycle reset) writes both shadows back whole before the block is freed,
  and the banks then hold what the native draw would have left. A fault, or a
  release inside a redirected draw, skips it (`FF1FastRenderOwned`).
- **Diagnostics.** `FF1FastRenderCopyStats` (tag `FR7S`): rows published,
  longwords written to Chip, write-backs, view seeds. `tools/fr4_probe.py`
  reads it and, at the final stop, checks that both Chip banks' displayed
  region equals their shadows and, in mode 2, the view mirrors.
- **Builds.** `tools/fr7_build.py TAG` makes the candidate and the
  `-copy1` and `-copy0` arms by patching the preset word.

**Checks (candidate `a00d4072…`).**

| Check | Result |
| --- | --- |
| Probe, 030‑50 BCE, 300 draws | 0 faults, 0 hardware blits; Chip, shadows and views equal in the displayed region of both banks; 616 dirty displayed rows and 1,266 of 6,160 longwords written per draw (FR6 wrote 625.5 whole rows, about 30,000 bytes) |
| 30 frames normal and grid against B8-PAL | 0 error |
| Elapsed clock | 0.093 % |
| Smokes: 030‑50 BCE, 040‑40 BCE, 020+Fast, A500+Fast | passed |
| MMU: 030 and 040 | passed |
| Route and modal: 030‑50 BCE, 040‑40 BCE, 020+Fast | passed |
| Controls: 020+Fast, 030‑50 BCE, 040‑40 BCE | passed |

FPS, 300 presentations, warp off; the arms share the candidate's layout:

| Machine | Mode 2 (compare) | Mode 1 (displayed) | Mode 0 (FR6) |
| --- | ---: | ---: | ---: |
| 030‑50 BCE | 40.04 | 36.98 | 35.57 |
| 040‑40 BCE | 22.69 | | 22.06 |

About 80 % of the displayed longwords in dirty rows are unchanged from the
frame before in that bank, so the compare, which costs only Fast reads,
removes most Chip writes. The 040 gains too but stays below its native
24.5; it was not profiled (the work concentrates on the 030).

### FR8 — Frame pacing at 50 FPS

- **Normal operation.** Expect one tick per frame. Ticks are 20 ms and fields
  20.03 ms, so a field holds two ticks about every 12.5 s; that is not a
  missed frame. Publish before the VBL; copy only into the bank that is not
  displayed.
- **Late frames.** A late frame is shown one field later.
- **Opponent-update frames.** These come once in five. If they overrun, a
  steady 40 FPS judder results. Reduce their cost where possible; otherwise
  accept it (user decision, 2026-11-02). Do not split the native 100 ms
  update; that would change state ordering.
- **Evidence.** Interval histograms for normal, solo, grid and dense. Confirm
  there is no tearing by checking the displayed bank against the copy log.
- **Optional third Chip bank** (old H16): only if the wait before the copy
  still costs measurable time.

### FR8 results (2026-11-06, done)

Done in the emulator, on the 030 (the 040 is set aside). Pacing is not what
limits the frame rate: in every scene the draw alone takes longer than a
field. The one change is the early LoadView request below. It shows every
frame in the field after its copy and makes the motion steadier, with the
same frame rate. The data is in `tmp/manifest/fr8-validation.json`.

**Code** (assembled only with `FF1_FAST_RENDER`; the release slave is
unchanged).

- **Early LoadView request** (`FF1FastRenderShow`, `FastRender.s`). After the
  publication, `FR_B8Cut` calls the native `$2428a` (copper lists and
  `LoadView`) for the bank just drawn (`$66f88`). Natively the request waited
  for the next `B8Draw`, after the next tick's wait and logic, so a frame
  copied just before a VBL showed a field late.
  - **One request per frame.** The next `B8Draw` skips its own request
    (`FF1FastRenderNativeShow`) when the early one showed the same bank and
    GfxBase's `ActiView` and `LOFlist` are unchanged since. Anything that
    loaded another view in between (pause, a menu) makes `B8Draw` request as
    before. In 1.3 `LoadView` installs the copper lists `MrgCop` already built,
    so the early request costs what the native one did.
  - **Same field.** Two requests in one field would hide a frame, so a
    request in the field of the last one (`FF1FastRenderShownField`, read
    after each call) is left to `B8Draw`.
  - **Conditions.** Only with owned shadows, where nothing draws into the
    bank after the publication. The next frame's field wait counts from its
    road preparation, after both requests, so it stays safe.
  - **Preset.** The immutable `FF1FastRenderEarly` (1; 0 is the native arm).
    `FF1FastRenderShowStats` (`FR8S`) counts the early requests, those left
    to `B8Draw` (same field) and the `B8Draw` requests skipped. In the final
    normal run all 869 early requests were followed by a skip.
- **Pacing log** (diagnostic, `FF1_FAST_RENDER_PACING`,
  `src/FastRenderPacing.s`). Each frame records the field and beam line at:
  - the last tick's start;
  - the road preparation;
  - the end of the draw;
  - the start of the copy;
  - the end of the copy.

  It also records the ticks, the opponent pulses and the bank.
  `test_h5_fps.py` saves the log and the game's field counter at each census
  window. `tools/fr8_report.py` lines the log up with the census, which shows
  the bank displayed in each field, and reports:
  - the phase times;
  - the histograms;
  - tearing;
  - the delay from each frame's tick to the screen.

  `tools/fr8_build.py` builds the candidate, the log build, the four
  scene fixtures (through `fr0_build.py`'s matched builders) and the
  `-early0` arms. The log moves the layout, so it shifts the frame rates by
  up to 1 %; compare arms built together.

**Where a frame's time goes**, 030‑50 BCE, the log build of the final
candidate, milliseconds per one-tick frame. Pulse frames run the native
100 ms opponent update. Steady motion is the share of frames whose ticks
equal their fields on screen.

| Scene | FPS | Logic (pulse) | Draw | Wait | Copy | Busy | Intervals 1 / 2 fields | Steady |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| normal | 40.5 | 0.5 (1.9) | 22.3 | 0.0 | 1.7 | 24.6 | 230 / 70 | 55 % |
| solo | 45.1 | 0.6 (2.0) | 19.8 | 0.0 | 1.3 | 21.7 | 268 / 32 | 88 % |
| grid | 38.9 | 0.6 (2.0) | 23.0 | 0.0 | 1.4 | 25.0 | 215 / 85 | 54 % |
| dense | 29.8 | 0.6 (2.0) | 30.9 | 0.0 | 1.2 | 32.7 | 98 / 202 | 34 % |

- **Normal operation.** A frame is busy for more than a field in every
  scene, solo included. The loop therefore never waits for a tick (idle
  0.1 ms), and two-tick frames follow. 50 FPS needs a draw of about 17.5 ms.
  That is drawing work (the FR6 kind), not pacing.
- **Field wait.** 4–8 % of frames wait at all, and the mean wait is under
  0.01 ms. No third Chip bank is needed.
- **Opponent-update frames.** These cost 1.4 ms more logic and cause no
  judder of their own. They are accepted, and the native 100 ms update is not
  split.
- **Late copies.** 5–7 % of copies end after the VBL they started before; the
  early request still shows them in the next field.
- **No tearing.** The census was lined up with the log in all twelve runs
  (the four final scenes, and four scenes in both arms of the version that
  still requested twice). Across 9,768 checked fields, no copy wrote a bank
  while it was on screen, except after line 256.

**Early request against the native request**, measured on the version that
still requested twice per frame (the same layout in both arms), 030‑50 BCE.
The table shows the share of frames shown in the field after their copy, and
steady motion.

| Scene | FPS early / native | Next field | Steady motion |
| --- | --- | --- | --- |
| normal | 39.41 / 39.31 | 100 % / 94 % | 47 % / 38 % |
| solo | 44.84 / 44.84 | 100 % / 95 % | 84 % / 77 % |
| grid | 37.63 / 37.63 | 100 % / 94 % | 45 % / 35 % |
| dense | 30.07 / 30.07 | 100 % / 96 % | 32 % / 32 % |

In the final candidate every frame shows in the field after its copy (100 %
in all four scenes). Its steady-motion shares are higher than the table's,
but it has another layout, so the difference is not attributed to removing
the duplicate request.

**Final candidate** (`fr8-candidate`, `e9ae9b3c…`; native arm `-early0`,
`d7e7c0f2…`), 300 presentations, warp off:

| Machine | Early | Native arm |
| --- | ---: | ---: |
| 030‑50 BCE | 39.94 | 39.94 |
| 040‑40 BCE | 22.52 | 22.52 |

Gates, all passed: frames (normal, grid) and timing, the FR4 probe
(030‑50 BCE), smokes (030‑50 BCE, 040‑40 BCE, 020+Fast, A500+Fast), MMU (030
and 040, twice), route and modal (030‑50 BCE, 040‑40 BCE, 020+Fast) and
controls (020+Fast, 030‑50 BCE, 040‑40 BCE).

- **Frame gate.** It screenshots a fixed number of fields after `B8Draw`,
  where the early request already shows the next frame, so the early arm's
  capture differs from the B8-PAL reference. `ff1_gates.py` therefore runs
  the frame fixtures with `FF1FastRenderEarly` 0. The arms differ only in that
  word, and the native arm matches the reference.

**Still open: steady motion.** At 1.2–1.6 fields per frame, the delay from a
frame's tick to the screen is 2 or 3 fields depending on the phase, so the
simulated time per frame and the time on screen often differ ("1 tick, 2
fields" next to "2 ticks, 1 field"). There are two ways to make the delay
constant:
- hold the request to a fixed delay, which stalls the next copy without a
  third bank;
- run the tick a frame needs slightly ahead of its due time, which changes
  when input is sampled.

Either is a design decision. A faster draw shrinks the problem: solo, at
1.1 fields per frame, is already 88 % steady.

### FR12 — Draw speed on the 030

FR8 showed that the draw limits the frame rate: 20–31 ms per frame against
about 17.5 ms for 50 FPS. Each step is profiled first (`tools/fr6_trace.sh`,
with the per-site attribution), kept only where it gains, and goes through
section 4. The tick-to-screen delay (FR8, "Still open") is measured again
after the draw work, and then a predicted-tick variant is tried (the user's
decision, 2026-11-06: no frame rate is traded for steady motion).

**Profile of the FR8 candidate** (030, 60 fields, shares of the draw):

| Site | Share | Mostly |
| --- | ---: | --- |
| Cars (`$32d50`: mask, colour and cookie-cut blits) | 19 % | ABCD $CA cookie-cut |
| Road lines (`$6ac4a`) | 18 % | X-major one-dot lines |
| Bitmap blits (`$24ae0`, both sites) | 16 % | BCD $CA, $0A |
| Road fill | 8 % | the fill kernel |
| Cockpit and gauges (`$6ba18`) | 6 % | ABCD $CA |
| Publication | 7 % | |

Across all sites about 24 % is per-blit work outside the kernels:
translation, span lookup, row marking, setup and end state.

**Step 1: one-dot X-major lines** (`FRKLineXS`, `FastRenderKernels.s`). In a
one-dot line only the first pixel of each row is written. The other pixels
now skip the minterm and keep only the error term, the steps and the C read
(for CDAT). Host check (`fr2_unicorn.py`): 0 mismatches on the 68020, 030
and 040; a seeded fault in the new path was caught. 030 FPS (normal):
40.26 against 39.94.

**Step 2: merged car planes** (`FRCar`, `FastRender.s`, preset
`FF1FastRenderMerge`). Natively each car takes a mask blit, then per plane a
colour blit into a scratch (except for colours 0 and 3, FR H2) and a
cookie-cut. The colour of a plane is one of 0, P1 & P0, P1 & ~P0 or P1 (the
table at `$32d48`, A = P1, B = P0), and the shift commutes with these
functions, so one pass reads P1 and P0 once, shifts each once and writes
D = (C & ~M) | colour into planes 0 and 1. Plane 2 still runs natively, so
the mask scratch and the register image end as before. The colour scratch
is no longer written for planes 0 and 1. Only the same plane's cookie-cut
reads it, and beyond the car's words only in the masked extra word (BDAT and
BHOLD, which every later blit loads or does not use).
- Hook: `$32e0c` (`asr.w #4,d6; lsl.w $12(a7)`, six bytes before the plane
  loop). The install checks those bytes and the minterm table.
- Conditions: owned shadows only. A span outside the mirrors, or a width
  below two words, leaves the car to the native blits (`FR12` stats: merged
  and native cars).
- Host check (`tools/fr12_car.py`): FRCar assembled alone under Unicorn
  against the native blits on the FR2 model, on random cars (width, height,
  clipping, shift, position, colour bits): 0 mismatches in 1,500 cars on each
  of the 68020, 030 and 040. A seeded fault (the shift read from the wrong
  word) was caught.
- The first emulator run failed the frame gate: the pass read the native
  registers' high words from the stack. The host check, written then, finds
  it at once.
- 030 FPS (normal): 44.31, against 40.26 after step 1.

**Checkpoint after steps 1 and 2** (`fr12-candidate`, `b0a3b937…`; arm
`-merge0`, the native car blits, `e8de2ef9…`; `tools/fr12_build.py`). FPS,
300 presentations, warp off, the same layout:

| Machine | Merged | Native car blits | Native game |
| --- | ---: | ---: | ---: |
| 030‑50 BCE | 44.31 | 40.59 | 24.55 |
| 040‑40 BCE | 24.59 | 23.33 | 24.5 |

Gates, all passed: frames (normal, grid) and timing, the FR4 probe
(030‑50 BCE: 0 faults, no hardware blit, shadows and views equal to Chip),
smokes (030‑50 BCE, 040‑40 BCE, 020+Fast, A500+Fast), MMU (030 and 040,
twice), route and modal (030‑50 BCE, 040‑40 BCE, 020+Fast) and controls
(020+Fast, 030‑50 BCE, 040‑40 BCE). The 040 now matches the native game.

**Profile of the checkpoint** (shares of the draw): road lines 21 %, road
fill 10 %, bitmap blits (`$24ae0`) 19 %, publication 8 %, cockpit 6 %, cars
12 %.

**Step 3: zero words in the road fill** (`FRKFill`, `FRKFillD`). A zero word
fills to all ones with the carry and to zero without, in both modes, and
leaves the carry; most words of a road row are zero. The kernels keep that
word in d4 and update it only after a non-zero word. Host check: 0
mismatches on all three CPUs, a seeded fault caught. 030 FPS: 45.52 against
44.31.

**Tried and dropped** (no gain beyond the layout noise of about 1 %; the 030's
256-byte instruction cache makes small changes move the frame rate either
way):
- BCD $CA with ADAT = $FFFF as a plain shifted copy from the third word
  (45.25).
- Leaner per-blit work: fewer registers saved per blit, no tracking call for
  read channels with owned shadows, the last mirror tried first in `FRSpan`
  (45.11).

**Step 4: the whole car in one pass.** Step 2's pass now draws all three
planes, and the mask blit is skipped too: `FRT32df6` defers it, and `FRCar`
either draws the car and returns to the routine's `rts` (`$32f0e`), or runs
the deferred mask blit and leaves the planes to the native code (the
register image still holds the mask setup). The routine's plane loop changes
only d0, d1, a3, a5 and the colour argument words, which `FRCar` sets as the
loop would. The car's blits are gone, so the blitter registers end
differently; the register census of the other sites shows that each loads
what it uses (the bitmap routine sets ADAT, the road its line registers and
texture, the cockpit sites flush their own). The mask and colour scratch are
no longer written; only the same car's cookie-cuts read them. Host check
(`tools/fr12_car.py`, now three planes and the end registers): 0 mismatches
in 1,500 cars on each CPU; a seeded fault in the argument words was caught.
Frame gate: passed. 030 FPS: 48.47 against 45.52.

**Checkpoint after step 4** (`fr12-candidate`, `3c1a0f16…`; arm `-merge0`,
the native car blits, `182c052b…`). FPS, 300 presentations, warp off:

| Machine | Whole-car pass | Native car blits | Native game |
| --- | ---: | ---: | ---: |
| 030‑50 BCE | 48.47 | 40.70 | 24.55 |
| 040‑40 BCE | 28.53 | 25.00 | 24.5 |

Gates, all passed, the same set as the first checkpoint: frames (normal,
grid) and timing (elapsed error 0.059 %), the FR4 probe, smokes, MMU (030
and 040), route, modal and controls. The 040 is now ahead of the native
game.

**Profile after step 4** (030, shares of the draw): the road lines 23 %, of
which under two fifths is the line kernels and the rest the general per-blit
path (translation, span lookup, tracking, setup); the bitmap blits 21 %, half
of it the same path; publication 8 %; the cockpit cookie-cut 7 %; the fill
5 %.

**Step 5: the road lines on their own path** (`FRLineFast`, preset
`FF1FastRenderLine`). The two line sites (`$6ad8a`, `$6adde`) call it instead
of `FF1FastRenderSize`. With owned shadows, a one-word `$0B4A` line whose C
and D spans each lie in a bank shadow is translated, its D rows marked and
the kernel run directly; the span is FRTranslate's line span, now one routine
(`FRLineSpan`) for both. Anything else takes the general path. 030 FPS:
49.75 against 48.15 for the same build with the lines on the general path
(arm `-line0`).

**Step 6: area blits on their own path** (`FRAreaFast`, preset
`FF1FastRenderArea`). `FF1FastRenderSize` sends every redirected area blit
there when the shadows are owned: FRTranslate's spans and mirror test inline,
no tracking for read channels, a write marks bank rows (as `FRTrackChannel`
does with owned shadows). A line, or a span outside the mirrors, takes the
general path. 030 FPS: 49.92 against 49.26 (arm `-area0`).

**The view switch** (`FF1FastRenderShowSafe`, `FF1FastRenderVbl`). With
frames at one field, the census (FR8's log, whose alignment now holds)
showed a few copies into the bank still on screen: 4 in 1,126 fields of the
normal scene after step 5. The cause is how 1.3 switches views. `LoadView`
only stores the view's copper list in GfxBase (`LOFlist`); graphics' VBL
server loads it into `COP2LC`, and `copinit` jumps to `COP2LC` at line 12.
So a view shows from the first field after the request whose VBL is
serviced before line 12. In the log, one late switch followed a VBL serviced
at line 58; the others followed requests late in the field (none late below
line 256; from line 304 on all were late), which the ROM's sequence does not
explain and may be the emulator's CPU and copper timing. The copy into the
back bank now also waits until the bank cannot be on screen: the last
request (field R, line L) shows from field E = R + 1, or R + 2 for L ≥ 256,
at the first VBL from E on serviced before line 8 (the game's VBL server
records it). The copy goes ahead once that VBL has passed, or from line 256
of field E − 1 on, past the display. `FR8S` counts the held polls. After
the change no scene shows a copy into a displayed bank; the one flagged copy
in the normal scene took 18 ms instead of about 2 (a stall seen once before
the change too, cause not known), and one in the grid scene started at line
0, before that field's VBL server counted it. The cost is within the layout
noise (normal 49.59 against 49.75).

The pacing log (`FF1_FAST_RENDER_PACING`) now has 48-byte entries: the
copy field's VBL service line and the last request's field, line, kind and
bank. `test_h5_fps.py` reads the entry size (`FR8EntryBytes`) and
`fr8_report.py` decodes either size.

**Checkpoint after steps 5 and 6** (`fr12-candidate`, `766c50db…`; arm
`-merge0` `cc7c3389…`). FPS, 300 presentations, warp off:

| Machine | Candidate | Native car blits | Native game |
| --- | ---: | ---: | ---: |
| 030‑50 BCE | 49.92 | 44.18 | 24.55 |
| 040‑40 BCE | 29.36 | 25.64 | 24.5 |

Gates, all passed: frames (normal, grid) and timing (elapsed error 0.059 %),
the FR4 probe, smokes, MMU (030 and 040), route, modal and controls.

**The scenes** (030‑50 BCE, the log build of the same source; milliseconds
per one-tick frame; steady motion is the share of frames whose ticks equal
their fields on screen, FR8 in brackets):

| Scene | FPS | Draw | Copy | Intervals 1 / 2 fields | Steady |
| --- | ---: | ---: | ---: | --- | ---: |
| normal | 49.92 (40.5) | 16.1 | 1.8 | 300 / 0 | 99.6 % (55 %) |
| solo | 49.92 (45.1) | 16.1 | 1.2 | 300 / 0 | 99.9 % (88 %) |
| grid | 49.92 (38.9) | 16.4 | 1.3 | 300 / 0 | 99.9 % (54 %) |
| dense | 45.52 (29.8) | 19.7 | 1.3 | 271 / 29 | 88.7 % (34 %) |

Normal, solo and grid now draw every field. Dense is the one scene left
above a field; its profile: the car pass 21 %, the bitmap kernel 6 %,
publication 6 %, the area and line paths 8 %, row marking 3 %.

**Step 7: transparent car words** (`FRC_WORD`). Where the shifted mask
P1 | P0 is zero, every colour formula leaves C, so the pass skips the word's
three planes. Host check (`tools/fr12_car.py`, now with about 40 %
transparent source words): 0 mismatches in 3,000 cars on each CPU; a seeded
fault in the skip was caught. Dense: 46.51 FPS against 45.52, the draw
19.3 ms against 19.7. Checkpoint `caff0a86…` (arm `-merge0` `95943925…`):
030‑50 BCE 49.92 (44.05), 040‑40 BCE 29.66 (25.69); all gates passed
(elapsed error 0.026 %).

**Step 8: WaitBlit returns when the blitter is idle.** The game's WaitBlit
wrapper (code hunk $2a130: save a6, load GfxBase, call WaitBlit) runs after
every blit the FR path has already finished in Fast RAM. The patch tests
BBUSY first, as WaitBlit does, and returns at once when the blitter is idle;
otherwise it continues into the native call. Dense: 47.85 FPS against 46.51,
the draw 18.9 ms against 19.6, busy 20.8 ms against 21.4. Checkpoint
`376d1164…` (arm `-merge0` `27a2373f…`): 030‑50 BCE 49.92 (45.25), 040‑40
BCE 29.77 (25.73); all gates passed (elapsed error 0.026 %).

Tried for dense and dropped, against step 8:

- Publication with `cmpm.l` and offset stores: the draw fell 0.45 ms and the
  copy rose by the same; busy 20.8 ms both.
- Two middle car words per longword step: 45.8 FPS, the draw 19.8 ms. About
  83 % of the middle words are opaque in the busiest variants, so this cut the
  plane work in half where it runs, yet it lost. Not alignment: with the bank
  long aligned on each row (one word first where needed; the longword path in
  the eight variants dense uses) it was 45.66 FPS, the draw 19.9 ms. The cause
  is unknown. With it the fine payload grew
  enough that `move.l public_table(pc),a0` in `FastRender.s` took the 32-bit
  displacement form in the second payload pass only (the build's bindings
  check stops); `(public_table.l,pc)` fixes that if the payload grows again.

**FR12 is closed** (the user's decision, 2026-11-06). Result, checkpoint
`376d1164…`: normal, solo and grid draw every field on the 030; dense is
47.85 FPS (busy 20.8 ms; 50 FPS needs about 19.5). The dense profile has no
large item left: the remaining ideas, merging the line path into one
routine (about 125 lines of about 18 pixels per draw, the path costing more
than the pixels), a single-dot line loop without the per-pixel C read, and
lighter area setup, add up to an estimated 0.6–1.0 ms, short of the 1.3 ms
needed. They stay here for a later look.

**Steady motion: the predicted-tick variant is dropped** (the user's
decision, 2026-11-06). After the draw work the ticks match the fields on
screen in 99.6–99.9 % of frames in normal, solo and grid, so the variant
would only change frames that take more than a field. Dense goes on to one
field instead (the user's decision, the same day).

### FR9 — 030 data cache (optional)

Only if the 030 takes the FR path. Find the cause of the performance-mode
startup crash with the data cache under WHDLoad's MMU option; HEAD crashes
the same way. Then decide whether the FR path may enable the data cache
without the MMU option. Gates: section 4 plus both MMU smokes.

### FR10 — Checkpoint and release

- Run the full gates (section 4) and the FR selection gate per CPU; enable
  the path on each CPU that passes.
- Add an `ff1check.py` feature check named `fastrender`, covering
  `src/FastRender*.s` and the redirected sites. Extend
  the FPS check with the one-field share. Run the memory check if FR3
  changed the reservation.
- Update `docs/slave.md`, `release/ReadMe` and `RELEASE_QUALIFICATION.md`. State plainly
  that these are emulator results, that 060 is assumed to behave like the 040,
  and that real hardware is untested.
- Record what limits each CPU next.

## 4. Gates for every code step

The reduced test matrix applies: no 060, no WHDLoad 17.0, one A500 setup
except for memory checks.

- **Exact state:** 100 updates with identical state and private fractions.
  Presentation never advances simulation, so states match whatever the frame
  rate.
- **Exact frames:** 30 complete frames each for normal, solo, grid and dense
  match the B8-PAL/H6c references on 040‑40 BCE. These fixtures use fixed
  poses, so they stay valid at any frame rate.
- **Elapsed clock:** at most 0.25% error over 60 simulated seconds.
- **Controls and lifecycle:** pause, tow, pit, menu, re-entry, fault exit,
  overlay reload and INTENA restoration. All patch words restore.
- **Unchanged paths:** `CUSTOM2=0` legacy-exact on 020+Fast with both
  `CUSTOM1` values. The 68000 and chip-only 020 payloads are byte-identical.
- **Smokes:** the five core smokes plus both MMU smokes.
- **Performance:** 300 complete presentations, warp off, on 040‑40 BCE,
  030‑50 BCE and 020+Fast, path on versus off in the same session.
- **FR selection gate (user decision, 2026-11-02):** there is no fixed FPS
  target. A CPU takes the path when it is faster than today's path in the
  normal, solo, grid and dense scenes combined and slower in none. Report the
  interval histograms; one field per frame is the ceiling.

## 5. Risks

| Risk | Mitigation |
| --- | --- |
| Line-mode or fill corner cases differ from the blitter | FR2 oracle on every captured blit plus generated coverage; zero-difference gate |
| A native writer or reader missed by the census | FR1 attribution gate; VERIFY bank write-watch during prefix stages; production destination check |
| The 100 ms opponent frames exceed the field | Measured in FR0a; FR8 decision |
| Copy slower on real A4000/A1200 accelerators than in the emulator | Recorded as emulator-only; FR7 reduces bytes; hardware testing deferred |
| Fast memory headroom | FR3 measures the pool; all-or-nothing allocation; memory check |
| Native code draws into a bank outside the fine draw | FR1 persistence list; FR3 resync on every such route |
| The 030 is too slow without a data cache | FR0 decides the 030; FR9 optional |
| Overlay reload moves hunks and sources | Existing binding and ledger rebinding; mirrors refreshed on reload |

## 6. Work size and order

- **Large:** FR2 (complete software blitter and oracle), FR5 (six
  redirection steps) and FR6 (kernels).
- **Medium:** FR1 and FR3.
- **Small:** FR0, FR7, FR8 and FR10.

Dependencies:

```
FR0 (go, 2026-11-02) → FR0h → FR1 (done 2026-11-02) → FR2 (done 2026-11-03) → FR3 (done 2026-11-03) → FR4 (done 2026-11-04) → FR5a (done 2026-11-04) → FR5b (done 2026-11-04) → FR5c…FR5f (done 2026-11-05) → FR6 (done 2026-11-05)
  → FR7 (done 2026-11-06) → FR8 (done 2026-11-06) → FR12 (done 2026-11-06) → FR10 → (FR11, optional)
                                      ↑ checkpoints at FR5c and FR5f
FR9 any time after FR0, only if the 030 takes the path.
See "FR0 decision and plan revisions" for the changes to FR1–FR6.
```

Stop adding kernels or copy work on a CPU once it reaches one field per frame
in common scenes, or when further steps stop gaining there.
