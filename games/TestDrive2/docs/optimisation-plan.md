# Optimisation plan

> How to make the original game faster **as WHDLoad slave patches**, and in what order.
> **Subordinate to `docs/open-work.md`**: rendering speed is work item W6 there, after the
> simulation/rendering timing architecture is understood and a design is chosen.
> Numbers are from `docs/profiling.md` traces (stock-A500-equivalent machine, 2026-10-04).

## Constraints

- **Ship as slave patches only.** The slave already patches `duel` with `resload_PatchSeg`
  lists (`pl_main_v1`: protection, `set_copper`, keyboard joystick). Optimisations are more
  entries in that list: `PL_P`/`PL_PS` to replacement routines assembled into the slave, and
  `PL_W`/`PL_L`/`PL_NOP` for in-place byte changes. The slave is position-independent and is
  loaded into WHDLoad's memory, which on an A500 is chip/slow RAM like the game itself — slave
  code runs at the same speed as the code it replaces.
- **Game version.** All offsets are for `duel` v1 (108 868 bytes), the only version we have.
  The slave also supports v2 (109 248 bytes, different offsets); the optimisations must be
  limited to v1 (`get_version`) unless a v2 `duel` is obtained and the patches ported.
- **Optional.** Gate the speed patches behind a WHDLoad tooltype (`CUSTOM2`, `slv_config`
  `"C2:X:...:1;"`, `PL_IFC2X 1`). That gives users a way out, and gives us an A/B switch
  inside one slave binary.
- **No game bytes in the repo.** Replacement routines are our own code; patch lists name
  offsets. The slave source (JOTD, public domain) is in `whdload/`.

## Fast-CPU ceiling: blitter priority and CPU shapes (2026-10-04)

**On fast CPUs the renderer is chip-bus bound, not CPU bound.** Emulated
A1200/68030 at 25 MHz and at 100 MHz both give exactly 25.0 fps (one frame per two
fields). A 100 MHz 68020 cycle trace (`review-020-100`, CUSTOM2=3) spends 63%
of all cycles polling BBUSY (65% self time in `duel:0f114`), 8% in JOTD's beam
wait and 0.9% in the 50 Hz simulation. Per-blit accounting of that trace
(BLTSIZE writes at `0f1d4/0f224/0f27e/0f4ce/0f524/0f5ee/0f714/0f812/0fbc0`, polls
attributed to the preceding blit): shape cookie-cut 69 blits/field, 4,748
words/field, 54.7% of cycles waiting; shape clear-under-mask 6.7%; every other
blitter user ≤1%. A cookie-cut word costs ~19 colour clocks instead of the ideal
8: five low-res bitplanes take 28% of slots and the CPU's DMACONR polls 22%.

**Blitter priority (CUSTOM2 bit 2, shipping option):** DMACON BLTPRI set for the
game's lifetime, original value restored. Same build (`pri-*`), CUSTOM2=3 → 7:

| Machine | fps 3 → 7 |
|---|---|
| A500 (68000, 512K chip + 1.5M slow) | 5.2 → 5.4 |
| A1200 (68EC020, 2M chip + 4M fast) | 16.1 → 16.7 |
| 68020 100 MHz, same RAM | 21.1 → 25.0 (swap counter repeats 25.0) |
| 68030 25 MHz, same RAM | 25.0 → 25.0 |

Simulation state with/without bit 2 on the A500 is recorded in open-work.md.
**Trap:** with BLTPRI set, the 68020 cycle trace is corrupt (268 fields of cycles
in 40, PCs near zero) — use `SWAP_ONLY=1` for fps; do not read routine costs.

**CPU shapes (removed; in git history as `whdload/render-cpu.s`, commits
"Add a CPU shape-drawing experiment…" and "Merge CPU shape blits…"):** it kept the game's clip routine and reproduces each blit of
`0f114` word for word (ASH/BSH carries, FWM/LWM, modulos, minterm $CA, D-only
mode, original phase order). The VERIFY twin (`make verify VASMFLAGS=-DCPUSHAPES=1`,
CUSTOM2=11 CUSTOM5=9) compared it against the blitter: 18 shapes, 0 mismatches
(`cpu-twin-a1200`). It is **slower everywhere** (same build, CUSTOM2=7 → 15):
A1200 16.7 → 7.5, 68030/25 MHz 25.0 → 12.4, 68020/100 MHz 25.0 → 16.3 fps.
Even at 100 MHz the CPU's chip-RAM accesses, not its instructions, are the
cost: each CPU access takes longer on the chip bus than a blitter DMA slot, and
the blitter is the most efficient chip-RAM user available.

A second version (commit "Merge CPU shape blits per plane with longword chip
access") merges each shape's blits per destination plane (A is shared, so a
plane ends as A ? last B : C), builds shifted A/B for all rows in fast buffers
with aligned long chip reads, and combines each plane once with aligned long
chip reads/writes: ~8 chip accesses per word instead of 20 for a typical
five-plane shape. Twin: 276 shapes, 0 mismatches (`cpu3-twin-a1200`). Still
A1200 16.7 → 7.1 fps (a row-at-a-time variant: 5.3; 68030/25 MHz 10.3 vs 25.0).
The user accepted 25 fps as the cap; the CPU drawer was then removed.

**What could pass 25 fps:** less chip-bus work per frame, not a faster CPU or
moving blits to the CPU. The one structural option measured as plausible is a
fast-RAM back buffer for 68030+: point the bitmap planes at fast RAM so all
CPU drawing (spans, clear, masked copy) runs from cache, replace *every* blitter
user with CPU code (the exact twin above is the shapes' building block), and
copy only the 3D viewport to chip at the swap. Its copy cost and the remaining
display contention have not been measured; treat it as a new design to propose,
not an optimisation.

## One-field release revalidation (2026-10-04)

The final normal slave uses 50 Hz physics. Two fixed-window boots per arm give
4.5 fps with CUSTOM2=1 and 5.2 fps with CUSTOM2=3: 15.3% more frames, with every
original wait retained. Cross-CPU state matches 6000/6000; the render option does
not change the 1800-field input trajectory. Shape twins complete 18/33 cases on
the two CPUs, with no mismatches. The recommended combined mode repeats full raw
first/last images; the serial baseline differs only outside the game viewport
and is not claimed to pass that raw check. See open-work.md for exact evidence.

The additional simulation updates use CPU time; this fps gain is measured against
the same 50 Hz simulation, not against the faster three-field release. The
candidate bounds and experiments below are historical three-field measurements.
No new speculative rendering algorithm or changed blitter wait is included.

## Three-field W6 measured update (2026-10-04)

W1–W5 and the user's higher-rate design are now complete; their evidence is in
open-work.md. The tables and predicted gains below are the original handoff,
not current release measurements. In particular, a function's binary being
assembly does not establish its original source language. Inspect its actual
stack and register traffic before proposing a C rewrite.

The shape wait-before-start prototype lost speed: 5.6 → 5.4 fps in two
same-build fixed-window boots per arm. With unused blitter IRQs suppressed the
combined prototype reached 6.2 fps. IRQ removal alone reached 6.5 fps in the
same comparison build. The asynchronous prototype was removed, retaining all
original blitter waits, ownership and display contracts. The line routine
already waits before each blit; it did not have the assumed wait-after pattern.
JOTD's beam wait has not changed. The normal release repeats 5.6 versus 6.5 fps with identical first/last images
in both arms. Cross-CPU/slow-rendering state, fatal and normal trainer checks
pass; exact evidence is in open-work.md.

After that structural experiment, individual costs were summed from the
IRQ-only fixed window `w6-irq-only-a` (all 100 fields, exact saved slave):

| Candidate | Measured cost / bound | Decision |
|---|---:|---|
| Pair span interior stores | stores 2.623%, DBF 0.874%; 25%/50% savings give ≤1.093% before extra setup | skip |
| Tighten CPU clear | clear kernel 3.809%; bulk MOVEM 3.170%, at least 104/112 of that is mandatory writes; even deleting all other clear work saves <0.87% | skip |
| Cache projection angle accumulators | all four affected memory instructions together cost 0.346%; actual removable work is smaller | skip |
| Masked-copy rewrite | 2.77% of the inspected complete serial frame | skip |
| Remove beam wait | 1.5% in the handoff; preserves JOTD's display fix | retain |

The span and both projection passes already hold loop state in registers rather
than stack temporaries; the clear already uses two 13-register MOVEM writes per
104 bytes. Straight register allocation is not a measured ≥3% opportunity here.
This does not establish an optimal renderer. Colour-specific span edges, an
indexed sign scene and an early DMA clear are possible **new algorithmic
experiments**, needing their own reproducible scene, pixel twin and same-build
A/B. They have no claimed gain and are not part of this release. A DMA clear
would need a new safe overlap window: CPU-loop lower bounds do not bound DMA
latency hiding.

## What the original profile said

The game is **CPU-bound and serial**: the CPU never idles, and draws a frame every ~7 fields
(**6.9–7.1 fps**) in the first attract demo. Fast RAM barely helps (bus contention is not the
limit). The cost centres, in % of all CPU cycles:

| | Cost | Routine | Kind |
|---|---|---|---|
| A | 12–14% waiting, ~9% setup | `duel:0f114` shape blitter: BLTSIZE, then poll BBUSY, per plane × 5 | blitter serialisation |
| A′ | up to 18% in scenes with signs | `duel:0f91a` blitter **line** drawer: one blit per line, full `movem` save/restore and a BBUSY wait each | blitter serialisation |
| B | ~11.6% (but see below) | ~150 blitter-finished interrupts per frame through Kickstart 1.3's dispatcher, to graphics.library's empty blit-queue server | OS overhead |
| C | 13% | `duel:0789c` CPU span fill of 5 separate bitplanes | CPU fill |
| D | ~16% | `duel:07370`, `duel:079c6` road/object projection (`muls`, tables, globals in `-x(a4)`) | Aztec C |
| E | ~7% | `duel:09588` masked word copy, loop variables in the stack frame | Aztec C |
| F | up to 8% with signs | `duel:0a142` linear scan for a `$FF` marker (`cmpi.b #-1,(a1); addq.w #4; dbf`) | algorithmic |
| G | 3.6% | back-buffer clear with `movem.l` in `duel:0844e` | CPU fill |
| H | 1.5% | the slave's own `set_copper` beam wait (JOTD's flicker fix) | WHDLoad |

**B is mostly not on the critical path.** Measured with a test slave that clears INTENA's BLIT
bit before starting the game (`make -C whdload noblitirq`) (benchmark window below): the interrupts disappear, but the frame
rate only goes from 6.9–7.1 to **7.2 fps** and the blitter wait rises from 12–14% to **21%**.
The interrupts were firing while the CPU was already polling BBUSY, so they cost waiting time,
not work. The real cost is that **the CPU stops for every blit**. (The DMA slot count — blitter
5% of slots — understates how long the blitter is busy: line mode and shifted cookie-cuts have
internal cycles that use no bus slot.)

## Strategy, in order

### 0. Infrastructure (before any optimisation)

1. **Benchmark window** — `tools/fixed_window.sh OUTDIR [SLAVE]`: deterministic boot, break at
   the first driving frame of the first demo, trace 100 fields, report fields/frame. The first
   demo always starts the same way (desert, 2.6 miles, 0:00), but **is not pixel-identical
   between boots**, so compare frame rates, never frames. Baseline: 6.9, 6.9, 7.1 fps (three
   boots). A patch has to beat ~±0.15 fps to be visible; run each arm at least twice.
2. **Does the game move per frame or per elapsed time?** If physics/AI advance a fixed step per
   rendered frame, every speed-up also makes the *game* faster, and the release needs a frame
   cap (e.g. the 50/n Hz the original effectively ran at, or a user option). If movement is
   scaled by elapsed VBLs (there is a VBL counter at `-$30E2(a4)`, incremented in the game's
   own VBL server at `duel:02330`), speed-ups are free. Determine it by comparing distance/clock
   progress per field between the shipped slave and a deliberately slowed slave (busy loop
   in `set_copper`). **This decides the whole release design — ask the user once it is known.**
3. **Correctness oracle per patch, inside the slave.** A `VERIFY` build of the slave keeps the
   original routine callable (the patch jumps to our routine; the original bytes stay in the
   segment, reachable by a `PL_PS` to a trampoline), runs both on the same input into a shadow
   buffer, compares, and counts mismatches + the first offender in slave variables that gdb
   reads at the end of a benchmark window (same pattern as RoF's asm twins). Screens differ
   between boots, so this is the only exact check available.

### 1. Let the CPU run while the blitter works (A, A′; biggest, lowest risk)

Both blitter routines start a blit and **immediately** spin until it ends. Move the wait to
**before** the next register write instead (wait-before-start), so the CPU's setup of the next
plane/line and — after the last blit — the caller's own work overlap the blit. Nothing else in
the game must touch the blitter or the destination planes before waiting; check every blitter
user (grep for `btst #6,2(a6)` / BLTSIZE writes at `$58(a6)`) and add a wait at each entry.
Also drop the redundant double `btst` and the `nop`s (68000-safe: the first DMACONR read after a
BLTSIZE write is only unreliable on fast CPUs/A1000 Agnus — keep one dummy read).
For the line drawer, also hoist the per-line `movem` save/restore and constant register setup
(BLTAFWM, BLTADAT, BLTBDAT, modulos) out of the per-line path.
Then re-measure **B**: once the CPU no longer waits, the blitter interrupts steal real time,
and clearing INTENA BLIT (one `move.w #$0040,$dff09a` in `_bootdos`, restored at exit) becomes
worth more. Verify nothing uses `QBlit`/`QBSBlit` (they would never complete).

### 2. Cheap algorithmic wins (F, H)

- **F**: replace the linear marker scan with an index built once (the table is static scenery
  data); or at least a tighter loop. Scene-dependent, large where it matters.
- **H**: JOTD's `set_copper` waits for VPOS ≥ $84 before writing COP1LC, emulating a slow
  machine's timing to avoid tearing on fast ones. On a 68000 the original timing is the real
  one; consider waiting only for the blitter instead, or skipping the wait on a 68000. Must not
  bring back the flicker JOTD fixed — test on a 68020/68030 config as well.

### 3. Rewrite the hot C in assembly (C, D, E, G)

- **C** span fill: long-word stores (two 16-pixel words per `move.l`) on the interior, merged
  edge masks, and an unrolled interior loop; or, for long spans (road), let the blitter fill
  while the CPU continues (D-only blit with BLTADAT pattern), now that §1 has made the blitter
  asynchronous. Measure both: the blitter is already the busier unit.
- **E** masked copy and **G** clear: register-allocated asm loops; the clear can become a blitter
  clear started early and waited for late.
- **D** projection: the largest single CPU block. Aztec C keeps globals in `-x(a4)` and re-reads
  them; an asm rewrite with register allocation and 16-bit `muls` tables should halve it. Needs
  the most understanding of the data — do last, with the `VERIFY` oracle comparing outputs.

### 4. Release

`make -C whdload` builds the slave; package it as an update to the v1.5 install (slave +
ReadMe/history entry), with the speed patches under `CUSTOM2` and v2 left unpatched. Test on the
stock-A500-equivalent machine, on 68020/fast-RAM, and with the infinite-lives trainer on.

## Original estimate (not a measured result)

If §1 recovers most of the waiting (12–21%) and §2–§3 halve C–G, a frame shrinks by roughly
40%, i.e. **~7 → ~11–12 fps** in the demo window — before any frame cap that §0.2 may require.
These are estimates to be replaced by benchmark-window measurements, one commit per patch.
