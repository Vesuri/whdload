# Open work

No slave changes yet; the performance investigation below is measured, and the plan after it
is not started. `src/EncounterHD.s` is JOTD's 1.2 source as upstream has it; the game
directory only sets it up on the repository layout: it unpacks, builds (to the same code as
the shipped slave, not the same bytes: [development.md](development.md)), and boots to the
title screen and the attract-mode demo on the default a500.

Nothing is released from here. A release would need a new slave version with a
`$VER: <name> <version> (dd.mm.yyyy)` string (the packager reads the version and date from
it; 1.2 has no date) and a ReadMe entry above JOTD's history.

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

0. **Harness.** The benchmark run is the test route, plus the attract demo, which plays by
   itself after boot and goes through the same main loop.
   - Make the byte-level data-flow scan (scratch `exact.py` today) a tool next to
     `tools/chipprofile.py`.
   - Add a state hash of world memory per logic step. Screens, copper lists, presentation
     lists and code are excluded; step 3 fixes the exact set.
   - Add a VERIFY build switch that exposes the hash and logs every logic step.
   - Add a `demo` route to `tools/route.py`: boot with no input until the demo runs, then
     a few seconds of it, with a contact sheet.

   Done when two benchmark runs give the same hash sequence, and two demo runs do too.
1. **Slave skeleton.**
   - Add the `$VER` with a date, `ws_Version` 17 with `ws_config`, the optional ExpMem and
     the gate.
   - Cache policy through `resload_SetCPU`, honouring `NoCache`: instruction cache as now.
     Enable the data cache only where WHDLoad can make BaseMem non-cacheable, because the
     blitter writes screens the CPU also reads.

   Done when the a500, a1200 and a1200-030 with Enhanced off give the 1.2 benchmark reports
   byte for byte. Fault-inject: no ExpMem, ExpMem in chip, a 68000. Each falls back to the
   1.2 path.
2. **Stack in fast.**
   - Move the supervisor stack, `$7FFFE` at the entry, to a guarded area at the top of the
     ExpMem.
   - Find every place the game reloads SP (entry, restarts, game over) and redirect it.

   Done when the run is equivalent, the trace has no stack accesses at `$7FD00`–`$7FFFF`,
   and the gain is measured.
3. **Code copy in fast.** Copy `$8000`–`$12FFF` and the sprite routine at `$5296` to the
   ExpMem after decryption and the slave patches, then relocate the copy:
   - the absolute `jsr`/`jmp` into the program (17 in the window's code);
   - code addresses in immediates: the level-3 vector `$6C` (`$804E`, set at `$E1A0`) and
     any other vector the game sets, the audio sequencer continuations
     (`move.l #$8C2E,$8266` and the like);
   - jump tables (`$C5D6`, read PC-relative, so the copy's entries change).

   Data stays at its chip addresses and is reached by its absolute operands (640 `abs.l` in
   the window's code). The rest needs care:
   - The PC-relative reads of written data become absolute: `$C536` and `$C558` (the key
     byte `$C526`, written by the level-3 handler at `$C4E4`), and `$CA6C` (`$CA4E`).
   - The horizon plotter `$CA52`–`$CB8C` writes its own instructions (slots
     `$CB0A`–`$CB1C` and `$CB80`–`$CB84`, from the table at `$12A40`). Replace it with a
     version that does not modify itself, for example a loop per slot combination. That
     also removes a stale-cache risk the original has on 68020+ (unverified).
   - Re-apply keyhp (`$C4D2`) and SAVEHIGH (`$94C6`) to the copy.
   - Build the reference list from Ghidra seeded with all traced PCs, because the window
     executes only part of the program. Code the benchmark does not reach stays safe if a
     reference is missed: it runs the chip original, which keeps the slave's patches, and is
     only slower.

   Done when:
   - the benchmark's trace shows no code fetches from chip while Enhanced is on;
   - a VERIFY build traps any execution in the chip program's code bytes (the audio ranges
     are left alone);
   - per-step hashes match 1.2's;
   - the gain on the 030 and the 020 is measured against the model above.
4. **Native logic, 50 Hz presentation.**
   - Restructure the copy's main loop as in design point 3: pacing to one field, `$11E67`
     per presented frame, and `$11E36` and `$11E0C` per logic frame.
   - First version: the staged pose is the snapshotted camera with the committed objects.

   Done when:
   - world steps per second are 25.0 on the 030 and the 020;
   - the sequence of per-step hashes equals 1.2's on the a1200-030 under the same per-field
     input. 1.2 there does every frame's work in under 2 fields (worst 1.82), so its world
     steps are exactly 2 fields apart and the two line up;
   - presentation frames write nothing in the hashed set and never call the RNG (`$7000`
     moves only in logic frames);
   - the demo's per-step hashes equal 1.2's, and its contact sheet shows the same scenes;
   - fps is reported over the benchmark.
5. **Interpolated objects.**
   - Snapshot object positions before each world step.
   - Stage the midpoints in the logic frame's pose. Snap objects that appear, disappear or
     move further than a threshold.
   - Find the exact inputs of `$E32A` and the drawing with the data-flow scan.

   Done when contact sheets show objects moving every field without jumps at spawn, death or
   the explosion, and the hashes are unchanged.
6. **CPU-only data in fast.**
   - Read-only tables first: `$12000`–`$122FF` and `$12700`–`$12FFF`, `$17000`, `$20000`,
     `$28000`–`$29FFF` and `$59000`–`$5FFFF` read 690 times per field and are never written
     in the window. Copy them rather than move them, so DMA elsewhere in the game still
     finds them in chip. Redirect readers hottest first; partial redirection is safe while
     the data does not change. Static analysis must show that nothing writes a table after
     the copy (a level start that rebuilds one would leave the copy stale).
   - Then the written regions. These are moved, so the benchmark cannot vouch for the rest
     of the game. Each is moved all or nothing, with every reference relocated, and only
     when static analysis shows that no DMA pointer the game loads points into it:
     - the object arrays `$1000`–`$3FFF` (870 reads and 130 writes per field), reached
       through base registers set by immediates;
     - the variables in `$11000`–`$11FFF` and in the program range;
     - the low page.

   Done as step 3: equivalence, no chip CPU-data accesses outside the DMA map, gain measured.
7. **Drawing work, as the measurements then require.** Candidates:
   - Clear the back buffer with the blitter while the CPU runs logic and transform from fast
     memory. The blitter is busy in 5% of slots; the CPU clear `$DF94` is 9% of the CPU.
   - Overlap the blitter strips in `$BB22` with CPU work instead of busy-waiting.
   - AGA only: 64-bit bitplane fetch (`FMODE`). Bitplane DMA takes 22.5% of the chip slots;
     Mercenary 3 measured a gain from it.
   - Replace the O(n²) sort `$E724`, and speed up `$E32A`.

   Target: the 020/14 + fast holds 50 fps through the explosion. Each item is A/B measured,
   kept only if it gains, and shown to leave the hashes unchanged.
8. **Matrix and acceptance.**
   - a1200-030: 50 fps through the benchmark; the demo as in step 4.
   - a1200-fast and a500-020: measured.
   - a1200-040 and a1200-060: functional, with MMU and caches, as Road Rash's checks.
   - a500 and a1200 without fast memory: 1.2 behaviour byte for byte.
   - A DMA capture showing nothing reads or writes the ExpMem.
   - The fault injection from step 1.
   - World steps per second at 25 on every Enhanced cell.
9. **Release.**
   - Write a ReadMe entry describing the option, the requirements and the credit to Harry
     and JOTD.
   - Add the icon tooltype `CUSTOM1=1`.
   - Bump the version, then package.

## Other candidates

Not started and not measured; each needs its own investigation before it is planned.

1. The ReadMe's open bug: rarely the colours turn white, and the slave's numeric `]` key
   (`$5B`) works around it by rewriting the AGA bitplane control registers
   ([internals.md](internals.md), "Patches"). The cause is unknown; the self-modifying
   horizon plotter under the instruction cache (step 3) is one unverified suspect.
2. The keyboard handshake wait the slave inserts (`DBFD1`, three raster-line changes)
   and the game's own timing on fast CPUs have not been examined.
