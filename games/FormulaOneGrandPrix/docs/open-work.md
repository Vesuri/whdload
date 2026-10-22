# Current scope

Goals: keep world simulation at real-time speed, present smooth motion up to 50 fps,
and improve performance, especially on 68020+ with fast RAM. The implementation plan
is [plan.md](plan.md); verified findings are in [internals.md](internals.md).

# Stop: B3 decision required

B1 and B2 are committed: original loader reconstruction reassembles exactly; the new
version-17 slave builds from pinned shared kick13 inputs and boots Quick Race. A1
identifies the menu RNG busy-wait feeding gameplay randomness. A5 maps copper
publication and safe buffer retirement; A6 maps interrupts/input and sound cadence.

**B3 does not pass.** In the 500-field green window, original and same-size padded
original match all 500 screenshot digests, while the rebuild matches none. The rebuild
reaches the language screen 31 fields earlier and places hunk 0/1 `$2720` lower;
padding the original does not reproduce that layout. Full evidence and limitations:
[internals: B3](internals.md#b3-acceptance-failure--decision-required).

Next: the user decides whether to continue exact compatibility/allocation/timing work
under the existing gate, or revise B3 explicitly for the newer KickEmu. Do not silently
accept the mismatch. `tools/slave_compare.py compare` reports FAIL for green and
INCOMPLETE for tow/follow. Existing captures stay in ignored `tmp/b3/`.

A2 (mode routes and call counts), A3 (optional write audit), and B4 (gating, disabled-byte
checks and developer/VERIFY targets) remain open. B5 and later steps are not authorised
by this session. No simulation or performance patches have been installed.
