# Current scope

Goals: improve the game's performance, especially on 68020-with-fast-RAM and faster
Amigas, and make the simulation speed independent of the frame rate.

The launcher boots the installed game to gameplay on the A500-equivalent machine.
`docs/internals.md` records the verified slave and executable structure. No profiling, slave reconstruction or patching
has started.

# Next

1. Automate the menu route to Quick Race (`docs/internals.md`) from a deterministic boot.
2. Choose the profiling window inside the Quick Race (start-line traffic with the
   player nearly stationary, the "Viewing" sequence, then the follow-car camera), a
   field-exact anchor and a frame marker; take baselines on the A500-equivalent and `a1200-fast` per AmigaXDev's
   playbook §7–§8.
3. Model how game time advances (playbook §9; AmigaXDev
   `docs/playbooks/fixed-time-simulation.md`) before any change to frame pacing.
4. Entering Quick Race without the menus needs a patch to `f1gp` through a rebuilt
   slave; no slave source is available.
