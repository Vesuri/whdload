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
apart), and 122. Of the plan to 50 fps on a fast CPU (steps 11-15: frames between world
passes, the chip bus's time per frame, the landscape's code for real CPUs) steps 11-13
are done: with the 68030 at 400 MHz the slave draws frames between the world's passes and
the sky and the objects' images from fast memory, 480 frames in the window against the
cap's 166, turning every one a field apart, with 15.3 ms busy a frame, 8.7 of it chip
accesses; step 14 found the rest of that chip time to be the conversion's plane writes
(5.2 ms), waits and items of 0.4 ms or less, and nothing more worth moving. Step 15's
landscape loop in the 68030's instruction cache (a 254-byte copy of its common path, the
equivalence check `tools/rr_land.py` first) took the aprof core from 130 to 140 frames, the
landscape 30.4 → 24.7 ms a frame, the setup's core from the cap's 166 to 176 (some frames
between passes there now) and 400 MHz from 480 to 485; its spans (20 ms, the instruction
cache's too) were examined and not changed (their calls batched out of the loop measured
slower, 137 frames); on the 68040 and 68060 the slave uses Kalms' 040/060 conversion
(about 0.9 ms a frame less as the emulator times those CPUs, by instruction count; no real
040 or 060 measured). The AGA plan is done; its checks in play are left (below). The ECS
plan for the A500 is done: steps 1 and 2 (the conversion and the
sky, `docs/internals.md`, "ECS improvements") took the walk from 15 to 17 frames, the mean
frame interval from 649.5 to 578.2 ms; steps 3 and 4 were examined and not done, the
landscape code being register-bound (about 1% each). On the AGA's 50 MHz 68030 the ECS
game draws 57 frames against the AGA's 122 (its data all in chip memory, its frames on the
player's runs only); of its plan to 50 fps on 68020 and up with fast memory (steps 5-11,
the A500 path apart) steps 5 and 6 are done: the tools find START in any machine's fast
memory, the ECS `profile` build counts frames, `tools/rr_passes.py` and `tools/rr_objects.py`
take the ECS game, and `tools/rr_sites.py` maps the AGA slave's patch sites to the ECS
game's (`docs/internals.md`, "The AGA's sites in the ECS game"). Both developer builds boot straight
into the game (the AGA one with detail and window at HIGH), and `tools/rr.py ingame` drives
any AGA build there through the intro and menu (`docs/development.md`). The game is on the
repository layout with CFou!'s v1.2 slave sources and the improvements; both variants build
with vasm and boot to the title screen on their default machines.

The rebuilt slaves are not byte-identical to the shipped v1.2 slaves: they carry the current
WHDLoad 20.1 KickEmu instead of the 2013 one and are assembled by vasm instead of Barfly
(`docs/development.md`, "Byte identity"). `release/slaves.sha256` records the vasm builds.

Next, in order:

1. The AGA plan's checks in play (`docs/performance.md`, "Plan", "AGA, to 50 fps"), by
   eye: step 15's frames between passes on the setup's core with step 11's (the pointer's
   picking between passes, INFERRED); steps 7-13 in other areas (other maps, shade
   tables, skies and objects) and in heavier scenes than the jungle start. The other
   areas are reached only by playing (the forest's level program in `JUNGLE.DO`'s place
   does not start). In the jungle, a 4,900-field walk with `MAPCHECK` found every copy
   equal (240 drawings, 4,419 object images given) and filled step 13's cache to 63,919
   of its 65,536 bytes (37 images) before emptying it once. The 040/060 conversion on a
   real 040 or 060.
2. The ECS plan's steps 7-11 (`docs/performance.md`, "Plan", "ECS on a fast CPU"): its
   memory and 68020 code, the AGA's steps 7-13 at the sites step 6 found, and the A500's
   own path. The game has to keep working correctly on the 68000: each
   step chosen at install and checked on the A500 as well.
3. Play-test both variants further (loading and saving) with the rebuilt slaves, against
   the shipped ones (`make run SLAVE=original`); step 10.2's swap is play-tested with the
   mouse pointer moving and the scripts drawing (inventory, messages). The AGA game's
   objects' frames are in fast memory since step 1: check that a game saved with v1.2
   loads with the new slave and the other way round.
