# Open work

Set up from Harry's and StingRay's V1.01 slave. Without the version strings the build
equals the shipped slave but for the code hunk's padding word
([development.md](development.md#the-build)). It boots to the
title, landscape 0000's overview and into the landscape on the a500, the a1200, the
a1200-040 and the a1200-060, and since step 5 the 68040 and 68060 draw correctly.

## Release

2.0b (23.11.2026), not published: V1.01 with `$VER` and the info text in the slave, the
ReadMe entry above StingRay's, the self-modification fix (step 5) and the effect trigger's
wait (step 6); `make dist` builds
`SentinelEnhanced-2.0b-20261123.lha`.

## The goals

1. Correct drawing on the a1200-040 (68040, MMU, Zorro III fast memory, instruction and data
   caches), and so on every fast machine, with the 68000 unchanged.
2. Holding a pan (the pointer at the screen edge, or the ReadMe's S, D, L and comma keys; D, raw `$22`, pans right) scrolls the view
   continuously at 50 fps on capable machines (68040 and 68060), with game speed unchanged.

What is known so far is in [internals.md](internals.md#rendering-and-panning): the drawing
fault is self-modifying code in the edge scan converter, every pixel is drawn by the CPU into
chip memory, and a pan is a 128-pixel strip render followed by an 8-frame scroll-in.

## Step by step

### A. Harness (done)

`tools/sentinel.py` (the route, pans, the swap meter) and `tools/render_check.sh` (pans in all
four directions against the a500's pictures), [development.md](development.md#driving-it).

### B. Correct on the 68040 (bug fixes, always on)

4. **Self-modifying code census** (done): only the edge scan converter's five stores, over
   4085 traced a500 fields ([internals.md](internals.md#rendering-and-panning)). Not yet
   traced: the Sentinel absorbing the player, a completed landscape, the landscape code entry.
5. **Remove it** (done): `EdgeStep`, equal to the game's code under Unicorn
   (`tools/edgecheck.py`, 200000 edges, and three deliberate faults caught). The render check
   matches on the a500, a1200, a1200-030 (`MMU DCACHE`), a1200-040 (defaults, `NOCACHE`,
   `CACHE`, `DCACHE`) and a1200-060 (defaults, `DCACHE`, `BRANCHCACHE DCACHE`).
6. **Other fast-CPU hazards** found while reading, each checked and fixed if real:
   - the sound effect trigger's CPU-timed DMA-off wait (module `$F2E`, 11.3 lines on the
     68000, under one on the 040): fixed, `SfxDmaWait` waits 12 lines or more on every CPU
     ([internals.md](internals.md#sound)); the music and the player's resume are as on the
     68000. Not judged by ear: FS-UAE's audio hack did not fire for the trigger in the runs
     (its DMA-on is usually a later field).
   - blitter waits (open): StingRay's wait at `$30C` covers the start of each plane's blit, but
     nothing waits for the last plane before the swap or before the CPU next writes that
     buffer; with code in the instruction cache the 68040 is no longer held by blitter-nasty
     (`BLTPRI`) as the 68000 is;
   - CPU-timed delays: the other `dbf` and count-down loops in the program read as benign
     (none times hardware); `jmp ($10)` at `$1ED6` is never reached.
   - `movep`: 23 sites in the program (the span filler's are hot); the 68060 traps every one.
     FS-UAE's 68060 executes `movep` unless `--uae_cpu_no_unimplemented=true`; with it the
     render check matches on the a1200-060 (109 fields in pans against 104), so the trap
     works and its cost is small in emulation; real 68060 cost is not measured.
   - the data cache on chip memory: with the MMU, WHDLoad's `Cache` and `DCache` make chip
     memory cacheable write-through, so a CPU read of chip memory the blitter or a disk load
     wrote since the CPU last read it can see the old bytes (the buffer copy at `$4822` reads
     a buffer the scroll blits wrote). FS-UAE's MMU model caches chip data (real boards'
     chip memory is usually not cached); no stale read showed in the render check with
     `DCACHE` on the 030, 040 and 060.
7. **Matrix**: a500, a1200, a1200-030 with WHDLoad's `MMU`, a1200-040 and a1200-060, each
   with WHDLoad's defaults and with `NoCache`, `Cache` and `DCache` (and `ChipNoCache`, and
   `BranchCache` on the 060), and a 28 MHz 68020 with Zorro III memory (`EXTRA_ARGS`): the
   render check, title to landscape to pans to F10. Then a fix-only 2.0b: one ReadMe line
   ("drawing fixed on 68040/060 with caches").

### C. Measure before optimising

8. Game time (playbook §9): what moves the Sentinel, the sentries and the energy, and at
   what rate. The VBL handler (`$570`) runs game code (`$6D0` calls into `$2D36`); the
   field counter is `$58C6E`; CIA-A timer B is `$3900`, CIA-B timer B `$008E`. Establish
   whether faster drawing changes game speed before changing the frame loop.
9. Profiles: the A500 per-routine split is in [internals.md](internals.md#rendering-and-panning);
   repeat it on the a1200 and a 68020 with fast memory (traced), and take strip-pause fields on
   the 040/060 from `swaps`, plus aprof instruction counts on `68040-NOMMU`.

### D. Fast strip rendering (68020 and up, a `CUSTOMn` option)

10. **Fast memory.** Allocate at install (exec `AllocMem`, MEMF_PUBLIC; skip the option if it
    fails): the strip buffer, the edge tables and the span pattern tables (`$56100`, `$56800`,
    `$56C00`, `$56E60`). The strip moves first and almost for free: the scroll-in reads it
    only through `$5C848` (the column copy at `$493E`), and the filler writes it through
    `$195A`; find every other reader and writer of `$70000` first.
11. **Rewrite the edge scanner and the span filler** in the slave for the option's path,
    reading and writing fast memory, with no `movep` and no self-modification. Together
    they are 45% of the A500's pan time. Fixture: identical strip bytes to the original's for
    the recorded polygons (Unicorn), and the render check.
12. **The rest of the strip render** (projection at `$11D8`, `$6BDA`, `$17A2` and smaller):
    profile again on the 020 and decide what else moves. The program's code stays in chip
    memory (absolute addressing throughout and no relocation table); with the
    self-modification gone the 040/060 instruction cache holds it.
13. **Caches stay WHDLoad's** (decided 23.11.2026): the slave adds no cache setting of its
    own (the original's `resload_SetCACR` instruction cache stays as it is), and the game
    must work with each of WHDLoad's options (step 7).

### E. Continuous 50 fps panning (the same option)

The pipelined pan (step 15) is decided once B and D are done (23.11.2026).

14. Measure the strip pause on the a1200-040 and a1200-060 after step 11. If it is under a
    field, the original sequential loop already pans continuously; otherwise:
15. **Pipeline the pan.** Run the 8 scroll-in steps (the plane blits, the column copy, the
    swap) from the vertical-blank interrupt while the main loop renders the next strip, in the
    direction still held, into a second fast strip buffer; drop it when the pan stops or turns.
    This needs the point where the view angle (`$18C4`, `$18C6`, `$1683`) is committed, and it
    must not let game time run ahead (step 8). A strip render under 7 fields then gives a
    swap every field.
16. **Chip bus.** Drop blitter-nasty (`BLTPRI` in the `DMACON` write at `$342`) on the option's
    path so the CPU's few chip accesses are not held behind the scroll blits.
17. **Acceptance**: with a pan held for 10 s on the a1200-040 and a1200-060, the pan meter
    shows a swap every field; the render check matches the A500's; game speed is unchanged
    (step 8); with the option off the slave applies the original code paths, and the
    68000 still works correctly with it on. FS-UAE's 040/060 timing is not hardware's (about
    an instruction count), so the 50 fps figure is confirmed on a real accelerator.
