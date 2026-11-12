# Open work

2.0b (12.11.2026): JOTD's 1.2 with Enhanced framerate, steps 0–5 and 7–9 below done and
step 6's read-only part: the harness; the gate, caches and optional ExpMem; the stack and
the code in fast memory; the 50 Hz presentation with the world at 1.2's 25 Hz; the objects
between their positions; the read-only tables in the copy; the clear ahead, a cheaper staged
frame. The a1200-030 shows 49.90 fps on the benchmark, the 020/14 with fast memory
44.50. Also the GAME OVER pause as a field wait (internals.md,
"Patches"). Open: the 020/14 in the explosion (step 7), the written data (step 6, which
needs a complete code map first). 1.2's source is kept unchanged in `src/original/` as the
reference build ([development.md](development.md)).

## Enhanced framerate: 50 fps at the original game speed

Goal: an "Enhanced framerate" option that draws at 50 fps on CPUs that can do it while the
world keeps the game's own rate. The 68000 path must not regress. Enhancements may be limited
to setups that gain from them (68020 or better with fast memory). Everything that can be in
fast memory goes there.

### What the benchmark shows

Level-1 benchmark ([development.md](development.md), "Benchmark"; tables in
[internals.md](internals.md), "Frames and time" and "Performance"):

- **The 25 fps cap, not drawing, sets the rate on fast machines.** The a1200-030 runs at 25.00
  fps with 44% of the CPU in the pacing wait. The a1200 (68020/14) runs at 24.70. A frame's
  work is 1.06 fields at the median on the 030 (p90 1.24, worst 1.82 in the explosion) and
  1.19 on the 020 (p90 1.38, worst 2.11). 50 fps needs every frame under one field.
- **The game is bound by the chip bus.** A 3.5 times faster clock (020/14 to 030/50) cuts a
  frame's work by only 10%. Every byte of the game is in chip memory. Outside the wait, the
  030's chip accesses per field are:
  - 50% code fetches;
  - 26% the screens (22% writes, 4% reads);
  - 14% CPU-only data;
  - 8% the stack;
  - under 1% blitter sources, copper, audio and sprites.

  So 73% of the CPU's chip traffic could be in fast memory. Each chip access costs the 030
  about 29 clocks; fast memory costs a few. The a1200-fast gives the a1200's figures: the game
  never uses the fast memory.
- **The world runs per frame; only the player's own steps run per field.** The world and
  game logic step once per frame with no time scaling (see the table below). Uncapped at 50
  fps, the world would run twice as fast; on the a500 (15.7 fps) it already runs at 63%
  speed. Two counters outside the world step count frames too:
  - `$11E36` ticks every second frame (on the odd toggles of the screen-swap parity
    `$11E67`) and feeds an index the world uses (`$10858`);
  - the start-of-level countdown `$11E0C`.
- **The transform `$E32A` and the depth sort `$E724` are presentation.** They read the
  world and write only lists the drawing reads, so they can run again on a frame that does
  not step the world.
- **Budget estimate (a model, not a measurement).** It recosts the traced code and stack
  accesses (then also CPU-only data) at 3 to 5 clocks instead of their measured chip cost.

  | Machine | Frames | Now | Code and stack in fast | Plus CPU-only data |
  |---|---|---:|---:|---:|
  | 030 | window mean | 1.10 | 0.49–0.57 | 0.36–0.46 |
  | 030 | explosion (fields 100–199) | 1.31 | 0.61–0.70 | 0.41–0.53 |
  | 030 | worst frame | 1.82 | 0.85–0.97 | 0.57–0.74 |
  | 020/14 + fast | window mean | 1.24 | 0.68–0.80 | 0.53–0.70 |
  | 020/14 + fast | worst frame | 2.11 | 1.16–1.36 | 0.90–1.19 |

  Values are fields of work per frame. The 030 should hold 50 fps with the code and stack
  moved and has margin with the data moved too. The 020/14 should hold it except around
  explosions, where the drawing work in step 7 decides. Because the world steps at a fixed
  rate (design below), a frame that misses its field costs one presented frame, not game
  speed.

The world block, per frame, in the main loop's order. Row order is execution order:

| Routine | Runs | What |
|---|---|---|
| `$ED76`, `$A1F6` | once a frame | world: shot spawn, player and object state (writes the shown palette through `$124B6`) |
| `$A836`, `$E7AA`, `$FD26` | per elapsed field, up to 3 | player: input `$11E72`, heading `$11EB4`, position |
| `$A570`, `$E29E`, `$F0A6`, `$CC2C`, `$F2CA`, `$EE86` x2, death check | once a frame | world: object motion, colour cycling, collisions |
| `$E32A`, `$E724` | once a frame | presentation: transform and cull, depth sort |
| `$C536` | once a frame | keys |

### Design

1. **Gating.** Enhanced framerate is `CUSTOM1=1`. The slave already reads `CUSTOM1`, which
   1.2 leaves unused. It becomes `ws_config` `C1:B:Enhanced framerate;`, with `ws_Version`
   17, and the installed icon sets it, as Powerdrome and Road Rash do. The option is active
   only when all of these hold; otherwise the game runs the 1.2 path with the same game
   memory:
   - `CUSTOM1` is 1;
   - `WHDLTAG_ATTNFLAGS_GET` reports a 68020 or better;
   - the optional ExpMem was allocated in fast memory: `$200000`–`$9FFFFF` or from
     `$1000000` up, never chip or the `$C00000` slow memory;
   - every relocation check passed.
2. **Memory.** The ExpMem is optional (a negative `ws_ExpMem`), so a machine without spare
   memory still runs the game. No DMA ever points into it.
   - Stays in chip:
     - the screens `$68000`–`$6FFFF` and `$78000`–`$7FFFF`;
     - the copper lists `$12300`–`$126FF`;
     - the sprites `$5400`–`$59FF`;
     - the audio samples `$7000`–`$80FF` and `$8200`–`$82FF`, the second inside the program;
     - the blitter sources `$20300`–`$205FF`, `$3F100`–`$41FFF` and `$70000`–`$715FF`.

     These are the regions the benchmark sees. Other levels and sounds may use more, so
     nothing the CPU reads is moved out of chip on the benchmark's evidence alone
     (step 6).
   - Goes to fast: the code (as a copy; the chip program stays intact because audio plays
     from it), the supervisor stack, and the CPU-only tables and variables.
3. **Logic stays native; presentation frames go in between** (Mercenary 3's design, also
   a Novagen engine). The copy's frame end paces to one field. The chip original keeps
   `$11E4C` at 2, so a path that still enters 1.2's loop runs it at 1.2's speed.
   - Every second field a **logic frame** runs the world block as 1.2 at the cap runs it,
     minus `$E32A` and `$E724`: the world, then the player step twice (both on the current
     input, as 1.2's two steps do), then the rest of the world and the keys.
   - Every frame then runs only `$E32A`, `$E724` and the drawing:
     - The logic frame draws a staged pose: the camera as it was after the first player step
       (snapshotted), and the objects halfway between their positions before and after the
       world step. The committed state is restored right after.
     - The next field's frame draws the committed state, which is what 1.2 would draw.

     The committed pose is on screen one field later than in 1.2. Motion is interpolated,
     never predicted.
   - `$11E67` is the screen swap: it picks the copper list of the screen just drawn
     (`$12370` shows `$68000`, `$12324` shows `$78000`), so it toggles every presented frame.
     `$11E36` moves to every second logic frame, and `$11E0C` counts logic frames.
   - A frame that overruns skips the in-between presentation. Due logic frames run back to
     back, at most 2 a frame, so world steps per second stay at 25.
   - The attract demo runs the same schedule; its per-field loop count is already fixed at 2.
4. **One build, two paths.** The 68000 and Enhanced-off paths keep 1.2's code and placement.
   All Enhanced code is in the slave or the ExpMem and is installed only after the gate.

### Steps

Each step ends measured: the benchmark (fps, work per frame), the outcome (score 15, targets
16, shield 4 in `end.png`), and from step 3 on, the equivalence check.

0. **Harness.** Done. `tools/dataflow.py` (the data-flow scan, saved by every benchmark),
   `tools/codemap.py` (the static code map), `tools/statehash.py` and the `hash N NAME`
   and `demo` steps of `tools/route.py` ([development.md](development.md), "Equivalence
   checks").
   - The hash is taken by the harness through a breakpoint at the world step's start
     (`$DA56`, after the draw and the frame end; the main-loop head `$DA30` until step 7)
     rather than by the VERIFY slave: no slave code, and emulated time is not disturbed.
     The VERIFY build instead traps chip code execution and guards the stack.
   - The hashed set: base memory `$0`–`$12FFF` without code bytes, `$10`, the field counter
     `$11DEA`, the last pacing exit `$11ECC` and the copper lists; screens are compared
     separately.

   Measured: two benchmark runs give the same 250 hashes (all distinct), two demo runs the
   same 150.
1. **Slave skeleton.** Done: `$VER` 2.0b, `ws_Version` 17 with `ws_config`, the optional
   ExpMem and the gate (also a CRC of the decrypted program), caches through
   `resload_SetCPU` on the Enhanced path only (BaseMem write-through, non-cacheable on a
   68040/060).
   - With Enhanced off (a1200-030), and on where the gate refuses it (a1200: ExpMem in chip;
     a500: a 68000), frame count and the fields between swaps equal 1.2's. The reports are
     not byte-identical: the pacing wait differs by a few thousand cycles in the traced
     total (under 0.001%), as the longer slave start shifts the phase.
   - Fault injection (VERIFY, `CUSTOM2`): no ExpMem, ExpMem in chip, a 68000 and another
     program each leave `$D7E2` unpatched and run exactly as 1.2 (fields 135–633).
2. **Stack in fast.** Done: `$D7E2`'s `movea.l #$7FFFE,a7` is the only SP load in the code
   map; its operand in the copy points at the top of the ExpMem page. VERIFY's guard fill
   shows 112 bytes used on the benchmark, 88 in the demo.
3. **Code copy in fast.** Done, as [internals.md](internals.md) "Enhanced framerate"
   describes. Changes from the plan:
   - The copy is `$5000`–`$12FFF` (the sprite routine `$5296` included), relocated from
     `tools/codemap.py`'s static map rather than Ghidra; the map reaches every PC traced on
     the a500, a1200 and a1200-030. Chip routines whose addresses are held in data get a
     `jmp` into the copy.
   - The PC-relative written variables (`$C526`, `$CA4E`) move into the copy instead of
     their readers becoming absolute.
   - The horizon plotter keeps its self-modification, writing the copy and then flushing the
     caches: the colour index goes past 16 table entries, so per-colour variants were wrong.
     Under `NOCACHE` and with the flush the plotter matches 1.2; the stale-cache risk in 1.2
     was not seen.
   - From fast memory the level-3 handler re-triggered (its `rte` overtook the INTREQ
     clear); the copy acknowledges twice.

   Measured (benchmark, `CUSTOM1=1` against 1.2, `tools/bench.py`):

   | Setup | fps | work per frame, fields: median / max | chip code fetches per field |
   |---|---|---|---|
   | a1200-030, 1.2 | 25.00 | 1.064 / 1.824 | 8373 |
   | a1200-030, Enhanced | 25.00 | 0.654 / 1.042 | 0 (3 trampolines, under 1 a field) |
   | a1200-fast (020/14), 1.2 | 24.70 | 1.188 / 2.107 | 7718 |
   | a1200-fast, Enhanced | 25.00 | 0.878 / 1.448 | 0 |

   Equivalence: the benchmark's 250 hashes and screens equal 1.2's; in the demo all 150
   screens are equal and 134 hashes, the rest differing only in the elapsed count `$11ECE`
   and the audio sequencer's timing bytes (1.2 takes 3 fields for some demo frames). The
   VERIFY build traps no chip code execution on either route; it does when a trampoline
   is removed.
4. **Native logic, 50 Hz presentation.** Done: the slave's main loop `_eloop`
   ([internals.md](internals.md), "Main loop"). Changes from the design:
   - The staged frame saves and restores everything the transform, the sort and the draw
     write (`_stab`, 5.5 KB), so it leaves no trace in the state; the committed frame is
     1.2's draw, and always runs, because 1.2's draw also steps state (the background
     objects' animation `$10D08` up, the horizon's turn `$11EB2`, the radar dot).
   - Logic frames never run back to back: the committed draw belongs to its logic frame.
     Only the staged frame is dropped, when the beam-timed estimate (the last staged frame,
     or the last committed draw + 64 lines, + 1/8) says it would not end by line 300.
     Lower margins let staged frames overrun and delay logic frames by a field (5 of 250
     with + 24 lines).
   - `$11E67` toggles per presented frame; a logical parity drives `$11E36` and is put back
     into `$11E67` when the loop is left. The radar dot's erase position is kept per screen
     buffer, because the committed frames all go to one buffer.

   Measured (benchmark, `tools/bench.py`, `CUSTOM1=1`):

   | Setup | fps | world steps per second | work per presented frame, fields: median / max |
   |---|---|---|---|
   | a1200-030 | 39.50 | 25.00 (every logic frame 2 fields apart) | 0.677 / 1.046 |
   | a1200-fast (020/14) | 25.00 (no staged frame fits) | 25.00 | 0.879 / 1.452 |

   Equivalence on the a1200-030:
   - Benchmark: all 250 logic-head hashes and shown screens equal 1.2's, at the same fields.
   - Demo: all 150 shown screens are equal; hashes equal at steps 1–134. Step 0 differs in
     the elapsed count, which the demo does not use. Steps 135–149 differ in the audio
     sequencer's bytes only, after a transition that takes 9 fields instead of 1.2's 44,
     as with the 25 fps copy (step 3).
   - Presentation frames call no RNG: `$7000` is in the hashed set.
   - The VERIFY build traps no chip code on either route; the stack peaks at 112 bytes.
   - With Enhanced off the benchmark is identical to 1.2.

   A contact sheet of 8 consecutive demo fields shows a new image every field, turning
   evenly.
5. **Interpolated objects.** Done ([internals.md](internals.md), "Objects between their
   positions"):
   - The data-flow scan: only `$E32A` reads the positions (x `$2794`, y `$2998`, z
     `$2B9C`, 128 slots); the depth sort reads only the visible list. The drawing's other
     object inputs (animation, colours) stay committed.
   - `_objsnap` copies the positions and lifetimes before the world step. The staged frame
     sets the midpoints and puts the positions back after its draw. It snaps slots that
     are new, were used again (their lifetime rose) or moved `$10000` or more.
   - Changes from the plan:
     - The positions are saved per moved slot into the ExpMem, not as part of `_stab`.
       Saving all three arrays (1.5 KB more chip traffic each way) let staged frames
       overrun: with `STAGEPAD` 64, 8 of 250 logic frames ran at other fields than 1.2's. At 96 they were
       on time, but only 2 staged frames in 500 fields ran (25.2 fps).
     - The snapshot runs only when the staged frame can fit (the line the last logic frame
       ended at plus the estimate). Without that the 020/14, where no staged frame fits,
       showed 9 committed frames a field late instead of 1.

   Measured (benchmark, `tools/bench.py`, `CUSTOM1=1`):

   | Setup | fps | world steps per second | work per presented frame, fields: median / max |
   |---|---|---|---|
   | a1200-030 | 38.40 (step 4: 39.50) | 25.00 (every logic frame 2 fields apart) | 0.672 / 1.046 |
   | a1200-fast (020/14) | 25.00 | 25.00 | 0.880 / 1.452 |

   - Of the 135 staged frames in the a1200-030's window, 132 had a snapshot.
   - Slots per step on the benchmark, from 1.2's dumps:
     - 2585 slots interpolated, at most 40 in one step;
     - 46 snapped as new and 41 as used again;
     - 16110 not moving;
     - none over the distance threshold.

     In the demo: 57 interpolated and 6 new.
   - Equivalence on the a1200-030, as in step 4:
     - the benchmark is identical to 1.2 (all 250 hashes, screens and step fields);
     - in the demo all 150 screens are equal, and the hashes differ from 1.2's only in the
       elapsed count at step 0 and the audio sequencer's bytes after the transition;
     - the VERIFY build traps nothing, and the stack peaks at 112 bytes;
     - with Enhanced off the benchmark is identical to 1.2.
   - The presented frames, dumped at every swap: shots shrink every field as they fly off.
     A new shot keeps its first position for two fields. The explosion's debris falls
     every field in which a staged frame runs.
6. **CPU-only data in fast.** The read-only tables are done
   ([internals.md](internals.md), `_rel_tab`); the written data is not.
   - Read-only, in fast memory:
     - the tables inside the copy, by relocating their base operands: the model pointers
       `$D1B0`, `$E408`, the horizon's patterns `$11EEA`–`$122FF`, `$12700`–`$12FFF`;
     - until step 8, the window `$54000`–`$65FFF` (the math tables at `$59FFE`, `$5DFFE`,
       `$5D400`, and the star tables), copied after the entry generates the star tables.
       Step 8 dropped the copy: its 72 KB kept the game from starting on a 1 MB A500
       (step 8). It was worth 46.40 against 44.50 fps on the a1200-fast and 50.00 against
       49.90 on the a1200-030 (without FMODE).

     A missed reader still reads chip, where the bytes are the same.
   - Not movable as planned:
     - The models `$17000`–`$5A000` (about 370 chip reads a field, through `$D1B0`): the
       blitter reads parts of them through pointers made from the same model addresses.
     - The object arrays `$1000`–`$3FFF` and the transform's arrays in the low page (about
       2000 chip accesses a field). The code addresses them as `$2794(a0)` with a0 the
       slot's offset, so the displacement is the chip address, and a 16-bit displacement
       cannot reach fast memory. Moving them means reassembling the routines that use
       them.
     - The written variables (`$11DEA`–`$11EE9`: about 370 reads and 80 writes a field,
       and those in `$C000`–`$10FFF`). Their addresses are also operands of code that
       `tools/codemap.py` does not reach. That code runs from chip and would keep using the
       chip copy. Examples:
       - `$D29C` (`addq.w #1,$11E40`, the level advance);
       - `$100AA`–`$10322` and `$1098C`–`$10B48`, held in the handler tables;
       - `$ACFC`, a branch table.

       The hottest variables (`$11E60`, `$11E66`, `$11EB4`, `$11EB6`) are among those
       operands. Seeding the tables' longs as code brings in data (the `$11346` table holds
       audio sequences), so each table's layout must be worked out first. A complete code
       map would also put that code in fast memory.

   Measured (benchmark, `tools/bench.py`, `CUSTOM1=1`):

   | Setup | fps | world steps per second | work per presented frame, fields: median / max |
   |---|---|---|---|
   | a1200-030 | 42.00 (step 5: 38.40) | 25.00 | 0.653 / 0.976 |
   | a1200-fast (020/14) | 25.00 | 25.00 | 0.859 / 1.410 (step 5: 0.880 / 1.452) |

   - Chip reads per field on the a1200-030: the window 417 → 3; the program's tables 295 → 0.
   - Equivalence as in step 5:
     - benchmark identical to 1.2;
     - demo identical to step 5's;
     - VERIFY clean, stack 112 bytes;
     - Enhanced off identical to 1.2.
   - The chip tables and their copies are equal at every logic step of both routes.
7. **Drawing work.** Done ([internals.md](internals.md), "Main loop"); the
   020/14 still misses frames in the explosion. Each change A/B measured on the a1200-030 benchmark
   (`CUSTOM1=1`):

   | Change | fps |
   |---|---:|
   | step 6 | 42.00 |
   | the clear ahead: `$DF94` in the time after a swap once the beam is past the view | 48.7 |
   | the staged frame's estimate from its measured parts instead of `STAGEPAD` (no logic frame late) | 48.2 |
   | `_sort`: `$E724`'s sort on a copy in fast memory | 48.7 |
   | the committed transform and sort in the committed frame's field, not the logic field (the logic field's median 259 → 190 lines) | 49.70 |
   | the estimate's margin 1/16 instead of 1/8 | 49.90 |
   | the staged frame saves only what it writes: the slots the transform writes (`_tcow`) and the animation words, 5.5 KB → about 2.2 KB | 50.00 |

   - With the last change the margin was tried at 1/8 again: 49.90, so 1/16 stays.
   - The staged frame's own work (save, staging, restore) fell from 37 lines to 16. Before,
     `_save` and `_restore` took 18 and 12 lines, 43 and 28 clocks a long, about the cost
     of a chip access each.
   - The clear covers rows 0–135 (`CROWS`), as `$DF94` does: the view ends at line 180,
     not 205. The clear's first chunked version cleared rows 0–159 and wiped the panel's top
     rows, which are drawn once; the screen check caught it.
   - Not kept:
     - The blitter for the clear, alone or beside the CPU: no gain. The clear is bound by the
       chip bus, which the blitter shares.
     - `_kclr` (chunks with beam checks) for whole clears: 60–64 lines against `$DF94`'s
       50, with fixed-offset `movem`, 14 registers, plane order or no beam checks. It only
       does clears that may stop.
     - Leaving the slot arrays to the committed transform: the screens differ (it skips
       slots its view checks drop).
   - Not done: overlapping the blits with CPU work (`$BB22`'s strips, the skyline `$BFB8`
     and the mountains `$D374` wait for each blit, and the game sets BLTPRI, so the CPU
     stalls; about 14% of the traced cycles) and a faster `$E32A` (40 lines in
     the explosion, with 105 slots in use).

   Measured (benchmark, `tools/bench.py`, `CUSTOM1=1`):

   | Setup | fps | world steps per second | fields between swaps |
   |---|---|---|---|
   | a1200-030 | 50.00 (step 6: 42.00) | 25.00 (every logic frame 2 fields apart) | 1: 500 |
   | a1200-fast (020/14) | 46.40 (step 6: 25.00) | 25.00 | 1: 431, 2: 28, 3: 4 |

   - The 030's frames in lines (313 a field), median / max: world + staged 221 / 311,
     committed 174 / 306.
   - The 020/14 misses 32 frames: 22 in the explosion (fields 147–196) and 10 over fields
     346–456. In 36 of its 250 logic frames no staged frame fits.
   - Equivalence on the a1200-030:
     - the benchmark is identical to 1.2 (all 250 hashes, screens and step fields);
     - in the demo all 150 screens are equal; hashes equal at 135 of 150, the rest
       differing only in the audio sequencer's byte `$827B` after the transition;
     - the VERIFY build traps nothing, and the stack peaks at 112 bytes, guard intact;
     - with Enhanced off the benchmark is identical to 1.2;
     - `end.png`: score 15, targets 16, shield 4.

   Then on the a1200-fast (020/14), A/B on the same source:

   | Change | fps |
   |---|---:|
   | the above | 46.40 |
   | FMODE 3 on AGA, the fetch window `$30`/`$A8` (the display 22.5% → 5.6% of the chip slots; the object draw 78 → 72 lines, `$10B48` 36 → 28); not kept, "Other candidates" | 47.50 |

   - Not kept on the 020/14:
     - the estimate's margin at 1/32, or `STAGEEND` 304: 47.50 and 47.40, each with a
       logic frame late;
     - a merge sort for `_sort` (any sort gives `$E724`'s bytes, the keys being unique):
       47.40, slower on the usual short lists; below 32 entries the selection sort and a
       merge sort above: 47.50, no frame gained. In the explosion it saved about 11 lines.
   - Where the 020/14's explosion goes: the committed frame's transform and sort take about
     100 lines (line 32 to about 140; `$E32A` about 90 of them), the object draw over 100.
     `$E32A`'s cycles are spread over the routine: the slot reads from chip, the octant
     logic, and 18% in the log normalisation's rotate loops, which `bfffo` could shorten by
     perhaps 5–10 lines. The draw is blitter-bound: one short 4-channel blit per plane per
     column, each set up and waited for by the CPU. 50 fps there needs a new object drawer
     or transform, not a tuning step.

   Target: the 030 holds 50 fps through the benchmark (met); the 020/14 + fast holds 50 fps
   through the explosion (not met: 44.50 in the release, without FMODE and the window copy).
8. **Matrix and acceptance.** Done. The benchmark (`tools/bench.py`) on the release build,
   against 1.2 (`tmp/ref`):

   | Setup | 1.2 | 2.0b, Enhanced off | 2.0b, `CUSTOM1=1` | world steps per second, Enhanced |
   |---|---:|---:|---:|---|
   | a1200-030 | 25.00 | 25.00 | 49.90 | 25.00, every step 2 fields apart |
   | a1200-fast (020/14) | 24.70 | | 44.50 | 25.00, every step 2 fields apart |
   | a500-020 (ECS, fast memory) | 23.10 | | 34.10 | 25.00; 1: 15, 2: 219, 3: 14, 4: 1 fields apart |
   | a1200 (no fast memory: ExpMem in chip, refused) | 24.70 | | 24.70 | as 1.2 |
   | a500 (a 68000, refused) | 15.70 | 15.70 | 15.70 | as 1.2 |

   - The 1 MB A500 (512 KB chip, 512 KB slow) did not start with 2.0b: WHDLoad stopped with
     DOS error 103 loading its "Resload" overlay. Base memory is all the chip, so the system's
     chip contents go to the slow memory, and the optional ExpMem (then 144 KB) took what the
     overlay needed. 124 KB booted, 136 KB did not. Dropping the table window's copy (72 KB,
     step 6) brought the ExpMem to 72 KB. Without it the a500-020 went from 35.20 to 34.10;
     the AGA cells, then with FMODE 3, measured the same (50.00, 47.50). Without FMODE they
     measure 49.90 and 44.50 (the window copy: 50.00 and 46.40).
   - Equivalence on the a1200-030, as in step 7: the benchmark identical to 1.2 (250 hashes,
     screens and step fields), with Enhanced off too; the demo's 150 screens equal and 135
     hashes, the rest differing in the audio sequencer's bytes `$8277` and `$827B` after the
     transition, which takes fewer fields; VERIFY traps nothing, stack 112 bytes on the
     benchmark and 88 in the demo, guard intact.
   - a1200-040 and a1200-060 (functional, MMU and caches): Enhanced on (the entry jumps to
     the copy), the benchmark ends at score 15, targets 16, shield 4 on both.
   - The GAME OVER pause: 108 fields on the a500 with 1.2, 1 on the a1200-030; 2.0b waits 108
     fields everywhere (the a1200-030 with Enhanced and the VERIFY build measured).
   - DMA: every page the bitplane, copper, blitter, audio and sprite channels touch on the
     benchmark is in chip below `$80000` (`chip.txt`), none in the ExpMem.
   - The fault injection (VERIFY, `CUSTOM2` 1, 2, 4, 8 with `CUSTOM1=1`, a1200-030): each
     leaves `$D7E2` unpatched and runs the benchmark exactly as 1.2 (250 hashes and step
     fields).
9. **Release.** Done: the ReadMe entry above JOTD's history (the option, its requirements,
   the credit to JOTD and Harry), `CUSTOM1=1` in the icon (`release/release.json`), the
   version 2.0b (12.11.2026).

## Other candidates

Not started and not measured; each needs its own investigation before it is planned.

1. The ReadMe's open bug: rarely the colours turn white, and the slave's numeric `]` key
   (`$5B`) works around it by rewriting the AGA bitplane control registers
   ([internals.md](internals.md), "Patches"). The cause is unknown; the self-modifying
   horizon plotter under the instruction cache (step 3) is one unverified suspect.
2. The keyboard handshake wait the slave inserts (`DBFD1`, three raster-line changes)
   and the game's own timing on fast CPUs have not been examined.
3. FMODE 3 on AGA (measured: the a1200-fast 46.40 → 47.50 fps with the window copy). Tried
   with the play lists' fetch window at `$30`/`$A8` (the game's DIW `$2C71`/`$F4D1` and
   modulos 0 unchanged; planes and rows 8-byte aligned) and removed: in interactive play on
   the a1200-030 it showed black one-line strips 16 pixels wide in the screen columns 48–63
   and 112–127, the HUD, view and panel alike, different every frame; the same build without
   FMODE showed none. The gdb-stub runs never showed them. The game shows sprites 0 and 1
   (the frame's edges, lines `$2C`–`$CB`) and points 2–7 at an empty sprite (`$5410`); the
   fetch starting at `$30` instead of `$34` may take sprite DMA slots. The loader's list
   (`$528`) is still shown at the entry, so FMODE must be set by the game's lists, not by
   the CPU there.
