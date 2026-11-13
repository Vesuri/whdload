# Drawing rate: blitter waits and triple buffering

Current 2.0b (13.11.2026) draws faster with Enhanced framerate (`CUSTOM2`) by changing two
things: shorter blitter waits and a third screen buffer for the Road Drawer. Both are part
of the C2 patch set; with C2 off the game draws as before. Neither is tested on real
hardware yet.

## Why the drawer was slow

The Road Drawer (h4 $B84 loop, priority −1) renders into the back View, publishes it at
h4 $C0A (h3 $175E through -32106(a4): LoadView and the front/back exchange), then calls
WaitTOF before it may draw into the old front. A frame therefore lasts a whole number of
fields. On the a1200-030 machine rendering took 3.1–3.9 fields, so every frame took 4
(12.5 fps). TD2 runs at 16–17 fps in attract-mode driving on the same machine.

Stopping the emulator at random moments during the race (660 samples, ±1.8%) put 27.7% of
the time in the blitter busy-wait (root $D44) and 23.8% idle after rendering, waiting for
the next field. The game's own counters show about 435 blitter waits and 10 200 busy polls
per frame: TD1 draws its road as many small blits.

## Blitter waits

| Patch | Change |
|---|---|
| root $D5E (`PL_W 2`) | $D44 returns after two consecutive "not busy" DMACONR reads instead of ten |
| root $DB6, $E08, $F8E, $11D8 (`PL_NOP`) | the clear, fill, plane-copy and shape routines no longer wait for their last blit. Every blitter user waits before it programs the blitter |
| h4 $1D8C (`blit_plot_wait`, `render.s`) | the road walker's CPU pixel plot now waits for the blitter first, as the other CPU plot at h4 $3A3A already does |

On the a1200-030 the median rendering time per frame went from 3.64 fields to 3.15
(the shorter wait alone gives 3.26; removing trailing waits alone gives 3.49). The
frame rate stayed mostly at 4 fields per frame.

Two reads have less margin than ten on hardware that delays chip writes (some
accelerator boards).

## Triple buffering

`src/buffers.s` adds a third View (V2) so the drawer starts the next frame at once
instead of idling until the next field. The file's header describes the design in
detail; in short:

- **Chip memory.** V2, its ViewPort, RasInfo, BitMap, RastPort, copper list and five
  8000-byte planes are one `AllocMem` block of about 41 KB (`TB_SIZE`). It is allocated
  when the drawer's hold ends (the start of each race and after a pause) and freed when
  the simulation holds the drawer (pause, crash, race end). In a race the chip pool has
  about 142 KB free, about 101 KB with V2. If the allocation fails, the drawer stays
  double buffered.
- **Copper list.** The game frees its ViewPorts' intermediate copper lists after MrgCop,
  so V2 cannot be built with MakeVPort/MrgCop. `tb_copper` copies the front View's
  hardware list (sprites, the dashboard palette split) and moves the five bitplane
  pointers to V2's planes. It renews the copy each time V2 is shown, and V2 is not
  used if the list does not have the expected shape.
- **Swap** (h4 $C0A, `tb_swap`). The drawer shows the frame it just finished and then
  waits only until the View that went off the display one LoadView earlier is free.
  That View becomes the new back buffer.
- **Per-buffer renderer state.** Three renderer states assume two buffers. Each now
  keeps a third copy for V2:
  - the gear-lever redraw handshake (h4 $3AE4, `tb_lever`);
  - the cluster speed/RPM cache (h4 $4246 and its reset at $4238);
  - the steering-wheel image ring (h4 $240A, $2450).

  The buffer index at h4 $AEA (`tb_index`) is 2 for V2. A scan found no other swap pairs
  or toggles in the drawer.
- **Hold** (h4 $B88, `tb_hold`). Before acknowledging a hold, the drawer goes back to V0
  and V1. If V2 is on display, it is copied into the back View first, which is then
  shown. The rest of the game therefore sees only the original two Views. The
  simulation may release the hold before the drawer first runs, so a start stays due
  until one is tried.

### Measurements

Attract race, both slaves built from the same source, with and without the triple-buffer
patches, measured in one batch: fps in three windows per machine.

| Machine | Double buffered | Triple buffered |
|---|---|---|
| A500 | 5.4, 5.6, (0.2) | 5.8, (1.6), 5.8 |
| A1200 | 10.0, 8.2, 9.6 | 10.2, 10.6, 10.0 |
| a1200-030 | 14.2, 12.4, 12.4 | 14.0, 15.4, 12.8 |

The bracketed windows are far below the rest and probably did not measure the race; the
cause is not confirmed. Without them the A1200 goes from about 9.3 to 10.3 fps and the
a1200-030 from about 13.0 to 14.1. Two earlier 250-field windows on the a1200-030 gave
15.2 and 17.6 fps against 12.4–12.6 before the changes. The scenery of each attract race
differs, so single windows vary a lot.

### Verification

- **Frame-matched captures** (attract race, 68030, A1200, A500, each frame against the
  double-buffered frame drawn from the same simulation step). No frame shows dashboard
  content from an older buffer. The remaining differences are:
  - the radar-detector lamp;
  - the moment the route map turns into the air vents at race start;
  - 1–2 px cloud and scenery shifts.

  The same three appear between 2.0b and the blitter-wait build: the original game
  ties them to the field counter or to the number of frames drawn (render_backdrop and
  render_heading_latch carry state from the previous frame).
- **VERIFY route tape** (gears, throttle, steering) on all three machines: no state
  mismatches, and the steering-wheel image sequence is identical in both builds.
- **Crash run** (police chase, crash, penalty, recovery, stop): the police check passes.
  Recovery comes at entry 613, against 615 for the 2.0b evidence, and the 668 unit
  assertions pass.
- **Pause** returns to the two original Views and gives the chip block back. Resuming
  switches to three Views again with the picture intact.
- **Static checks:** the hook, simulation, render and audio audits pass.

NTSC and real hardware are untested. The scratch tools for this work are in the ignored
`tmp/td030/`.
