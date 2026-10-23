# Current scope

Goals: keep world simulation at real-time speed, present smooth motion up to 50 fps,
and improve performance, especially on 68020+ with fast RAM. The implementation plan
is [plan.md](plan.md); verified findings are in [internals.md](internals.md).

# A2 and B4 complete — stop point reached

B1–B4 and A1/A2/A5/A6 are complete. A2 identifies the shared live loop for race,
practice and qualifying, the replay loop, and the one-time cockpit-return redraw.
All six drawing/pacer callers have native-route call-count evidence.

B4 has release/developer/VERIFY targets, declared options and a source-driven,
relocation-aware disabled-hook checker. Release, developer and VERIFY with all options
off preserve every declared optional hook byte. A VERIFY-only relay proves the enabled
path and the checker's rejection of changed bytes. All four fresh-boot cases pass loader
checks and real F10 exit; adversarial checks pass. See [B4 evidence](internals.md#b4-option-gates-and-disabled-byte-checks).

B3's modern-KickEmu baseline remains accepted for its pinned build; original-slave
race equivalence is not claimed. B4's changed builds have their own gating captures,
not a relabelled B3 baseline. No simulation or CPU-performance patches are enabled.
Builds, captures and rejected attempts remain in ignored `tmp/`.

Next work, requiring a new scope:

- **A3:** audit each live-loop call's writes and every renderer side effect consumed
  by simulation; required before C.
- **B5:** enable caches and validate menus/full races across the CPU matrix.
- **A8:** use developer/VERIFY gates to measure renderer ceilings.
- **A7:** complete the machine matrix; can proceed alongside the above.

The requested stop after B4 has been reached. C and later implementation remain outside
this session's scope; A4 will be needed before D's presentation snapshots.
