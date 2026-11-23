# Open work

Set up from Harry's and StingRay's V1.01 slave. Without the version strings the build
equals the shipped slave but for the code hunk's padding word
([development.md](development.md#the-build)). It boots to the
title, landscape 0000's overview and into the landscape on the a500, the a1200, the
a1200-040 and the a1200-060; the 68040 and 68060 draw wrongly.

## Release

2.0b (23.11.2026): V1.01's code with `$VER` and the info text in the slave and the ReadMe
entry above StingRay's; `make dist` builds `SentinelEnhanced-2.0b-20261123.lha`. No
improvement yet: the ReadMe entry's one line ("no changes to the game yet") is replaced by
the fixes' lines when they land. Not published.

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

4. **Self-modifying code census.** Known: the edge scan converter (`$1440`..`$17EE`) writes
   opcodes at `$1546`, `$15BE`, `$15F6`, `$1630` (`subq.w`/`addq.w #1,d1`) and a branch
   displacement at `$15C3`, from `$1516`, `$156A`, `$1598`, `$15DA` and `$161C`. Complete the
   list from a 68000 trace (every executed instruction's bytes against every CPU write in the
   same trace) over the title, the overview, a landscape, pans in all four directions,
   absorb/create/transfer, hyperspace and game over; check the sound module at `$20000` and
   the title code too.
5. **Remove it.** Replace each patched loop with fixed variants selected through a pointer
   (no cache flushes: the stores run per polygon edge, and a flush on a 68040 with copyback
   costs more than the edge). Prove equivalence on the 68000 path: run the original routine
   and the replacement under Unicorn on random and recorded edges and compare the edge tables
   at `$7B00`/`$7D00`. Done when `WHD_ARGS=NOCACHE` is no longer needed on the a1200-040
   and a1200-060 for the render check.
6. **Other fast-CPU hazards** found while reading, each checked and fixed if real:
   - the sound module's DMA-off, `dbf`, DMA-on wait (`$20110`..`$2012E`, file offset in the
     module), the CPU-timed audio wait that loses notes on 68040/060 (playbook §8); judge it
     with FS-UAE's audio workaround off;
   - blitter waits: StingRay's wait at `$30C` covers the start of each plane's blit, but
     nothing waits for the last plane before the swap or before the CPU next writes that
     buffer; with code in the instruction cache the 68040 is no longer held by blitter-nasty
     (`BLTPRI`) as the 68000 is;
   - CPU-timed delays: the `dbf`-to-self and count-down loops (playbook §8);
   - `jmp ($10)` at `$1ED6` (the illegal-instruction vector used as a pointer) under
     WHDLoad's vector handling with the MMU;
   - `movep`: 23 sites in the program (the span filler's are hot); the 68060 traps every one.
     Count them per strip on the 060 and measure the cost.
   - the data cache on chip memory: with the MMU, WHDLoad's `Cache` and `DCache` make chip
     memory cacheable write-through, so a CPU read of chip memory the blitter or a disk load
     wrote since the CPU last read it can see the old bytes (the buffer copy at `$4822` reads
     a buffer the scroll blits wrote). Find every such read and invalidate the lines first.
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
