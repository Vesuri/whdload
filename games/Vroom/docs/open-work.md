# Open work

Set up from Mr.Larmer's and CFou's v1.4 slaves (the import builds byte-identically to them).
The slaves now run with the caches on: the self-modifying code is made cache-safe on 68020+,
and the blitter queue no longer overruns on fast CPUs (`docs/internals.md`, "Fixes" and
"Self-modifying code"). Vroom's demo race renders correctly, with no WHDLoad dump, on the
a500, the a1200 with `CACHE`, the a1200-040 with `DCACHE`, and the a1200-060 with every
cache option on. The data disk runs its title, a player race, the scores and a second race
on the a1200-040 (`CACHE`), and its demo race on the a500. With Enhanced framerate
(`CUSTOM1=1`) the race runs on a fixed tick on a 68020 and up (step C): 16.7 Hz, or 25 Hz with
`CUSTOM2=1`, and with fast memory draws frames between the ticks (step 15).

## Release

2.0b (23.11.2026), the fix-only release: phase B's fixes, with a ReadMe line for each.
`$VER` and info text in both slaves, the ReadMe entry above CFou's. `make dist` builds
`VroomEnhanced-2.0b-20261123.lha` (`lha t` passes; its slaves match
`release/slaves.sha256`). Vroom's slave passed the four-machine matrix. The data disk's slave
ran its demo race on the a500 and the a1200, and the menu, a player race and a second race on
the a1200-040. Not published. Its archive was built at commit 494c65a1; the slaves since
then carry step C (`ws_Version` 17), which the 2.0b ReadMe does not describe.

## Decisions (the user's, 23.11.2026)

- **Enhanced framerate** (`CUSTOM1=1`) is one toggle for the whole enhancement: the fixed
  tick, the frames between ticks and every performance change (step E). It applies on a
  68020 or better (`WHDLTAG_ATTNFLAGS_GET`, as `src/smc.i` gates already). Bug fixes
  (step B) stay on for every CPU and every setting.
- **Game speed** (`CUSTOM2`), as in Virus: 0 is 16.7 Hz (a tick every 3 fields, the
  default), 1 is 25 Hz (every 2 fields). The slaves get WHDLoad's config splash with
  `ws_config` `"C1:B:Enhanced framerate;C2:L:Game speed:16.7 Hz,25 Hz;"` (`ws_Version` 17,
  so the ReadMe's requirement becomes WHDLoad 17).
- **The 68000 and 68010 keep the original loop**, with the option on or off: one step per
  frame, as today.
- **Caches are left to the icon.** The slave makes no cache calls (`resload_SetCPU`). The
  installed icon carries `CACHE` beside `CUSTOM1=1` (step 21).

What this means per machine, from the race-start figures:
- A 14 MHz 68020 with chip memory only (17.5 fps today) gets a steady game speed; at 25 Hz
  it runs catch-up ticks instead of extra frames (a tick is about 11% of an a500 frame).
  Frames between ticks appear only where frames are shorter than a tick.
- The 68040 and 68060 get a steady speed from step C. The frames between ticks come with
  step D, and reach 50 a second as step E brings their frame time under a field (31.8 and
  44.5 fps today).

## Step by step

### A. Harness (done)

The tools are in `docs/development.md` ("Tools"); the facts they rest on are in
`internals.md` ("Input, the menu and the race controls").

1. **Benchmark window** (done). `tools/vroom.py bench N` gives the fields the first N frames
   take after the green light of the first demo race, with the distance as a check: the demo
   replays recorded controls once a frame, so it is the same race on every machine. Equal
   distance at equal frames on every machine below.
2. **Per-step state log** (done). `statelog N FILE` reads the race state block $DBC0-$E073
   (globals, the 16 cars of 64 bytes, the car order) at every frame end, through a
   breakpoint at $D510, which works on every CPU. `tools/statecmp.py` compares two logs. The
   first demo race's 300 frames agree on the 68000, 68020, 68040 and 68060. What $DBEC
   and $DBF0 mean (for step 15) is still open: $DBF0's high word follows the player's
   lateral position $DC56.
3. **A real race through the menus** (done). `race` goes from the boot through the title
   (right button) and the menu (left button held on START) to the green light of an ARCADE
   race. `drive` then drives it: full throttle, shifting, steering against the lateral
   position. It crashes now and then and goes on. Served with `BOOT_BREAK=0x3658`, two boots
   drive identically. The controls are positions read once a frame (step 13).
4. **Machine matrix** (done). `tools/matrix.py` boots each cell once with a deadline and
   reports `bench`, dumps and a screenshot. `bench 300` from the demo's green light, with
   phase B's fixes (the 68020 and up wait for each swap to be shown, step 7):

   | Machine | Options | Fields | fps | Fields per frame | Distance |
   |---|---|---|---|---|---|
   | a500 | - | 1124 | 13.3 | 3-6, mostly 4 | 90006 |
   | a1200 | - | 968 | 15.5 | 2-5, mostly 3 | 90006 |
   | a1200-030 | `MMU` | 731 | 20.5 | 1-4, mostly 2-3 | 90006 |
   | a1200-040 | `CACHE` | 610 | 24.6 | 1-3, mostly 2 | 90006 |

   Before step 7 the 68020 and up ran 17.2, 24.4 and 29.8 fps; the `--full` cells then were
   the a1200-fast at 18.4 and the a1200-040 with `DCACHE` at 36.3. No cell left a WHDLoad dump.
   The four default cells are the check after a finished change (a few minutes); `--full` adds
   the two others for one-off decisions such as step 21. The distance is read at the last
   frame's end (a breakpoint at $D510). It used to be read at the next field boundary, where it
   could include the next frame's step. That gave 90304 on most machines, 90006 on the a1200
   after step 7, and probably the a1200-060's 96505 (it runs a frame per field), which also
   matched the others under `statelog`. The 060 is left out until the 68040 work is done.

### B. Correct on the 68040 (bug fixes, always on)

5. **SNOOP run** (done). `SNOOPAGA CHKBLTWAIT DCACHE` on the a1200-040: five demo races and
   a player race (`race`, then `drive` for 6000 fields) without a fault.
6. **CPU-timed waits** (done; `internals.md`, "Fixes" and "CPU-timed delays"). The keyboard
   handshake ($A2AC) was too short on every CPU and is now a 3-line beam wait. Five `dbf`
   delays (the menu's wipes, pauses after menu choices) are beam waits of their 68000 length on
   a 68020 or higher. The sound player has no CPU-timed wait: it restarts audio DMA at the
   next VBL. The loader's drive delays were already removed by the original slave.
7. **The flickering roadside objects** (fixed on 68020+; `internals.md`, "CPU-timed delays
   and the swap"). The next frame drew into the buffer still on screen until the VBL took the
   new one. The landscape now waits for that VBL: the 68040's frame rate drops from 29.8 to
   24.6 fps until step 16's third screen. The a500 keeps the original loop.
8. **Untested paths.**
   - The end of a race and the second race start work on the a1200-040 (`CACHE`): an ARCADE
     race driven until its time ran out, the scores table (it waits for the right button at
     $5360), the menu, and a second race. That start reloads part of the program to $439C
     ($817E), and `Fix_Decrunched` patched it again. No dump.
   - The highscore save is still untested: the test driver's score stays under the table's
     lowest entry (2000), and gdb cannot write memory to give it one.
   - **The data disk's crash at its first race** (fixed; `internals.md`, "The data disk's
     two disks"). Its race start read the directory from `Disk.1`, so the data disk's files
     were loaded from the Vroom disk. On the a500 the demo race ran, and the title came back
     after it. On the a1200-040 (`CACHE`) the title prompt, the menu, a player race to its end,
     the scores and a second race all ran. No dump.
9. **Game speed.** On a fast machine the game runs 2.7-4.2x too fast. That is fixed by step C,
   which is therefore part of goal 1, not only of 50 fps.

Then a fix-only release: B's fixes, with a ReadMe line for each.

### C. Simulation on a fixed tick (Enhanced framerate, 68020 and up; done)

`src/enhanced.i`; `internals.md`, "Enhanced framerate", has the design and the checks.

10. **The option's plumbing** (done). `CUSTOM1`, `CUSTOM2` (and `CUSTOM3`, a test knob for
    step 14) read at install, applied on a 68020 or higher only. Both slaves have
    `ws_config` (`ws_Version` 17). `game.conf` adds `CUSTOM1=1` to `make run`/`serve` unless
    `ENHANCED=0` or `WHD_ARGS` sets `CUSTOM1`. The a500 runs its first three demo races
    (three circuits) at 13.8, 17.5 and 13.9 fps, so 16.7 Hz is about 1.2 times its speed on
    two of them and the same on the third. A player race on several circuits is not
    measured: the test driver's car was nearly stopped in the windows taken.
11. **The tick and the frame** (done). Each race loop pass stays one tick. A pass that
    catches up leaves out only what draws: in `$D13C` the road spans, the objects, the
    scaler and the swap. The landscape `$E4F8` runs whole, because it is not only drawing:
    its first part follows the track for the simulation, and its projection decides whether
    the car is off the road ($10AAA, at $FA62/$FAC6). A build that left the projection out
    diverged at that flag only. `$D13C` runs its timekeeping in every pass: the ARCADE score,
    the start lights, the pit stop, the crash sequences.
12. **The scheduler** (done). At the start of each pass ($AF56): wait while early; a pass
    whose next tick is due already does not draw (at most 3 in a row); debt over 50 fields
    is dropped and counted ($1CC). The race's entry ($AF50) and the end of a pause ($B724)
    restart the tick clock. Link play keeps the original loop.
13. **Input and frame-counted timers** (done, no change needed). The mouse is read as
    positions once a pass; a gear change acts on the release, once however many passes see
    the press; the demo's controls advance one entry a pass. Every frame-counted timer is in
    the pass, so it counts ticks.
14. **Validation** (done). The per-pass state equals the a500's for 599 passes on the
    a1200-040 with two of three passes undrawn and on the a1200 at 25 Hz. The distance at
    equal fields matches the a500's at the same tick (within one tick, 0.56%) on the a1200,
    a1200-030 and a1200-040 at both speeds. A pause runs no ticks and restarts with no
    catch-up. Gear changes act once. The a500 with `CUSTOM1=1` runs the original loop.
    Not covered: laps (no run went past a lap), link play, the data disk beyond its first
    demo race.
    - The cost: an undrawn pass still runs the landscape and its projection. With the
      sky and ground clear left out of undrawn passes and the wait for the shown screen
      after the landscape (phase E, step 22), the 68020 at 25 Hz draws 486 frames in 1200
      fields (20.3 fps, 15.8 without the option); at 16.7 Hz 399 of 400. The plan had
      expected a catch-up tick to cost about 11% of a frame. Step 22 measured what is left.

### D. Frames between ticks (Enhanced framerate, 68020 and up)

15. **Interpolation (done).** The ticks draw nothing; frames are drawn between them, each
    showing the last two ticks' states mixed by the time since the newer tick was due
    (`internals.md`, "Frames between ticks"). The snapshot is the race state and the
    landscape's variables; a frame re-runs the landscape with alpha of the tick's step
    (it integrates by the step, so it is not mixed), mixes the other cars, and stops short
    of the line. Needs fast ExpMem (now 80 KB); the a1200 without fast memory keeps drawing
    in the ticks. On the way the landscape got a wait for the blitter queue in every mode:
    a crash in a player race on the a1200-030 was a frame's landscape writing $11368 inside
    a queued blit. At 16.7 Hz (`bench 500`): the a1200-fast 24.4 fps, the a1200-030 36.9, the
    a1200-040 34.3 (each 16.7 before). The ticks match the a500 (`statelog`). Still to
    look at: a frame by frame visual check of a player race (restarts, crashes, the pit
    stop), and the demo cameras.
16. **Pacing (done; `internals.md`, "Frames between ticks").** A frame now starts as soon
    as the last one has swapped, so its landscape runs while the last frame waits for the
    VBL; its alpha is for the field it will be shown in, and a tick due by then runs first.
    `bench 300` at 16.7 Hz: the a1200-040 and the a1200-030 41.67 fps (34.25 and 36.87),
    the a1200-fast 26.50 (24.44), the data disk on the a1200-040 49.34. On the way: alpha
    could go negative (an early tick, then the VBL took the frame), which crashed the
    a1200-fast; the map marker drew before the wait for the shown screen; a tick drew the
    wheel's lower part and the panel updates into the screen on display (`shown`: none of 80
    frames now); a frame's cars kept the tick before's order, so one the player had just
    passed could be behind the camera, and the cars' sort then wrote over the landscape's
    variables (a crash on the a1200-030 in a player race; frames now leave such a car out).
    Ticks wait for the shown screen again (about 3%). No tearing: the swap is
    the copper list's at the VBL. Left for 50 fps: most frames fit a field on the a1200-040,
    about 1 in 5 takes 2 (step 24). A third screen would let a frame that runs over draw on instead
    of waiting: not tried (32000 bytes of chip memory, not yet found inside BaseMem).
    Later, from a player race on video: the camera's and the player's lateral positions,
    the pitch and height (hills, jumps, the crash), the sky objects against the horizon
    (the mountain's top) and the crash's flying wheel still moved once a tick, and the
    frames wrote the engine's pitch from the tick before's revs; each is now mixed, or left
    to the ticks (`internals.md`, "Frames between ticks"). Then the road on a flat
    stretch (its slope from the unmixed pitch at $F436) in a jump, and the engine's
    sample: the snapshot held the sound's interrupt state, and frames put it back.

### E. Speed: a frame per field on the 68040 (Enhanced framerate, 68020 and up)

17. **Ceiling first** (done). On the a1200-040 with the option off (the original loop, a frame
    as fast as it draws), `bench 500` gives 24.75 fps (2 fields a frame), and 28.0 with an
    instant blitter (`--uae_immediate_blits=true --uae_blitter_cycle_exact=false`); the
    a1200-060 preset is not cycle-exact (50.1 fps, no ceiling). An aprof profile of 100 race
    fields (`aprof`, `CPU=68040-NOMMU`, `tools/aprof_report.py`) splits a frame:
    - chip memory accesses are 84% of the time (the program, its data and the screens are all
      in chip memory; the emulated 68040 charges little else);
    - about 20% waits for the VBL to take the last frame (`fix_Landscape`): with two screens
      a frame takes whole fields, and the work is about 1.6 fields, so it must fall below one
      field, by about 40%, before the frame rate moves;
    - the scaler `$18154` 30.5%, the road spans `$10CD2` 11.6%, the landscape about 13%;
    - waiting for the blitter about 22%: the objects' wait for the blitter queue ($1421E,
      `jsr $1123A`, once a frame) 8%, the original slave's wait after each blit (`$10C`-`$124`,
      about 13000 blits in 50 frames) about 10%, the rest the queue waits of step B.

    The bypasses were left out: the profile gives each part's inclusive time directly, and a
    bypass would only move the frame across a field boundary or not.
18. **Blitter waits** (done; `internals.md`, "Enhanced framerate", "Blitter waits"). 91 of
    the 134 blitter starts the original slave made wait are followed by the game's own wait
    before its next blit: with the option they only start the blit. The 68020 draws 21%
    faster (option off, `bench 500`: 19.11 fps against 15.76; every site 19.89), every frame
    the same above the cockpit. At 25 Hz it shows little (490 frames in 1200 fields, 486
    before): drawn frames still take whole fields. Left: the 40 starts that reach a branch
    before the game's wait (loops; 0.8 fps more at most) and drawing the smallest blits with
    the CPU.
19. **Fast memory for data and the race block** (done; `internals.md`, "Fast memory").
    With an optional fast ExpMem the stack and the race block move there. Checked with
    `statelog`, `frames`, an MMU-protected developer build through the menus, a driven race,
    its end and a second race, the data disk, and the matrix. Without fast memory, or on a
    68000, nothing moves. What else in chip memory the CPU uses most (the a500's 100 race
    fields): the span table ($34D00-$350FF, 43000 data accesses), the projection's variables
    ($3048E-$3049F, 22000), and read-only data in $2FC96-$36800 written before the race. The
    screens, copper lists and anything the blitter reads or writes stay in chip memory.
20. **Code in fast memory** (done). The block now runs to $1B4FF: besides the race loop and
    the renderer, the objects ($140C0), the scaler ($18154) and the bitmap scaler
    ($19FB0-$1AF3F) with their variables. Any offset works, so the ExpMem is the block's
    size. At 25 Hz the a1200-fast (68020) draws 25.05 fps (none undrawn), against 24.78 with
    the step 19 block and 23.19 with the block in chip; on the a1200-040 aprof puts the
    drawing at 39.0% of the time (47.0%) and the wait for the next tick at 52.1% (43.6%).
    With fast memory every measured machine draws all but at most 1 of 500 ticks at 25 Hz,
    so triple buffering could only help without fast memory (the a1200) or above 25 Hz.
21. **The icon's cache tooltype** (done): `CACHE`. Both options mark chip memory cacheable
    write-through under the MMU; `Cache` turns the data cache off in the CACR (everywhere,
    fast memory too), `DCache` turns it on. On real boards chip memory is never cached, so
    `DCache` could only gain on the data in fast memory (the stack and the race block's
    variables), and on a 68060 every rejected cacheable chip access is restarted (WHDLoad's
    `cache.html`: reads about 3 times, writes about 5 times slower), in a race whose time is
    mostly chip accesses (77% on the 68040). Measured, `CUSTOM1=1 CUSTOM2=1`, the first demo
    race:
    - `bench 500` on the a1200-060 without an MMU model (`--cpu=68060-NOMMU`, chip data not
      cached, as on boards): 25.03 fps with either option, 1 of 500 passes undrawn. aprof on
      the 68040 without an MMU model: the same profile with either (that model charges
      nothing for fast memory, so a data cache there cannot show); with `CACHE` the wait for
      the next tick (`enh_Pass`) is 50.5% of the time.
    - `statelog 600 tick` (`CUSTOM3=2`) against `CACHE` on the a1200-040: the 68040 and the
      68060 without an MMU model agree in every pass with `DCACHE`. With the MMU model, where
      FS-UAE caches chip data, `DCACHE` changes the race from its first passes (the 68040 at
      pass 1, the 68060 at pass 0) and the frames (`frames 150`: none of 150 the same in
      lines 36-171): the CPU reads chip memory the blitter or the loader wrote since. An
      emulator with an MMU model is the one place that caches chip data.

    `CACHE` it is: all but 1 of 500 ticks drawn at 25 Hz on the 68030, 68040 and 68060, no
    chip-access restarts on a 68060, and correct in emulation with or without an MMU model. The ReadMe
    (step 26) names `DCache` as the alternative for boards, not for emulators.
22. **The hot routines** (done, no change: nothing measured is worth rewriting). aprof,
    `CUSTOM1=1 CUSTOM2=1`, 200 fields of the first demo race (`internals.md`, "Where the
    time goes (68020)"). With fast memory every measured machine already draws all but at
    most 1 of 500 ticks at 25 Hz (step 20), and the a1200-fast (68020) still waits 16% of
    its time for the next tick, so only the a1200 without fast memory falls behind (20.7 fps
    at 25 Hz; at 16.7 Hz it keeps up). There 89% of the time is chip memory accesses, spread thin:
    no instruction of the landscape takes more than 0.5%.
    - The candidates: the projection's `muls` ($F672, $F680, their mirrors $F6E4/$F6F4 and
      $F74C/$F752) take 1.1% together; the road spans (`$10CD2`, 9.7% inclusive) and the
      span filler (`$10E72`, 3.3%) are whole-line writes to the screen, already long words
      and `movem`; the scaler (`$18154`, 29.4%) draws into the screen too.
    - The cache flushes. Two of the landscape's self-modifying shift-count sites
      (src/smc.i's `smc_Sh1_10`, `smc_Sh1_12`) run about 5 times a pass, each followed by
      `resload_FlushCache`: 3.2% of the a1200's time (1.3% on the a1200-fast). A scratch
      build replaced the four routines with precompiled variants chosen through a pointer, as the bitmap scaler's
      pairs are (no code written, no flush; checked word for word against the game's
      routines and tables; `statelog 600 tick` the same as the a500's on the a1200 and the
      a1200-040). The stubs fell to 0.16%, but the landscape's own time rose (31.4% to
      33.3%, the indirect jumps and their fetches from chip memory) and `bench 500` gave
      20.63 fps against 20.68 and 20.71: not kept. Clearing the instruction cache in the
      CACR directly instead crashed every machine where WHDLoad moves the VBR to fast
      memory (a1200-fast, a1200-4m, a1200-030; it ran with `NOVBRMOVE` and without fast
      memory), and WHDLoad allows cache changes only through its calls (`howto.html`).
    - Leaving the projection out of undrawn passes (the open item from step 14): a
      measurement build that skips it whole drew 21.11 fps on the a1200 against 20.68 and
      20.71, about 2%: the ceiling for working out the flag without the projection (the
      flag diverges in that build, so the race does too; a second run raced differently
      and drew 18.75). Not worth an exact copy of the projection's first line.

    Left for the a1200 at 25 Hz: a third screen (step 16), not measured.
23. **Loading time (done).** An aprof profile of the boot to the green light (`aprof race`;
    `internals.md`, "Where the load's time goes") put the program's unpacker first among
    the game's own work (164 of its 772 fields, and 54 for its table setup). That was its
    reads of its own Huffman tables in chip memory, not the track reads or its code, so the
    slave moves the tables and the unpacker's variables to a page of the ExpMem (then 76 KB, now 80 KB)
    and rewrites the loader's 24 addresses of them (`enh_Move`, with the block; behind
    `CUSTOM1` with fast memory). Reading whole archives into fast memory and a copy of the
    unpacker were not needed. The game's field counter at the green light (`race`, two runs
    each; the boot before the game varies by ±100 fields with the emulated hard drive):

    | | before | after |
    |---|---|---|
    | a1200-040, `CACHE` | 769, 771 | 607, 617 (-3.2 s) |
    | a1200-030, `CACHE` | 637, 639 | 540, 541 (-2.0 s) |
    | a1200-fast | 961 | 909 (one run each) |

    `statelog 600 tick` against the a500: the same in all 599 passes on the a1200-040, and on
    the a1200-030 except 11 passes that differ only by the copy's offset (`development.md`).
    The race on the a500, the a1200 and the a1200-fast, and the data disk's race, scores and
    second race on the a1200-040 and the a1200-030, ran with no dump.
    - On the way: the title's copy of its load routine to $1CF94 had been relocated into the
      fast copy and wrote 302 bytes past the ExpMem since step 19 (`internals.md`, "Fast
      memory"; fixed in `tools/reloc.py`). And the scaler's pointer table runs past the
      block's end, so the unpacker's page starts at the next page after `ENH_TAIL`.
    - Left: the boot loader's unpacker (58 fields, before the slave reads `CUSTOM1`), a
      sound sample's decode (28), and the boot before the game (Kickstart, WHDLoad,
      `PRELOAD`: about 450 fields in FS-UAE, its hard drive's timing).

24. **The blitter's share** (`internals.md`, "64-bit fetch"). What was left after step 16
    is blitter time: with an instant blitter the a1200-040 and the a1200-030 draw every
    frame in a field (`bench 300` at 16.7 Hz: 50.17 fps). aprof on the a1200-040 put 12.4%
    of the time in the objects' wait for the blitter queue ($1421E: the sky and ground clear
    `$10F90` queues is still running when the road spans are done) and 10.7% in the
    slave's waits after single blits; 11.3% waited for the VBL. Measured, scratch builds:
    - Blitter nasty (`BLTPRI`) for the whole race: 40.76 fps on the a1200-040 and 42.13 on
      the a1200-030 (41.67 and 41.55 before); only while the slave waits for a blit, 42.25
      and 42.98. The game already sets it in its own queue waits ($11202-$1125C), and it
      takes the slots from the CPU's own screen writes: not kept.
    - **The 64-bit fetch (done)**: FMODE 3 on AGA, the screens 6 bytes lower. `bench 300`:

      | | before | FMODE 3 |
      |---|---|---|
      | a1200-040 | 41.67 | 46.30 |
      | a1200-030 (`MMU`) | 41.55 | 47.02 |
      | a1200-fast | 26.09 | 27.83 |
      | a1200 | 14.73 (41 undrawn) | 15.86 (17 undrawn) |
      | the data disk, a1200-040 | 49.34 | 49.67 |

      `statelog` agrees with the a500's in all 300 frames, `shown` none of 80 frames, the
      data disk's race and a driven player race ran with no dump, and screenshots match the
      FMODE 0 picture (the title, the menu, both programs' races).

      Left after it (aprof): the objects' wait for the queue was still 3 ms a frame, the
      sky and ground fill (a D-only blit, which FMODE 3 hardly sped up).
    - **The ground fill by the CPU (done)**: the queue's ground entries fill planes 2 and 3
      below the ground's top line (the road spans draw the others), so the CPU fills them
      (`enh_Ground`) while the blitter runs the horizon and the sky. The queue wait fell
      from 14.1% to 2.3% of the time. `bench 300`: the a1200-040 48.23, the a1200-030
      (`MMU`) 48.54, the a1200-fast 28.20, the a1200 16.04 (13 undrawn), the data disk 49.67.
      `frames 200` (`CUSTOM3=2`) against the FMODE 3 build: every frame the same in lines
      36-174; the other checks as above. Tried and not kept, `bench 300`:
      - the CPU fills the sky too (the blitter keeps the horizon and the sky's last row,
        which the horizon's 21-word rows overlap): 47.02, 48.08, 27.62;
      - the fill behind the beam while a frame waits for the VBL (the buffer to draw into is
        on display, but a row the beam has passed is not shown again), the rest as above:
        the same 48.23 and 48.70 as without it on the a1200-040 and the a1200-030, 28.41
        against 28.20 on the a1200-fast. The frames that take 2 fields are the ones that
        hardly wait.

      Left for 50 fps: 1 frame in 25 takes 2 fields on the a1200-040; the scaler (31%) and
      the landscape (21%) are the most of a frame now.

### F. Acceptance

25. With the installed icon's tooltypes, on the a1200-040 and the a1200-060, the `bench`
    window and a real race show a swap every field. Game speed is within 1% of the chosen
    tick on every machine. The render and state checks (steps 2 and 14) pass. With the
    option off, the original code paths run. The 68000 works correctly with the option on
    and off. FS-UAE's 040/060 timing is not hardware's, so the 50 fps figure needs a real
    accelerator to confirm.
26. **Release.**
    - The installed icon gets `CUSTOM1=1` and the cache tooltype. `Vroom.inf` and
      `Vroom.colicon` ship with no tooltypes, so the packager's `tooltypes` cannot add them.
      Instead, add two `settooltype` lines to the Install script's `P_SelectIcon` block,
      beside its `Slave` and `PreLoad` (a replaced `release/Install` in `release.json`).
      That covers every icon variant, Vroom's and the data disk's.
    - The ReadMe describes CUSTOM1, CUSTOM2 and the cache tooltype.
