# Open work

Powermonger Enhanced 2.0b (21.11.2026) on Wepl's v1.4.1 slave (`wepl/winstalls` at
`c12fcf04`, whose unchanged source built byte-identically to the shipped slave). CUSTOM4
(Enhanced framerate, set in the installed icons) runs the world at the A500's pace, one tick
every 13 fields, and draws as often as the machine can. With fast memory it also runs the
terrain renderer from fast memory and no longer waits for the display before drawing
([internals](internals.md#enhanced-framerate-custom4)). Without CUSTOM4 the slave is
v1.4.1. CUSTOM4 also copies only the changed screen parts to chip memory
([internals](internals.md#copy-only-changed-screen-parts)); until the first test build this
was a separate option, CUSTOM5. `make dist` builds `PowermongerEnhanced-2.0b-20261121.lha`. The release is not published.

Tested in the emulator: the game pace on four setups (12.8-13.2 fields per tick), the long
hands-off game on three setups, the frame rates in
[internals](internals.md#version-20b), the release build booting to the title. Not tested:
play with the mouse and keyboard, and real hardware.

## Before a first release

1. Play-test on the owner's A600 with a Furia (68020 at about 37 MHz, fast memory): turning
   and moving the view, giving orders, a battle, saving and loading a game, the end
   sequence. Look for stale pixels from the partial copy and for graphics that blink.
2. Play-test on a stock 68000 with CUSTOM4: busy scenes, where Enhanced framerate leaves
   out frames to keep the pace.
3. Decide the version number (2.0b now) and publish with a tag and a release archive as the
   other games (`docs/releasing.md`).

## Candidates

- If real hardware shows stale pixels, make the partial copy a separate option again.
- Measure the A500's fields per tick in views that the player turns or zooms, and in large
  battles. `TICKFIELDS` (13) comes from a hands-off game.
- Frames between ticks show the same world. Interpolating people between ticks, as Virus
  does, would make movement smoother at high frame rates.
- The keyboard camera moves faster at higher frame rates, on purpose. Scale it if play shows
  that it is too fast.
