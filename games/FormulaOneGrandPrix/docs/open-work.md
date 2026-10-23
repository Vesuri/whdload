# Current scope

Goals: keep world simulation at real-time speed, present smooth motion up to 50 fps,
and improve performance, especially on 68020+ with fast RAM. The implementation plan
is [plan.md](plan.md); verified findings are in [internals.md](internals.md).

# Next: B4

B1–B3 and A1/A2/A5/A6 are complete. The user selected a modern-KickEmu baseline instead
of requiring the original slave's timing-dependent race. B3 explicitly checks
repeatability and loader behavior; original-slave equivalence is not claimed.

The missing original 10,000-byte filesystem I/O cache is restored. The normal build
uses unmodified shared KickEmu; local legacy-allocation experiments are rejected.
On `a1200-fast`, paired green/tow/follow windows match all 1500 screenshot digests,
routes, anchors and actual hunk bases. All captured loader checks pass. Real F10 input
returns cleanly to AmigaDOS. `python3 tools/slave_accept.py` reports PASS for the
current build. See [B3 evidence](internals.md#b3-modern-kickemu-baseline).

A2 identifies the shared live loop (race/practice/qualifying), the replay loop, and
the one-time cockpit-return draw/pacer pair. All six caller sites are documented with
native-route profile counts.

Next work:

- **B4:** add feature gating, disabled-hook byte checks and developer/VERIFY targets.
- **A3:** optional in the original session scope, required before C: audit call writes
  and drawing side effects that simulation consumes.

Stop after B4 passes under the original session scope. B5 and later implementation
remain outside that scope. No simulation or CPU-performance patches are installed.
All builds, captures and rejected experiments stay in ignored `tmp/`.
