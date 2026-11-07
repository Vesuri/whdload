# Open work — Legends of Valour

## State

- The slave is rebuilt from CFou!'s v1.0 disassembly on WHDLoad 20.0's kick13 example
  (`src/`), with a VERIFY-only input tape and instruments. Release 2.1b (beta),
  `LegendsOfValourEnhanced-2.1b-20261107.lha`, is built from the original installer by
  `make dist` (`tools/release.py`, `docs/releasing.md`).
- Release builds have one switch, Enhanced frame rate (`C2:B`; the installed icon sets
  `CUSTOM2=1`, and any nonzero value, such as 2.0b's `CUSTOM2=64`, counts). It turns on
  every enhancement: W1–W6, the game timing, mouse precision and click inputs; `CUSTOM2=0`
  runs the original game. Developer/VERIFY builds keep a CUSTOM2 bit for each (0–8).
- W1–W6 rendering patches (`docs/performance-patches.md`). Spin route: 2.5 → 3.2 fps on the
  A500-equivalent, 12.4 → 16.1 fps on a 14 MHz 68020 (`docs/profiling.md` §9).
- Frame-independent game timing, developer bit 6 (`docs/simulation-timing.md`). One-degree
  direct mouse precision, bit 7; UI turn buttons retain native behavior
  (`docs/one-degree-turning.md`).
- Click inputs, bit 8 (`docs/click-inputs.md`): clicks act once per press (the U-turn no
  longer flips back and forth while held); walk, turn and the compass ring still repeat.
- Only the English AMIGA2 of the 0837 archive is enhanced. `_lov_version` recognises it by
  its 17 hunk sizes; any other AMIGA2 runs as CFou!'s v1.0 with CUSTOM2 cleared. German and
  French reports (05.11.2026) aborted in the W1 (German) and W2 (French) install checks
  under 2.0b; they now start, unenhanced. Checked with a VERIFY build whose size table is
  skewed (`-DVERIFY_FOREIGN_VERSION=1`): CUSTOM2 ends 0, every declared range stays
  original, and the spin route plays through.

## Open

- **German and French enhancements:** need their data. Every patch site is a fixed offset into
  the English AMIGA2, and no other version is available here. With a German or French
  `data/AMIGA2` (and its `LegendsOfValour.lha`/disk source pinned in `inputs.sha256`),
  `tools/unpack.py` decrunches it; then compare hunks with the English one, give each hook a
  per-version offset table and add the version's sizes to `_lov_version`.
- **Click inputs:** the U-turn, the movement hold and the options dialog are checked at
  runtime; the item, shop and conversation screens, combat and the save-name editor are not.
  Combat's attack buttons now act once per click; play feedback may want them to repeat.

- **Mouse precision:** accepted in play testing. The requested native-button behavior
  replaces one-degree button taps; further play feedback is welcome.
- **Game timing:** automated checks pass; subjective play feedback may still lead to changes.
  Re-run the affected comparisons in `docs/simulation-timing.md` after any change.
- **Conversation panel:** it polls through h2, so a tape `W` entry cannot wait for it and routes
  click EXIT blindly every 100 fields. A hook on its poll would make routes shorter and remove the
  risk of a window that starts inside a conversation.
