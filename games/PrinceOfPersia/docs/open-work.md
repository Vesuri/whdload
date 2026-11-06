# Prince of Persia open work

The A500 performance plan (`PERFORMANCE_PLAN.md`) is complete: phases A–C, G1 met on every
benchmark route, G2 accepted at the current room-transition performance, D1 (68040/68060),
D2 (US, German and French versions), D3 (real A1200/68040, reported by the user) and D4
(the 5.0b beta, 17.10.2026). The enhancements default on; `CUSTOM5=16` selects the original
routines. After 5.0b one fix followed: the shape-expansion fallback restores the
`move.w #-1,d0` its entry patch overwrites (the level-4 crash, 23.10.2026). It has no
write-up in `internals.md` yet, and the version string is still 5.0b.

Upstream merged this work. JOTD took the `princeofpersia` branch into jotd666/whdload_slaves
as 5.1 (bf4b0e80 "cleaned up", 9b4fb8a6 "PoP", 16.10.2026: the version renamed, his build
date in the version string, his Makefile),
then took the fallback fix (866499ac here as the last imported commit) and released the
optimisations as opt-in in 5.2 (8c35810f, 31.10.2026: `CUSTOM5` bit 4 now turns them on, and
the splash screen offers it). whdload.de has released 5.2 (24.10.2026). Those upstream commits are not imported; `UPSTREAM` is the
state this work started from (eb73c315). With upstream carrying the work, a release here
is not planned.

1. If a release is made here after all: settle the version (5.0b plus the fix, against
   upstream's 5.1/5.2), date the `$VER` string, give the ReadMe the "Enhanced" title
   (the repository's `docs/releasing.md`) and play-test on `SETUPS`. `make dist` gives
   `PrinceOfPersiaEnhanced-<version>-<date>.lha` from the installer archive.
2. Room transitions still pause (G2 was accepted, not met): `PERFORMANCE_PLAN.md` C6 has
   the remaining work.
3. NTSC and 68030 cells of the D1 matrix were outside the agreed scope and are untested.
