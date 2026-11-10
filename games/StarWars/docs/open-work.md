# Open work

No improvement work has been done yet. The game is set up on the repository layout:
`src/StarWars_WHD.s` is StingRay's v2.00 source with three build fixes
(`development.md`), it builds, boots the Retroplay SPS 0403 install to the attract screen
on `a500-1.5m` and `a1200`, and `release/slaves.sha256` records that build. It is not
byte-identical to StingRay's shipped slave because the shared WHDLoad 20.1 `kick13.s` is
newer than the one he assembled against (`development.md`, "Build").

1. Choose what to improve (the playbook's survey): the frame-rate cap the timing fix sets
   (three frames per update, `internals.md`, "Game time") is the obvious candidate.
2. Before a release: a `$VER` string in the slave (`docs/releasing.md`; `make dist` needs
   it), the new ReadMe entry above StingRay's, gameplay tests on `SETUPS`.
3. Only SPS 0403 is pinned and tested. The slave also accepts SPS 2926; the ReadMe's third
   version (SPS 939) has no entry of its own in the version table, so it is presumably
   byte-identical in the checked range to one of the two. Testing either needs its
   installed archive pinned in `inputs.sha256`.
