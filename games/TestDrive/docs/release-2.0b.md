# Current release: 2.0b (13.10.2026)

All post-JOTD 1.4 work is one release. ReadMe has a concise, player-facing
2.0b history entry. The 1.5b–1.8b names in earlier phase reports identify
unpublished development snapshots, not separate releases. Preserve their
binaries and evidence, including the deferred hardware overlay A/B pair.

## Templates and installation

ReadMe and Install are based on the installed WHDLoad 20.0
`Install Template/Xxx Install` examples. Template hashes are pinned in
`manifest/release-2.0b-templates.json`. ReadMe retains the A500 Kickstart
requirements, quit key, icons, instructions, original authors/thanks and JOTD
history, expressed as user-visible changes. The optional enhancement and PAL
beta limitations are explicit.

Install retains the standard template helper bodies and its file-copy mode.
Test Drive adaptations set the directory, data subdirectory, documentation,
icon suffixes and labels; the file-copy branch requests TEST DRIVE and copies
Cars, Pics, Songs, DEVS, C, S, Sfx, HighScores and cars.txt, then the supplied TD.
It rejects a missing DEVS/system-configuration. Only WHDLoad is required up front;
unused DIC/RawDIC/Patcher checks were removed. Install.info retains its original
APPNAME=Test Drive; the script explicitly uses TestDrive as its filename prefix.
The optional local high-score filename is HighScores, not an empty string:
Installer treats an empty source as the current drawer.

## Validation and packages

Current 2.0b includes the main-view road-jump correction described in
`road-shift.md`, analogue rev-counter limit described in `rpm-needle.md`,
the steering-reversal visual correction described in `steer-reversal.md`, and
the bend-response/close-traffic corrections in `handling-collision.md`, and
the curve/bank near-plane correction in `corner-jump.md`, and the opening-audio
repeat correction in `audio-repeat.md`. The cornering fix
passes the native geometry and A1200/68040 CACHE smoke checks; its measured
A500 cost exception to the former 3% sample gate is recorded explicitly there.
The bend correction also changes rate-dependent curvature rounding; other fixes
change display code, apart from the separately verified audio interrupt fix. The earlier version-only equivalence
report applies only to the preserved pre-fix 2.0b baseline. The full phase-11
regression remains evidence for unchanged simulation/features, complemented by
the targeted road-fix regression and 68040 smoke checks. The fixed release date
is in ReadMe; the reproducible build omits build dates.

`make dist` packages the release with the shared packager (`release/release.json`):
the original installer archive with the release slave, `release/readme`,
`release/Install`, `release/TestDrive.inf` and the source the release build was assembled
from, checked for exact membership, unchanged members, LHa integrity and extraction.
It replaces the harness's own packager (`tools/package_release.py`, which also wrote the
local preinstalled archive and a portable source Makefile to `tmp/dist/2.0b/`); the
installer members both share are byte-identical. The packaged source no longer carries
`Makefile_windows.mak` (the repository builds the slave), `BUILDING.txt`, the generated
lvo bridges or the VERIFY-only `simulation-verify.s`.

`tools/test_release_installer.py` uses actual Installer 43.3 in disposable
emulated Amiga drawers, with deterministic requester answers. This covers
script flow and file/icon operations, not interactive requester behaviour.
Its inputs are pinned in `manifest/release-2.0b-installer.json`. The disk fixture
uses the verified preinstalled data with authored C/S directory fixtures,
since the preinstalled archive omits the original disk's C/S contents.
No host accessibility or input automation is used. Diagnostic runs are retained
under separately named directories; only `installer-tests/report.json` is the
final report. All six cases pass: fresh Normal, GlowIcon 1, GlowIcon 2,
existing-drawer Skip, existing-drawer Delete, and missing required file.
Destinations contain spaces; copied data and documents, icon options, sibling
files and the existing-drawer marker are checked. OS 3.1 icon.library resets
positions, rewrites pointers and drops newer icon extensions as the standard
template saves icons; classic document-icon content is verified. A first fixture exceeded AmigaOS's 30-character name limit;
the accepted destination `Install with spaces` stays within that limit.

Real A1200/68040 testing remains deferred and NTSC unvalidated. Archives remain
local; branch testdrive is pushed and upstream PR #28 is open. The preinstalled package contains game
data and must not be published.

Current normal slave SHA-256:
`a598677ddfccb693bc9ab8586983336820078c1dfad45fd6e51abd7e3edb5fef`.
It includes the audio fix and unreachable-code cleanup (`dead-code.md`).
The previous cornering-only release and package stage are preserved as
`tmp/dist/2.0b-before-audio-fix` and `tmp/release-2.0b/package-before-audio-fix`.

## PR review state

Documentation cleanup is committed as `ec72d8a`; dead-code cleanup is
`e3c38ac`. The ReadMe contains one
2.0b (13.10.2026) entry covering user-visible changes only; it distinguishes
the optional framerate mode from fixes that apply with either setting.
The WHDLoad 20 template-based Install is unchanged. Source header/plan notes
and Windows makefile line endings are cleaned up; the full branch diff passes
`git diff --check`. All branch commits use the required personal identity.
Hooks and signing are disabled. The working tree is clean; testdrive is pushed to the Vesuri fork.
Upstream PR: https://github.com/jotd666/whdload_slaves/pull/28 (open, targeting
master, head e3c38ac). The description discloses AI assistance with extensive
human steering and the beta validation limits.

The documentation-only cleanup rebuilt byte-identically to the audio-tested
release. The current dead-code cleanup changes layout but passes fresh native
checks recorded in `dead-code.md`.
The current combined patch audit covers 88 ranges and passes; the focused audio audit
also passes. Refreshed archives pass integrity, independent extraction,
exact membership/payload checks and byte-identical packaged-source rebuilds.
`tmp/dist/2.0b/manifest.json` contains current archive hashes. Pre-review packages
are preserved as `tmp/dist/2.0b-before-pr-cleanup` and
`tmp/release-2.0b/package-before-pr-cleanup`. The documentation-only changes required no emulator regression; the subsequent
dead-code cleanup passed the fresh checks in `dead-code.md`.

PR disclosure: real A1200/68040 results are deferred, NTSC is unvalidated,
and the intermittent steering-dot report is unconfirmed (`wheel-dot.md`).
The user confirms the opening sample-repeat fix on the cached a1200-040 release.
Phase 12 knowledge transfer remains separate open work. No runtime-buffer
allocation change is included in this release cleanup.
