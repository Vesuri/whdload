# Formula One Grand Prix

Investigation and WHDLoad slave rebuild for the Amiga game Formula One Grand Prix.
The goal is real-time simulation independent of frame rate, smooth presentation up to
50 fps, and improved performance, especially on 68020+ with fast RAM.

The supplied four-disk installation uses Codetapper's v1.0 WHDLoad slave.
No source is available for the supplied slave; this repository contains a rebuilt
loader. The mapping (A), the rebuild (B), the real-time world clock (C), smooth
presentation between the game's updates (D), the performance work (E), F1GP-Ed
compatibility (F) and the step-dependence fixes (H) are complete. The release slave turns
them on where the machine supports them with its "Enhanced frame rate" option, which the
shipped icons set (G1); the developer build keeps each behind its own `CUSTOM2` bit. The release (G) is in
progress: `make dist` builds the 2.0b beta archive.

See [current status and next steps](docs/open-work.md) for the scope, and
[internals](docs/internals.md) for the evidence and executable structure.

- [Development setup](docs/development.md)
- [Current scope and next work](docs/open-work.md)
- [Plan: real-time speed, up to 50 fps, performance](docs/plan.md)
- [Internals](docs/internals.md)
- [Original archives](inputs.sha256), pinned by SHA-256

Original archives and extracted files live only in ignored `tmp/` (`make unpack
ARCHIVES=<directory>`). The repository contains instructions, setup helpers, filenames
and checksums, not game bytes. `make run` boots the release slave, `make dist` builds
the release archive into the repository's `dist/`.
