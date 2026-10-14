# OCS candidate support and release hand-off

P13E3 is complete. This is a reviewable local candidate, not a published release.
The two candidates below reproduce the exact E1 binaries accepted by E2. No
runtime code, installer or public option changed during this hand-off. CD32 E1
and phase 12 remain paused; their release ReadMe and save/load stash are separate.

## Candidate identity

Enhancements support only the supplied English OCS SPS 1657 executable,
`data/Wing.english`, 278,304 bytes, SHA-256
`eff90d6cfbc80b008e5e508ff6488f221b6e7243958aaff6fdfd0b06e6724a30`
(WHDLoad CRC16 `00e8`). Its input archive is pinned in
[`manifest/inputs.tsv`](../manifest/inputs.tsv). The original 5,324-byte OCS slave
has SHA-256 `eec155c946e8a247e2c4811fc2279d476c330f2d1b5797cc0defb35918913913`.
The original installer's broader revision list is not enhancement support.
Other language/revision patch lists retain original behaviour; unrecognised or
changed enhancement hook sites reject before partial enhancement installation.
No German or SPS 824 enhancement or gameplay compatibility is claimed.

Both candidates are 40,352 bytes and enable the 10 Hz flight/title/asteroid
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

| Configuration or feature | Candidate policy and evidence | Limit |
|---|---|---|
| A500, 68000, OCS, 512 KiB Chip + 4 MiB true Fast | Default native blitter; PAL intro, simulator and flight checked | Coasting 9.98 world updates/s and 2.75 pictures/s; heavy scenes overload |
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

## Selection and options

Backend choice is currently a **build option**, not a WHDLoad tooltype:

- `auto` is conservative: production has no measured-clock certificate, so it
  retains native blitter conversion. `native` explicitly retains that backend.
- `cpu` selects word writes on 68000/68010 and longword writes on 68020+, only
  after the physical source bank qualifies as Fast. Exec's `MEMF_FAST` alone is
  insufficient because it can also describe slow expansion RAM. Failed checks
  or allocation retain native conversion and its Chip source/workspace.
- `--math-fast` implies `--intro`, `--prediction` and `--clock`. Omitting it is
  not a runtime switch to original behaviour: use the original reconstruction
  for a complete original control. `--changed` defaults to `off` in these exact
  E2 candidates. C6's optional two-history changed-block experiment is not part
  of this hand-off; enabling it changes the binary and adds 128,000 bytes.
- `--exit-probe` is diagnostic-only and absent from both hand-off binaries.

Original OCS tooltypes remain unchanged:

| Option | Meaning |
|---|---|
| `CUSTOM1=0` / omitted | English; the pinned revision is the enhancement target |
| `CUSTOM1=1` | Original German selection; enhancements unsupported |
| `CUSTOM2=0`, `1`, `2` | No cheats, cheat mode, cheat mode with invincibility |
| `CUSTOM3=1..13` | Original system selection; requires cheat mode |
| `CUSTOM4=0..2` | Original mission selection; requires cheat mode |
| `CUSTOM5` | No OCS enhancement/backend selector; CD32 meanings do not apply |
| `PRELOAD` | Used by the tested launcher; RAM floor includes that setup |
| Quit | Original `*` / PrtSc key (raw key `$5d`); WHDLoad's `QUITKEY` may override |

Cheat/system/mission semantics are preserved, not a claim that every combination
was played. Cache policy remains the original OCS slave's policy; this candidate
does not import CD32's public option map or promise arbitrary cache overrides.
The test environment uses the shared WHDLoad installation and user-supplied
Kickstart 1.3 image/RTB. It does not establish compatibility with every WHDLoad or
host OS version. Never include those dependencies in a game archive.

## Proposed preinstalled archive

Prepare a separate local `WingCommander_OCS_candidate.lha` under `tmp/` when
packaging is requested. It must not replace the CD32 archive or claim to be a
final version 2.0b release. Keep the tested candidate's existing embedded metadata
unchanged until release metadata is deliberately reviewed.

Proposed contents:

- `WingCommanderOCS/` with only the verified OCS archive's game data, original
  documentation/credits and OCS icon adapted to that drawer.
- `WingCommander.Slave` as the conservative default, a clearly named CPU/Fast
  alternative and original rollback slave. Separate launch icons must identify
  their slave explicitly; do not create a fictional backend CUSTOM option.
- An OCS-specific `ReadMe` with the identity, options, RAM floor, measured limits,
  fallback and rollback instructions above; preserve Psygore and Kalms credits.
- A candidate manifest with source commit, build arguments, slave hashes and
  archive hash recorded outside the archive. No test saves or personal pilot data.

Share archive creation, icon handling, checksums and round-trip verification
machinery with CD32 where practical, parameterised by variant. Keep distinct
input pins, asset trees, slave names, icons and ReadMes. The existing
[`release/ReadMe`](../release/ReadMe) is CD32-only and must not be copied as OCS
instructions. No new packager or archive is required for this proposal gate.

## Later release checklist

1. Select the release identity and intended support envelope. Keep the heavy-load
   and coverage limitations visible unless new evidence resolves them.
2. Rebuild using the [hand-off commands](development.md#p13e3-reproducible-hand-off).
   Check hashes against the candidate table; code/option changes need the
   affected native and live gates again, not an assumed carry-over of E2.
3. Review public selection/rollback UX and OCS ReadMe. If adding runtime options,
   changing metadata or combining C6 histories, validate those new binaries.
4. Stage from the verified OCS input into a new `tmp/` tree. Preserve existing
   installations and saves; never overwrite a changed game tree. Exclude CD32
   assets, ROM/OS/WHDLoad files, traces, dumps and development fixtures.
5. Create the LHa, extract to another fresh scratch tree and compare every file
   and hash. Check both launch icons select the intended slave, data and options.
6. Smoke-test the extracted archive through intro, simulator/name and quit on
   the default and explicit CPU profiles. Test save persistence after a fresh
   boot before adding that claim; user play-testing can cover longer campaign,
   devices and real hardware without relabelling the current evidence.
7. Record the final archive checksum and exact support statement. Publication is
   separate from this hand-off. Keep CD32's phase-12 save/load stash separate;
   its identifier and restore procedure remain in [open work](open-work.md#phase-12--definitive-edition-polish-and-release).

P13A1–P13E3 are complete with the documented limitations. The checklist above is
later release work, not unfinished P13E3 implementation or a new performance matrix.
