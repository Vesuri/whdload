# Optimisation plan

> How to make the original game faster **as WHDLoad slave patches**, and in what order.
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
  `"C2:B:speed patches;"`, `PL_IFC2`). That gives users a way out, and gives us an A/B switch
  inside one slave binary.
- **No game bytes in the repo.** Replacement routines are our own code; patch lists name
  offsets. The slave source (JOTD, public domain) is in `whdload/`.

## What the profile says

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

## Expected result

If §1 recovers most of the waiting (12–21%) and §2–§3 halve C–G, a frame shrinks by roughly
40%, i.e. **~7 → ~11–12 fps** in the demo window — before any frame cap that §0.2 may require.
These are estimates to be replaced by benchmark-window measurements, one commit per patch.
