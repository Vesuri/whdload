# OCS candidate support and release hand-off

P13E3 is complete. The current public-option candidate adds the requested
**Enhanced framerate (68020+Fast RAM)** checkbox. It is not published yet; it ships
with the CD32 slave in the single combined installer archive (below). CD32 E1/phase 12
and their save/load stash remain separate.

## Current public-option candidate

Build with `--public` to generate `WingCommander.Slave`, `WingCommander.info`
and the OCS `ReadMe`. The generated icon, used for test boots (`make run`), contains
`CUSTOM5=1` and `DCACHE` (instruction/data caches); in a release the installer writes the
same tooltypes into the installed icon. Command-line launches must supply them
explicitly. Clear the checkbox, use `CUSTOM5=0`, or omit the option
for original per-frame simulation, rendering, waits and cache behaviour in the
same slave. Only the value 1 requests enhancements; other values stay original.

Regardless of the checkbox, 68000/68010 and systems without verified true Fast
RAM retain original behaviour. The gate checks Exec CPU flags and memory headers,
requiring a nonempty FAST/non-CHIP bank in Zorro II Fast space or above 16 MiB.
It rejects trapdoor slow memory even when marked MEMF_FAST. KickEmu excludes the
slave reservation from its managed memory, so `TypeOfMem(slave)` is not a valid
presence test. The off path installs only E1's four bit-exact arithmetic and
collision shortcuts, which return native results, and the two hooks that draw
the waypoint marker after the scene; no other enhancement hook occurs. A damaged
site keeps the untouched original game. See
[always-on shortcuts](internals.md#always-on-exact-e1-shortcuts-in-original-mode).
Other revisions/languages continue through Psygore's original patch lists.

The public build includes the E1 enhancements and defaults to explicit CPU
conversion. Individual source allocation still requires the converter's audited
Fast bank; failure retains the native blitter safely. This per-source fallback
is distinct from selecting original behaviour at startup. Unknown high-memory
converter placements retain native conversion; high Fast admission to timing
is not a new performance claim. Optional C6 changed-block histories stay off.

The public slave reserves 1 MiB of expansion memory: 256 KiB for Kickstart and
768 KiB for the native game pool. This adds 64 KiB of pool headroom for saved
side-cockpit images after normal campaign entry. The reservation applies in
all option modes; the off path still uses original simulation and rendering.
Legacy diagnostic builds and original reconstruction retain their old budgets.

Current build: `tmp/waypoint-always-ocs/`, 40,388-byte slave, SHA-256
`4a8c4a694713fc6560bfe571e349a0257748ce5acb06604c2355ad358cb5298f`.
See [public-option validation](internals.md#ocs-public-enhanced-framerate-toggle)
and [commands](development.md#ocs-public-enhanced-framerate-toggle).
The user-facing [OCS ReadMe](../release/ReadMe.OCS) describes the option.

## Pre-toggle acceptance baseline

Enhancements support only the supplied English OCS SPS 1657 executable,
`data/Wing.english`, 278,304 bytes, SHA-256
`eff90d6cfbc80b008e5e508ff6488f221b6e7243958aaff6fdfd0b06e6724a30`
(WHDLoad CRC16 `00e8`). Its input archive is pinned in
[`inputs.sha256`](../inputs.sha256). The original 5,324-byte OCS slave
has SHA-256 `eec155c946e8a247e2c4811fc2279d476c330f2d1b5797cc0defb35918913913`.
The original installer's broader revision list is not enhancement support.
Other language/revision patch lists retain original behaviour; unrecognised or
changed enhancement hook sites reject before partial enhancement installation.
No German or SPS 824 enhancement or gameplay compatibility is claimed.

The two pre-toggle acceptance candidates are 40,352 bytes and enable the 10 Hz flight/title/asteroid
clock, field input, bounded prediction, first-interval projectile motion, safe
publication and exact arithmetic/collision shortcuts. Music and credit deadlines
remain native. The separate Origin sequence is not retimed.

| Candidate | Build selection | SHA-256 |
|---|---|---|
| Conservative default | `--math-fast` (`--backend auto`) | `7485ed46341185afaceb87c430b129a529538cdc03dc25199a6c96729d49f424` |
| Explicit CPU/Fast | `--math-fast --backend cpu` | `ad33a2a1452e22b6a98df5701cdfff3092cdf28a468cbd3e747f7681d3dee247` |

Fresh hand-off builds are `tmp/p13e3-native/` and `tmp/p13e3-cpu/`; each contains
`WingCommander.Slave` and `build.json`. Both match E2's accepted E1 candidates
byte for byte. `build.json` describes construction; its `live_validated=false`
is not rewritten to imply a new live test. Acceptance comes from the exact hash
match and the [E2 evidence](internals.md#p13e2-compatibility-and-functional-gate).
The original reconstruction remains available as the rollback/control.

## Support and limitations

“Checked” below means the bounded emulator/native-CPU gate, not hardware certification.
The A500 enhancement measurements describe the earlier ungated experiments; the
public candidate always runs original behaviour on 68000/68010, with only the
bit-exact E1 shortcuts, waypoint marker order, TrainSim key fix and mouse hooks. E2 campaign
coverage belongs to those acceptance binaries, not a repeated full campaign on
the new public-option binary.

| Configuration or feature | Candidate policy and evidence | Limit |
|---|---|---|
| A500, 68000, OCS, 512 KiB Chip + 4 MiB true Fast | Original mode with bit-exact E1 shortcuts; native blitter. Credits 6.19 and held fire 5.59 pictures/s (control 5.79/5.39) | Ungated 10 Hz experiments: coasting 9.98 world updates/s and 2.75 pictures/s; heavy scenes overload |
| Same 68000, forced CPU | Word-write converter, Fast source; pixels/ownership checked | Slower; correctness override, not the recommended backend |
| 68020, OCS, 512 KiB Chip + 4 MiB Fast | Explicit CPU uses longword conversion; native override also checked | C2's measured 14 MHz profile favours CPU/Fast; not a universal accelerator threshold |
| Accelerated AGA 68020, 2 MiB Chip + 4 MiB Fast | Four-plane OCS output with explicit CPU, instruction cache enabled | Short model regression; no 030/040 data-cache claim |
| PAL / NTSC | 50/60-field clock handling and pixel/ownership checks pass | Not every configuration crossed with both standards |
| 68010/030/040/060 and unknown accelerators | ISA/startup-selection coverage; conservative auto policy | No OCS live gameplay or performance certification for these CPUs |
| No true Fast, slow expansion, failed source allocation | Native fallback before source movement; failure/unwind checks | Not a supported low-memory installation or proof it can boot |
| Minimum RAM | Tested launcher floor: 512 KiB Chip + 4 MiB Fast with preload | 1 MiB expansion fails reservation; 2 MiB stalls even in original game; no universal minimum inferred |
| Campaign / controls | First mission, native keyboard, all nine player cameras, weapons, autopilot, steering, afterburner, pause/resume | No full campaign/endings, physical joystick or mouse acceptance |
| Save/load / exit | Same-session native records match; save flushed; WHDLoad quit returns to DOS | Cold-boot reload remains untested |
| Intro / transitions | Full 15-page credits and repeat; simulator/name, bar, barracks, briefing and combat | Scripted cinematic branches are not all covered |
| Display integrity | Completed-image and observed DMA pixels/ownership pass | Unknown DMA words remain unverified; no new hardware visual claim |

The A500 asteroid window reaches 8.59 world updates/s and 4.19 pictures/s;
sustained fire reaches 8.99 updates/s with one new picture in four seconds.
Catch-up retains world debt and can starve drawing. This candidate does not
promise smooth 25/50 FPS or sustained 10 Hz in those workloads. See
[E1 measurements](internals.md#p13e1-focused-ocs-performance-gate) for scope and tails.

## Backend build selection and runtime options

Backend choice is currently a **build option**, not a WHDLoad tooltype:

- `auto` is conservative: production has no measured-clock certificate, so it
  retains native blitter conversion. `native` explicitly retains that backend.
- `cpu` selects word writes on 68000/68010 and longword writes on 68020+, only
  after the physical source bank qualifies as Fast. Exec's `MEMF_FAST` alone is
  insufficient because it can also describe slow expansion RAM. Failed checks
  or allocation retain native conversion and its Chip source/workspace.
- `--math-fast` implies `--intro`, `--prediction` and `--clock`. Omitting it is
  not the public option build: use `--public` for the runtime switch. The original
  reconstruction remains a separate byte-identical control. `--changed` defaults to `off` in these exact
  E2 candidates. C6's optional two-history changed-block experiment is not part
  of this hand-off; enabling it changes the binary and adds 128,000 bytes.
- `--exit-probe` is diagnostic-only and absent from both hand-off binaries.

Original OCS CUSTOM1–4 tooltypes remain unchanged; the public build adds CUSTOM5:

| Option | Meaning |
|---|---|
| `CUSTOM1=0` / omitted | English; the pinned revision is the enhancement target |
| `CUSTOM1=1` | Original German selection; enhancements unsupported |
| `CUSTOM2=0`, `1`, `2` | No cheats, cheat mode, cheat mode with invincibility |
| `CUSTOM3=1..13` | Original system selection; requires cheat mode |
| `CUSTOM4=0..2` | Original mission selection; requires cheat mode |
| `CUSTOM5=1` | Request Enhanced framerate; CPU/Fast gate still applies |
| `CUSTOM5=0` / omitted / other | Original simulation, rendering, waits and cache request; bit-exact E1 shortcuts; waypoint marker drawn over the scene |
| `PRELOAD` | Used by the tested launcher; RAM floor includes that setup |
| Quit | Original `*` / PrtSc key (raw key `$5d`); WHDLoad's `QUITKEY` may override |

Cheat/system/mission semantics are preserved, not a claim that every combination
was played. Cache policy remains the original OCS slave's policy; this candidate
does not import CD32's public option map or promise arbitrary cache overrides.
The test environment uses the shared WHDLoad installation and user-supplied
Kickstart 1.3 image/RTB. It does not establish compatibility with every WHDLoad or
host OS version. Never include those dependencies in a game archive.

## Release archive

The OCS slave ships only in the combined installer archive,
`WingCommanderEnhanced-<version>-<YYYYMMDD>.lha` (`make dist`,
[development](development.md)), as `WingCommanderECS.slave`; its Install script
writes `CUSTOM5=1` and `DCACHE` into the OCS game icon. No preinstalled archive
is made: a release never carries game data.

## Release checklist

A release is one archive holding both slaves: the installer asks for the disk (OCS/ECS)
or CD32 version and installs `WingCommanderECS.slave` or `WingCommanderCD32.slave`.

1. Select the release identity and support envelope: the version and date in both
   slaves' `$VER`, the matching `Wing Commander Enhanced <version> (<date>)` line and
   history entry in `release/ReadMe` (kept identical to `release/ReadMe.OCS`). Keep the
   heavy-load and coverage limitations visible unless new evidence resolves them.
2. Rebuild using the [hand-off commands](development.md#p13e3-reproducible-hand-off).
   Check hashes against the candidate table and `release/slaves.sha256`; code/option
   changes need the affected native and live gates again, not an assumed carry-over
   of E2.
3. Review the public checkbox/rollback UX, the ReadMe and the installer's choices: the
   disk version's icon gets `CUSTOM5=1` and `DCACHE`, the CD32 icon `CUSTOM5=0` (its
   enhanced mode) and `DCACHE`. If changing runtime options, changing metadata or
   combining C6 histories, validate those new binaries.
4. `make dist` stages the package from Psygore's verified installer archive
   (`tools/release_install.py`), packs `WingCommanderEnhanced-<version>-<YYYYMMDD>.lha`,
   extracts it again and compares every file with the staging report. It carries no
   game data, ROM/OS/WHDLoad files, traces, dumps or development fixtures, and every
   original member it does not replace stays byte-identical.
5. Smoke-test both slaves from the extracted archive with the installer's tooltypes
   through intro, simulator/name and quit on the default and explicit CPU profiles.
   Run the installer's two choices on an Amiga with the original disks and CD before
   claiming installer acceptance, and test save persistence after a fresh boot before
   adding that claim; user play-testing can cover longer campaign, devices and real
   hardware without relabelling the current evidence.
6. Record the archive checksum and exact support statement, then publish as
   `docs/releasing.md` at the repository root describes. Keep CD32's phase-12
   save/load stash separate; its identifier and restore procedure remain in
   [open work](open-work.md#phase-12--definitive-edition-polish-and-release).

P13A1–P13E3 are complete with the documented limitations. The checklist above is
release work, not unfinished P13E3 implementation or a new performance matrix.
