# Road Rash harness

## In this repository

Run every command from `games/RoadRash`. `make unpack ARCHIVES=<directory>` installs the
version 2.0 (SPS 1313) drawer in `tmp/game/RoadRash/` and keeps the installer archive in
`tmp/archives/`; `make slave` builds the release into `tmp/build/release/`, `make run` boots it
on `a1200-fast` (`WHD_ARGS=CUSTOM2=1` for Enhanced framerate, `SETUP=custom` for the 68000
A500 with 1 MB chip and 1.5 MB slow RAM, `SLAVE=original` for the shipped 2.0 slave).

The tools below are the development harness from the work's own worktree (its ignored
`tmp/dev/`), with paths rewritten for this layout: `tmp/dev/tools/` is `tools/`,
`tmp/dev/fixtures/` is `tools/fixtures/`, `tmp/dev/tmp/` is the game's `tmp/`, the slave
source is `src/` and the shipped files are `release/`. Sessions (`tools/rr.py`,
`tools/drive.py` and everything built on them) boot `common/run.sh` as their own instance,
`tmp/run/session-<OUT under tmp/>/`, with the old launcher's variables: no `SLAVE` boots the
shipped slave, `AMIGA_SETUP=''` is the custom A500 of `game.conf`, `RR_PAD=1` a CD32 pad in
port 1. `tools/build.sh` keeps its interface and writes `tmp/build/RoadRash*.slave`.
`tools/build-fsuae.sh` needs `AMIGAXDEV=<AmigaXDev checkout>`. It clones from
`$AMIGA_SHARE/fs-uae-aprof-build`, which the current shared setup no longer installs, so for
now it has to be pointed at another clone of the pinned commit. `tools/installer_g.py` and
`tools/run_installer_g.py` drove the G-phase installer test through a private copy of the old
launcher and are not ported.

The release source (the commit JOTD merged) has no VERIFY instrumentation: the VERIFY
modules (`verify*.s`) and the `VERIFY_*`/`C_*` build switches the A–F tools rely on are in
the development branch, up to the commit before "Road Rash 3.0b: optional enhanced
framerate" in this game's history. To use those tools, export that commit's `src/` into
`tmp/` and point `RR_SOURCE` at it. Normal builds of the development tip and of the release
source are not byte-identical (the release source was reduced to its configuration), so
evidence recorded against the development builds names their own slave hashes.

### Blitter-sync observer and the bike-shop route

`tools/patches/fsuae-blitsync.patch` adds a diagnostic to FS-UAE. With `BLITSYNC_LOG=FILE`
set, it logs every CPU access that isn't synchronised with a running blit. A blit stays open
from its BLTSIZE write until the CPU reads DMACONR with BBUSY clear. While it's open, the
observer logs:

- CPU access to the blit's D rows;
- CPU writes to its A/B/C rows, when the minterm uses those sources;
- CPU writes to the blitter registers (`REG`).

Each is logged once per (PC, blit, channel). `live` says whether the emulated blit was still
running and `irq` gives the interrupt mask. DMA and copper accesses aren't logged. The patch
applies to the source of the shared `$FSUAE_ARM` build: the pinned commit plus the AmigaXDev
patches listed in that build's `source-revision.txt`. Build it with that build's static
SDL2_ttf and libmpeg2 (the `configure` line in `tools/build-fsuae.sh`) and keep the binary
under `tmp/`.

`tools/blitsync.py LOG` summarises a log by blit PC and channel, with main-hunk offsets
(native base `$80000`).

`tools/shop_route.py OUT` reaches the bike shop, which only opens after a race. It builds
`OUT/shop-test.Slave` from `src/` with a test-only keyboard hook that never ships: keypad `*`
moves the player to just before the finish. It then starts a race with CUSTOM2=0, finishes it,
presses F3 on the results screen and steps through two bikes. It leaves screenshots and
traces in `OUT/run`. CUSTOM2=1 isn't supported, because the hook uses the native actor
addresses. Run the two together:

```sh
BLITSYNC_LOG=$PWD/tmp/bs.log FSUAE=<observer fs-uae> python3 tools/shop_route.py tmp/shop
python3 tools/blitsync.py tmp/bs.log
```

The rest of this document is the harness's own, from the development branch.

Current accepted baseline: [a-baseline.md](a-baseline.md). Old exploratory tools/results are
not the current baseline. Choose a fresh output directory every time. Fixtures are in
`tools/fixtures/`; all generated evidence stays under the ignored `tmp/`.

```sh
bash tools/build.sh
python3 tools/validate_a.py tmp/new-validation
bash tools/matrix.sh tmp/new-matrix --deadline 180
bash tools/matrix.sh tmp/new-normal --normal --deadline 180
python3 tools/replay_a.py tmp/new-replay --normal
python3 tools/check_a.py tmp/new-hash --hash
python3 tools/compare_a.py REFERENCE CANDIDATE --exact --out comparison.json
python3 tools/profile_a.py tmp/new-020 --kind barto
python3 tools/profile_matrix_a.py tmp/new-fast-profiles
```

Matrices deliberately return nonzero while uncached 030 remains broken; inspect matrix.json
and retained per-cell logs. They continue after a failed cell and enforce per-cell deadlines.
For A/B changes omit --exact on compare_a.py: distance ±1%, final racer order/crash count,
and identical scheduled screenshots remain gates. Different pictures require manual scene
review, never automatic acceptance. Exact mode additionally checks same binary, initial and
fixed checkpoint states, frame counts and slave hash when available. validate_a.py runs
repeat pairs and five negative controls. Comparisons must use the same cell/build mode.

build.sh produces normal, VERIFY, VERIFY_HASH_FIELD=590, and VERIFY_MMU slaves. Normal
had to remain byte-identical to the upstream build (fixtures/before-A.slave, a built slave not
kept here; build the import base commit's src/) until implementation work started.
The hash build samples inside the field hook and is for correctness only. The timing build
never hashes game state. VERIFY frame totals are cross-checked against record rotations.

VERIFY ABI (big endian, marker RRA1STAT, version 1, 320 bytes):

| Offset | Value |
|---:|---|
| 8, 12 | startup/race CACR (-1 if unsupported) |
| 16 | last race field |
| 20, 22 | first race/last completed-frame DMACONR (words) |
| 24, 28 | frame count / last completed frame field |
| 32, 36 | ABI version / size |
| 40, 44 | optional 040/060 TC / AttnFlags |
| 48, 52, 56 | requested hash field / completed field / rotate-xor state hash |
| 60 | bit 0: TC snapshot enabled |
| 64 | 64 longword frame-interval buckets; 63 includes overflow |

Startup CACR follows resload_Control: baseline has no SetCPU call. At future D1 add a
post-SetCPU snapshot. Hash input is clock plus all 35 actor records ($a5d4c..$a6edf), nearest
rider/rank cells $a7220..27 and displayed rank $a59f4. Host SHA-256 snapshots and full 15-racer
order supplement this hash. Rank is stored as raw BCD. The cop is not in racer order.

Route waits for race hook $a5916=$87040 then settles at exactly field 100. monitor fields N
advances N+1 fields from a vsync stop; screenshots advance two. Neither reading snapshots nor
applying joystick events advances a field. Tape schedules and screenshot replacements account
for this. Avoid one-field requests and debugger memory writes (this stub silently ignores
writes). Keep both host joystick mappings disabled; only monitor JOY2_* events drive the game.

Session isolates each emulator in OUT/.run and stops its own processes on exit. WARP=1,
DETERMINISTIC=1, JOY0=none, JOY1=none. FSUAE may override the pinned private binary; other
binaries must advertise required harness capabilities. Effective CPU/MMU configuration is
checked: 030 no-MMU uses 68EC030; 040/060 use NOMMU selectors. Do not use the nonexistent
68030-NOMMU alias, or combine a CPU preset with raw uae_cpu_model (shared argument deduplication
can suppress the preset). MMU checks use WHDLoad MMU, TC=$8000, uaeboard=full,
uae_cpu_data_cache=false; exclude these cells from timing conclusions.

Barto records five 99-complete-field chunks over 500 elapsed fields. Compress raw trace-*.bin
losslessly after capture and verify decompressed SHA-256 before removing originals; retain a
manifest. summary.py reads profile.pkl.gz. aprof records 500 vsyncs; profile.json exposes flat
PC execution and chip-time rankings. Avoid inclusive costs with unmatched returns, and never
interpret 040/060 emulation as measured hardware instruction cycles.

## B development

See b-correctness.md and performance-plan.md §10 for accepted B runs and limits.
Builds may be isolated with RR_BUILD_OUT=/absolute/output (default tmp/build).
VERIFY_DEFINES accepts -DVERIFY_B, -DVERIFY_SKIP_RENDER and
-DVERIFY_FRAME_PERIOD=N. These are functional diagnostic stimuli, never
release features or measured real-hardware throughput. Period N waits for
N-1 ticks before the original next-field swap. CUSTOM2 bit 1 still imposes
its two-field minimum during such a diagnostic run.

VERIFY_B adds a separate RRBSTAT1 block (96 bytes), found from the $875bc
hook: +8 gate calls, +12 closed gates, +16 drain calls, +20 maximum queue,
+24/+28 reserved, +32 sixteen longword delta bins (15 includes overflow).
RRANIM01 near the animation hook records field and phase at +8/+12.
RR_B=1 asks replay_a.py/check_a.py to capture the B block.

matrix_a.py supports RR_WHD_EXTRA (e.g. CUSTOM2=3) and RR_BUILD_DIR for MMU
variants. SLAVE selects normal/VERIFY for other cells. Use dedicated DEBUG_PORT
values when running independent checks concurrently; retain launcher failures.
CD32 tests use RR_PAD=1: register a released PLAY event during startup, before
controller detection, to enable the emulator's serial pad support.

## C dependency audit and prototype

The frame-limiter implementation was removed after clarification. Accepted new
work is the audit in simulation-timing.md and VERIFY_C_AUDIT snapshots.
Build with VERIFY_DEFINES='-DVERIFY_B -DVERIFY_C_AUDIT' (selected frame defaults40;
VERIFY_C_AUDIT_FRAME overrides it), then tools/audit_c.py on a functional fast
configuration. Snapshot range a5900..a873f. Never use this build for timing claims.
Accepted captures: c-audit-frame40 (71), c-audit-frame200 (360), c-audit-frame600
(1129). c-audit-frame1200 failed closed because only 937 calls occurred by field1800.

Scratch prototype source is tmp/c-step-source (not production); build.sh RR_SOURCE
can select it. VERIFY_C_STEP and VERIFY_FRAME_PERIOD=1/4 split core physics from
rendering, run a provisional four-field quantum and freeze state at sim field601.
It has NO historical input queue, actor-animation split, interpolation, or pause/
transition validation. Do not release or claim C complete. step_c.py captures its
snapshot and per-step actor hashes. c-step-render1/4 and c-hash-render1/4 prove the
same player position but NPC divergence starting at step6. The banner animation
8f552 advances on render and sets race-active a59d4; the latest c-start*-build
moves it to the step and returns cached sprite from the render call. Further
results are under c-start-render1/4. Four fields is experimental, not a selected
production timestep. Normal builds from this scratch source remain B-identical.
