# Click inputs (developer CUSTOM2 bit 8)

Read this before changing `src/clicks.s`, `src/clicks_hooks.s`, or the button paths of
`src/simulation_input.s` and `src/simulation_combat.s`.

Release builds enable it with the other enhancements (Enhanced frame rate). A click acts
once; it acts again only after every mouse button has been released. The main panel's
movement gadgets keep acting while the button that pressed them is held.

## Why

The game polls its buttons as a level, so a held button repeats its command on every poll:

- `h1:01b8c` copies the window's pointer and the buttons (`h12:05288`) into
  `$e036/$e038/$e03a(a4)` for every UI: the main panel, the modal screens (through the
  thunk `h2:063dc`), combat (`h9:00654`), the save-name editor (`h8:00842`) and the start
  screen (`h1:02044`, list `$b7c6`).
- The button hit test `h6:007da` (list, x, y; called through `h1:02b64`, `h2:06370`,
  `h8:0081e`, `h9:00636`) finds the gadget under the pointer through `h6:0076c` and returns
  its id (record `+4`) whenever bit 0 of `$e03a` is set.
- The modal screens also treat "button down, no gadget" as a click outside (`tst.w
  $e03a(a4)` after the hit test, for example `h2:0011a`). Many of them wait for release
  themselves (`h2:06388` loops), but not all.

The main panel's U-turn (id 23, dispatcher `h5:01a74` → `h5:01c4c`, heading + 180) therefore
flips the heading on every tick it is held: with the 25 Hz timing that is 90/270/90/… at 25
Hz whatever the frame rate.

## Design

- **Press events at the source.** `_click_reader` replaces the reader's final `move.w
  d0,-8134(a4)` / `rts` (`h1:01ba8`) and stores the filtered word with the same instruction,
  so callers see the same D0 and CCR. `_click_filter` passes a press once, then reports no
  buttons until all buttons are up. Any button counts, because the click-outside tests the
  whole word.
- **Hold gadgets.** `_click_hit` wraps the hit test (`h6:007da`, continuing at `h6:007e2`;
  stack overflow to `h6:008d0`). When it returns a main-panel (`-18266(a4)`, `$b8a6`) id in
  17–22, 24 or 38–61, the filter keeps passing the held button. These are turn left,
  forward, turn right, strafe left, run, strafe right, back, and the compass ring, which sets
  an absolute heading so a drag around it keeps working. The rest of the panel (U-turn 23,
  25, the second pad 26–34, the side buttons, the item slots) and every other list are
  clicks. Dragging off a movement gadget onto another gadget neither triggers it nor counts
  as a click outside: the wrapper clears the id and `$e03a`.
- **History under the 25 Hz timing.** The main tick takes its pointer and buttons from
  history at `h1:026ea` (`_sim_input_pointer`) and combat at `h9:00408`
  (`_sim_combat_pointer`); both pass their historical buttons through `_click_filter`.
  Combat's live read at `h9:00404`, which the history overwrites, skips the filter
  (`_click_skip_return`), so the filter never sees two streams. Historical samples whose
  buttons the live UI already consumed (`_sim_ui_until`, `_sim_tick_ui_cleared`) are neither
  a press nor a release.
- **Screens opened from the main tick.** Under the timing the main tick never calls the live
  reader (`h1:026ea` reads history), so every live read comes from another screen: the
  hunk 2 screens (27 calls of the thunk `h2:063dc`, among them the character screen
  `h2:0511e` at `h2:051f2`), the save-name editor (`h8:00268`) and the start screen
  (`h1:02044`). The character screen (Rank, main panel id 25, `h5:01c8a`) runs inside the
  main tick and does not suspend the timing, so history keeps recording while it is open.
  After it closed, the main tick replayed the queued sample of the press that opened it:
  the filter, re-armed by the screen's own polls, took it as a new press, and Rank under
  the pointer opened the screen again (08.11.2026 report). `_click_reader` now calls
  `_sim_input_live_read` after the filter: with the timing on, it marks the history up to
  the current field as consumed (`_sim_input_mark_ui`, as the item panel and options dialog
  do when they close) and clears the sample the current tick holds. Elapsed time and mouse
  motion are kept; only the buttons are dropped, and the filter blocks a still-held button
  until it is released.
- **Mouse look** (right button) reads `h12:05288` directly (`h5:01ea2/01ebc`), where a held
  left button walks forward. It is not filtered.
- **Layout.** VERIFY builds use up the 16-bit reach of the tag list (`_custom*`, `_hunks`)
  before the end of the slave. `clicks.s` (with the other features) only gates and loads the
  hunk addresses; `_click_patch` and the hooks are in `clicks_hooks.s`, after the VERIFY
  instruments, and are reached relatively (`lea`/`adda.l #label-anchor`).

## Invariants a change must keep

- Bit 8 off: `h1:01ba8` (6 bytes) and `h6:007da` (8 bytes) stay original
  (`PERF_RANGE ... bit=8`, `tools/check_disabled.py`).
- The reader's store and its CCR stay as in the original.
- Exactly one button stream feeds the filter at a time. Under the timing, a live read
  marks the queued history as consumed, so a screen's presses never replay in the main
  tick.
- Movement gadgets keep native repeat: `tools/turning_input_validate.sh` (with bit 8 on)
  still sees twenty five-degree ticks for a 40-field turn-right press.

## Verification

Captures as in `docs/simulation-timing.md` (VERIFY, `KEEP_SLAVE=1`, `STATE_ONLY=1`):

| Check | How | Result |
|---|---|---|
| U-turn held 40 fields | `tools/tapes/click-uturn.txt`, CUSTOM2=511, `STATE_TICKS=60`; heading and buttons per tick | both CPUs: one 270 → 90 flip, then 90 for the whole hold; with CUSTOM2=255 (68020) it alternates 90/270 every tick |
| U-turn without the timing | same tape, CUSTOM2=447, `STATE_FIELDS=80` (68020) | one flip |
| Movement hold | `tools/turning_input_check.py --hold` on the turn-button pulse (VERIFY `TIMING_STUDY VERIFY_WAIT_RESCUE`, spin route, CUSTOM5=8389121), CUSTOM2=511 | both CPUs: twenty 5° ticks, native dispatcher target |
| Character screen closed at Rank | `tools/tapes/click-character.txt`, CUSTOM2=511, A1200/68040 (`SETUP=a1200-040`); screenshot one second after the anchor | the main view; without `_sim_input_live_read` the character screen has reopened and history is stuck on the button-down sample |
| Modal screen | `tools/tapes/click-options.txt`, CUSTOM2 255 and 511 (68020); view width `h12:0002e` at the anchor | small view (80) in both: the options dialog already waits for release |
| Disabled ranges | `check_disabled.py --custom2 255` | bit-8 ranges original |

Not covered at runtime: the item, shop and conversation screens, combat clicks and the
save-name editor. Combat hit-tests the main panel list (`h9:0041c`) and acts on ids 26–28,
which are clicks now: holding one no longer repeats the attack.
