# Current scope

Goals: improve the game's performance, especially on 68020-with-fast-RAM and faster
Amigas, and make the simulation speed independent of the frame rate.

The launcher boots the installed game, and `tools/f1gp.py quickrace` drives it from
boot to the first field of a Quick Race at Silverstone. `docs/internals.md` records the
verified slave and executable structure. No profiling, slave reconstruction or patching
has started.

# Next

1. Choose the profiling window inside the Quick Race (start-line traffic with the
   player nearly stationary, the "Viewing" sequence, then the follow-car camera), a
   field-exact anchor in place of the route's 25-field screen polling, and a frame
   marker; take baselines on the A500-equivalent and `a1200-fast` per AmigaXDev's
   playbook §7–§8.
2. Model how game time advances (playbook §9; AmigaXDev
   `docs/playbooks/fixed-time-simulation.md`) before any change to frame pacing.
3. Entering Quick Race without the menus needs a patch to `f1gp` through a rebuilt
   slave; no slave source is available. The scripted route makes it optional.
