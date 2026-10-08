# Open work

The goal: game time (car motion, opponents, clock, sound) independent of the CPU, with
rendering as fast and as smooth as the machine allows, shipped as WHDLoad slave patches for
`duel` v1. Slave 1.6b (an unreleased beta of 1.6) does this behind "Enhanced framerate"
(`CUSTOM2`). How it works: [simulation-design.md](simulation-design.md),
[subunit-rendering.md](subunit-rendering.md); the game itself: [game.md](game.md).

## Working rules

- **No claim without a measurement from the right instrument.** Frame rates only from
  `tools/fixed_window.sh`, two fresh boots per arm; game speed only from state captures,
  never screenshots. See [testing.md](testing.md).
- **Every change is a slave patch** behind `CUSTOM2`, duel v1 only, with the original bytes
  kept when it is off (`check_disabled.py`). Rendering changes must stay within the 3% A500
  sub-unit budget or bring a measured frame-rate gain.
- Do not touch JOTD's `set_copper` beam wait without testing a 68020/68030 configuration for
  tearing.

## Open

1. **NTSC.** Everything is validated on PAL. The step period counts fields and the race clock
   assumes 50 fields per second, so on NTSC physics and clock would run 20% fast. Needs a
   VPOSR/display-mode check and NTSC-scaled clock quanta, then the state checks on an NTSC
   machine.
2. **Natural police chase.** The police counters are unit-tested and the police car has its
   own latched render position, but a chase in ordinary play has never been captured.
3. **A4000/68060 black screen.** A user reports that both JOTD's original slave and 1.6b stop
   at a black screen on an A4000/68060. Emulated 68060 configurations (A1200 ROM and chipset,
   with and without MMU) reach the race, so this is not reproduced. Waiting for the
   accelerator, ROM, WHDLoad version and MMU configuration. Then: find whether it stops before
   KickEmu, before LoadSeg, in the intro or on race entry; compare both slaves there; capture
   the stopped PC, stack and cache/MMU state; patch the demonstrated cause. Only a hardware
   test confirms a fix.
4. **duel v2.** Its patch list is JOTD's v1.5 one; porting the patches needs a v2 `duel` to
   find the offsets.

## Dropped (user decisions; do not propose again unless reopened)

- **A500 frame rate**: 7.1 fps is accepted. The remaining CPU-loop candidates (span store
  pairing, projection caching, early DMA clear) each recover under 1% of a frame.
- **Beyond 25 fps**: the only plausible route, a fast-RAM back buffer with every blitter user
  replaced and the viewport copied to chip (68030+), is dropped for now.
- **Smoother car and object sizes**: the sprites are pre-drawn at fixed sizes; per-frame
  scaling is not viable and load-time in-between sizes cost chip RAM and appearance.

## Tooling debts (fix when they bite)

- `td2_report.py` names self time by the nearest preceding `link a5` or call target, so a
  function without `link` merges into its predecessor.
- Traces hold no fast-RAM snapshot, so the scripts dump the code region separately; a trace is
  ~5.4 MB per field and `monitor profile` stops at 100 fields.
- The lldb profiler-window fix is tied to this FS-UAE binary's addresses.
- The fixed-window calibration cache ignores `WHDLOAD_BINARY`.
