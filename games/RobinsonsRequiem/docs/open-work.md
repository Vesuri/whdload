# Open work

Both games are profiled (`docs/performance.md`: where the frame time goes turning in the
jungle, and the plan). The AGA plan's steps 1-9 and 10's first change are done, its step 5
measured and not kept and its step 6's pacing replaced by step 7 (`docs/internals.md`, "AGA
improvements"): the world runs on the game's own 3-field grid whatever the drawing takes,
the camera and the other moving objects are drawn between their runs (step 9 seen smooth
by eye in play with `human` walking up to the player), and each drawing starts as soon as its list has run, so the
drawing sets the frame rate (148 frames in the window on the setup's core, 101 on the
aprof core, against 55 on the player's 9 fields). Step 10.2's map and shade table in fast
memory and its swap without the beam wait took that to 166, the cap (every frame 3 fields
apart), and 122. The plan to 50 fps on a fast CPU (steps 11-15: frames between world
passes, the chip bus's time per frame, the landscape's code for real CPUs) is written, not
started: with the 68030 at 400 MHz the game is at the cap with 22.3 ms busy a frame, 13.7
of it chip accesses. The ECS plan for the A500 is done: steps 1 and 2 (the conversion and the
sky, `docs/internals.md`, "ECS improvements") took the walk from 15 to 17 frames, the mean
frame interval from 649.5 to 578.2 ms; steps 3 and 4 were examined and not done, the
landscape code being register-bound (about 1% each). On the AGA's 50 MHz 68030 the ECS
game draws 57 frames against the AGA's 122 (its data all in chip memory, its frames on the
player's runs only); its plan to 50 fps on 68020 and up with fast memory (steps 5-11, the
A500 path apart) is written, not started. Both developer builds boot straight
into the game (the AGA one with detail and window at HIGH), and `tools/rr.py ingame` drives
any AGA build there through the intro and menu (`docs/development.md`). The game is on the
repository layout with CFou!'s v1.2 slave sources and the improvements; both variants build
with vasm and boot to the title screen on their default machines.

The rebuilt slaves are not byte-identical to the shipped v1.2 slaves: they carry the current
WHDLoad 20.1 KickEmu instead of the 2013 one and are assembled by vasm instead of Barfly
(`docs/development.md`, "Byte identity"). `release/slaves.sha256` records the vasm builds.

Next, in order:

1. The AGA plan's step 11, frames between world passes, then steps 12-14, the sky's and the
   objects' chip reads and the rest of a frame's chip time (`docs/performance.md`, "Plan",
   "AGA, to 50 fps"), each measured at 400 MHz and on the setup's and the aprof cores
   (`tools/rr_prof.py`, `tools/rr_passes.py`, `tools/rr_objects.py`); step 15, the
   landscape's code, for real CPUs. Steps 7-11 also in a heavier scene than the jungle
   start (more trees and objects) and in other areas (other maps and shade tables).
2. The ECS plan's steps 5-11 (`docs/performance.md`, "Plan", "ECS on a fast CPU"): the
   tools, the AGA's sites in the ECS game, its memory and 68020 code, the AGA's steps 7-14,
   and the A500's own path.
3. Play-test both variants further (loading and saving) with the rebuilt slaves, against
   the shipped ones (`make run SLAVE=original`); step 10.2's swap is play-tested with the
   mouse pointer moving and the scripts drawing (inventory, messages). The AGA game's
   objects' frames are in fast memory since step 1: check that a game saved with v1.2
   loads with the new slave and the other way round.
4. `tools/rr_prof.py` on `a1200-060` did not reach the game in 10 minutes (both slaves
   reach the flags screen there through `tools/rr.py serve`): not looked into.
