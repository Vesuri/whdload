# Plan

Goal: faster on every supported machine, rendering up to 50 fps, world and game logic at
their native speed. Steps are in order of value to the player; take the first one not done
whose dependencies are met. Design and decisions: [open work](open-work.md). Rules:
`AGENTS.md`.

## How to work

- **One option per feature.** Each behaviour change is a `Custom1` bit (then `Custom2`) in
  `whdload/Mercenary3.slave.asm`, listed in `_config`. With every option off the slave runs
  the shipped code. Debug aids go in the `VERIFY` build.
- **Build** with `make original slave verify` before each commit.
- **Measure** with `tools/fps.py` on `a1200-fast` and `a500-1.5m`: the same build with the
  option off and on, same session. Keep a change only if it gains 2% or more somewhere and
  loses nowhere. Run `tools/matrix.sh` only where a step says so. The 040/060 cells give
  emulator counts that don't follow the CPU frequency; use them only to check that the game
  runs there.
- **Check the game still works** with three tests, not more:
  1. **Options off:** the performance slave gives the shipped slave's frame count in the
     same session on `a500-1.5m`.
  2. **World speed:** `tools/sim_speed.py` shows the native walking and turning rates per
     field (6 units, 2 heading units).
  3. **Play:** play the route, and the screens the step touches, and look at the
     screenshots.

  Build heavier checks (lockstep runs, pixel twins, static audits) only to chase a fault
  these show.
- **Done** means the step's check passes, the result is a short entry in `internals.md`,
  and the box below is ticked. Commit each step on its own.
- **(U)** marks a decision for the user: ask, record it under Decisions in `open-work.md`.

Addresses: code as `Disk.1` offsets, variables as chip addresses (a chip code address `A`
is `Disk.1` `A + $3CB0`).

## Steps

### O. Settle the existing options

**O1. Options 0–2** (one-time DMA enable; FMODE 3 on AGA; stack in expansion memory).
- Play through the screens the route doesn't reach: the map, a vehicle, a flight, game over
  and restart, save and load. Look for display faults.
- For FMODE 3, if a screen shows its own copper list, check whether it sets the fetch
  window (`$0092`/`$0094`); patch it or turn FMODE off while it shows.
- Make `ws_ExpMem` optional (a negative size) and fall back to the chip stack without it.
- Check: play; options-off test.

### L. Native world speed on fast machines

**L1. Logic gating** (new bit). At the main loop head (`Disk.1` `$5DF92`, a 6-byte `jsr`),
in walking mode (chip `$7122` = 1): if fewer than 4 fields have passed since the last pass,
wait for the next field; otherwise run the pass with the true elapsed count in chip
`$52954`. The world can no longer run fast above 12.5 fps; nothing changes below it.
- Check: world speed on `a1200-fast` and the fastest cell; play.

### P. Smooth frames between logic passes

**P1. Presentation frames with the player extrapolated** (needs L1). Where L1 would wait,
draw a frame instead:
1. save the restore set;
2. put the extrapolated player pose in chip `$7142..$7161`: committed pose + per-tick rate
   × fields since the last pass, with the rate taken from the last pass's pose change;
3. run the camera derivation (`$5D844`) and view setup (`$5E0BA`, `$5DA50`, `$5A91E`,
   `$469C4`);
4. publish (`$5E458`), clear (`$5E840`), draw (`$5410E`, `$593A6`, `$5AFAA`, `$577BE`);
5. restore.

The restore set is what the write audit lists for those calls ([internals](internals.md#renderer-inputs-and-writes)):
the render scratch at chip `$0340..$4000`, the drawing's variables, the object-table areas
and the self-modified code words. Leave the display state alone: copper list pointers
`$72B2`/`$72B6`, `$42C00`/`$42C01` and the copper lists. Keep `$7180` counting logic passes
(blinking).

Never run the collision test in a presentation frame. Snap to the committed pose after a
collision (`$6F56`), a mode change or a stop.

- A `VERIFY` check hashes chip `$5350..$68000` before step 1 and after step 5, and reports
  any changed address outside the display state. This is the one check that the game logic
  is untouched.
- Check: the hash check holds over the route; world speed; play, and look for smooth turning
  in per-frame screenshots. Measure the frame rate on `a1200-fast` and with `matrix.sh`.

**P2. Other objects interpolated** (needs P1).
- Find where moving objects keep their position and orientation (start from the object
  tables at chip `$AF36..`/`$B31E..` and what the drawing reads).
- Keep the previous pass's poses. In a presentation frame, draw objects between the last two
  passes, then restore. Snap new or vanished objects and jumps.
- Check: the P1 hash check; play near moving objects.

**P3. Other movement modes** (needs P1).
- The vehicle, flight and lift paths (`Disk.1` `$5E214`, `$5E3CA`) move a step per frame,
  so they run fast on fast machines today. Gating them restores native speed **(U)**.
- For each agreed mode, apply L1 and P1. Leave the rest native.
- Check: world speed in that mode; play.

### M. Code and data in fast RAM (68020+ with fast RAM)

**M1. Hot code in fast RAM** (new bit).
- Find the routines behind the instruction-fetch misses (`bus_audit.py` page counts:
  `Disk.1` `$4EDB0..$4EFAF` and `$5B5B0..$5B9AF` lead; 18.5 KB covers 95%).
- At boot, copy them to expansion memory, put a `jmp` to the copy at each entry, fix
  PC-relative references that leave a copied routine, and flush the caches.
- Handle self-modifying code: the drawing writes code words at chip `$459BA`, `$4F700..` and
  `$4F9C2..`. The slave's 68040 path already turns four such sites into indirect calls
  through chip `$C0..$CC`; use that variant, or point the writers at the copies.
- Only on a 68020 or later with real fast RAM; otherwise the original code.
- Check: play; options-off test; measure on `a1200-fast`, then `matrix.sh`.

**M2. Hot read-only data** used by the moved code, if `bus_audit.py` still shows chip reads
worth 2% or more. Same checks.

### R. Faster drawing

**R1. Renderer inner loops.** Profile the drawing routines on `a1200-fast` and `a500-1.5m`.
Rewrite the loops worth 3% or more, one at a time, per CPU class (68000: long and `movem`
stores; 68020+: cache-sized loops). Compare screenshots with the option off and on; build
a pixel twin only if they differ. Keep each rewrite only where it gains.

**R2. Blitter back-buffer clear** (new bit). Clear the 3D view with the blitter instead of
the CPU (`$5E840`). Wait for the blitter before the first drawing. Measure per CPU class.

**R3. Triple buffering (U).** It removes the publication's wait for the next field (7–10%
on `a1200-fast`). It needs 32 KB of chip RAM beyond the 512 KB BaseMem, which drops 512 KB
chip machines.

**R4. Data cache on 68030+ (U).** Measure the slave requesting the data cache as well, then
ask.

### X. Release

**X1.** Propose one player-facing toggle and its default **(U)**. Update the ReadMe
(requirements, options). Run `matrix.sh`, a play pass with the release options on each
CPU class, and the options-off test.

## Status

- [ ] O1
- [ ] L1
- [ ] P1 [ ] P2 [ ] P3
- [ ] M1 [ ] M2
- [ ] R1 [ ] R2 [ ] R3 [ ] R4
- [ ] X1

P1 and M1 are independent; after L1 they can run side by side.

## In place

- Byte-exact reconstruction of the shipped slave (`make original`); the performance slave
  with `Custom1` bits 0–2.
- `route_profile.py` (instruction profile, or `MODE=counter` untraced), `fps.py`,
  `matrix.sh`, `sim_speed.py`, `state_trace.py` (per-pass state, `--compare`),
  `write_audit.py`, `bus_audit.py`.
- The game-time model and the renderer's inputs and writes ([internals](internals.md)).
