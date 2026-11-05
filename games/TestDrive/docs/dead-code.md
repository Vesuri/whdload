# Dead-code cleanup

The tracked source no longer contains the four obsolete enhanced visual-RNG
read hooks at h4:$1EEE/$1F00/$1F10/$1F76 or their sim_visual_* mask helpers.
The sim_windscreen_draw and sim_windscreen_draw_next hooks unconditionally
bypass those native spawning/aging blocks whenever C2 installs the removed
hooks. sim_visual_step owns the active updates. A conservative direct-branch
scan finds no external entries into the skipped ranges. C2-off VERIFY RNG
hooks remain reachable and are retained, as are all active fixtures and the
zero-size renderer boundary symbols used by local profiling tools.

Also removed: unreferenced read_fire2, the unreachable _doio seek check,
get_version's unreferenced alternate-version branch, and unused tag/custom1
storage. These are inherited leftovers, not active experimental modes.

Validation in tmp/dead-code/audit.json and checks.json: 88 patch ranges pass;
all four removed sites retain original instructions in all three captured
build/mode combinations. Native VERIFY assertions: 668 simulation/input and
1421 renderer, all pass. Cached 68040 normal C2=0, normal C2=1 and VERIFY C2=1
reach driving and return to AmigaDOS on native quit. Screenshots inspected.
Normal slave is 12772 bytes (116 fewer); VERIFY is 26036 bytes (120 fewer).
Both refreshed archives pass independent extraction and byte-identical
packaged-source rebuilds. No user-visible changelog entry is warranted.

Raw .bin captures from these three checks are removed after checking; compact
results, copied slaves/listings, effective machine configs and screenshots
remain. Prior release packages are preserved with before-dead-code-cleanup.
