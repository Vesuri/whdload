# Optional simulation timing: source and acceptance audit

The runtime option is CUSTOM2 bit 6, “25 Hz simulation”. It is independent of
W1–W6 and the bit-7 one-degree renderer. PAL world ticks consume two fields;
combat retains the native four-field minimum cadence. This feature changes
world progression on machines that previously ran below the original movement
compensation range. It also adds CPU work between rendered frames.

## Source invariants checked

- `_sim_install` returns before validation/writes when bit 6 is off or CUSTOM1
  selects character creation. All installs follow opcode/relocation checks.
  The hunk table supplies every game continuation; no capture address is embedded.
- `_sim_loop` consumes active fields in two-field increments. Overdue ticks run
  player, actor, clock and projectile logic, skipping the separate drawing,
  sprite and display calls. Modal redraw callers do not advance the world again.
- `_sim_vbl` keeps the saved native game clock and a separate active-field count.
  Native pause and private suspension gates stop accumulation. Clock readers
  subtract pending active fields, preserving native rest/load time jumps.
  Day-boundary events wait until their logical tick is due.
- The native frame cap, display clock dispatch and beam wait remain unpatched.
  The old frame-time compensation table changes only when timing is enabled.
- Relative mouse motion uses cumulative VBL positions, consumed once per tick.
  Entry to mouse look clears the current delta as the native code did. UI return
  suppresses already-consumed historical buttons while retaining active time.
- The keyboard collector owns the one native console request in task context.
  VBL only samples memory/signals fixtures; it never submits device IO. FIFO
  records are published after initialization. Full queues retain the completed
  byte and wait for space before resubmitting. Gameplay uses historical cutoffs,
  while blocking/UI readers consume immediately; combat has a separate cutoff.
- Shutdown cancels/waits for pending IO, restores the port owner, removes the
  worker before freeing its memory, then continues the native console close.
- Combat drawing thunks alone are gated. Native attack scripts, RNG, damage and
  sound retain order. Combat pointer samples use the independently advancing
  VBL counter while the native caller pauses world time.
- Branch-dependent hook results branch inside the adapters; clock readers use
  address arithmetic where the original instructions preserved X. The replaced
  VBL game-clock ADD is followed by native MOVE/SUB instructions that overwrite
  the relevant flags. Installers flush the instruction cache.
- Input history is finite. A request older than retained history explicitly
  rebases and counts recovery, discarding unrecoverable input/time. Ordinary
  validation requires zero recoveries. This is not unbounded stall recovery.

## Build boundary

Normal and ordinary VERIFY builds remain byte-identical to the integrated
candidate after adding the native text/mode test fixtures. Normal code is
64,144 bytes, SHA256
`2a0346511cd50d70cdf2e73fd4c5528c68d7ff37a71fb2e9a5ae86bda691b3fa`.
Both build with 68000 instructions and PIC checks. Normal builds exclude the
tape, drawing delays, state observers and input-device test tasks.

Historical `SIM_KEYBOARD_EXPERIMENT` and `SIM_COMBAT_EXPERIMENT` names now default
to inclusion; bit 6 gates their runtime installation. `SIM_FIRE_EXPERIMENT`
remains off: the unexercised private cosmetic-RNG experiment is not enabled by
this feature. Shared sprite phases, actor animation and texture cadence use the
accepted timing correction described in `timing-investigation.md`.

## Acceptance evidence

Detailed hashes, fixtures, route limits and reproduction commands are in
`timing-investigation.md`. The completed both-CPU spin A/B and split catch-up
costs are in profiling §8. The A500 loses rendering throughput to the additional
world ticks; this is explicitly reported, not hidden by averaging catch-up calls
with rendered frames. All four spin captures retain original cap/beam code and
all disabled-option instruction ranges.

Native save-name editing now passes on both CPUs, with real console input,
backspace/Return, balanced suspension and continued world ticks. All eight repeated input-mode/W1 off/on captures now pass on both CPUs,
with four transitions, negative heading wrap, no motion leakage and identical
logical state within every normal/delayed pair. Each run consumes exactly
240 logical fields over 120 ticks, with all wall-time differences accounted
for as pending debt. Maximum observed debt is 27 PAL fields under deliberate
drawing delay. The replacement stationary-wall matrix now completes on both CPUs and is
recorded in profiling §8. Equal-field captures additionally quantify live
world-state differences during blocked/in-progress ticks, with initial clock
epoch offsets reported explicitly. They complement the complete-tick
comparisons rather than replacing their determinism gate.

## Normal interactive trial

The verified normal slave is launched in `tmp/playtest-simulation-final`, using
68020 at 28,375,160 Hz, 2 MB chip/8 MB fast, PAL, warp off, normal blitter timing
(`immediate_blits=false`, `waiting_blits=false`) and CUSTOM2=255. Its installed
slave hash matches the normal hash above. There is no VERIFY tape or debugger.
The emulator process and its on-screen window are confirmed. Native window
capture was unavailable, so no screenshot of this normal trial is claimed.
The preceding private trial had exited; no emulator in amiga/.run was touched.

The timing feature ships entirely as optional slave patches. Automated
acceptance gates are complete; subsequent subjective gameplay feedback may
motivate refinements. Game, ROM, WHDLoad and generated bytes remain in tmp/.
