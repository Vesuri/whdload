# Battlehawks 1942 (Amiga) — performance study

Profiling the ORIGINAL 1989/1990 Lucasfilm Games flight game (PAL v1.0), run under Galahad's
WHDLoad install (slave v1.0, 12/05/03, Retroplay pack `tmp/Battlehawks1942_v1.0_0053.lha`).
No game source and no slave source: Galahad's slave is reconstructed in
`whdload/original/Battlehawks1942.s` (rebuilds byte-identically, `make -C whdload original`).
The slave we build and patch is `whdload/Battlehawks1942.s` (WHDLoad 20 KickEmu, 512 KB chip
+ 512 KB fast memory). Work from cycle-exact FS-UAE traces and disassembly. Any change to the
game is meant to ship as WHDLoad slave patches. Goal: frame-rate-independent gameplay, 50 fps
on faster Amigas.

## Rules

- **Never commit game, Kickstart or WHDLoad bytes**, or anything made from them: disk images,
  extracted files, traces, memory dumps, screenshots, input recordings, built slaves. They live
  in `tmp/` (ignored).
- Addresses in docs are **`bh:` hunk-0 offsets of the game executable `BH`** (on `Disk.1`),
  `bh-data:` data-hunk offsets, `kick:` ROM addresses (`$FC0000`-based), or `slave:` offsets
  (the `Lxxx` labels) — never absolute addresses.
- Commits: author Vesa Halttunen <vesuri@jormas.com>, unsigned, no hooks, no Co-Authored-By lines.
  One commit per coherent feature.
- Never `pkill fs-uae` or `pkill gdb` (other projects run emulators): `fsuae_common.sh` kills only
  our own pid.
- No performance claim without a measurement from the right instrument (`docs/profiling.md`).
- Instruments (the input tape, experiments, anything that changes behaviour for measurement)
  go in the `VERIFY` build only. Game patches for players go behind an option.
- Only what DMA needs belongs in chip RAM; everything else in public memory (fast when there
  is any). BH already allocates that way; keep it so in any patch.
- Never edit a script while a capture is running it (bash reads scripts as it goes).

## Reference docs — read before working in the area

| Doc | Read it when |
|---|---|
| `docs/open-work.md` | **First.** What is known, what is not, ordered work items |
| `docs/profiling.md` | Running the game, driving it, tracing it, or quoting any performance number |
| `docs/c2p.md` | Touching the chunky-to-planar pass |
| `Test Drive 2'sdocs/new-game-playbook.md` | The method this repo follows |
