# Open work

Set up from Mr.Larmer's and CFou's v1.4 slaves (the import builds byte-identically to them).
The slaves now run with the caches on: the self-modifying code is made cache-safe on 68020+,
and the blitter queue no longer overruns on fast CPUs (`docs/internals.md`, "Fixes" and
"Self-modifying code"). Vroom's demo race renders correctly, with no WHDLoad dump, on the
a500, the a1200 with `CACHE`, the a1200-040 with `DCACHE`, and the a1200-060 with every
cache option on. The data disk reaches its title ("Insert VROOM disk then click") on the
a1200 and the a1200-060.

## Release

2.0b (23.11.2026): `$VER` and info text in both slaves, the ReadMe entry above CFou's;
`make dist` builds `VroomEnhanced-2.0b-20261123.lha` (`lha t` passes). The 2.0b slave
runs the demo race on the a1200-040 with `DCACHE`. Not published.

## The goals

1. **Correct on the a1200-040** (68040, MMU, Zorro III fast memory, instruction and data
   caches), and so on every fast machine, with the 68000 unchanged. That includes game
   speed: today a fast machine plays the game too fast (below).
2. **50 fps on capable machines** (68040 and 68060) with Enhanced framerate: the
   simulation at one fixed rate on every 68020 or better, separate from rendering.

What the measurements say ([internals.md](internals.md#frames-and-game-time)):

- The simulation takes one fixed step per rendered frame, with no elapsed-time factor. Game
  speed follows the frame rate: after 1000 fields from the green light the a1200-040
  (`CACHE`) has driven 2.7x and the a1200-060 4.2x as far as the a500. The race clock is real
  time, so lap times shrink on fast machines. On the a500 itself the speed changes with the
  scene (3-6 fields a frame at the start, 2-3 later). So simulation and rendering are not
  separated yet.
- The renderer is 89% of an a500 frame and nearly all CPU work: landscape projection and
  polygon spans, whole-line road spans and the object scaler, all writing chip memory. The
  blitter does about 20 small blits a field, each followed by a wait.
- Everything is in chip memory: code, data, tables, both screens. The a1200-040 with
  `CACHE` (instruction cache only, closest to real hardware) draws 31.8 fps at the race
  start, and the a1200-060 44.5. FS-UAE's `DCACHE` figure (39.3) comes from caching chip
  data, which no board does.

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
   - **The data disk crashes at its first demo race**, on every CPU and with CFou's v1.4
     slave too, so the bug predates these slaves. After the title's "Insert VROOM disk then
     click", the demo race loads its track archive ($F) into the small buffer at $3458. It then
     asks for the large archive $15 while that buffer is still selected, and the load runs
     over the program from $3658 on (an illegal instruction in the decruncher at $1D946, or
     a crash in the stack area on the a500). The click
     replaces the data disk's directory ($1D938, $1D950) with Vroom's, and from then on the
     slave's `Load2` loads every track from `Disk.1`. It switches disks only on the first read
     at offset $183C0 and on any read at $33614. So the data disk's own tracks are probably
     never loaded where the real game swapped disks. Next: find where the data disk's program
     asks for its own disk again and how it restores its directory, and switch `DiskNr` there.
9. **Game speed.** On a fast machine the game runs 2.7-4.2x too fast. That is fixed by step C,
   which is therefore part of goal 1, not only of 50 fps.

Then a fix-only release: B's fixes, with a ReadMe line for each.

### C. Simulation on a fixed tick (Enhanced framerate, 68020 and up)

10. **The option's plumbing.** `WHDLTAG_CUSTOM1_GET`/`CUSTOM2_GET` at install, with the
    attnflags gate. Add `ws_config` to both slaves, and make `game.conf` default to
    `CUSTOM1=1` for `make run`/`serve` unless `ENHANCED=0`, as Virus does. With CUSTOM1 off,
    or on a 68000/68010, no Enhanced framerate patch is applied. Also measure the a500's
    fields per frame over whole demo and player races on several tracks. That says how
    16.7 Hz compares with the speed a500 players knew; the a500 runs at its native rate
    either way.
11. **Split the race loop** into a tick (simulation only) and a frame (rendering only).
    Audit every state write in `$E4F8` and `$D13C`, and every read in the logic after the
    landscape call ($C96E-$CCF2) of what `$E4F8` produces (the projected road, $E254,
    $DBEE). If off-road or collision checks use the projected road, that part of the
    projection runs in the tick. Rendering must leave the simulation's state as it found it:
    compare a state hash before and after a render-only frame.
12. **The scheduler.** Each frame: from the field counter $A884, run the ticks owed at 3 or 2
    fields each (CUSTOM2), with the debt bounded (say 1 s) and dropped time counted in
    VERIFY. Then render once. The race clock
    stays as it is. Pause, the menus, the replay and the start lights rebase the tick clock
    without catch-up.
13. **Input and frame-counted timers.**
    - The VBL adds the mouse's movement into ($A2CC) every field, but the race reads the
      throttle and steering as clamped positions once a frame ($AF56), so catch-up ticks
      can read the same values. The gear shift acts on a button's release ($DC1A): a tick
      must not see one release twice or miss one. The demo's recorded controls advance one
      entry a frame ($DC26), so in the tick they advance one entry a tick.
    - Find every countdown in frames ($DC32 = 50 at $CA50, the start lights, sound triggers
      from the loop) and classify it with the playbook's timer table. Those inside the tick
      need nothing.
14. **Validation.**
    - The per-tick state sequence equals the original per-frame sequence on the a500 (step 2):
      the simulation itself is unchanged.
    - At equal fields, distance and laps agree within 1% on every 68020+ machine and render
      rate, at both speeds, including a deliberately slowed render (VERIFY).
    - The 68000 runs the original loop with CUSTOM1 on: the a500 racelog is unchanged.
    - One-shot inputs act once. With the option off, the original code runs.

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

17. **Ceiling first** (playbook §8, "Find the ceiling"). On the a1200-040 (`CACHE`) and
    a1200-060, run matched builds with an instant blitter and with single bypasses (an
    `rts` at the landscape spans, the road spans `$10CD2`, the scaler `$18154`). Add aprof
    instruction counts on `68040-NOMMU`. These tell how far each part is from one field.
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
    writes, the span filler ($10E72) and the scaler.

### F. Acceptance

23. With the installed icon's tooltypes, on the a1200-040 and the a1200-060, the `bench`
    window and a real race show a swap every field. Game speed is within 1% of the chosen
    tick on every machine. The render and state checks (steps 2 and 14) pass. With the
    option off, the original code paths run. The 68000 works correctly with the option on
    and off. FS-UAE's 040/060 timing is not hardware's, so the 50 fps figure needs a real
    accelerator to confirm.
24. **Release.**
    - The installed icon gets `CUSTOM1=1` and the cache tooltype. `Vroom.inf` and
      `Vroom.colicon` ship with no tooltypes, so the packager's `tooltypes` cannot add them.
      Instead, add two `settooltype` lines to the Install script's `P_SelectIcon` block,
      beside its `Slave` and `PreLoad` (a replaced `release/Install` in `release.json`).
      That covers every icon variant, Vroom's and the data disk's.
    - The ReadMe describes CUSTOM1, CUSTOM2 and the cache tooltype.
