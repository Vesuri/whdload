# Open work

## Release review

2.0b is complete: every phase of `docs/PERFORMANCE_PLAN.md` is done, and `make dist`
packages it. It was prepared as a contribution to JOTD's repository, which has not merged
it, so it is released here.

Still open before or after the release:

- The owner confirmed the post-race queued-key fix. The latest intro-music correction for
  fast CPUs ("Current 2.0b fast-CPU music fix" in the plan) still needs a listening check
  on the physical A1200 with a 40 MHz 68040; it was checked in emulation only.
- The interactive installer (`release/Install`, on the WHDLoad 20 templates) has been
  checked statically and packaged, but not run on an Amiga.
- WHDLoad 17.2 (the stated minimum), other executable versions than v1.0 and real
  68000 hardware are untested ("Open questions" in the plan).

See `docs/PERFORMANCE_PLAN.md` for the evidence and limitations of each step.
