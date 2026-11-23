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

### A. Harness (first; no slave change)

1. **Benchmark window.** The first demo race from the green light is the same race on every
   machine (the simulation is per frame and deterministic). `tools/vroom.py racelog`
   already logs it per field. Add `bench N`: the fields taken for frames 0-N after the green
   light. That gives one fps figure per machine, comparable before and after each change.
2. **Per-step state log.** The equivalence check for step C: at every frame (later: every
   tick) record the car table ($DC4E, 64 bytes per car), $DC50, $DBEC and $DBF0 (the view's
   angle and lateral offset, still to be confirmed) and the race clock. Sampling at field boundaries mixes up frames on fast machines, so this needs an
   exact point: a breakpoint at $12FA6 on the 68000/68020 (slow, but exact), or a
   VERIFY-only slave log read at the end (gdb cannot write memory).
3. **A real race through the menus** with `monitor mouse`/`monitor input`: right button on
   the title, the menu with the left button, a race with steering and throttle held. This is
   needed for steps 6, 7 and 13, and for gameplay checks the demo cannot give. The race
   controls are not yet mapped.
4. **Machine matrix script**: a500, a1200, a1200 with fast memory, a1200-030 (WHDLoad
   `MMU`), a1200-040 (`CACHE`, then `DCACHE` for the functional run), a1200-060, one boot at
   a time with a deadline. It reports `bench`, dumps and a screenshot per cell.

### B. Correct on the 68040 (bug fixes, always on)

5. **SNOOP run.** `SNOOPAGA CHKBLTWAIT` with `DCACHE` on the a1200-040 for several demo
   races and a player race. Fix every hit, as with the drive-motor and blitter-queue fixes.
6. **CPU-timed waits** (playbook §8):
   - the sound player ($9432) for audio DMA off, `dbf`, DMA on, which loses notes on a
     68040/060 (judge with FS-UAE's audio workaround off);
   - the keyboard interrupt ($A04A) for its handshake delay;
   - `dbf`-to-self and countdown loops in the program and the loader.

   Replace each with a beam-timed wait of its a500 length.
7. **The flickering roadside objects.** Reproduce on the a500 and the a1200-040 (screenshots
   at consecutive swaps in a real race). Candidates: the object list ($D23A onwards) built
   for the wrong buffer, the scaler's slot state across frames, and a missing blitter wait
   before a swap. Fix for every CPU.
8. **Untested paths**: the second race start, which reloads part of the program to $439C
   (`SMC_Decrunched`), the data disk's tracks, and the end of a race and the highscore save.
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
    - The VBL adds the mouse deltas into ($A2CC) every field. Decide how catch-up ticks
      share them; steering must not depend on the frame rate.
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
    distance $DC50, the view's angle and offset ($DBEC, $DBF0, step 2), and each car's
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
