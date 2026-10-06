# Open work

State of the setup against the playbook's "ready to improve" list (§12), and what comes next.
Read `docs/profiling.md` for how each item was measured.

## Done (2026-10-06/07)

- Repo, rules (`CLAUDE.md`), `tmp/` ignored; game, Kickstart, WHDLoad bytes and captures local only.
- Game, version, slave type and the slave's patches documented (profiling.md §1). The slave
  had no source: reconstructed byte-identically (`whdload/original/`).
- A WHDLoad 20 KickEmu slave (`whdload/Battlehawks1942.s`) with the same machine and the same
  game patch, plus a VERIFY build with an input tape that reaches the first training flight.
  It boots and flies; it has **not** been compared with v1.0 beyond that (see 2).
- `bh_report.py` names every hot region; traces have PCs.
- Fixed window: first 100 fields of the first training flight, anchored on the first c2p pass.
- Frame counter: c2p passes (one displayed buffer, delta c2p). `frames.py` done;
  `swap_fields.py` written, not validated.
- Baseline on the A500-equivalent: 9.6 fps, c2p 16 % self, CPU-only renderer, CPU never idle.

## Not done yet, in order

1. **Reproducibility, last step.** Two fresh captures: PCs, cycle costs and screenshots
   identical in all 100 fields; registers/DMA differ, traced to JOY0DAT reading `$0000` vs
   `$0101` at boot (profiling.md §7). Find where FS-UAE gets that value with `JOY0=none`
   (host mouse over the window? power-on counter state?) or neutralise it in the VERIFY build,
   then re-run `compare_traces.py` until it prints `identical`. Check whether BH reads the
   mouse (it uses an input.device handler).
2. **KickEmu slave vs v1.0.** Same fixed window, game state compared (BH data hunk). v1.0
   needs its own tape timing (the reconstruction can take `tape.s` back if needed). Also decide
   whether the normal (non-VERIFY) KickEmu build replaces v1.0 for players.
3. **68020 / fast-RAM baseline** (playbook §8): `AMIGA_MODEL=A1200 ... CPU=68EC020 FAST_KB=4096`
   with `fixed_window.sh` (BH still lands in chip: the slave gives no fast RAM; only the
   Kickstart and the slave move). Then `SWAP_ONLY=1` on a 68030 to find the ceiling, and
   validate `swap_fields.py` against a full trace on the same window.
4. **Game-time model** (playbook §9) — nothing measured yet. Leads:
   - no `VPOSR`/`VHPOSR`/CIA reads in BH hunk 0; the per-frame `timer.device` `SendIO`s seen
     in the trace are the Kickstart's own (input.device's timer events), not BH's;
   - BH's level-3 handler `bh:1ac26` runs every VBL (sound); check whether it or anything
     else counts fields that the simulation reads;
   - the frame time varies 4–6 fields: if the simulation steps once per frame, game speed
     depends on CPU speed (Galahad's ReadMe: "the game is too fast" with fast RAM — a strong
     hint that it does);
   - `rand()` at `bh:1adb6`: find what seeds it (`bh:1adea`).
   Then the state map (plane position/attitude/speed, drones), `state_*` tools adapted from
   TD2/I500, and the coupling test (68000 vs 68020 vs slowed drawing).
5. **CUSTOM gating** for the first patch, declared in `slv_config`, with a disabled-bytes
   checker (TD2's `check_disabled.py`).

## Candidates (no claims until measured in the fixed window)

- The delta c2p (`bh:1a2c2`): 16 % self on the A500; its compare loop alone is 13 %. A
  faster compare/convert, or skipping unchanged spans in bigger steps.
- The fill at `bh:16114..` (5–8 %), probably the chunky-buffer clear.
- Tearing: the c2p writes the visible bitplanes with no beam sync; a double-buffered display
  would need chip RAM the 512 KB machine may not have.

## Decision for the user (after item 4)

As in TD2: whether a faster renderer may speed up the game, or game time must first be
decoupled from the frame rate.
