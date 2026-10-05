# Open work — Legends of Valour

Status 2026-10-05: playbook §1–§5 done, §6 started. See `docs/profiling.md` for everything measured.

## Done

- Repo, rules, harness copied from Test Drive II (`lov.py`, `barto.py`, `lov_report.py`).
- Slave decoded without source (`tools/slave_info.py`): kickemu 1.3, `_bootdos`, stub and
  protection patches (`docs/profiling.md` §1).
- `AMIGA2` decrunched offline (`tools/unpack.py`); 17-hunk layout known.
- Boots on the A500-equivalent machine; traces carry PCs; `lov_report.py` names all 17 hunks, the
  Kickstart and the live slave.

## Blocking: how to reach a reproducible gameplay window

There is no attract demo. Gameplay is behind a mouse click (load button → slot → in game), and a
representative profile probably needs the player to move. **The user chooses:**

1. **FS-UAE input recording** (`RECORD=` in run.sh): the user records the clicks and some walking;
   playback replays them deterministically. Cheap to try, untested end to end (TD2 §7), and the
   recording is tied to the exact machine and slave.
2. **A VERIFY-only slave tape**: rebuild the slave from disassembly (needed for §10 anyway, as
   there is no source), hook the game's mouse/keyboard read and feed it a fixed script. Most robust,
   most work.
3. **Anchor without input**: a VERIFY slave calls the game's own load-slot routine at boot, then
   traces the first in-game frames standing still. Only useful if the game redraws while idle.

**Prior art (surveyed 2026-10-05).** None of the user's other projects injects input at the FS-UAE
level: no recordings, no Lua, and gdb writes are dropped. All of them script input *inside* the
emulated machine. Vette and Alone in the Dark override the mouse in their VBI with absolute
positions and button phases. Revs answers the game's own polls from an `AutoStep{key, polls,
hits, until}` table and counts polls, not time. Each step can also wait on a game-state byte.
Stunt Car Racer reads memory back through WHDLoad `COREDUMP`/`TIMEOUT`. For this game that points
to option 2 placed at `h12:0643e`/`h12:06480` (`docs/profiling.md` §5). Write absolute pointer
positions into `h11:008d2/008d4` and button bits into `h12:05292`, and advance on the field
counter `h11:0602c` or on game state.

Also needed: a save game to load. The archive's data has `16SAVE.lbm`, but which file a slot reads
is not known yet. Saves written during a run are lost (DH1 is recreated); run.sh needs a way to keep
them in `tmp/`.

## Next, in order

1. Decide the driving method (above); keep a save game under `tmp/`.
2. Find the frame marker (COP1LC / BPLxPT writes, `LoadView`/`ScrollVPort`, or a double-buffer
   flip, probably in h12) and the VBL handler; adapt `frames.py` / `swap_fields.py`.
3. Find an anchor (the first in-game 3D frame after loading) and adapt `fixed_window.sh`;
   prove two boots give identical fields (§6). Remove entropy (VHPOSR reads in h12, CIA, mouse).
4. Baseline on the A500-eq. and a 68020 (§8); game-time model (§9); rebuilt slave (§10).
