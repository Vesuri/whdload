# Open work — Legends of Valour

## State

- The slave is rebuilt from CFou!'s v1.0 disassembly on WHDLoad 20.0's kick13 example
  (`src/`), with a VERIFY-only input tape and instruments. Release 2.0b (beta, 08.11.2026),
  `LegendsOfValourEnhanced-2.0b-20261108.lha`, is built from the original installer by
  `make dist` (`tools/release.py`, `docs/releasing.md`).
- Release builds have one switch, Enhanced frame rate (`C2:B`; the installed icon sets
  `CUSTOM2=1`, and any nonzero value, such as the 09.10.2026 icons' `CUSTOM2=64`, counts). It turns on
  every enhancement: W1–W6, the game timing, mouse precision and click inputs; `CUSTOM2=0`
  runs the original game. Developer/VERIFY builds keep a CUSTOM2 bit for each (0–8).
- W1–W6 rendering patches (`docs/performance-patches.md`). Spin route: 2.5 → 3.2 fps on the
  A500-equivalent, 12.4 → 16.1 fps on a 14 MHz 68020 (`docs/profiling.md` §9).
- Frame-independent game timing, developer bit 6 (`docs/simulation-timing.md`). One-degree
  direct mouse precision, bit 7; UI turn buttons retain native behavior
  (`docs/one-degree-turning.md`).
- Click inputs, bit 8 (`docs/click-inputs.md`): clicks act once per press (the U-turn no
  longer flips back and forth while held); walk, turn and the compass ring still repeat.
- English (0837), German (0525) and French (1768) AMIGA2 are all enhanced by one slave
  (`docs/versions.md`). Game offsets are `hN_OFFSET` symbols (`src/offsets.s`, generated
  by `tools/versions.py`). The build appends the German and French words as a fixup table,
  and `_lov_version` applies it at boot. Any other AMIGA2 runs as CFou!'s v1.0 with CUSTOM2
  cleared. German and French reports (05.11.2026) had aborted in the W1 and W2 install
  checks. Both now boot with every hook installed and pass the C2P, wall, sprite and ray
  twins in all views.
- Blitter waits in every build (`src/blitwait.s`, `docs/performance-patches.md`): text drawn
  after a `RectFill` lost bitplanes on a 68040, in CFou!'s v1.0 as well (08.11.2026).

## Open

- **German and French play testing:** install checks, signatures and the VERIFY twins pass.
  Gameplay (timing, clicks, mouse precision) has not been played in those versions.
  Host-side analysers read English h11 offsets, so the state comparisons in
  `docs/simulation-timing.md` and `docs/click-inputs.md` have English results only.
- **Second English version:** CFou!'s v1.0 supports one more English AMIGA2. It is not
  available here and runs unenhanced. With its archive, pin it, add its sizes to
  `_lov_hunk_sizes`, a fourth language to `tools/versions.py`, `src/offsets.s` and the
  fixup table.
- **Click inputs:** the U-turn, the movement hold, the options dialog and closing the
  character screen (`click-character.txt`) are checked at runtime; the item, shop and conversation screens, combat and the save-name editor are not.
  Combat's attack buttons now act once per click; play feedback may want them to repeat.

- **Mouse precision:** accepted in play testing. The requested native-button behavior
  replaces one-degree button taps; further play feedback is welcome.
- **Game timing:** automated checks pass; subjective play feedback may still lead to changes.
  Re-run the affected comparisons in `docs/simulation-timing.md` after any change.
- **Conversation panel:** it polls through h2, so a tape `W` entry cannot wait for it and routes
  click EXIT blindly every 100 fields. A hook on its poll would make routes shorter and remove the
  risk of a window that starts inside a conversation.
