# Internals

Offsets are code-hunk offsets in `AlienBreed3D.slave` (the source's `Lxxxx` labels);
game addresses are offsets into the relocated game executable.

## How it loads

A direct slave (WHDLoad 18, 68020 and AGA required): 576 KB chip (428 KB without
music) and $158000 bytes of ExpMem.

- Stacks: SSP at ExpMem+$157e00, USP 1 KB below.
- Caches (`resload_SetCPU`): instruction and data cache on; on a 68040/060 also copyback for
  ExpMem and the slave, the store buffer, branch cache and superscalar dispatch; base
  memory stays non-cacheable.
- Interrupts: level 2 (keyboard, quit key, the game's key callback), level 3 (VBL reads
  the joypad, holding Reverse+Forward+Play 1 s quits; the game's VBL callback), level 5,
  level 6 (CIA-B timer for the end part's HackAB3D music; not in the no-music slave).
- `team` (the Team 17 picture) is shown from chip $40000 for 4 s.
- Exec and dos are 2048 words of ILLEGAL each, at the start of ExpMem, with only what
  the game calls: exec AllocMem/FreeMem on the slave's own allocator (`_allocmem`,
  `_freemem`; a chip pool after the loaded executable, a fast pool in ExpMem), and
  Forbid, Permit, SuperState, UserState as RTS; dos Open (the name is the handle), Read
  (loads the whole file with `resload_LoadFileDecrunch`, dropping a 5-character volume
  prefix), ExamineFH (`resload_GetFileSizeDec`), Close and Delay as RTS. ExpMem then
  starts $2000 further on.
- Without NOMUSIC, `HackAB3D` is loaded when present, relocated, patched (`_pl_hack`) and
  initialised; the game follows 12 KB after it.
- The executable: `abd8ch` with CUSTOM3=1, else `abd.pk`, else `abd`, else `abd8ch`.
  `resload_LoadFileDecrunch`, then its CRC16 picks the patch list: $23d2 `_pl_v1`,
  $fd78 `_pl_v2`, $c4dc `_pl_v3` (another CRC aborts with TDREASON_WRONGVER). It is
  relocated (`resload_Relocate`, chip hunks into the chip pool, 8-byte alignment,
  LoadSeg layout), `prefs` is loaded, the list applied with `resload_PatchSeg`, and the
  game started with `jmp 8(a6)`.

## Slave patches

Each version's list (game offsets differ; `_pl_v1` shown): CUSTOM1 bit 0 unlimited
energy, bit 1 unlimited shots, bit 2 F1 skips the level (`PL_IFC1X`); CUSTOM2 mouse
button layouts (`_p_control`); the game's VBL and keyboard handlers taken as callbacks
(`_p_setvblcb`, `_p_setkeycb`); copper and beam access through the slave (`_p_setcop2`,
`_p_vhposr`, `_waitvbl`, `_p_waitlines`); the joypad read through the slave
(`_p_readjoyport`); two bounds checks that skip the game's code on an out-of-range read
(`_p_boundsread`: an index outside 0-511; `_p_boundsl13`: an address past
ExpMem+$153000, the level 13 access fault fixed in 1.3); `prefs` saved by
`resload_SaveFile` (`_p_saveprefs`); the end part's scroll replaced by the slave's
(`_endpart`: a copper list of its own, scrolled until a button, then quit); music on and off around the end part (`_p_musicon`,
`_p_musicoff`, not in the no-music slave). Item by item: the `PL_` lists in the source.

## Display

The 3D view is drawn at 2x2 pixels (the original's renderer).
