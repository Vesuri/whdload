# Open work

Set up from Mr.Larmer's and CFou's v1.4 slaves (the import builds byte-identically to them).
The slaves now run with the caches on: the self-modifying code is made cache-safe on 68020+,
and the blitter queue no longer overruns on fast CPUs (`docs/internals.md`, "Fixes" and
"Self-modifying code"). Vroom's demo race renders correctly, with no WHDLoad dump, on the
a500, the a1200 with `CACHE`, the a1200-040 with `DCACHE`, and the a1200-060 with every
cache option on. The data disk runs its title, a player race, the scores and a second race
on the a1200-040 (`CACHE`), and its demo race on the a500. With Enhanced framerate
(`CUSTOM1=1`) the race runs on a fixed tick on a 68020 and up (step C): 16.7 Hz, or 25 Hz with
`CUSTOM2=1`.

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
  installed icon carries the cache tooltype beside `CUSTOM1=1` (step 21 picks which one).

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
    - The limit: an undrawn pass still runs the landscape and its projection, and waits
      for the VBL to take the last frame (it draws into the draw buffer, which right after
      a swap is still on screen). At 25 Hz the 68020 then draws 356 frames in 1200 fields
      (14.8 fps), below its 15.8 without the option, and fewer in the heavier parts; at
      16.7 Hz it draws 397 of 400. The plan had
      expected a catch-up tick to cost about 11% of a frame. Step 22 picks this up.

### D. Frames between ticks (Enhanced framerate, 68020 and up)

15. **Interpolation.** At the end of each tick, keep what the renderer reads: the player's
    distance $DC50, the view's angle and offset (probably $DBEC and $DBF0; step 11 settles it), and each car's
    distance and lateral position. Each frame, write interpolated copies with
    alpha = fields since the tick / fields per tick, render, then put the tick's values back.
    Wrap distances at the track length ($DBD4), take angles by the shorter way, and snap at
    the start, restarts and crashes. The demo cameras and the player's view may prepare the
    camera differently: validate in a real race, not only the demo.
16. **Pacing.** The loop already allows a frame per field ($D142) and swaps at the VBL. Check
    for tearing at 1 field a frame. If frames end up just over a field (25 fps by
    quantisation), consider a third screen: 32000 bytes of chip memory inside BaseMem,
    not yet found.

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
18. **Blitter waits.** Each small blit is followed by the original slave's wait, so on a
    fast CPU the CPU idles through every blit. The waits stay as they are without the
    option. Move each wait to before the next blitter
    access, or draw the 1-5 word blits with the CPU on 68020+. Measure both.
19. **Fast memory for data** (optional ExpMem, the patches skipped without it, as in
    BuggyBoy's 2.0b). Moves in order of CPU read share:
    - the landscape work buffers ($2F000-$32FFF);
    - the span tables ($34000-$35FFF);
    - the renderer's variables and tables ($10000-$11FFF).

    The renderer's variables sit between its code and are read PC-relative. So move the
    renderer block ($E000-$11400 or so) whole into fast memory: code and data together keep
    their PC-relative reach. Patch the absolute references into and out of it from a static
    census, and check it against every address observed in a 68000 trace. Next come the car
    table and state ($D000-$EFFF; the race loop reads them PC-relative too, so the same
    approach) and the object graphics ($49000-$58FFF, read by the scaler; first confirm
    the blitter never reads them).

    The screens, copper lists and anything the blitter reads or writes stay in chip memory.
20. **Code in fast memory.** The 68040's 4 KB instruction cache holds the inner loops but not
    a frame's code. Once step 19 has moved the renderer, measure what else (the race loop,
    the scaler) is worth moving.
21. **The icon's cache tooltype.**
    - `Cache` turns on the instruction cache and turns the data cache off for the whole
      program, so data moved to ExpMem in step 19 would run uncached.
    - `DCache` caches both. Chip memory gets marked cacheable write-through, which real
      boards refuse for data; BuggyBoy's notes say 68040/68060 boards are slower on such
      accesses.
    - Without either, WHDLoad leaves BaseMem uncached: 18.8 fps on the a1200-040, against
      31.8 with `Cache`.

    Measure `Cache` against `DCache` once step 19 is in. For real-hardware data-cache
    figures, run `CPU=68040-NOMMU`/`68060-NOMMU` (playbook §8): without an MMU model, FS-UAE
    refuses to cache chip data, as boards do. Choose
    one tooltype for the icon. The ReadMe describes both and how to remove them.
22. **Then the hot routines.** Profile again (a traced 68020 with fast memory, aprof on the
    040). Candidates: the projection's `muls` ($F672, $F680), the road spans' whole-line
    writes, the span filler ($10E72) and the scaler. Also the off-road flag ($10AAA, from
    the nearest projected line at $FA62): worked out without the projection, a pass that
    catches up could leave the projection out, which the 68020 at 25 Hz needs (step 14).
23. **Loading time.** From the boot to a race's green light (`race`, field counter $A884)
    takes 930 fields on the a1200-030 with `CACHE` and 976 on the a1200-040, about 19 s.
    With `DCACHE` it is 691 and 578, and on the a1200-030 without caches 2221. PC samples
    put most of the load in the program's streaming loader and unpacker ($1D4xx-$1D8xx,
    entry $1D798), which runs from chip memory. Its track buffers ($7C174, $3458) and its
    output are in chip memory too. The steps:
    - Profile the boot on the a1200-040 with `CACHE` with aprof, not field-boundary
      samples (those land in the VBL handler). That gives the loader's share against the
      fixed waits (the menu wipes, the start lights).
    - If the loader dominates, the slave reads each archive from the preloaded disk image
      into ExpMem. It unpacks it with its own copy of the unpacker, run from fast memory, so
      only the output goes to chip memory.
    - It is a performance change, so it sits behind `CUSTOM1`. The data disk switches disks
      in the same loader (`internals.md`, "The data disk's two disks"), so the copy must
      keep that switch.

### F. Acceptance

24. With the installed icon's tooltypes, on the a1200-040 and the a1200-060, the `bench`
    window and a real race show a swap every field. Game speed is within 1% of the chosen
    tick on every machine. The render and state checks (steps 2 and 14) pass. With the
    option off, the original code paths run. The 68000 works correctly with the option on
    and off. FS-UAE's 040/060 timing is not hardware's, so the 50 fps figure needs a real
    accelerator to confirm.
25. **Release.**
    - The installed icon gets `CUSTOM1=1` and the cache tooltype. `Vroom.inf` and
      `Vroom.colicon` ship with no tooltypes, so the packager's `tooltypes` cannot add them.
      Instead, add two `settooltype` lines to the Install script's `P_SelectIcon` block,
      beside its `Slave` and `PreLoad` (a replaced `release/Install` in `release.json`).
      That covers every icon variant, Vroom's and the data disk's.
    - The ReadMe describes CUSTOM1, CUSTOM2 and the cache tooltype.
