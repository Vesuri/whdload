# Stellar 7: current work

The profiling setup is being established. No optimization has been enabled and
no gameplay performance figure has been measured yet.

1. Complete original-slave first boot and inspect menu/demo behavior.
2. Rebuild the original game-specific loader using WHDLoad 20.0 KickEmu.
3. Establish deterministic gameplay input and a state-based capture anchor.
4. Validate a frame marker against both trace and breakpoint counts.
5. Measure A500-equivalent and 68020 baselines in the same window.
6. Map game time, state and coupling before selecting an optimization design.

See `development.md` for local reproduction and `internals.md` for verified facts.
