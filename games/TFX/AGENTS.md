# TFX

TFX 2.2 for Digital Image Design's TFX (the AGA install, WHDLoad kick31 slave): the newest
FPU executable (`tfx.020`) chosen automatically on FPU-equipped 68020/030/040/060, faster
rendering and fast-RAM data in it, native 68040 FPU maths in place of FPSP traps, faster
rendering in plain `TFX`, and the sort and duplicate-missile fixes. The goal is the fastest
68040 version (A1200 + Apollo 1240/40) with native 040 FPU maths, plus the palette glitches,
without regressing 020/030/060; the plan is `docs/PERFORMANCE_PLAN.md`. The original slave
is by JOTD (game.conf `AUTHOR`, `UPSTREAM`): his `T/TFX/usr` in whdload_slaves at ce5a2a25,
with the 2.0 and 2.1 rendering work its ReadMe credits. Upstream merged this work
(0cf43ac9, merge 1635ba0e) but has not released it.

The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | upstream's status, where the work stands, open items, harness reference, pitfalls |
| `docs/development.md` | inputs, builds, runs, the harness and each step's tools, what was not imported |
| `docs/PERFORMANCE_PLAN.md` | the plan: steps 1-14, the 20 fps action plan and the executable comparison, with each outcome |
| `docs/executables.md` | the TFX executables and which the slave runs |
| `docs/replay-flight.md`, `docs/frame-counter.md`, `docs/baseline-matrix.md` | the reproducible flight, the frame counter and the baseline fps matrix |
| `docs/profile-040.md`, `docs/symbol-map.md` | the 040 profile and the symbol and patch-site map |
| `docs/correctness-fixes.md`, `docs/chip-placement.md`, `docs/native-fpu.md`, `docs/rendering-port.md`, `docs/tuning-040.md` | steps 7-11: fixes, chip placement, native FPU maths, the 040 renderer, tuning |
| `docs/palette-investigation.md` | the open palette glitch |
| `docs/selection-regression.md`, `docs/executable-comparison.md` | executable selection and its regression coverage |
| `docs/optimization-20fps.md`, `docs/profile-20fps.md` | the 20 fps work and its profiles |
| `docs/open-work-history.md` | older handoffs and the full progress log |

The slave source is `src/` (`TFXHD.s` and its includes; `code040.s`/`code060.s` build the
FPSPs); `tools/` is the development harness and never ships (`tools/tfx.py` is the
gdb-stub server). `TFXHD.s` has CRLF line endings: edit it as bytes. `release/` holds the
installer package's files; `make dist` repacks the original installer archive with the
slave, ReadMe and source.

Commit hashes in `docs/` are those of the fork branch this history was imported from
(Vesuri/jotd_whdload_slaves, branch `tfx`); the commit messages here are the same.
