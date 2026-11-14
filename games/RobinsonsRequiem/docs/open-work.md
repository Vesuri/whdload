# Open work

Both games are profiled (`docs/performance.md`: where the frame time goes walking in the
jungle, and the plan). The AGA plan is done, its step 5 measured and not kept
(`docs/internals.md`, "AGA improvements"): walking, every frame lands on the followed
object's 8 fields, the ceiling. The ECS plan is done: steps 1 and 2 (the conversion and the
sky, `docs/internals.md`, "ECS improvements") took the walk from 15 to 17 frames, the mean
frame interval from 649.5 to 578.2 ms; steps 3 and 4 were examined and not done, the
landscape code being register-bound (about 1% each). Both developer builds boot straight
into the game (the AGA one with detail and window at HIGH), and `tools/rr.py ingame` drives
any AGA build there through the intro and menu (`docs/development.md`). The game is on the
repository layout with CFou!'s v1.2 slave sources and the improvements; both variants build
with vasm and boot to the title screen on their default machines.

The rebuilt slaves are not byte-identical to the shipped v1.2 slaves: they carry the current
WHDLoad 20.1 KickEmu instead of the 2013 one and are assembled by vasm instead of Barfly
(`docs/development.md`, "Byte identity"). `release/slaves.sha256` records the vasm builds.

Next, in order:

1. The AGA game in heavier scenes than the jungle walk (more trees and objects):
   `tools/rr_passes.py` shows whether the frames keep the 8 fields. The frame pacing
   takes MAIN round twice per frame instead of three times: check that what runs on every
   pass (the period-0 objects) keeps its speed in play.
2. Play-test both variants further (loading and saving) with the rebuilt slaves, against
   the shipped ones (`make run SLAVE=original`). The AGA game's objects' frames are in fast
   memory since step 1: check that a game saved with v1.2 loads with the new slave and the
   other way round.
3. `tools/rr_prof.py` on `a1200-060` did not reach the game in 10 minutes (both slaves
   reach the flags screen there through `tools/rr.py serve`): not looked into.
4. If the ECS game is to go further: the conversion with the blitter (`docs/performance.md`,
   "Plan", after step 4), checked with `tools/rr_ecsc2pcheck.py`; patches to the landscape
   with `tools/rr_snap.py` and `tools/rr_ecsland.py`.
