# Current scope

Goals: improve the game's performance, especially on 68020-with-fast-RAM and faster
Amigas, and make the simulation speed independent of the frame rate.

The launcher boots the installed game, `tools/f1gp.py quickrace` drives it from boot to
the first field of a Quick Race at Silverstone, and `tools/race_profile.py` profiles
three 10-second phases of that race. `docs/internals.md` records the
verified slave and executable structure. No slave reconstruction or patching has started.

# Next

1. Baselines exist for `a1200-fast` (`docs/internals.md`): the game is held to about
   8 fps by its frame pacer. Next: the same windows on the A500-equivalent and the rest
   of the playbook §8 machine matrix (the leads need recalibrating per machine), and a
   game-state anchor in place of screen signatures.
2. Game time is frame-locked at a nominal 1/8 s per frame (`docs/internals.md`). Next:
   find the simulation step and the in-game race clock in the code, verify the step
   size directly, and plan decoupling it from rendering (AmigaXDev
   `docs/playbooks/fixed-time-simulation.md`); measure the 68030/040/060 presets.
3. Entering Quick Race without the menus needs a patch to `f1gp` through a rebuilt
   slave; no slave source is available. The scripted route makes it optional.
