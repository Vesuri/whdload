# Legends of Valour (Amiga) — performance study

Profiling the ORIGINAL 1992 US Gold / Synthetic Dimensions game, run under CFou!'s WHDLoad install
(slave v1.0, 06.02.2005, `LegendsOfValour_v1.0_0837.lha`). No game source and **no slave source**:
work from cycle-exact FS-UAE traces and disassembly. The slave is a kickemu (Kickstart 1.3) slave;
the game is `data/AMIGA2`, a PowerPacker-crunched 17-hunk executable that `tools/unpack.py`
decrunches into `tmp/unpacked/AMIGA2`. Any change to the game is meant to ship as WHDLoad slave
patches.

## Rules

- **Never commit game, Kickstart or WHDLoad bytes**, or anything made from them: unpacked
  executables, traces, memory dumps, screenshots, input recordings, save games, built slaves. They
  live in `tmp/` (ignored).
- Addresses in docs are **`hN:OFFSET` offsets into hunk N of the decrunched AMIGA2** (the slave's
  game patches are hunk-1 offsets), `slave+OFFSET` slave code-hunk offsets, or `kick:` ROM
  addresses — never absolute addresses.
- Commits: author Vesa Halttunen <vesuri@jormas.com>, unsigned, no hooks, no Co-Authored-By lines.
  One commit per coherent feature.
- Never `pkill fs-uae` or `pkill gdb` (other projects run emulators): `fsuae_common.sh` kills only
  our own pid.
- Capture runs use `JOY0=none`: the host mouse over the window feeds port 0 and changes the game.
- No performance claim without a measurement from the right instrument (`docs/profiling.md`).

## Reference docs — read before working in the area

| Doc | Read it when |
|---|---|
| `docs/open-work.md` | **First.** What is known, what blocks a gameplay window, ordered work items |
| `docs/profiling.md` | Running the game, driving it, tracing it, or quoting any performance number |
| Test Drive 2 `docs/new-game-playbook.md` | The method this repo follows (set up from Test Drive II) |
