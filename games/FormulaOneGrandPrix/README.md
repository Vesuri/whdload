# F1GP

Investigation and WHDLoad slave rebuild for the Amiga game Formula One Grand Prix.
The goal is real-time simulation independent of frame rate, smooth presentation up to
50 fps, and improved performance, especially on 68020+ with fast RAM.

The supplied four-disk installation uses Codetapper's v1.0 WHDLoad slave.
No source is available for the supplied slave; this repository contains a rebuilt
loader. B1–B4 and A1/A2/A3/A5/A6 are complete. B5 cache validation is blocked by an
unsuccessful 68040 startup check; A7 measurements are incomplete and A8 has not started.
All 68030 validation is deferred. The cache policy is opt-in and disabled by default;
real-time simulation and extrapolation are not implemented yet.

See [current status and next steps](docs/open-work.md) for the blocker and scope, and
[internals](docs/internals.md) for the evidence and executable structure.

- [Development setup](docs/development.md)
- [Current scope and next work](docs/open-work.md)
- [Plan: real-time speed, up to 50 fps, performance](docs/plan.md)
- [Internals](docs/internals.md)
- [Input provenance](manifest/inputs.json)

Original archives and extracted files live only in ignored `tmp/`. The repository
contains instructions, setup helpers, filenames and checksums, not game bytes.
