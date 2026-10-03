# Test Drive II (Amiga) — performance study

Profiling the ORIGINAL 1989 Amiga game, run under JOTD's WHDLoad install (slave v1.5, `duel` v1,
108 868 bytes). No source: work from cycle-exact FS-UAE traces and disassembly. Any change to the
game is meant to ship as WHDLoad slave patches (`resload_PatchSeg` patch lists, like the slave's own).

## Rules

- **Never commit game, Kickstart or WHDLoad bytes**, traces, memory dumps or screenshots. They live
  in `tmp/` (ignored). Addresses in docs are `duel` hunk-0 offsets (the slave's patch numbering).
- Commits: author Vesa Halttunen <vesuri@jormas.com>, unsigned, no hooks, no Co-Authored-By lines.
  One commit per coherent feature.
- Never `pkill fs-uae` (other projects run emulators): `fsuae_common.sh` kills only our own pid.

## Reference docs — read before working in the area

| Doc | Read it when |
|---|---|
| `docs/open-work.md` | **First.** The goal (simulation vs rendering speed), what is known, ordered work items |
| `docs/profiling.md` | Running the game, driving it, tracing it, or quoting any performance number |
| `docs/optimisation-plan.md` | Planning or writing any speed patch; A/B-measuring a slave |
