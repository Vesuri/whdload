# Internals

## Slave

Codetapper's v1.0 (06.12.2002), 5464 bytes, no source. Header (slave offsets):

| Field | Value |
|---|---|
| `ws_Version` | 15 |
| `ws_Flags` | `$3402`: NoError, EmulPriv, ClearMem, Examine |
| `ws_BaseMemSize` | `$80000` (512 KB chip) |
| `ws_ExpMem` | `$C0000` (768 KB, includes the 256 KB Kickstart 1.3 image) |
| `ws_GameLoader` / `ws_CurrentDir` | `$170` / `data` |
| `ws_keyexit` | `$59` (F10) |

It is a KickEmu-style OS slave on Kickstart 1.3 (`kick34005.A500` + `.RTB`). The loader at
`$174`: creates the `F1GP_Disk_#1..4` assigns, sets preferences (fast pointer), turns the
audio filter off, then

1. unless `CUSTOM1` is set or fire is held, `LoadSeg`s and runs `frontend`, which is only
   the credits intro ending at "Click to Load Main Program";
2. `LoadSeg`s `f1gp`, accepts file sizes 582992, 582988 or 582780 (one patch list each,
   at `$2A6`, `$2DC`, `$312`), `resload_PatchSeg`s it, patches the built-in driver names
   (`$3D6`), and runs it with an empty argument line; on return, quits.

### B1: reconstruction and patch lists

`tools/slave_inputs.py` verifies `manifest/game-inputs.json`, generates symbolic assembly
for the loader and helpers in `tmp/slave/original.s`, and extracts the compressed driver
names into `tmp/slave/names.rnc`. The generated source reassembles byte-for-byte to the
original 5428-byte code hunk (5464-byte HUNK executable including its wrapper). The
previous `tmp/re/slave.bin` also included the final four-byte HUNK_END marker; it is not
part of the loaded slave.

Loader code is at slave `$170–2A5`, `$358–3A3`, `$3B6–423`; strings/header, patch lists
and the names payload are data. The old KickEmu starts at `$6EC` and extends through
the trailing workspace at `$1533`. Its entry receives resload in A0; the game-specific
DOS entry is `$174`. The generated reconstruction keeps old KickEmu as literal local
bytes, separate from the symbolic loader. B2 replaces that section with shared kick13
source; this is a behavioural rebuild, not a byte-identical KickEmu rebuild.

`PatchSeg` offsets below are cumulative **allocated hunk sizes**, including BSS, not
file offsets. For the supplied 582992-byte game, hunk 2 begins at cumulative `$6F394`.
Every list contains these six operations:

| Operation | 582992 (`$2A6`) | 582988 (`$2DC`) | 582780 (`$312`) | Replacement / purpose |
|---|---:|---:|---:|---|
| long | `$982` | `$982` | `$978` | `$22116000`: load expected protection answer and branch unconditionally |
| long | `$345C4` | `$345D8` | `$345CE` | two NOPs: remove the second protection failure branch |
| subroutine | `$6F840` | `$6F856` | `$6F84A` | slave `$3B6`: decode keyboard byte and abort on F10 |
| byte | `$A79CE` | `$A79C6` | `$A791E` | `$FF`: save-directory state flag |
| long | `$A7A42` | `$A7A3A` | `$A7992` | first four characters of `saves` |
| word | `$A7A46` | `$A7A3E` | `$A7996` | final character plus terminator |

For the supplied version, the original ranges are h0+$982 (CMP.L (A1),D1 and
BEQ opcode), h0+$345C4 (BNE.W), h2+$4AC (ROR.B then EORI.B keyboard decode),
h2+$3863A (zero byte) and h2+$386AE (the six-byte `DF0:` buffer). The keyboard
replacement replays both displaced instructions before comparing the decoded key with
`ws_keyexit`; it preserves the decoder result on return. The other two game variants
are accepted by the original loader but are not supplied here: their replacement lists
are decoded; their original bytes and hunk-relative mappings remain unverified.

The driver-names routine at slave `$3D6` obtains a relocated pointer from h0+$91A
(or +$910 for 582780), adds `$900`, and checks for the eight-character prefix
`Carlos S`. Only on that match it calls `resload_Decrunch` on the RNC1 payload at
slave `$424–6EA`: 693 compressed bytes plus an 18-byte header, 1480 unpacked bytes.
Otherwise names remain unchanged. The compressed bytes are extracted locally, never
committed. The names restore is unconditional with respect to CUSTOM1; CUSTOM1 only
skips `frontend`. The loader also tests both fire-button bits, tolerates a missing
frontend, runs with an empty argument line, unloads each segment and quits on return.


### B2: shared-KickEmu loader

`whdload/F1GP.s` builds with slave version 17 (developer and VERIFY builds 20, for E2–E4's
alternative memory configuration) and the pinned shared kick13 source.
It retains the original memory requirements, assigns, frontend/fire/CUSTOM1 decision,
three size-selected patch lists, conditional names restore, empty argument line and
F10 quit hook. The default path retains the old CPU mask and installs no performance
changes; the later B5 pilot adds an opt-in cache policy. DOS BSTR assign names are
explicitly longword-aligned.
The shared kit is consumed in place, rather than copying WHDLoad source into this repo.

B2/B3 baseline build checks: bash 3.2, ordinary and spaced output directories produced identical
6100-byte executables with `IOCACHE = 10000`. A deterministic `a1200-fast` Quick Race boots successfully:
language 807, protection 1184, startup 1413, track 1608, race 2115 fields. The existing
original route begins at language 838 and has identical subsequent intervals (all
screens 31 fields later). B3 validates repeatability of this modern-KickEmu baseline below.

### B3: modern-KickEmu baseline

The user selected a new baseline with the shared modern KickEmu. Exact original-slave
screenshot matching is no longer the gate: game randomness depends on menu execution
and allocation, so those screenshots cannot independently distinguish loader bugs
from legitimate KickEmu changes. B3 now requires paired deterministic captures of all
three windows, captured-memory loader checks and clean F10 quit. This is a deliberate
change to the plan, not a claim that the original comparison passed.

The allocation investigation identified a missing configuration setting: the old
slave's filesystem code uses a 10,000-byte I/O cache (read path at slave +$10C6,
write path +$117C, free path +$13D4). Defining `IOCACHE = 10000` in the rebuild restores
that setting. It is a filesystem cache, unrelated to the CPU caches deferred to B5.

| Deterministic `a1200-fast` check | Original | Rebuild without I/O cache | Modern rebuild with I/O cache |
|---|---:|---:|---:|
| Slave file bytes | 5464 | 5684 | 6100 |
| Language field | 838 | 807 | 807 |
| First race field | 2146 | 2115 | 2115 |
| Green anchor, fields after race entry | 857 | 826 | 778 |
| Hunk 0/1 placement relative to original | unchanged | `$2720` lower | `$28` higher |
| Hunk 2/3 placement relative to original | unchanged | unchanged | unchanged |

The same-size padded original reproduced all 500 original green screenshots and its
actual layout; it never reproduced the rebuilt layout. Restoring the I/O cache moves
both fast hunks by `$2748`. A diagnostic reducing the modern DOS environment table
from 16 entries to the original 11 moved them back by `$18`, leaving `$10` difference.
Also removing the device name caused a "Can't find disk" requester before the language
screen. These local adaptations are rejected: the normal build uses unmodified shared
KickEmu. The remaining allocation difference is not itself a defect.

The 31-field language difference is one polling interval, not a precise measurement
of loading duration. All later route intervals agree. Restoring I/O caching does not
change that route difference. The old slave explicitly invokes `resload_LoadKick`;
the modern version-17 header lets WHDLoad load Kickstart before entering the slave.
Modern KickEmu also changes early CPU setup and OS patches. Those are remaining boot
path differences, not isolated causes of the measured route difference. No artificial
startup delay or fixed RNG seed is installed to force the original race.

Current paired captures and their acceptance report are in `tmp/b3/baseline`,
`tmp/b3/repeat` and `tmp/b3/comparison.json`. The report checks 500 digests per window,
route, anchors, hunk bases, slave/emulator hashes, input pins and capture-tool hashes.
Captured memory is also checked for the two protection patches, save flag/directory,
the live keyboard hook and F10 key, and 1480 restored driver-name bytes against the
original capture. Other game-file variants have no supplied runtime fixtures.

Paired captures pass on `a1200-fast` (supplied 582992-byte game, caches unchanged):

| Window | Anchor after Quick Race | Matching screenshot digests | Loader checks |
|---|---:|---:|---|
| Green | 778 fields | 500/500 | pass in both runs |
| Tow | 5692 fields | 500/500 | pass in both runs |
| Follow | 6372 fields | 500/500 | pass in both runs |

Every pair has the same route, actual hunk bases, executable/input/tool hashes and
window length. The B3 accepted slave SHA-256 is
`c44d576c6e0bed066a91abe44d9e7b1925863e2c7f8cd7f5e430cf9e08607eed`.
The green, retirement and follow-camera screenshots were visually inspected.
The separate `CUSTOM1=1` quit probe follows the same menu route, confirms no return
marker exists before F10, sends the real key, and observes WHDLoad return `OK`. Its
screen shows the host AmigaDOS prompt without an error requester.

**B3 passes the revised gate.** `tools/slave_accept.py` checks the paired windows,
coherent capture identities, current build and clean quit. Adversarial local fixtures
confirmed rejection of missing/short windows, a changed picture, wrong layout, a
failed patch check, missing/failed/stale quit evidence and mixed slave builds. Build
repetition including a spaced output path, input hashes, Python compilation, bash 3.2
syntax and whitespace checks also pass. Captures, probe records and checker fixtures
remain in ignored `tmp/b3/`; no game or built-slave bytes are tracked.


### B4: option gates and disabled-byte checks

The build now exposes the existing `CUSTOM1` skip-intro option in `slv_config`.
`CUSTOM2–4` remain unassigned: no unimplemented performance or simulation option is
advertised. Release and developer targets currently assemble identical code; the
`DEVELOPER` define is the entry point for future individual feature switches. VERIFY
adds `CUSTOM5` bit 0, **Verify pacer relay**, solely to exercise an actual optional hook.
It is not a faster-pacer or simulation patch.

For the supplied game only, the VERIFY patch list uses `PL_IFC5X 0` around the six-byte
JSR at `h0+$3C9D2`. The relay tail-calls the original `h0+$1272` through the stack,
leaving registers and X intact; its MOVE changes NZVC, which the original pacer's first
MOVE replaces before use. Off installs nothing. Release/developer contain neither the
relay nor its option. The whole original JSR is replaced, with no return adjustment.
Other game variants have no diagnostic hook and remain unverified.

`tools/check_disabled.py` reads `PERF_RANGE` comments beside optional hooks. It checks
annotation/patch address and length, the enclosing CUSTOM bit condition and matching
`slv_config` declaration, rejecting missing, malformed, empty or unsupported inventories.
It rebuilds original hunk relocations from the pinned executable using the capture's
actual DOS segment chain. **All bytes, including relocated operands, are compared**;
relocations are not masked out. All five CUSTOM values must be zero. Source, slave,
input pins and actual layout must match capture metadata. Mandatory protection, save,
keyboard and names patches retain the B3 baseline and are separately checked, rather
than falsely required to equal the unpatched original.

B4 runtime evidence (`tmp/b4`, `a1200-fast`, fresh deterministic boots):

| Build / option | Optional range | 50-field live update / draw / pacer | Loader checks | Real F10 exit |
|---|---|---:|---|---|
| Release, all off | Original six bytes | 8 / 8 / 8 | All eight pass | OK |
| Developer, all off | Original six bytes | 8 / 8 / 8 | All eight pass | OK |
| VERIFY, all off | Original six bytes | 8 / 8 / 8 | All eight pass | OK |
| VERIFY, CUSTOM5=1 | Relay installed; target resolves to original pacer | 8 / 8 / 8 | All eight pass | OK |

All four quit screenshots show the AmigaDOS prompt without an error requester. The
release/developer raw traces and RAM dumps match; VERIFY is a distinct build. These
short checks establish B4 gating, not full-race regression or performance equivalence.
All four routes reach language/protection/startup/track/race at
1706/2083/2312/2507/3014 fields; the actual layouts agree between these four cases.
Relative to B3, h0/h1 stay at the same bases and h2/h3 move by −$A8. This changed
startup route is not treated as a performance result or proof of a specific cause.
B3's 500-field paired baseline remains evidence for its recorded 6100-byte build;
it is not relabelled as a capture of these changed binaries.

Current build sizes/hashes:

- Release/developer: 6116 bytes,
  `e34ac9c3f726d7de2c566c2f73c29ac0a363c9d1165023674e77990542f9d568`.
- VERIFY: 6180 bytes,
  `69ef15a83eb41573d79269fd01dff6ddb284b1160e19ce1f60ab6d6e2e75a87d`.

The checker rejects independent corruption of each of the six bytes, an actual enabled
relay even when its copied metadata claims all-off, nonzero options, stale source and
wrong layout. Nine malformed-source cases also fail, including an undeclared option,
missing annotation, wrong address/length/bit, extra hook, orphan and empty inventory.
`tools/slave_gate.py --check` rechecks the retained runtime set and negative tests before
writing PASS. All three builds also reproduce byte-for-byte with relative and absolute
output paths containing spaces; guarded cleanup succeeds on all six directories.

The first runtime attempt failed at the WHDLoad configuration splash: adding
`slv_config` activates `ConfigDelay`, and the route's repeated fire input kept restarting
that timer. The automated launcher now supplies `CONFIGDELAY=0` as well as
`SPLASHDELAY=0`. The failed capture stays in `tmp/b4/rejected-configdelay`. A release
build initially hit bash 3.2's empty-array/nounset behavior; explicitly defining both
build symbols fixed it. Neither failed attempt is counted as acceptance evidence.

### B5: gated cache pilot — passed for the current scope

`CUSTOM2` bit 0 requests instruction/data caches through `resload_SetCPU`, with
BaseMem write-through and ExpMem/Slave copyback. The 030 write-allocation disable bit
is clear because the game runs in user mode. This follows WHDLoad's documented Amiga
hardware inhibition of Chip/IO data caching; it is not permission to cache DMA buffers
on arbitrary hardware. WHDLoad's `NoCache` override remains effective. All CUSTOM bits
zero retain the old CPU request and original hooked game bytes. Caches remain opt-in
until a release build turns them on; no simulation/presentation patch is enabled.

VERIFY requires slave API 18 and logs `CACR` using `resload_Log` after the cache request.
The read runs through Exec Supervisor, guarded by WHDLoad's 68020 attention bit; the
68000 never executes `MOVEC`. Release/developer builds retain API 17 and omit the audit.
The installed runtime accepts **`FileLog`**, not `FileLog=1` despite the API autodoc's
numeric-option description. The rejected numeric-option probe never launched the game.

Inputs are pinned in `manifest/runtime-inputs.json` as well as the game/toolchain manifests.
Emulator SHA-256 for the pilot rows below: `ef14ed962d646ca4f85a29c184d86963a9e2a6a2a4de0ed745e8b6e413f6ec3f`.
Release SHA-256: `93dde23f76df6dab0ca3beea3507e29e25fb5e6a6bb3b06dab2e8697c4c75495`;
VERIFY: `ceba5ad09b28dd8741df9e0725395655b0d4dffa484edeab9ac4f1d2acc327f8`.

| Probe | Observation | Scope |
|---|---|---|
| 68020 + 8 MB Fast, caches requested | `CACR=$00000001`; Quick Race through results and finishing times; F10 returns OK | One whole-race pilot, not the full B5 matrix |
| Same release, all CUSTOM bits zero | 50-field capture: original hook bytes, all eight loader/name checks and F10 pass | `tmp/b4/b5-release-off`; actual four-hunk layout retained |
| 68030/50, MMU-capable emulator core, WHDLoad `NOMMU` | Startup stalls in indirect directory-drive handling | No language screen, no game/cache audit reached |
| Verified 68030/50, explicit MMU=0 | Same indirect-drive semaphore wait after 84 seconds of host time; no language screen | Effective CPU and MMU checked before capture |
| Invalid `68030-NOMMU` spelling | Effective CPU silently falls back to 68020; indirect-drive probes stall, direct/data-cache-off probe boots | All three rejected as 030 evidence; no 030 normal-speed conclusion |

The failed startup probes' host stack samples show `filesys_iteration` → `trap_get_bytes` →
`call_hardware_trap_back` waiting on a semaphore inside the emulation thread. The first
25-field startup command stops making progress. Valid 030 samples cover both
`m68k_run_mmu030` and `m68k_run_2ce`. The direct-drive control selected the wrong CPU
and changed two coupled settings, so it does not establish the cause of the 030 stall.
The host samples localize the observed wait to shared
emulator startup, not to a demonstrated F1GP cache-coherency failure. A longer deadline
cannot itself fix the sampled wait; the stalled runs were stopped using verified
project-owned PIDs rather than allowed to occupy the entire deadline.

Evidence is retained under `tmp/b5/`: `smoke020` (rejected option syntax), `smoke020b`,
`020-on-clock`, `030-on-clock`, `030-nommu-on-clock`, `direct030-diagnostic` and
`normal-speed030-diagnostic` (the latter three use an invalid 030 spelling and are
rejected as 030 evidence). The runner now checks the emulator's effective CPU/MMU report
and retains `debug.uae`; the valid 030 non-MMU override is `--cpu=68030 --uae_mmu_model=0`
(the order mattered with the launcher of the time; since TOOL2 it doesn't). `030-effective-on-clock` retains the corrected, still-failing non-MMU
030 capture and its host sample. Failure messages following deliberate emulator termination
include input-release errors; the old screenshot helper could also reuse a stale trace
and report a misleading screen timeout after disconnection. It now deletes the previous
trace and requires a newly produced one-field capture. These messages are not additional
game failures. Any `rejected-stale-failure.png` is also excluded: the shared shot
command could reuse its old trace after disconnection. The runner no longer requests
failure screenshots from a disconnected target. Stack samples and debugger logs are
the evidence for the startup wait.

The 020 clock pilot reached results after 20,703 fields from the cockpit route. Between
sample fields 2,010 and 13,869 it counted 8.002 frames/s; the existing 128-ms/frame proxy
would give 1.024×. Its winner was Senna, 4:58.855. This is neither a cache-gain comparison
nor a new precise clock calibration. The early collector saved only hunk 0's base, so
this pilot is **not** a complete A7 cell; the updated collector records all four hunks
and saves partial samples as it goes.

A separate uncached 020 whole-race control in `tmp/b5/020-off-clock` reaches results
after 21,105 fields, logs `CACR=$00000000`, and quits OK. It validates the revised route
and incremental clock collector, including the four-hunk metadata. It is not a matched
per-scene gain measurement.

**Gate: passed for the current scope** (68000, 68020, 68030; user decision to defer
040/060 timing). Menus and whole races pass with caches on on every CPU, and A7 records
the 020/030 gains. Matched 040/060 gains are deferred work, not a pass. The 030/040 startup stalls were an emulator deadlock, now fixed
(next section). All six 030/040/060 setups start with caches on and repeat exactly under
deterministic mode. Whole-race pairs now pass on all six 030/040/060 setups (see below).
A7's matrix is complete under its explained-failure gate. The 040/060 CPU traces are
empty (see below), so no 040/060 gain is claimed. Disabling data-cache emulation is
not an accepted substitute. AmigaXDev TOOL2 (the launcher refuses unknown CPU names) and
TOOL3 (failed captures leave no image or trace) are also fixed and installed. F1GP's
runner keeps its own effective-CPU and fresh-trace checks as extra guards.

### Current B5/A7 validation

This evidence was captured with emulator SHA-256
`950f14c966ba852372d382dec8e40544f1c49184eb9f2c24e901f352ecd9b048`
(TOOL1 plus the first window-title change). The current pins and their re-pin check are
under [Current runtime](#current-runtime-and-whole-race-validation). Earlier evidence keeps its
original hashes. Mouse auto-switching is explicitly disabled for new captures.

Cache-on whole-race pairs reach results, agree on every retained screenshot and clock
sample, and quit with F10 OK on all seven required 020/030/040/060 setups. Evidence:

| Machine | Pair under `tmp/` | Result field after cockpit route | PNGs per run |
|---|---|---:|---:|
| 020 + Fast | `matrix-workers/remaining/tmp/nocache-clocks/020-on-a`, `-b` | 20703 | 106 |
| 030 non-MMU | `b5-final/030-on-clock-d`, `-e` | 19296 | 99 |
| 040 non-MMU | `b5-final/040-on-clock-a`, `matrix-clocks/040-on-b` | 18693 | 97 |
| 060 non-MMU | `matrix-clocks/060-on-a`, `-b` | 20502 | 105 |
| 030 MMU | `matrix-clocks/030-mmu-on-a`, `-b` | 21708 | 111 |
| 040 MMU | `matrix-workers/040-mmu/tmp/clocks/040-mmu-on-a`, `-b` | 18492 | 96 |
| 060 MMU | `matrix-workers/060-mmu/tmp/clocks/060-mmu-on-a`, `-b` | 21507 | 110 |

**Cache-off controls require `NoCache`.** The original `$3B3D` CPU request under mask
`$7F3F` specifies noncacheable BaseMem and copyback ExpMem/Slave. Without an MMU it
switches caches off globally; with an MMU Fast regions remain cacheable. Thus all bits
off preserve the original policy, but are not a fully uncached MMU control. The matrix
now adds WHDLoad `NoCache` to every off arm and audits CACR, including the 060 branch
cache. Earlier off captures without this override are reference only. Fresh explicit
NoCache whole-race pairs pass on all three MMU CPUs under each worker's
`tmp/nocache-clocks/`; on/off are distinct deterministic races, never expected to be
pixel twins. The abandoned old 030-MMU off capture was intentionally stopped after
this control error was identified; it is not a game failure.

The corrected zero-lead follow predicate passes a fresh 030 cache-on pair in
`tmp/matrix-workers/profiles/tmp/a7/030-on-follow-a` and `-b`: green at 850, tow at
3219 (Mansell), follow at 3688 (Alesi). All six PNGs and semantic profile reductions
match. The new `all` capture collects 100 fields at each of these three independently
recognized anchors in one race and includes the timed fields in its anchor accounting.
This is a new capture protocol, not a relabelled B3 baseline.

### 040/060 CPU profile coverage failure

Fresh non-MMU cycle-exact 040 and 060 green/tow/follow pairs repeat all ten PNGs,
anchors and reductions exactly. However, their reductions contain **zero CPU instruction
records and zero call/frame events**, despite 100 valid fields and nonzero CPU DMA
activity in each window. Thus drawing/tick time, work and event-derived fps are
unavailable. Repeating empty CPU data does not satisfy a timing gate. The 030 control
contains instruction records and complete calls with the same collector.

Evidence: `tmp/matrix-workers/{040-mmu,060-mmu}/tmp/a7-all/{040,060}-on-{a,b}`
(the worker names describe isolation directories; these captures explicitly use
non-MMU CPUs). Effective logs and configuration are retained. The installed runtime
source-revision lists the normal tracing patches but not the separate optional `aprof`
patch; that alternative has not been validated here. No shared tooling was modified.

`matrix_report.py` now reports `UNAVAILABLE` and the missing samples explicitly;
`ceiling_report.py` fails any arm without a measured frame rate, as well as a mismatched
layout. Whole-race clock samples and DMA counts remain separate usable observations.
This blocks B5's matched gain requirement on 040/060 and their A8 CPU-event ceilings.
A7 permits an explained unavailable cell and its full matrix is now recorded below.
The user has chosen to keep shared-profiler repairs deferred.

### A7 machine matrix — gate passed with explained timing failures

Every machine/cache/window cell has a fresh exact-repeat pair. There are 24 measured
CPU-timing cells (A500, A1200, 020, 030) and 12 explicitly unavailable CPU-timing cells
(040, 060), whose missing instruction records are explained above. Field and DMA data
exist for all 36 cells. All 12 three-window pairs agree on routes, anchors, four-hunk
layout, every PNG and semantic profile reductions, and quit cleanly. The gate permits
an explained failure; this does **not** turn unavailable 040/060 timings into passes
for B5 or A8. Shared profiler work remains deferred by the user.

Each window is 100 PAL fields, with zero leads and distinct green/tow/follow anchors.
FPS is from complete frame intervals; drawing/tick ms are complete-call means including
interrupt time within the call. Partial calls are excluded. Ratios use the captured
128.84521484375 ms game-clock increment times observed fps, not a rounded 128-ms proxy.
The native step is separately 125 ms. Short windows include normal 6/7-field pacing
variation, so slightly over 8 fps is not a new sustainable frame cap.

CPU/blitter columns are chip-bus slots per field; free is the percentage of 71,051 PAL
slots unused. These are emulator measurements, not real 040/060 accelerator timings.

| Machine | Cache | Window | fps | Draw ms | Tick ms | CPU slots | Blit slots | Free % | Clock ratio |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| a500 | off | green | 5.79 | 135.11 | 33.37 | 27390 | 945 | 35.6 | 0.75 |
| a500 | off | tow | 4.06 | 191.12 | 46.98 | 28025 | 463 | 35.5 | 0.52 |
| a500 | off | follow | 3.86 | 227.66 | 23.39 | 27434 | 649 | 35.7 | 0.50 |
| a500 | on | green | 5.79 | 135.11 | 33.37 | 27390 | 945 | 35.6 | 0.75 |
| a500 | on | tow | 4.06 | 191.12 | 46.98 | 28025 | 463 | 35.5 | 0.52 |
| a500 | on | follow | 3.86 | 227.66 | 23.39 | 27434 | 649 | 35.7 | 0.50 |
| a1200 | off | green | 8.05 | 97.54 | 22.44 | 27885 | 1215 | 34.5 | 1.04 |
| a1200 | off | tow | 5.76 | 134.14 | 34.02 | 28171 | 695 | 34.9 | 0.74 |
| a1200 | off | follow | 7.58 | 111.75 | 15.11 | 27941 | 820 | 34.7 | 0.98 |
| a1200 | on | green | 7.98 | 64.70 | 20.05 | 27290 | 1260 | 35.3 | 1.03 |
| a1200 | on | tow | 8.13 | 82.49 | 21.56 | 28124 | 985 | 34.6 | 1.05 |
| a1200 | on | follow | 8.14 | 72.18 | 13.27 | 27317 | 1652 | 34.5 | 1.05 |
| 020 | off | green | 7.98 | 61.06 | 9.02 | 8785 | 1260 | 61.3 | 1.03 |
| 020 | off | tow | 8.05 | 90.62 | 14.57 | 13916 | 842 | 54.8 | 1.04 |
| 020 | off | follow | 8.14 | 68.18 | 6.10 | 11608 | 1297 | 57.1 | 1.05 |
| 020 | on | green | 7.98 | 47.79 | 8.70 | 7071 | 1260 | 63.7 | 1.03 |
| 020 | on | tow | 8.06 | 60.76 | 11.09 | 10483 | 927 | 59.5 | 1.04 |
| 020 | on | follow | 7.98 | 58.15 | 6.68 | 9834 | 1046 | 59.9 | 1.03 |
| 030 | off | green | 8.01 | 46.00 | 2.51 | 10540 | 1260 | 58.9 | 1.03 |
| 030 | off | tow | 8.02 | 56.63 | 5.17 | 14270 | 1053 | 54.0 | 1.03 |
| 030 | off | follow | 8.01 | 50.26 | 1.87 | 12542 | 1039 | 56.1 | 1.03 |
| 030 | on | green | 8.09 | 39.65 | 2.61 | 9177 | 1260 | 60.8 | 1.04 |
| 030 | on | tow | 8.02 | 53.85 | 3.38 | 13408 | 927 | 55.4 | 1.03 |
| 030 | on | follow | 8.02 | 53.66 | 1.77 | 13135 | 1820 | 54.2 | 1.03 |
| 040 | off | green | — | — | — | 11106 | 1260 | 58.1 | — |
| 040 | off | tow | — | — | — | 15782 | 1053 | 51.9 | — |
| 040 | off | follow | — | — | — | 13724 | 1039 | 54.5 | — |
| 040 | on | green | — | — | — | 7200 | 1260 | 63.6 | — |
| 040 | on | tow | — | — | — | 10828 | 927 | 59.0 | — |
| 040 | on | follow | — | — | — | 9392 | 1015 | 60.6 | — |
| 060 | off | green | — | — | — | 11204 | 1260 | 57.9 | — |
| 060 | off | tow | — | — | — | 15597 | 985 | 52.2 | — |
| 060 | off | follow | — | — | — | 13068 | 1061 | 55.4 | — |
| 060 | on | green | — | — | — | 6842 | 1260 | 64.1 | — |
| 060 | on | tow | — | — | — | 9887 | 927 | 60.3 | — |
| 060 | on | follow | — | — | — | 8861 | 894 | 61.5 | — |

The A500 has no caches: on/off request arms produce the same race and measurements.
This modern baseline reaches tow and follow on the A500; the older original-slave
observation that it did not retire must not be carried over to this build.

Observed work-per-frame reductions with caches requested (positive means less work):

| Machine | Green | Tow | Follow |
|---|---:|---:|---:|
| a500 | +0.0% | +0.0% | +0.0% |
| a1200 | +29.3% | +38.4% | +32.6% |
| 020 | +19.0% | +32.1% | +14.4% |
| 030 | +12.7% | +9.1% | -3.2% |
| 040 | unavailable | unavailable | unavailable |
| 060 | unavailable | unavailable | unavailable |

Each comparison uses the same binary, memory layout and anchor protocol. On/off races
differ through A1 timing/RNG inputs, including the followed driver and visible geometry.
These are observed workload changes in corresponding race phases, not isolated
instruction-cache gains on identical pictures. The 030 follow regression is retained,
not averaged away. No matched work gain is claimed for 040/060.

Whole-race counter measurements, between sample fields 2,010 and 13,869 after each
machine's own cockpit anchor (not used to anchor any scene):

| Machine | Off fps | On fps | Off clock ratio | On clock ratio | Off / on results field |
|---|---:|---:|---:|---:|---:|
| a500 | 5.490 | 5.490 | 0.707 | 0.707 | 30552 / 30552 |
| a1200 | 7.290 | 7.998 | 0.939 | 1.031 | 21105 / 19698 |
| 020 | 7.998 | 8.002 | 1.031 | 1.031 | 21105 / 20703 |
| 030 | 7.998 | 8.002 | 1.031 | 1.031 | 21507 / 19296 |
| 040 | 8.002 | 8.002 | 1.031 | 1.031 | 21507 / 18693 |
| 060 | 7.998 | 7.998 | 1.031 | 1.031 | 20502 / 20502 |

The roughly 8-fps pacer hides work savings on Fast machines. MMU clock runs are
functional evidence only; raw debugger RAM can lag copyback cache state and is not
used for MMU timing conclusions.

Evidence locations under `tmp/matrix-workers/`:

- `profiles/tmp/a7-all/{020,030}-{off,on}-{a,b}`.
- `040-mmu/tmp/a7-all/{040,a1200}-{off,on}-{a,b}`.
- `060-mmu/tmp/a7-all/{060,a500}-{off,on}-{a,b}`.
- `remaining/tmp/nocache-clocks/{a500,a1200,020}-{off,on}-{a,b}` and `030-off-{a,b}`.
- `040-mmu/tmp/nocache-clocks/040-off-{a,b}` and the equivalent `060-mmu` paths.
- Cache-on 030/040/060 and MMU whole-race pairs are listed in the B5 table above;
  fresh MMU off pairs are in each corresponding worker's `tmp/nocache-clocks/`.

The baseline VERIFY SHA-256 is
`ceba5ad09b28dd8741df9e0725395655b0d4dffa484edeab9ac4f1d2acc327f8`;
all runs use the `950f14…` emulator and `5a61a854…` launcher. Each capture records actual
four-hunk bases, full effective configuration, build/runtime/tool hashes and cache audit.
No game or trace bytes are tracked. Reproduce with the development matrix recipes.

### A8 developer ceiling gates — passed for the current scope

Developer and VERIFY builds expose `CUSTOM3` bit 0 (four NOP bytes replacing the pacer
branch at `h0+$1288`) and bit 1 (RTS at polygon filler `h0+$1F388`). `CUSTOM4` bit 0
suppresses preference-change notifications during startup to keep the 030 comparison's
allocation stable. These are developer measurement options; native simulation coupling
is retained, so no-wait intentionally speeds up the game. Release omits all three
options and retains its SHA-256:
`93dde23f76df6dab0ca3beea3507e29e25fb5e6a6bb3b06dab2e8697c4c75495`.

The filler walks edge lists, loads the back buffer through `h0+$1252`, and writes four
bitplanes. A3 classifies its scratch as presentation. All-off gates for the current
release/developer/VERIFY builds and the actual enabled VERIFY relay pass in
`tmp/b4/prefs-*`: all eight loader/name checks, original optional game-hook bytes and
clean quit. Negative tests reject mutations of all 12 hook bytes, wrong gates/layout/
source and a falsely labelled enabled relay. The aggregate is
`tmp/b4/prefs-acceptance.json` (`slave_gate.py --check --prefix prefs-`).

Within each machine's comparison, all four arms use one VERIFY binary, identical
hunk placement, `CUSTOM1=1`, and the native start transition at `h0+$3B4FA`, followed
by the next complete field. The breakpoint is removed before the 100-field timed
window. Instant blits change only `immediate_blits`; the effective blitter-wait policy
must agree across arms. Every accepted row passes exact fresh repeats, actual patch
bytes, configuration checks and clean quit.

| Machine | Normal pacer fps | No wait fps | No wait + no fill fps | No wait + instant blits fps | Four-arm audit |
|---|---:|---:|---:|---:|---|
| A500-equivalent | 5.81 | 5.81 | 6.82 | 5.93 | PASS |
| A1200, Chip only | 7.98 | 11.52 | 13.60 | 11.56 | PASS |
| 020 + Fast | 7.98 | 17.15 | 20.05 | 17.31 | PASS |
| 030/50 + Fast | 8.01 | 25.30 | 28.05 | 25.29 | PASS, CUSTOM4=1 throughout |
| 040/25, 060/50 | unavailable | unavailable | unavailable | unavailable | CPU instruction records missing |

These are observed ceilings in this start window, not every scene or a real-time
presentation implementation. The 030 instant arm shows no uplift in this window;
that does not establish zero blitter cost throughout the game. The A500 has no CPU
caches and its cache audit correctly logs zero.

A500/A1200/020 audits are `tmp/a8-single-setting/{020,a1200,a500}-audit.json`, using
VERIFY SHA-256 `084d897ceb94d431646dad4ffa41e5fafabe49df6eb5c27a51600454b60c4bd8`.
That directory links its unchanged control/no-wait/no-fill captures to the retained
original directories and contains fresh single-setting instant arms. The 030 audit is
`tmp/matrix-workers/prefs/tmp/a8-stable-prefs/030-audit.json`, with all eight captures
named `030-{control,no-wait,no-fill,instant}-{a,b}`. Its VERIFY SHA-256 is
`777ac5f59bd6cb640f77ce71fc61d4f247ba21bcd3c63519eaab62a08bd1b843`.
Neither build is the earlier B5/A7 VERIFY baseline.

**030 allocation cause and control.** In `tmp/alloc-stages/`, both arms have identical
free memory on entry to `_bootdos` and before `fast_pointer`. The instant arm uses 24
extra Fast bytes after that helper. `tmp/alloc-prefs/` narrows this to `SetPrefs`:
free memory agrees immediately before the call and differs immediately afterward.
The inherited loader passes a leftover nonzero D1 as the API's `Inform` argument.
The NDK `SetPrefs` contract defines true as requesting preference-change messages.
This startup effect precedes `LoadSeg`, not the renderer or the timed window.

The new developer-only `CUSTOM4` bit reads its option before the helper while preserving
the helper's original input registers. When enabled it passes `Inform=FALSE`; when off
it preserves the original D1. Read-only debugger probes in `tmp/prefs-argument-gate/`
confirm nonzero D1 with the gate off and zero with it on. The same rebuilt binary's
`tmp/matrix-workers/prefs/tmp/gate-off-{normal,instant}` probes still differ by 24 Fast
bytes, while all eight gate-on captures have identical four-hunk placement. Thus the
control is effective without padding or a relaxed layout audit. This does not identify
the individual OS allocation object or claim an OS defect.

Earlier failed controls remain reference evidence: skipping the frontend removes the
020's 168-byte Chip allocation difference but alone leaves the 030's 24-byte Fast
difference; passive boot input shifts both 030 arms equally and leaves the gap. Old
instant arms also changed the wait policy and fail the stronger configuration audit.
They are not accepted substitutes for the current comparisons.

The current combined `CUSTOM3=3 CUSTOM4=1` arm also passes fresh functional repeats on
030-MMU, 040-MMU and 060-MMU, including cache audits, screenshots/reductions and F10
quit: `tmp/a8-mmu-prefs/{030,040,060}-mmu-{a,b}`. These are functional checks, not MMU
timing measurements. Earlier C3-only MMU evidence remains tied to its original build.

**A8 passes for the current scope (68000, 68020, 68030).** The 040/060 CPU measurements
are deferred with the rest of the 040/060 work (user decision). No substitute core or
synthetic zero timing is accepted.

### Startup failures: cause and fix (68030, 68040)

The 030 and 040 startup failures had **one cause, in the emulator, not in F1GP or the
slave**. FS-UAE's deterministic mode deadlocked with the indirect UAE board, which every
data-cache setup needs, when the boot drive started, before WHDLoad ran. The earlier
"Remote connection closed" replies arrived only when the stuck emulator was killed. The
debugger link wasn't the cause. AmigaXDev TOOL1 fixed it (AmigaXDev `bfb2fbc`: with that
board, deterministic mode runs the filesystem and trap threads in lockstep). The installed
emulator, SHA-256 `cece3e1a9c19a58e2b9cd395615be54c25df5be6cc436187636917ec815c643e`,
is pinned in `manifest/runtime-inputs.json`.

Verification with the installed build:

- AmigaXDev's `test_fsuae_repeat.py` passes on `a1200-030`, `a1200-040` and `a1200-060`:
  a directory-drive boot, repeated, agrees at every stop.
- F1GP probes (`tmp/b5-fixed/`, `tmp/b5-cause/probe.py`, VERIFY slave, `CUSTOM2=1`,
  `WARP=1 DETERMINISTIC=1`) ran each setup twice from fresh boots. Both runs had identical
  route fields and identical first-race-field screenshots. CACR was logged, the emulator
  log never reported data-cache emulation turned off, and F10 returned OK.

| Setup | Route (fields since the command) | CACR |
| --- | --- | --- |
| 030/50 non-MMU | language 466, race 1358 | `$00002111` |
| 040/25 non-MMU, cycle-exact | language 435, race 1275 | `$80008000` |
| 060/50 non-MMU, cycle-exact | language 435, race 1249 | `$A0808000` |
| 030 MMU | language 435, race 1275 | `$00002111` |
| 040 MMU | language 435, race 1223 | `$80008000` |
| 060 MMU | language 435, race 1223 | `$A0808000` |

After the TOOL2/TOOL3 launcher was installed (`fsuae_common.sh` SHA-256
`5a61a854defeaaaeb610d7514b83acc4bcc998bfc4378d1db2615ececcad194a`, now pinned), a third
run each of the 030, 040 and 060 non-MMU setups gave the same screenshots as before
(`tmp/b5-fixed/*-c`). The launcher refused `--cpu=68030-NOMMU` before starting the emulator.

These checks cover start-up and menus with caches on, not whole races. Evidence from the
hang itself (host samples, the non-deterministic controls) is in `tmp/b5-cause/`.
B3/B4/A3 evidence was captured with earlier emulator builds and hasn't been re-run on this one.

## Executables

`data/game` is the original hard-disk loader (assigns, `frontend`, then `f1gp`); the slave
does not use it.

| File | Hunks (memory) |
|---|---|
| `f1gp` (582992 bytes) | 0 code `$44A54` any, file `$2C`; 1 BSS `$2A940` any; 2 code `$41C70` chip, file `$4990C`; 3 BSS `$14F84` chip |
| `frontend` (127816 bytes) | 0 code `$8` any; 1 BSS `$6F790` any; 2 code `$1EC04` chip, file `$60`; 3 BSS `$2FC58` chip |

`f1gp` holds the language dialog, the manual-protection prompt, the startup and main menus,
the race and the results screens (all their strings are in it, for example "Quick Race" at
hunk 2 `$3D8F0`). Menus and race therefore share one executable and need no handover.

### Current runtime and whole-race validation

**Current pins.** Emulator `f582f88316687b3409e518cc7aecec6b70318035a990d252894fb2a15d5a9f42`
and launcher `c316924a29b21a4665a3cf74b3f8a6b4bfc05178a941bf3d601944391725ba25`
(`fsuae_common.sh`, identical to AmigaXDev's), from AmigaXDev `7eda0f2`, which titles the
window with the running machine. With the current VERIFY slave
(`330662b72ba7c19d049a0eb68cb522cbe668e27470a9ccfd24df561465273b97`), the C4 input
capture `tmp/repin/c4-input` matches `tmp/c4/input-2` from the previous emulator in every
checked field except the runtime pins (state hashes, masks, latches, ticks, events, layout,
route). 030, 040 and 060 non-MMU boots to the race (`tmp/repin/{030,040,060}-{a,b}`)
log the expected CACR, quit OK and repeat their screenshots exactly.

Before that, the emulator hashed to
`950f14c966ba852372d382dec8e40544f1c49184eb9f2c24e901f352ecd9b048`.
Its source-revision record retains the TOOL1 determinism patch and adds AmigaXDev's
window-title patch (`d5ce108`); both patch hashes match the shared sources. The evidence
below and earlier startup evidence above belong to their recorded builds.

On this build, `tmp/b5-final/030-on-clock-b` completes the 030 non-MMU cache-on Quick
Race, reaches finishing times and returns F10 `OK`, with `CACR=$00002111`.
Results are detected at 19,296 fields after the cockpit stop (201-field sampling).
The first repeat (`-c`) matched all counters and gameplay images but differed in the
mouse pointer in three images at the results transition; that pair fails exact-image
acceptance. With `--joystick_port_0_autoswitch=0`, fresh runs `-d` and `-e` match all
99 PNGs, every clock sample, route and four-hunk layout; both quit `OK`. This establishes
a passing whole-race repeat pair for 030 non-MMU cache-on. The control supports retaining
the explicit input setting; it does not establish a cache gain or a shared-tool defect.
The preceding `030-on-clock-a` failed before debugger connection because the host sandbox
refused the connection; it is not evidence of a guest startup regression.

## Route to gameplay

From boot (`WHD_ARGS=CUSTOM1=1` skips the intro; otherwise click at its prompt): Choose
Language → O.K.; manual protection → any key, Return (the slave accepts anything); Startup
Menu → Quick Race, O.K.; Silverstone track screen → O.K.; "Please Wait" while the race
loads. The race then runs with no input. It opens in the player's cockpit ("Riding with
Nigel Mansell", car 5, fourth on the grid) at the start lights; the player's car only
creeps (5–16 mph) and drops to 26th while the field drives away. A "Viewing" sequence and
a follow-car camera follow until "Race won by …"; the game then returns to the
Non Championship Results menu.

`tools/f1gp.py quickrace` follows this route by recognising each screen from screenshot
pixels and stops at the first polled cockpit field. Once the language dialog is up, the
intervals are fixed per machine (fields after the language dialog, 25-field polling):

| Machine | protection | startup | track | race |
|---|---:|---:|---:|---:|
| A500-equivalent | 767 | 1100 | 1373 | 2348 |
| `a1200` (no fast RAM) | 559 | 866 | 1139 | 1854 |
| `a1200-fast` | 377 | 606 | 801 | 1308 |

With the CPU held from reset (`BOOT_BREAK`), the whole route and the race repeat exactly
from boot to boot; on `a1200-fast` the language dialog appears at field 838. Without it,
host timing changed the start and the race itself: in some boots the player's car kept
driving and was never retired.

## Race main loop

During the race the game runs one loop pass per frame at hunk 0 `$3C8F6–$3CA56` (the
live driving loop, also used by practice and qualifying). One pass:

1. `$3C8F6–$3C93C`: a timer check against a 2000 × factor deadline;
2. short calls `h0+396AC`, `h0+64`, `h0+34D24`, `h0+3BBF6`, `h0+39654`, `h0+3B5DE`, then
   (unless a mode bit is set) `h0+3B346`, **`h0+2AC14`**, `h0+3BF96`, optionally `h0+3C55C`
   and `h0+34028`;
3. **`h2+280F6`**, the drawing root;
4. `h0+258A2`, `h0+39542`, `h0+2DD74`;
5. the frame pacer, `h0+1272` (below).

`h0+2AC14` walks the car records through an offset list (each record points at its
track segment) and is the per-car update. Everything else in steps 1, 2 and 4 together
takes at most about 3% of all cycles on `a1200-fast`. Which of those calls are simulation and which are
presentation are classified in A3 below.

Inclusive cost per frame (`tools/race_profile.py`, green window, 500 fields; work is a
frame's cycles outside the pacer's wait):

| Machine | fps | drawing `h2+280F6` | per-car update `h0+2AC14` |
|---|---:|---:|---:|
| A500-equivalent | 5.84 | 124.3 ms (72.6%) | 38.6 ms (22.6%) |
| `a1200` (no fast RAM) | 7.67 | 97.4 ms (74.7%) | 25.9 ms (19.8%) |
| `a1200-fast` | 8.00 | 58.0 ms (46.4%) | 10.4 ms (8.3%) |

On `a1200-fast` the tow and follow windows spend 63.4% and 58.7% of all cycles in
drawing and 9.8% and 4.9% in the per-car update.

### A2: live sessions, replay and cockpit return

The three draw/pacer pairs are **two loops and a one-time redraw**, not three
independent session modes. Verified on the supplied 582992-byte game and the B3
6100-byte modern slave, `a1200-fast`, deterministic reset, no joystick sources:

| Path reached through native controls | h0 draw call | h0 pacer call | Behavior |
|---|---|---|---|
| Quick Race; Practise any Circuit; Non-Championship → Qualifying | `$3C9BA` | `$3C9D2` | Loop head `$3C8F6`, back edge `$3CA56`; per-car update at `$3C98E`. |
| Space, then R while paused (red R appears) | `$3CCE8` | `$3CD06` | Replay head `$3CC40`, back edge `$3CD0C`; update at `$3CCC6`. |
| Escape → Qualifying Frozen → Return to Cockpit | `$3C652` | `$3C65E` | Entry routine `$3C5C6`, called at `$3C8D2`, draws once and returns at `$3C66A`. No local back edge. |

These are all callers of `h0+$1272` and `h2+$280F6` in the supplied executable:
each target has exactly three relocated longword references in the two code hunks,
all operands of these absolute JSRs. The disassembly has no additional direct BSR/JSR
callers. No extra attract loop was found; this is not a full attract-mode play-test.

The entry routine tests `h2+$2A72C` at `h0+$3C5F8`, clears it at +$3C602, and takes
the one-time redraw path when resuming a session. A fresh session can bypass that path.
Replay is entered from live code at `h0+$3C984` through +$3CBD6. Its exit at +$3CCB6
returns to live +$3C962. Both live and replay call `h0+$2AC14`; replay must not be
classified as pure presentation merely because it shows recorded action. Pausing with
Space is consumed inside `h0+$3B5DE`, not a fourth draw/pacer pair. A3 must audit these
paths and their state writes before retiming them.

Call-site execution counts from raw profiles (`tools/loop_profile.py`):

| Capture | Fields | Entry draw / pacer | Live update / draw / pacer | Replay update / draw / pacer |
|---|---:|---:|---:|---:|
| Fresh Quick Race cockpit | 50 | 0 / 0 | 8 / 8 / 8 | 0 / 0 / 0 |
| Fresh practice garage | 50 | 0 / 0 | 8 / 8 / 8 | 0 / 0 / 0 |
| Fresh qualifying garage | 50 | 0 / 0 | 8 / 8 / 7 | 0 / 0 / 0 |
| Qualifying replay, red R visible | 50 | 0 / 0 | 0 / 0 / 0 | 8 / 8 / 8 |
| Return to cockpit, six contiguous 50-field chunks | 300 | 1 / 1 | 9 / 9 / 9 | 0 / 0 / 0 |

The qualifying window ends between a draw and its pacer; partial iterations at window
edges explain unequal counts. These are call counts, not new performance measurements.
The return's first four chunks contain neither pair, the fifth contains its sole entry
pair, and the sixth runs the live loop. A rejected breakpoint-started capture missed
the draw before the profiler's first field boundary; it is not used for that count.

Evidence is in `tmp/a2/route-{quickrace,practice,qualifying}`, `tmp/a2/replay.bin`
and `tmp/a2/resume-route`. Reports retain trace/dump hashes and actual hunk bases;
route captures retain the command log and slave hash. Fresh menu-route field counts:
practice reaches main/circuit/track/cockpit at 1622/1817/2016/2523;
qualifying reaches the same first three, weekend at 2367 and cockpit at 2718.
Quick Race remains 807/1184/1413/1608/2115. These counts describe these commands and
build only; the route recognizes screens rather than waiting those numbers.

### A3: simulation versus presentation

**Gate passed for the pinned 582992-byte game.** The call-boundary audit covers 50
complete drawn iterations each of green, tow, follow, qualifying and replay (250 total),
not 50 PAL fields. Each snapshot includes all four hunks: retaining code as well as data
avoids missing variables between routines. The report excludes the two live-discovered
32,000-byte bitmaps from its non-screen changes, but retains their bytes in compressed
snapshots. Every observed non-screen drawing change is classified. A separate reachable
instruction audit classifies **3,681 explicit memory-store instructions**, including
same-value and write/restore stores that a snapshot difference cannot reveal.

This is a write-ownership audit, not a new game-speed, performance or equivalence result.
Unexecuted conditional branches below have static evidence; they are not labelled as
play-tested. No game/slave instructions were changed for A3.

#### Calls in native order

`L` means h0's live loop; `R` its replay loop. All call-site offsets in this table are
in h0. The report's full changed-byte intervals are in `tmp/a3/*/diff.json`; the table
groups them by their owners and also includes conditional writes absent from a sample.
A zero net delta does **not** mean that a call is read-only.

| L site / R site | Target | Class and writes; required cadence |
|---|---|---|
| `$3C944` / — | h0+$396AC | Tick: replay checkpoints. Copies h1+$368–1955 car/session state and h0+$3A714–3A7BB into the h1 replay slots; updates h1+$1B03C slot pointers and h0+$3A7CA/+3A7CC/+3A7D2. Keep before the live tick. |
| `$3C94A` / `$3CC8E` | h0+$64 | Tick input: builds active-low masks h0+$18–1D from the keyboard table **h2+$52A**. Same values in an idle-input sample are still stores. |
| `$3C950` / — | h0+$34D24 | Tick input: controller masks/axes, player control fields (including record +$98–9B), calibration and input scratch. Hardware acquisition remains asynchronous as in A6. |
| `$3C956` / `$3CC9A` | h0+$3BBF6 | Tick/modal: consumes control/assistance edges, updates h2+$2A73E option bits and h0+$3A7A8 edge latches; descendants also affect control state and UI. Do not repeat at picture rate. |
| `$3C95C` / — | h0+$39654 | Tick: records control bytes in the h1+$1B048–1BE57 ring and advances h0+$3A728; includes player record +$7F and analog +$9A/+9B. |
| — / `$3CC94` | h0+$395F2 | Tick: inverse replay-input operation; restores masks and player controls, advances the same ring cursor. Replay really re-simulates cars. |
| `$3C962` / — | h0+$3B5DE | Tick/modal: pause/replay/view-key handling, edge latches and mode flags, with modal waits and UI updates. Preserve native entry/exit ownership. |
| — / `$3CCBA` | h0+$3B80E | Tick/modal: pause/resume key latch h0+$3A918, h0+$2CC2C/+2CC2E/+2CC32 handshake/deadline state and UI refresh flags; can wait for a key. |
| `$3C988` / `$3CCC0` | h0+$3B346 | Tick/session: start-light and race-state machines, h0+$3A73A–3A7A6 timers/flags, gameplay RNG h0+$3A7B0–3A7B4, car/ranking state and messages. Keep native order before car updates. |
| `$3C98E` / `$3CCC6` | h0+$2AC14 | **Mixed**, predominantly tick: car records h1+$5D6 onward (stride $C0), track/control/AI and physics scratch, ranking tables h2+$2AE56 onward, h0 game/sound state. It also calls HUD text drawing on some branches; see the bitmap-read finding below. Skipping only h2+$280F6 does not make a tick completely free of display writes. |
| `$3C994` / `$3CCCC` | h0+$3BF96 | Tick camera/view selection: h1+$234/+238/+23C/+23E source/view state, h0+$3A6BC–3A6C4 pending changes and +$3A915 edge latches, camera state through +$3C292. Includes automatic “Viewing” changes. |
| `$3C9A4` / `$3CCDC` | h0+$3C55C | Conditional mixed rebuild: waits for pending publication, rebuilds cockpit/external background, clears h0+$3A6CE and shifts refresh byte +$3A712. Pixel rebuild and tick-owned request consumption must be separated; do not discard the latter. Not exercised in the steady 50-frame samples. |
| `$3C9B4` / `$3CCE2` | h0+$34028 | **Mixed camera evolution/projection:** camera h0+$3A7F8–3A828, matrix inputs +$3A8C2/+3A8C4 and h2+$231D4/+231E0/+231E4. Its +$3676A call advances the damped camera state +$3A820/+3A824. Run that evolution once per tick; recompute pure projection inputs from staged presentation poses later. |
| `$3C9BA` / `$3CCE8` | h2+$280F6 | **Mixed renderer.** Pixels, blitter work, geometry/cache scratch and the tick side effects listed below. Cannot be called freely or omitted wholesale. |
| `$3C9C0` / `$3CCEE` | h0+$258A2 | Tick clocks: fixed increments to h0+$3A77C/+3A780 and +$3A782/+3A786, countdown/status +$3A7BA, deadline and dirty flags. Retain after the native drawing-side effects. |
| `$3C9C6` / `$3CCF4` | h0+$39542 | Mixed cockpit/UI: instruments, text scratch h2+$1F312 onward, dirty/event flags and h0+$3A799. Its +$39504 path reads the pit-animation word +$3A74A and can trigger a UI update. |
| — / `$3CCFA` | h2+$1DFB4 | Presentation: paints the red replay R into the remembered bitmap h0+$1256; reads/masks pixels, no world step. |
| `$3C9CC` / `$3CD00` | h0+$2DD74 | Mixed HUD: temporarily selects the remembered bitmap, draws text/status, consumes dirty flags h0+$3A6DE/+3A6DF, advances blink phase +$3A6E0, updates text scratch and related HUD state, then restores h0+$1252. Preserve tick-rate blink/request handling when extracting painting. |
| `$3C9D2` / `$3CD06` | h0+$1272 | Presentation/sound: fields-work/minimum/frame counters h0+$125A–1261, bitmap selection +$124E/+1252/+1256, publication address h2+$1DAAC and pending byte +$1DAB0. Replace by C's clock/publication contract, retaining A6's sound denominator meaning. |
| `$3C9E6` / — | h2+$51C | Escape-key predicate: reads the key table, changes condition codes, no game-state store. |
| `$3CA26` / — | h2+$8E2 | Exit-only hardware/modal handoff: interrupt/audio enable state; not an extra world tick. |
| `$3CA36` / — | h0+$29C1C | Exit-only classification: car ranking fields and h2+$2AE56 standings / +$2AE8A results. |
| `$3CA3C` / — | h0+$3B1E0 | Exit-only result status: writes h2+$2A736 from the selected car's retirement/finish flags. |

Inline code is part of the tick too: the loop headers update h0+$2CC2C/+2CC2E/+2CC32
against the game clock; the live exit sets h2+$2A75E and h0+$CC/+2CC06; the replay exit
clears h0+$3A70A before returning to live pause handling. The undrawn replay reconstruction
paths at h0+$3CA5A and +$3CB82 reuse control/session/car/clock calls; they are modal
reconstruction, not additional picture loops. C must not add a second clock around them.

A2's h0+$3C5C6 cockpit-return path is a **one-time transition**, not a third live loop.
Its draw/camera/HUD/pacer calls have the same ownership as above; its other calls initialise
object workspace (h2+$281AE), session/input state, restored replay state and scene data.
The clears of h2+$2A72C/+2A75E and h0+$3A6B0/+3A6CE and the final sound handoff remain
modal work. There is no proposal to execute this transition 50 times as a live loop.

#### Drawing writes and consumers

The static traversal starts at h2+$280F6, follows calls/branches, expands all sixteen
colour-kernel entries (24-byte and 96-byte dispatch strides), and resolves the three
`JSR (A5)` sites to the four selected transform routines h2+$23A98/+23D80/+24000/+24180.
It reaches 14,077 instructions with no unresolved control-flow edge. These dispatch
bounds belong to this pinned game's four-plane palette and are not a generic disassembler
heuristic. Every renderer store PC seen in the retained green/tow/follow traces is included.

| Write family | Ownership / consumer |
|---|---|
| Both bitmaps; fill/span work in h0+$1348–147B, +$1E802–222EB and h3+$112F8 onward | Presentation. h3's non-screen polygon buffer is also borrowed for race-order sorting, but h0+$2916E–291B8 rewrites all 26 entries before +$291CA onward reads them. The old polygons are not physics input. |
| h0+$25644 trig result | Shared math scratch. Physics consumers +$260AE/+260CA/+349D4/+349F6/+36B50/+36B72 and camera consumers +$262BA/+262D6 first call +$25648, which overwrites it at +$25670. No dependency on a preceding picture's result. |
| h1 palette/span tables +$0–21F; object list +$1AD6; projection/object work +$16294–16C49, +$1C3FC onward; h2+$23126–2327D, +$28168–281AB, +$29E16–29E2B | Presentation workspace: projected vertices, clipping/visibility results, object ordering, mirror staging and span preparation. No persistent physics result was found here. Raw changed intervals and writer PCs remain in the reports. |
| Track-record bytes +$A, +$1E, +$25, +$26, +$2A, +$2B (46-byte records) | Presentation association/visibility flags and packed clipping caches. +$29FAE–29FCC marks visible car associations; +$29FEA clears them. Physics at h0+$26912/+2695C tests bits 0/1 of record +$26 and the camera at +$33FA6 tests bit 3; drawing changes its high bits. The +$25 clipping nibbles are written by h2+$234A2–234B0 and consumed by clipping. Byte overlap is not a dependency on the renderer's bits. Keep the mark/cleanup pair within each draw. |
| h0 model decoration +$2E2EC, +$2E3EA/+2E4D6, +$31B96, +$32448/+32693/+327F0; h2+$2C3BF and object dimensions | Presentation: material/shape and projected-object selection from existing object/car/track state. Marshal/tow-object decoration copies the native phase/pose; these stores are not an independent world advance. Model updates and mirror staging must remain paired with their consumers. |
| h2+$1E278–1E65B queue and descriptors, +$1E804/+1E80E, +$1F4E6–1F561; custom `INTREQ` | Presentation/hardware: blitter command production and drain. Its interrupt also writes h2+$28C–291 and queue read cursors; keep asynchronous completion alive while pictures are skipped. |
| h0+$125E, sound RNG +$2578C–25790, pitch +$3A704, handshake +$2CC06; h2 copper pointers, +$93A, pending +$1DAB0 | **Asynchronous**, not renderer-owned, despite changes between draw entry and return. Call dumps include interrupt work. Trace attribution separates stacks; KickEmu's virtual SR means the recorded CCR alone cannot distinguish interrupts. |
| h0+$3A746/+3A748/+3A74A/+3A74C, +$257C4–257C8, +$3A820, +$3A770 | Persistent tick side effects, detailed below. These are the exceptions to freely repeating presentation work. |
| Stack pushes, saved registers and temporary pointers | Call-local storage. Explicit stores are counted; implicit call return-address pushes are classified as stack without treating them as game state. |

**Drawing side effects that must run once per native tick, in native order and with the
native view/car predicates:**

1. **Pit-service phases:** h2+$2A0FA, +$2A19E, +$2A226 and +$2A3CE advance, saturate,
   initialise or reset h0+$3A748, +$3A746, +$3A74A and +$3A74C. The normal-cockpit
   path at h2+$28070–28080 resets the first three when the relevant car flag is absent.
   Qualifying's 50-frame sample observes +$3A74A advancing. h0+$3950E reads it for a
   UI trigger; +$3BA68 reads it before admitting a pit/control action and recording car
   field +$92. These counters cannot become picture-rate animations. Keep the tick
   update and allow drawing to consume its result without advancing it again.
2. **Shared RNG and shake:** under the car-state-3/race predicate, h2+$2A144 calls
   h0+$25792 (state +$257C4–257C8) and +$2A14C adds its result to camera word +$3A820.
   That stream also has non-renderer simulation/sound consumers (A1). Preserve the draw
   count and order once per tick; moving it to each picture changes later random choices.
   The camera's +$3676A spring/damping update is also tick work, although its caller is
   immediately before drawing rather than inside h2+$280F6.
3. **Visible-car debris expiry:** h2+$29ACE–29AD8 changes zero h0+$3A770 to −1 when a
   rendered car has record +$19 bit 4. Simulation h0+$33CA4–33CDA consumes that deadline
   and can clear bit 4 from all cars. This is genuine visibility-to-simulation feedback.
   Retain a tick-rate evaluation using the native visibility predicates even on an
   undrawn tick; do not substitute “all cars” or the set visible in an extrapolated picture.

Other camera selection, “Viewing” cuts, start lights, phase timers, HUD dirty flags,
blink state and event/one-shot input consumption live in the surrounding calls above.
They remain tick/modal work. In particular, neither +$34028 nor +$2DD74 is a pure painter.
This audit identifies the split; implementing a tick-only visibility pass and extracting
embedded HUD writes are C's work, not changes already made here.

**Does physics read the painted screen?** The green/tow/follow and practice instruction
samples show no bitmap reads under the car-update call. Replay does: 192 distinct bytes,
at h2+$1F16E/+1F172/+1F1BE/+1F1C2/+1F216/+1F21A/+1F266/+1F26A. Following the path
from h0+$3CCC6 through call sites +$2AD38, +$28E74, +$28B10, +$2D50E and h2+$1EFE0
identifies glyph compositing (+$1F07A): it masks existing pixels and writes the composed
glyph to the bitmap(s). Those pixel values do not feed grip, collision or car integration.
Thus “the car-update call never reads the screen” would be false; the observed reads are
embedded presentation. No Revs-style painted-screen physics dependency was found.

#### Evidence and limits

Local evidence is `tmp/a3/{green,tow,follow,qualifying,replay}`: initial RAM, actual four
hunk bases, slave/emulator/input hashes, compressed before/after snapshots, paired event
indices, debugger command logs and classified byte ranges. Screen-anchored route/profile
records are in the `*-anchor` directories; qualifying/replay use native menu and key input,
with the red R checked visually. All use the B4 release slave, all CUSTOM values zero.
The accepted tow run has a different boot/anchor route from the other race samples;
its own route is retained. No field number was borrowed and no cross-race state match
is claimed. These samples do not replace the B3 repeatability baseline.

The supporting effective-address inventories use the retained `tmp/raw` race traces
and A2 practice/replay traces with their own RAM layouts. They are separate evidence,
not traces of the new breakpoint runs. The static scan covers conditional renderer
branches missing from those short traces. It is bounded by the pinned executable and
reviewed dispatch tables, not a proof for unavailable game variants or modified code.

Rejected probes remain local: the debugger rejected simultaneous breakpoint installation,
so the collector now uses one return breakpoint at a time and steps only between calls.
A tow attempt stopped on a malformed debugger memory reply after 38 complete frames;
it is not accepted. The retry uses bounded retries of that halted read only, validates
snapshot sizes/hashes and captures all 50 frames anew. Negative checks reject incomplete,
odd, corrupt or missing-frame evidence and an injected unclassified renderer change.

## State map (A4)

A4 is complete for the supplied, SHA-256-pinned executable. This is the native input
map for later snapshots, not an implemented presentation patch. Offsets below are hex;
`R` is a car-record base in hunk 1 and `T` its track-record pointer. Quantities retain
native integer units: no metres, degrees-per-second or physical timestep conversion is
implied. Static evidence is the named writer/consumer paths; the final subsection
separates that coverage from the retained live captures.

### Car records and the two pose representations

There are 26 `$C0`-byte car records at **h1+$5D6–1955**, so slot `i` starts at
`h1+$5D6 + i*$C0`. They are not iterated in physical-slot order. The word-offset list at
**h1+$520** selects records relative to `$5D6` (`h0+$2AC2E–2AC44`); view cycling also
uses this list (`h0+$3C36E–3C3AA`). Record `+$66` is its byte index into that list.
`h0+$29290` clears exactly `$C0` bytes; +$292B6 searches 26 slots at that stride.
Do not use the list index as persistent identity: ranking can reorder it. Retain the
record address/slot and driver identity (`+$AC & $3F`) with snapshot validity.

| Field relative to R | First-slot h1 offset | Width / meaning | Writer and rendering consumer |
|---|---:|---|---|
| `+$00` | `$5D6` | word, motion direction; distinct from body heading | `h0+$25F68` derives it from velocity components. Camera copies it at +$33ECE; chase orientation uses +$3996C. |
| `+$04` | `$5DA` | signed word, explicit-pose pitch | `h0+$2BAB4–2BADE` derives road slope projected onto body heading. `h0+$26218` returns it to camera/car drawing when explicit pose is selected. |
| `+$08` | `$5DE` | signed word, explicit-pose height | `h0+$2BA96–2BAB0`; read at +$2621C. |
| `+$0A` | `$5E0` | signed word, lateral offset in the segment's local frame | `h0+$2B95A–2B9C6` projects explicit world position back onto track axes. `h0+$26286` uses it in track-relative projection; +$33EDE publishes it for the road renderer. |
| `+$0C` | `$5E2` | signed word, uncorrected longitudinal local coordinate | `h0+$2B9CA`; combined with curvature/lateral correction to obtain +$1C. It is not a second lateral offset. |
| `+$10` | `$5E6` | word, speed magnitude | `h0+$25F4E–25F62` computes `sqrt(v0²+v1²)` from the high words of +$30/+34. Track-driven update also writes +$2B34A. Used by chase/camera selection at +$3995E/+39BFC; not an independent translation input to car drawing. |
| `+$12` | `$5E8` | long, pointer T to a `$2E`-byte track segment | Loaded at +$2AC44 and by `h2+$29A38`; explicit-motion segment search +$263F6 writes it, track-driven traversal +$2B558 writes it. |
| `+$16` | `$5EC` | word, curvature-adjusted segment length/denominator | +$2B9E8–2BA08 clamps it to at least `$10`; used when computing fraction. |
| `+$1A` | `$5F0` | word, body heading/yaw | Player angular integration +$37586; track-driven path +$2B618. Camera +$33ED6; car renderer +$29A54. One turn is `$10000`, quarter turn `$4000`; use wrapped word deltas. |
| `+$1C` | `$5F2` | signed word, corrected longitudinal segment coordinate | +$2B9CE–2B9E4 and +$2B55C; used with +$0A by +$26286. Segment traversal updates T and this coordinate together. |
| `+$1E` | `$5F4` | word, segment fraction, Q14 (`$4000` = one interval) | +$2BA0C–2BA2A / +$2B560–2B57E computes `((longitudinal-$400)<<14)/denominator + $4000`, with native signed division and overflow handling. Height/slope interpolation and AI use it. |
| `+$26` | `$5FC` | word, lap-relative segment index | +$2BAE4–2BB32 derives it from T's index, start-line origin and lap wrap; camera copies it at +$33EE6. |
| `+$28`, `+$2C` | `$5FE`, `$602` | signed longs, explicit horizontal world coordinates | +$26074 converts track coordinates; physics advances them. +$26210/+26214 supplies them to camera and car drawing. Native coarse track coordinates are these values arithmetically shifted right by 11. |
| `+$30`, `+$34` | `$606`, `$60A` | signed longs, horizontal velocity components with fractional low words | +$25F7C constructs them from direction/speed; +$25F4E reads their high words. Do not confuse these with the world positions at +$28/+2C. |
| `+$38` | `$60E` | long, angular-motion state; high word advances body heading | +$37506–37586. It is simulation input, not another renderer angle. |
| `+$48` | `$61E` | signed word, steering angle | Player path +$359BA and other control paths +$3681E/+3691C. `h2+$29A58` copies it to h2+$28168 for wheel-image selection. |
| `+$4A` | `$620` | signed word, track/body correction relative to motion direction | +$2B61C–2B620. `h2+$29A46–29A54` adds a scaled correction to rendered body yaw: +$1A plus the high word of `(+$4A * h0+$3A964)<<3`. |
| `+$72` | `$648` | signed word, speed change | +$2ADE4–2ADEA / +$2B34E; camera excitation at +$33EBA, not a pose angle. |
| `+$7E` bit 0 | `$654` | byte flag selecting explicit world pose | +$25FD8 enters explicit mode, +$26050 clears it; +$26206/+26272 choose representation. Snapshot this discriminator; do not interpolate it. |
| `+$80` | `$656` | word, packed lap position (segment index ×64 plus signed high byte of fraction) | +$2BB36–2BB3A; lower precision than the full segment pointer/fraction. Do not use it alone for smooth position. |
| `+$8C` | `$662` | signed word, vertical displacement above interpolated track height | +$34C7E; added at +$2623E / +$2BAAC. |
| `+$B6` | `$68C` | signed word, vertical-motion state used as cockpit pitch effect | +$34C7A, added only for cockpit at +$33F28–33F2C. This is not roll. |

The common pose accessor **h0+$26206** is essential. With `R+$7E` bit 0 set it returns
world X/Z from +$28/+2C, pitch from +$04 and height from +$08. Otherwise it reconstructs
X/Z from T, lateral +$0A and longitudinal +$1C (`+$26286`), interpolates height using
+$1E and +$8C, and derives pitch from T's slope and the difference between T's heading
and body heading +$1A. Copying only +$28/+2C will therefore miss track-driven cars.
`h0+$26272` is the position-only variant used by external-camera construction.

T points into hunk 1: the ordinary track starts at **h1+$53DE**, with alternate/pit
segments below it (including **h1+$2BFA**). Segment +$00 is heading, +$02 slope, +$04/+08
horizontal position, +$06 height, +$14 curvature and +$1A contains the segment index and
camera flags. Neighbour samples are `$2E` bytes apart. Runtime end/length/alternate-range
pointers are in h2+$1FAC2/+1FAC6/+1FAD6/+1FADE/+1FAE2. Follow native conversion/wrap
helpers (+$26326, +$26406, +$26794/+267DA), especially through the pit lane; interpolating
raw pointers across these boundaries is invalid.

**Roll and wheel rotation:** the mapped car-model transform takes horizontal position,
height, yaw and pitch; it has no independent roll argument. The road projection rotates
the horizontal axes and shifts the horizon; it has no camera-roll rotation. Do not invent
a roll word at the unused-looking record +$02 or +$06. Wheel steering consumes +$48 via
h2+$28168: h2+$28C30–28D34 combines it with relative yaw/perspective and chooses graphics
through h0+$147C. No independent per-wheel spin angle is consumed on that path. This
identifies the inputs to preserve; it does not promise new roll or wheel-spin animation.

### Camera records and selection

| h1 location | Meaning and owner |
|---|---|
| `+$224` (long) | Renderer track anchor. +$26502 converts the source's segment as necessary and publishes it; road +$25C26/+24CD2, object visibility +$298A8 and secondary track pass +$2A50C read it. |
| `+$234` (long) | Active pose source: selected car in cockpit, synthetic camera at h1+$256 in external views. Read by +$34036 and h2+$29E90; also determines self-car suppression at h2+$29F02. |
| `+$238` (long) | Selected/viewed car, independent of controlled player. View cycling and automatic Viewing cuts write it. External camera follows this car; its model, pit status and HUD can still be consumed while +$234 points elsewhere. |
| `+$23C` (byte) | View code: `$00` cockpit; `$80` TV before initialization, `$C0` initialized TV; `$A0` rear chase, `$B0` opposite/front chase. Bit 6 is the TV camera initialized/cut latch, not a separate car identity. |
| `+$23E` (byte) | One-shot view requests: bits 7/6 previous/next car, 3 player car, 4 cockpit, 5 TV, 2 rear chase, 1 front chase. Native +$3C292 validates availability and consumes these. |
| `+$240` (word) | Nonzero track-camera fallback/selection when no suitable target remains; low 15 bits select a track region. It is not a pointer or an angle. |
| `+$256–315` | Synthetic camera, same `$C0`-byte record shape. Relevant absolute offsets: direction `$256`, pitch `$25A`, height `$25E`, lateral `$260`, segment pointer `$268`, body yaw `$270`, fraction `$274`, lap segment `$27C`, world coordinates `$27E/$282`, list index `$2BC`, representation flag `$2D4`, packed lap position `$2D6`. |

The controlled player pointer is **h0+$3A720**, not h1+$238. Pending source/view/request
changes live at h0+$3A6BC/+3A6C0/+3A6C2 and are applied by +$3BF96. Key-edge latches
are at h0+$3A915. +$3C4E4 selects cockpit and sets +$234=+$238; +$3C516 selects the
synthetic record and resets the TV initialization bit. A view change, driver change,
TV cut, replay restore or transition into/out of a synthetic source invalidates pose
history even when the new source occupies the same address.

**TV:** +$397E4 dispatches to +$39A3C when bit 5 is clear and bit 6 is clear. It selects
a flagged track-camera location, initializes the synthetic record (+$29290), and writes
its explicit world coordinates/height (+$39BAC–39BB8). +$39BD0/+39CBE aims it at the
selected car; increasing target distance past the threshold clears bit 6 at +$39C64,
requesting a new location next tick. h0+$3A8F8/+3A8FA/+3A8FE/+3A900 hold selection
parameters; +$3A906/+3A908 hold current/previous distance. A nonzero h1+$240 instead
selects the track fallback (+$39C6E).

**Chase:** bit 5 dispatches to +$398AA. +$3990C positions the synthetic camera at an
offset from the selected car's world pose using h0+$3A90C and the evolving heading
h0+$3A710; +$3A70E is its initialization flag. Bit 4 reverses the offset direction by
`$8000` at +$399BC (front versus rear). Segment search and height derivation follow;
+$39CBE aims the camera at the target. This is a moving camera state, not just a fixed
offset that can be reapplied independently of its native update.

### Published camera and what the renderer reads

Camera preparation **h0+$34028** reads the source selected by h1+$234. Its +$33EA6
helper publishes the following hunk-0 values; they are not extra hunk-1 camera records:

| h0 offset | Contents / consumer |
|---|---|
| `+$3A7F8` | Source motion direction (+$00). |
| `+$3A7FA` | Pose pitch + h2+$231D8 view bias, plus source +$B6 only in cockpit. Used to calculate horizon h2+$231D4 at +$3404C. |
| `+$3A7FC`, `+$3A800` | Coarse X/Z words (`world >> 11`); track transform h2+$2329C/+232A2 subtracts these. |
| `+$3A7FE` | Pose height + view height bias h0+$3A904; h2+$232A8 subtracts it. |
| `+$3A802`, `+$3A806` | Full X/Z longs returned by the pose accessor. |
| `+$3A80A` | Source lateral offset; road clipping/detail selection h2+$24C46/+24C5C. |
| `+$3A80C` | Source body yaw; used for camera trig coefficients and relative car/model yaw. |
| `+$3A810`, `+$3A818` | X/Z longs reduced by 8 bits; car/model placement h2+$286F0/+286F6 subtracts them. |
| `+$3A81C`, `+$3A81E` | Source lap segment and anchor track heading; keep consistent with source and h1+$224. |
| `+$3A820`, `+$3A824` | Long spring displacement/velocity; high words consumed by +$3676A. Only cockpit adds displacement to the pitch used for horizon placement. A3 owns this evolution once per tick. |
| `+$3A8C2`, `+$3A8C4` | Derived yaw trig coefficients (+$3409E); road and car transforms consume them. Recompute from a staged yaw, do not independently extrapolate coefficients. |

The native views share this publication/geometry pipeline:

| View | Native pose inputs and relevant reads |
|---|---|
| Player cockpit | +$234=+$238=player record. Pose-discriminator inputs above, body yaw, lateral offset and segment/lap position; +$72 excites the camera spring and +$B6 affects pitch. The selected car is normally suppressed by h2+$29F02–29F12. |
| Onboard another car | Identical cockpit path, with +$238 selecting the other record. It does not switch physics/input ownership to that car. |
| TV cameras | +$238 remains target car; +$234=h1+$256. Synthetic explicit X/Z/height/pitch/yaw supply the published camera, while target pose/speed/segment drives aim and camera cuts. No cockpit spring displacement is added. |
| Rear/front chase | Same synthetic-source publication as TV, but +$398AA updates it from target position, speed/direction and chase history; bit 4 reverses placement. Rendered cars still come from the car offset list. |
| Replay | +$3976A restores checkpoints into h1+$368–1955 and h0+$3A714–3A7BB; +$395F2 reads recorded controls from h1+$1B048–1BE57. Replay then runs +$2AC14, +$3BF96, +$34028 and h2+$280F6. It has the same per-view records, not a separate recorded-pose render array. |
| Mirrors / secondary track passes | Preserve the same published camera and car poses. h2+$2A450 remaps track ranges from h1+$224 and temporarily changes projection/clipping workspace, restoring it before return. h2+$28774 onward uses relative car placement for cockpit side-image routing. No separately advancing mirror-car record was found. |

For **every visible car**, h2+$29A20 resolves R through h1+$520, calls +$26206, reads
body yaw +$1A, correction +$4A and steering +$48, then enters the shared model transform
+$28652. Model/visibility decisions additionally read +$19 (damage/debris bits), +$25
(model/colour selection), +$96/+97 (status) and +$AC (driver identity). Association
h2+$29E7C reads +$66, T and retirement flags and temporarily marks track records, as
classified in A3. These discrete values belong with snapshot validity but must not be
numerically extrapolated. The viewport is not determined by camera pose alone: keep
h1+$224, h2+$231E0/+231E4, horizon +$231D4 and the scene/association lists consistent.

For D1/D3, snapshot both representations and their discriminator, the selected target,
the synthetic camera when active, and the native camera history needed by that view.
Stage a consistent pose before projection/visibility work, then restore it before any
simulation. Recompute derived geometry from that staged pose without running camera
spring, TV-cut selection, replay advancement or A3 drawing side effects again. Hold
pointers, identities, flags and steering-image selection predicates at tick cadence;
segment crossing and lap wrap need native coordinate conversion, not pointer arithmetic.
D6/D8 must decide prediction and animation policies; this map does not implement them.

### A4 evidence and limits

`tools/state_map.py` verifies original input pins, decodes 15 selected native paths from
the relocated original (rejecting undecodable/incomplete ranges), then checks **250
camera-return snapshots**, 50 each from the retained A3 green, tow, follow, qualifying
and replay captures. It verifies each decompressed snapshot's hash and size, complete
frame coverage, source selection, four direct camera-word copies, both explicit X/Z
copies and their two precision reductions. Result: **PASS**,
`tmp/a4/state-map.json`. Negative probes reject a missing frame, a corrupt snapshot
and a changed camera heading even when its snapshot hash is updated. This reuses the
captured A3 build identities; it is not a new
runtime baseline or a timing measurement.

| Capture | View code | Pose source | Selected car | Frames |
|---|---|---|---|---:|
| Green | `$00` | h1+$816 | h1+$816 | 50 |
| Tow | `$A0` | h1+$256 | h1+$816 | 50 |
| Follow | `$A0` | h1+$256 | h1+$696 | 50 |
| Qualifying | `$00` | h1+$5D6 | h1+$5D6 | 50 |
| Replay | `$00` | h1+$5D6 | h1+$5D6 | 50 |

All five captured camera sources use explicit pose. Track-relative cars, TV cuts and
front chase are mapped from their native branches, not claimed as newly exercised UI
routes. A4 has an output requirement rather than a separate all-view play-test gate;
D7/G2 still require those routes after implementation. No game/slave or shared-tool
changes were needed for this map.

## Memory and the chip bus

`f1gp`'s hunk 0 (code) and hunk 1 (BSS) are `MEMF_ANY` and load into fast RAM when there
is any (slow RAM at `$C00000` on the A500-equivalent); hunk 2 (code and data, 269 KB) and hunk 3 (BSS, 86 KB) are `MEMF_CHIP`.
`tools/dma_census.py` over 50 fields of each `a1200-fast` window (`RACE_KEEP_TRACES=1`):

- The display is 4 lores bitplanes, 320 × 200 (`BPLCON0` `$4200`, `DDFSTRT`/`DDFSTOP`
  `$38`/`$D0`, `DIWSTRT`/`DIWSTOP` `$3581`/`$FDC1`, modulos 0, `FMODE` 0): 16,000
  bitplane slots per field, 22.5%. About 52–56% of slots are free.
- The CPU takes 14,742 chip slots per field in the follow window (20.7%): 8,532
  instruction fetches, all from hunk 2's code (hottest pages `h2+23000`, `h2+29000`,
  `h2+28000`, `h2+26000`, `h2+24000`), 3,036 data reads and 3,174 data writes, most of them
  to the two screen buffers.
- The two screen buffers (four 8,000-byte planes each) and the blitter's source masks lie
  in chip RAM just above hunk 2, consistent with hunk 3. Their plane pointers are 4 mod 8:
  aligned for a 32-bit AGA fetch (`FMODE` 1 or 2), not for 64-bit (`FMODE` 3).
- DMA reads only two parts of hunk 2 in these windows: the copper list at `h2+0000–0FFF`
  and audio samples at `h2+18000–1DFFF`. The blitter (1.3–2.2% of slots) works on the
  screen buffers and reads its sources above hunk 2.
- Hunk 2 interleaves variables with its routines (for example `h2+23126–231EA`,
  `h2+28168–281A0`, `h2+1E2DC–1E65A`, each right after an `RTS`). No write landed on an
  executed instruction in the three windows.

With WHDLoad's `CACHE` option the green window's work per frame fell from 71.7 to
63.0 ms (−12%) and CPU chip slots from 11.9% to 10.0%, so the 68020's instruction cache
is off under the supplied slave by default. (That run's race differed: green came 124
fields earlier and hunk 2 loaded `$A8` lower.)

## Frame pacing

The main loop ends each frame in a busy-wait at hunk 0 `$127C–$128B` (f1gp 582992 bytes):

```
0127c  move.w h0+125E,d0      ; fields since the last frame
01282  cmp.w  h0+125A,d0      ; this frame's minimum fields
01288  bcs.w  0127c
0128c  clr.w  h0+125E
01292  addq.w #1,h0+1260      ; frame count
```

The counter's only increment is at `h0+2CC3C`, in an interrupt routine at `h0+2CC38`
that ran exactly once per field (100 times in 100 traced fields). Before waiting, `$1272` copies the field counter to `h0+125C`, so that word holds the fields
the frame's work took. The code after the loop reloads the minimum from one of two 4-entry
word tables indexed by the frame count modulo 4: `h0+1262` (6, 6, 6, 7) or `h0+126A`
(7, 8, 7, 8). Which table applies depends on a chip-hunk word compared with 60, and a frame
whose work already took at least the table value keeps the old minimum. So the game holds
its frame rate to a fixed cadence instead of running as fast as the machine allows. Both
tables average 8 frames per second: 6.25 fields at 50 Hz, 7.5 at 60 Hz (the word compared
with 60 is presumably the display rate).

## Display publication (A5)

The race has two software screen addresses based on h0+$124A, separated by
h2+$231DA. The renderer reads its destination from h0+$1252; h0+$1256 remembers
that choice, while h0+$124E is the next requested display address. The tail of the
pacer, h0+$12F2–1332, chooses the complementary addresses and calls h2+$1DA62.
That routine writes the requested address to h2+$1DAAC, then sets pending byte
h2+$1DAB0. It **does not immediately change the displayed buffer**.

Publication is handled by the **copper interrupt**, not by the main-loop store and
not by h0+$2CC38's VBL handler. The level-3 dispatcher at h2+$2E4 tests COPER first
and calls h2+$60E. When pending, it calls h2+$1DA76, which rewrites the four pairs
of bitplane-pointer values in the copper list at h2+$0000 (plane stride 8000), then
clears pending. The list's interrupt request follows its late-screen WAIT. The new
pointer values are consumed when the copper next executes the list's opening moves.
Do not equate the pending-byte clear with proof that DMA has retired the previous bitmap.

The retained 50-field green, tow and follow profiles each contain 50 executions of
h2+$60E and eight executions of +$1DA76, matching eight pacer calls. This agrees
with one publication per native frame. The native 6–7-field cadence hides a hazard:
there is no pending-swap wait in h2+$1DA62. Two submissions before the copper services
them overwrite the single pending address; immediately recycling the other buffer
can draw into a bitmap still being scanned.

**50-fps publication rule for C2/D:** keep ownership of displayed, completed and pending
buffers explicit. Finish all CPU and blitter writes before submitting. Submit only the
completed off-screen bitmap; never overwrite a pending request. Before reusing the old
displayed bitmap, wait for acknowledgment **and the subsequent VBL / opening-list fetch**,
with at most one new submission per field. Use a monotonic field serial, not h0+$125E
which the pacer and keyboard path clear. If no retired buffer is available, wait or
skip the new picture. Modal/menu transitions must drain publication before changing
copper ownership. This is a design rule; no 50-fps publisher has been installed or tested.
The separate menu publisher h2+$36318 writes COP1LC and has its own pending state
(context +$2A3C); it must not be treated as the race's h2+$1DAB0 handshake.

## Interrupts and input (A6)

The game's race level-3 vector points to h2+$2E4, not directly to h0+$2CC38.
The dispatcher tests copper, VBL and blitter interrupt bits. VBL calls h2+$5DC,
which saves registers and calls h0+$2CC38; that callback increments h0+$125E at
+$2CC3C and returns with RTS. The outer dispatcher acknowledges VBL and returns
with RTE. Copper publication and the blitter command queue are separate branches
of the same level-3 dispatcher. The supplied slave's KickEmu/privileged-instruction
handling remains part of the measured interrupt path (the previously measured roughly
1.2% overhead); no interrupt-chain optimisation is installed.

The sound description needs a cadence distinction. h0+$36288 is inside
h0+$36246, called from the car-update path at h0+$2B952. Once per **frame**, it derives
a pitch increment, scales it by minimum fields / max(minimum, measured work fields),
and stores h0+$3A706. The VBL callback applies that increment to h0+$3A704 at
h0+$2CD02–2CD38 and updates Paula's channel-0 period, with a separate sound RNG.
The retained green/tow/follow 50-field profiles each count 50 calls to +$2CC38,
but only eight to +$36246 and +$36288. The +$2CD02 branch runs 50/0/50 times:
tow uses a different sound branch. C2 must retain both the per-tick increment calculation
and the per-field application, including the field-duration denominator.

| Input | Sampling / consumption |
|---|---|
| Keyboard in the race | Level-2 handler h2+$2D4 calls +$47E; +$488 reads CIAA ICR and +$4A8 reads SDR. The original slave's hook at +$4AC decodes the key and handles F10. The routine records pressed/released state in the key table h2+$52A. h0+$64 scans that table once per loop pass to form gameplay key masks. This is asynchronous acquisition with frame-rate consumption, not a once-per-VBL keyboard poll. |
| Keyboard acknowledgment | h2+$4E0 sets CIAA's serial-output handshake and starts CIAB timer B; h2+$5AA clears it on the level-6 timer interrupt. h2+$212–23E can wait up to ten VBLs for completion, clearing the game's elapsed-field counter in the process. |
| Joystick / digital mouse-counter input | h0+$34D24 is called from the race loop; the path at +$34E28 reads JOY1DAT and +$34E62 calls h2+$1D9F6. That helper reads JOY1DAT at +$1D9FC and the button at +$1DA38. Gameplay samples this path per frame/tick. |
| Analog control | The VBL callback alternates POTGO start at h0+$2CDD6 with POT1DAT read at +$2CDE2, accumulating values at h0+$3A928/+3A92A. Frame input processing uses the calibration words in h2+$2A658–2A662. This acquisition must keep running while rendering is skipped. |
| Menu input | Separate menu code uses OS events and a direct hardware path (h2+$2E4C0–2E548, +$324A6 and +$36166–3627E). The menu context and its field timers are separate from the race key masks and pacer. Preserve that ownership at mode transitions. |

For catch-up ticks, key-state scans and control consumption stay in native tick order;
edge-triggered view/pause handling still needs the A3 write audit. No input replay or
one-shot suppression has been implemented or validated by this mapping.

## Time sources (A1)

The gameplay RNG is **not seeded solely by a beam register**. There is a concrete
CPU-speed-dependent timing input before gameplay: the menu's busy-wait at h2+$31380
calls h2+$3652C repeatedly until the VBL counter reaches the menu's minimum. Faster
execution advances that RNG more times in the same field interval. A second wait at
h2+$3742C does the same. The RNG writes five bytes at h2+$2A794–2A798, reached through
the menu context's pointer to h2+$2A634. Its first longword is initially relocated
against hunk 1, so allocation layout is another input before any RNG draws.

At the protection prompt, h0+$8E4 reads h2+$2A797; h0+$8F0 advances the gameplay RNG
that byte **plus one** times (`DBF`). Removing the protection comparison does not remove
this RNG advance. Thus machine speed, CACHE and changed loader timing/layout can all
change the later race without changing any physics code. Identical field-count input
commands do not imply identical RNG state. Existing green captures have h2+$2A797
values `$53` (A500-equivalent), `$E7` (A1200), `$D6` (a1200-fast) and `$6D` (CACHE);
these are post-menu evidence, not the exact byte at the protection call.

**A1 gate:** the timing input is named: the number of menu RNG advances before each
VBL-paced wait ends, feeding the protection-time gameplay RNG advance. This explains
why CPU/CACHE comparisons are not tick-equivalence controls. It does not identify the
particular random decision that prevents the A500 player's retirement, nor prove there
are no additional causes. A VERIFY experiment must freeze this input before attributing
remaining differences to simulation changes; no pinning is installed in normal builds.

### Reader inventory

Offsets below were checked in the supplied 582992-byte executable, resolving relocation
target hunks rather than interpreting an unrelocated absolute operand as a runtime address.
The inventory distinguishes game readers from the KickEmu/OS implementation of clocks.

| Source and readers | Class / use |
|---|---|
| h0+$125E: h0+$1272, +$127C; h2+$232, +$27E98 | Presentation/hardware: elapsed work, frame wait, keyboard handshake timeout, renderer work/wait decision (at or above h0+$125A the scene skips its blit-queue drain). h0+$2CC3C increments once per VBL; h0+$128C and h2+$222 clear it. |
| h0+$125C: h0+$12A4, +$36288 | Presentation cadence and sound smoothing; no direct physics integration. |
| h0+$1260: h0+$1298 | Presentation: index modulo four into the PAL/NTSC cadence tables; increment at +$1292. It is a frame count, not a copy of elapsed fields. |
| Menu context A6 = h2+$37B44, +$2A40: h2+$31384, +$36308, +$36420, +$37430 | Presentation waits; +$31380 and +$3742C advance the menu RNG during those waits, indirectly influencing simulation. |
| Same context +$2A42: h2+$318A4 | Presentation/UI choice; free-running field count incremented at h2+$35FA4 / +$3601E (OS/direct interrupt paths). |
| Same context +$2A5C: h2+$2CE72, +$34C10, +$35FB0, +$36026 | Hardware/UI: countdown after DOS operations, decremented per field, used during OS handoff. |
| DOS DateStamp: h2+$2C88C, +$2D63C | Hardware/UI calendar state in context +$2A50, converted to date fields; separate from the race clock. |
| `$6C`: h2+$118 and +$34C70 install level-3 paths; +$34CDE–34CEE restore saved vectors | Hardware interrupt ownership. Game code uses the low vector table; no game `MOVEC VBR` found. KickEmu mediates privileged/OS interrupt handling. |
| CIAA SDR/ICR/CRA: h2+$488, +$4A8, +$4EE–512, +$5B4–5D0; menu +$36166–3627E | Hardware/input: keyboard serial data and acknowledgment. CIAB timer B is programmed at h2+$50C/+512; its interrupt releases the keyboard handshake. These are not physics clocks. |
| `$DFF004/6`, CIA timer-value and TOD registers | No direct absolute game reader found in either code hunk. The inspected custom/CIA-base paths implement input, DMA, audio, keyboard acknowledgment and interrupt dispatch. OS clock internals remain in KickEmu/Kickstart; this negative static result is not an exhaustive proof over dynamically computed addresses. |

### Random-number streams

All four routines use the same five-byte shift/XOR recurrence (right shifts of the
first and second words, XOR of their low bytes, shift the longword left by one byte,
append the fifth byte, replace the fifth byte with the result).

| Routine | State / seed | Classification |
|---|---|---|
| h0+$2572C | h0+$3A7B0–3A7B4, initial five bytes fixed in the executable | Simulation (cars, AI and race choices), also scene construction. Protection consumes a menu-dependent number of draws. h2+$1FE12/+1FE42/+2265E save the state, temporarily seed from h0+$12–16, then restore it at +$2027A/+22754. Those scoped draws must remain paired. |
| h0+$2575E | h0+$2578C–25790, fixed initial state | Sound: interrupt callers h0+$2CD3E and +$2CD6A add engine pitch jitter; separate from the gameplay state. |
| h0+$25792 | h0+$257C4–257C8, fixed initial state | Mixed simulation/presentation/sound callers: h0+$28BB8/+28C06, +$33BE6–33C68, +$3992E/+3A218; h2+$1D884–1D976 and +$2A144. Do not move these draws to an arbitrary presentation rate before A3 classifies their writes. |
| h2+$3652C (veneer +$325C2) | h2+$2A794–2A798 through context +$7CC; address-dependent initial longword | UI/presentation, feeding simulation via the protection seed byte. Direct callers +$31380 and +$3742C are VBL-bounded busy loops, not once-per-field calls. |

## Game time

The simulation advances a fixed step per frame; elapsed real time does not enter it.

- Besides the pacer itself, the only reader of the frame's elapsed fields (`h0+125C`) is
  `h0+36288`, which calculates the per-field engine-sound pitch step once per frame, scaling it by
  minimum ÷ elapsed fields, so the engine sound stays smooth when a frame overruns.
- The whole Quick Race (first cockpit field to the results screen, `tools/race_clock.py`)
  takes about the same number of frames on every machine while its real duration changes
  with the frame rate, and the in-game finishing times stay near 4:51–4:54:

| Machine | race fps | frames | fields to results | winner (game time) | game clock vs real |
|---|---:|---:|---:|---|---:|
| A500-equivalent | 5.49 | 3297 | 31557 (631 s) | Senna 4:53.111 | 0.70× |
| `a1200` (no fast RAM) | 7.23 | 3194 | 22914 (458 s) | Patrese 4:50.744 | 0.93× |
| `a1200-fast` | 8.00 | 3143 | 20301 (406 s) | Berger 4:54.233 | 1.02× |

  "race fps" is measured over fields 2000–14000; the last column is race fps × 128 ms.
  Game time per frame comes from an earlier `a1200-fast` race (Patrese 5:02.229), which
  compares the game's own frame counter with its race clock: green light to the
  "Race won by" banner took 2340–2372 frames for the winner's 302.229 s, 127–129 ms of
  game time per frame (200-field sampling at both ends; where the in-game clock starts
  relative to the green light is not established), so close to the pacer's 1/8 s.
- So the in-game clocks show game time. On the A500-equivalent a race shown as 4:53
  takes about 7:00 of real time; on `a1200-fast` the pacer holds the game at about real
  time. On slower machines the pacer seldom waits (A500-equivalent: work 7–13 fields per
  frame against a minimum of 6), so the game simply runs slower.
- The races differ between machines (on one machine a run repeats exactly, checked on
  `a1200-fast`), so the frame
  counts are not directly comparable.

Consequences for the goals: on `a1200-fast` and faster machines, faster code alone cannot
raise the frame rate while the pacer holds 8 fps, and removing the pacer would speed up
the simulation with it. Higher frame rates need the simulation step decoupled from the
displayed frame (AmigaXDev `docs/playbooks/fixed-time-simulation.md`); slower machines
need it to keep game time at real time.


### Native time step and F1GP-Ed's frame rate (F3 evidence)

The simulation's step is a variable, not a constant. The words at `h0+$34360–$34369` hold
`$0800 $1000 $2000 $2000 $2000` in the file (seconds × 65536, so `$2000` is 1/8 s), and
`h0+$3436A` is written at run time as 65536 ÷ the field rate (`h0+$34932`).

- `h0+$34366` scales the physics and AI: 30 `MULS`/`MULU`/`DIVS`/`DIVU` reads from
  `h0+$2762C` to `h0+$348F6`, including `DIVS` at `h0+$2BE70` and `h0+$2BF14`.
- `h0+$34368` gives the race clocks' per-update increments at session start
  (`h0+$25840`, read by the tick-clock routine `h0+$258A2`).
- `h0+$34364` is read at `h0+$36952` (selected by a car flag bit).

F1GP-Ed 3.44's frame rate (a setting saved into the file) uses this step; this comes from
static disassembly of F1GP-Ed, not from a run. Its local-speed-factor patch reads the
pacer minimum `h0+$125A` and the step `h0+$34364`, skips its frame-rate correction when the
step is `$2000`, and otherwise compares the step with a table indexed by the minimum
fields: `n × 1350` on PAL (20.6 ms a field) and `n × 1125` on NTSC (17.2 ms), `$2000` at the
default cadence. So a setting of n fields per frame sets both the minimum and a step of n
fields' game time:

| n | PAL fps | PAL step | NTSC fps | NTSC step |
|---:|---:|---|---:|---|
| 2 | 25 | 2700 (41 ms) | 30 (removed in 3.43) | 2250 (34 ms) |
| 3 | 16.7 | 4050 (62 ms) | 20 | 3375 (52 ms) |
| 4 | 12.5 | 5400 (82 ms) | 15 | 4500 (69 ms) |
| 5 | 10 | 6750 (103 ms) | 12 | 5625 (86 ms) |
| default | 8 (6.25 fields) | 8192 (125 ms) | 8 (7.5 fields) | 8192 |

When the machine keeps up the game stays near real time (about 3% fast, like the stock
clock); when it cannot, the game slows down. F1GP-Ed's guide records the side effects of
smaller steps: computer cars slower (its correction is 1.065× at 20 fps), the player's
car spinning in long races at 20–25 fps (presumably an overflow; not traced), and replays
and saves valid only at the rate they were made with. Not yet established: which of the
three `$2000` words F1GP-Ed writes (F1), and whether the native code also reads the
cadence tables `h0+$1262`/`$126A` it rewrites.

GPPatch 2.20's keys 1–6 (Toni Wilen; also in F1GP-Ed as "turbo keys") are different: its
routine at `$D1C` rewrites only the cadence tables, each word lowered by key − 1 (key 6:
1, 1, 1, 2 on PAL), and leaves the step at 1/8 s, so a machine that reaches the higher cap
runs the whole race faster than real time (the 030 at key 6 about 3.2×, from A8's no-wait
25.3 fps). Both tools patch from a process beside the game, which WHDLoad does not allow;
only F1GP-Ed's saved step reaches the slave.

### Elapsed-VBL world clock (C1)

**C1 is complete as a design.** The user selected elapsed vertical blanks for the
8 Hz world updates: no new CIA timer, no fractional physics updates and no scaling
of the native physics step. C2 installs the clock and separates the loops; no clock
hook or changed slave is part of C1. B5/A8's shared-profiler dependency remains open.

#### Source and ownership

Use a slave-owned, aligned unsigned 32-bit `field_serial`, incremented once in the
existing game VBL callback h0+$2CC38, beside the native increment at +$2CC3C. Preserve
that increment and all existing interrupt work. Count VBL callbacks only, not entries
to the shared level-3 dispatcher (which also handles copper and blitter interrupts).
Do not install another interrupt source or program CIA timer/TOD registers. Existing
keyboard handshake hardware remains under its native ownership.

The ISR is the only writer of `field_serial`; main code samples it with one aligned
`MOVE.L` instruction. Interrupts are taken between instructions, so the 68000's two
word bus transfers do not require a pair of separately interruptible word reads.
The future hook must preserve registers and CCR and retain the original callback's
return convention. The serial is never cleared by the pacer, keyboard or world-clock
rebase. Both h0+$128C and h2+$222 clear h0+$125E, so that native word cannot supply
lossless elapsed time; h0+$1260 counts frames, not fields.

At each active-world epoch, detect the physical display family from one complete
video-beam sweep, after synchronising to its wrap: a maximum line at or beyond 280
selects PAL (F = 50); otherwise NTSC (F = 60). Read VPOSR/VHPOSR and recheck VP8
before accepting the sample: the two bus accesses can straddle line 255/256.
The startup observation precedes the epoch's initial serial sample and therefore
creates no simulation debt. This uses neither host time nor a CIA timer.

The user approved this correction during C2. The proposed h2+$2A650 source proved
insufficient: it remained 50 under an actual NTSC display. The native pacer compares
it with 60, but that comparison does not establish hardware detection. Keep its raw
value and the observed beam maximum in C2 diagnostics; do not overwrite the native
word. A display-mode change requires a new epoch. The schedules use nominal 50/60
field rates, not a claim that physical fields are exactly 50/60 Hz.

#### Whole-field schedule

Keep an integer field credit and a small interval-table index. The repeating intervals
are PAL **7, 6, 6, 6** and NTSC **8, 7**. Starting with no credit at epoch field zero:

| Mode | First eight update deadlines, in elapsed VBLs |
|---|---|
| PAL | 7, 13, 19, 25, 32, 38, 44, 50 |
| NTSC | 8, 15, 23, 30, 38, 45, 53, 60 |

After E fields, the total updates due are `floor(8 * E / F)` if no time was dropped
or rebased. This formula is an independent check, not a required runtime multiply
or division. Each deadline runs one entire native update with unchanged constants.
There is no partial simulation step between deadlines. The PAL table is a rotation
of the native pacer's 6,6,6,7 table; starting with the longer interval ensures the first
update is not early. Do not run an extra free update on epoch entry. C2 must place the
epoch before the first scheduled update, using an already prepared scene if needed.

Main-code state consists of `last_serial` (32 bits), `field_credit` (0..F), `phase`
(table index), and VERIFY counters for observed, consumed, dropped and rebased fields
and completed ticks. The interrupt does no scheduling or simulation work.

1. Sample `now` once. Calculate unsigned `elapsed = (now - last_serial) mod 2^32`,
   then set `last_serial = now`. Re-reading the same serial adds zero.
2. Accept at most `F - field_credit` new fields, logging the rest as dropped debt.
   Compare elapsed with that free space **before** adding, to avoid 32-bit overflow.
   Retain the current table phase. The one-second cap includes partial credit and
   whole updates still owed, rather than allowing one second plus an extra remainder.
3. While credit covers the next interval, subtract that interval, run one complete
   tick in native order and advance the table index. Stop after four ticks per batch.
   Retain credit and phase across batches and pictures; finishing a picture does not
   reset either. Count a completed tick only after all its authoritative work finishes.
4. Observe the serial again at the next scheduling boundary. VBLs during simulation,
   rendering or publication waits accrue exactly once; do not replace `last_serial`
   with the tick-exit or draw-exit field without first accounting for that interval.

Within an epoch, `observed fields = consumed interval fields + field_credit + dropped
fields`. Without drops, once all due work has run, credit is less than the next
interval. A four-tick batch limit never silently discards the rest. Drops are recovery
from overload, not successful real-time operation. C2 retains its draw/publication
rule after each bounded batch; C6 measures whether slow machines can sustain the work.

Unsigned subtraction handles serial wrap provided observations are less than 2^32
active callbacks apart (over two years at either nominal rate). Main code never
resets the serial to manage wrap. Long inactive periods and handler/display ownership
changes require rebasing instead of interpreting their difference as race time.
A rebase samples the current serial, clears credit and phase, and starts with zero
ticks due. VERIFY closes the old epoch with its residual credit and records the reason
and excluded interval where observable, rather than hiding it in overload counts.
C3 determines the actual pause/menu/loading/replay boundaries; a scripted sequence
that natively advances the world must keep ticking. This clock must not independently
step the reconstruction paths at h0+$3CA5A / +$3CB82.

#### Interfaces and limits

C2 must stop the old pacer wait from also controlling enhanced loops while preserving
native consumers of h0+$125A/+125C. These words remain sound timing inputs, never the
new scheduler's debt or fractional remainder. The sound path at h0+$36288 uses
`minimum / max(minimum, measured fields)`; catch-up execution and zero-field spacing
need an explicit sound-duration policy and validation in C2. The per-field sound ISR
continues unchanged by this design. A5's buffer-retirement rule uses `field_serial`
for publication, independently of whether a world update was due. D may later use
field timestamps for presentation-only prediction; C1 introduces no predicted state.

A7 measures a native race-clock increment of **128.84521484375 ms per update**
(2111/16384 s), against the native 125-ms step. Eight updates therefore advance the
displayed clock by **1.03076171875 seconds per real second**; unmodified runs that reach
the 8-fps cap show the same ratio. The user chose to keep it: C5(a) measures the
world-tick rate (8.00 per second ± 1%), and the displayed clock's 1.031× ratio is
recorded separately as native behavior. C1 changes no race-clock constant, physics or
cadence.

Validation: `tools/test_world_clock.py` is a host executable specification, not game
code. Its five checks cover every field over 100 nominal seconds on PAL and NTSC,
irregular observations, unsigned wrap, repeated reads, fields arriving during work,
partial credit at the one-second cap, four-tick batches and epoch rebasing. The
independent due-count oracle is `floor(8 * E / F)`. All five pass. Static inspection
of the pinned game confirms the field-rate read, native counter increment/reset and
sound consumers; local disassembly is retained in `tmp/c1/clock-paths.txt`. No emulator
run, live hook validation, speed measurement or NTSC gameplay acceptance is claimed.


### C2 developer implementation — complete

The current prototype is compiled only for DEVELOPER/VERIFY, behind `CUSTOM2`
bit 1 and only in the supplied 582992-byte variant's patch list. Release bytes
remain identical to the pre-C2 build. The CPU HUD/background split, bounded loop and
sound-duration checks are complete. C3 adds the modal handoffs documented below; input
acceptance, whole-machine real-time validation and matched slow-machine performance
remain C4–C6 work. D's extrapolation is also separate.

The hook at h0+$2CC3C advances the slave's aligned 32-bit serial and reproduces the
native counter increment and flags. Live/replay heads at h0+$3C8F6/+$3CC40 reserve
whole ticks using the C1 integer schedule, one-second credit cap and four-tick batch
limit. The pacer replacement at h0+$1272 counts completed ticks and publishes after
the final tick in a batch. Other pacer callers retain native behaviour. Epoch entry
samples the display beam before starting the clock; the native rate word is retained
in diagnostics. `h0+$125A` receives the reserved interval and +$125C receives elapsed
fields since the previous tick start, capped at 32767; it does not receive clock debt.
The native sound path still applies its minimum/maximum denominator rule.

Each catch-up tick retains native camera evolution, geometry, visibility and the
A3 renderer side effects. Raster leaf gates suppress fills, sprites, clearing,
sky, cockpit sides, lights, hands and queued blits in the intermediate scene calls.
This preserves the native visibility predicate for debris and the order of pit/RNG
updates. The final tick paints normally. The replay R call at h0+$3CCFA is deferred to
publication, where h2+$1DFB4 paints once per published replay picture, including
zero-tick pictures. `CUSTOM4` bit 2 retains native painting as a same-build control.
Between ticks, the renderer can repaint
using staged entry values for the shared RNG, pit phases, debris latch, shake and
mirror request, restoring their authoritative post-tick values afterwards. No input,
camera evolution or HUD blink routine is repeated at picture rate. The D series stages
the predicted pose on top of this (below).

The field counter h0+$125E is cleared only at a tick, but the scene's h2+$27E90 skips
its wait for the blit queue to drain (h2+$27E98) once that counter reaches
h0+$125A. When pictures take one field each (a max-speed 030, the 040), a tick longer
than the reserved interval therefore drew its last repeat without the wait, and the
queued horizon blits landed on top of the CPU-drawn 3D for one field about every 25.
Each repeat therefore draws with the counter cleared at its own start, as a native
frame would, and adds the tick's fields back afterwards.

Publication waits for the pending copper request to clear and then for a subsequent
VBL before acquiring the complementary bitmap. It drains queued/active blits before
copying persistent pixels from the front to the retired back buffer and before
submission. Nine dual-bitmap HUD destination sites are redirected to the owned back
buffer while a tick runs. The CPU HUD raster regions are now queued while native request consumption and
text parsing remain tick work. The queue is drained before the final scene and
before publication, retaining the ordering of clears, copies, instruments and
glyph composition. Intermediate catch-up ticks do not paint these regions.

Local evidence is under `tmp/c2/`; each capture has its own build/source/runtime
identity. The older `normal`, `twin-dry-2` and `twin-raster` probes matched selected
A3/A4 authoritative ranges at tick 160, including all 26 car records and both RNGs.
They predate beam detection and are not current-build acceptance. `qualifying`
reached tick 160 and quit OK, but dropped 971 fields under overload; no real-time
claim follows. `ntsc-2` failed because the native rate word was 50 while the display
ran at about 60 Hz; this prompted the user-approved C1 detection correction.

With consistent beam sampling, `ntsc-stable-beam` selected 60 with maximum line 262,
reserved 160 ticks from 1200 consumed fields with zero dropped debt, and quit OK.
`pal-stable-beam` selected 50 and reserved 160 ticks from 1000 consumed fields with
zero dropped debt, then quit OK. `replay` reached its 40th replay tick, consumed 250
fields with zero dropped debt, and quit OK. These are bounded probes, not whole
replay or C5 acceptance. The pacer-entry snapshot has one fewer *completed* tick
because completion is counted inside the replacement pacer.

`replay-published` and `replay-native-paint` use the same build and hunk layout.
At replay tick 40, all selected authoritative A3/A4 ranges match: 26 car records,
view/source state, both RNGs, pit phases, debris latch, game clocks and camera/spring.
Their shared 50-field route window has 12 publications. The enhanced arm executes
12 R paints; the native-painting control executes seven. `c2_publication.py` accepts
the enhanced arm and deliberately rejects the control's missing paints between
publications. Both windows have one VBL callback per field, at most one publication
per field, and no CPU or blitter writes to the buffer read by bitplane DMA. This is
window-scoped evidence, not proof of all views, modal transitions or a whole replay.
The earlier cross-build comparison did differ in car/view/gameplay-RNG state and
is not used as equivalence evidence; startup timing must be controlled as in A1.

#### CPU HUD painting queue

Twelve raster regions are intercepted after native preparation: icons, dirty boxes,
box reuse copies, top-strip clears, digits, masked instrument images, text glyphs,
gear, packed RPM runs, assistance icons and conditional background clear/copy.
The background gates are at h2+$1DC84 and +$1DCBC; they retain prepared destinations
and copy extent, and leave the surrounding view/refresh state changes on the tick.
The native text parser still handles
control characters and cursor advancement; dirty-mask and blink state still evolve
once per tick. The RPM walker retains its address arithmetic and register outputs
while its stores are deferred. Each queued command holds its prepared registers,
text colours/mode and a raster-region identifier. The painter re-enters the native
region with a disposable stack frame, then restores authoritative text-parser state
and the HUD reuse flag after draining the queue. Asset pointers refer to immutable
native graphics; the front/back pair remains owned throughout a batch.

Boxes (Viewing, Riding with, Race won by and the other banners at h2+$1DF5C's nine
offsets) lie over the top rows of the view. Natively the HUD runs after every scene: it
draws a box once (h2+$1DDC0), then copies it from the front bitmap into each new picture
(h2+$1DEF6), so the scene never covers it. With the clock the HUD runs once per tick,
and a picture drawn between ticks starts from a copy of the front and draws the scene
over the box. The front then holds the damaged box, and the tick's own copies spread the
damage: in the external views the lower half of a banner stayed covered. The slave now
logs each tick's box draws and copies (offset and width) when they are queued, and
`c2_repeat_boxes` repeats those copies from the front after the scene of every picture
drawn between ticks. A box the last tick did not show is not copied, as natively.

The developer queue is bounded at 2048 commands of 96 bytes: **192 KiB** of additional
slave storage. It records current depth, high-water mark, queued/painted counts and
overflows. Overflow aborts with an explicit diagnostic rather than corrupting memory
or discarding painting. This storage and the CPU cost are not an optimisation claim;
C6/E still need matched machine measurements. Release bytes are unchanged.

`check_hud_hooks.py` traverses 665 native HUD/background instructions and rejects direct branch
or call targets inside a patch. Its negative fixture is the rejected glyph hook
placement. Earlier queue builds failed because hooks overlapped inner loop entries;
those captures remain failures. The initial 512-command queue also failed qualifying
at tick 22: its guard aborted after 512 pending glyphs. Both findings were fixed,
not relabelled as successful captures.

Selected-state probes with the corrected hooks pass for normal and forced-catch-up
quick races at tick 160 and replay at tick 40. The comparison now includes dirty
requests/deadlines, blink state, refresh flags, instrument history, text colours and
cursor/control state, and box reuse. The initial expanded comparison also included
h0+$3A706, which differed; this is the per-field sound pitch increment documented in
A6, not HUD state. Formula/cadence checks against elapsed fields now pass below;
raw equality across differing painting costs is not required. The failed report is retained.

`hud-qualifying-large` and `hud-qualifying-large-control` are the earlier HUD-build
qualifying pair at tick 160. Selected gameplay/HUD state matches, and their completed
32000-byte pictures are identical. The queued arm paints all 38,913 commands, peaks
at 825 pending commands and quits OK without overflow. It drops 1263 fields of debt
under overload, so this is not evidence of real-time operation. The earlier 512-slot
replay pair (`hud-replay-publish` / `hud-replay-control`) also has identical completed
pictures and selected state, but belongs to that smaller-buffer build. That build's
`hud-a500` probe reaches tick 160 and quits OK: 271 commands queued, 269 painted,
two pending at the pre-publication pacer boundary, and no overflow. It drops 41
fields of debt; this establishes functionality, not C6 performance. Wider
view/transition acceptance remains open.

#### Background, viewport and sound checks

Current-build regression captures all quit OK. `background-replay` and its control
match selected state and all 32,000 picture bytes at replay tick 40. The
`background-qualifying-current` pair does the same at tick 160, painting 38,915
queued commands with a peak depth of 825 and no overflow. Qualifying drops 1263
fields in the enhanced arm, so this is not real-time acceptance. TV and front-chase
probes confirm native view codes `$C0` and `$B0`. The current `background-a500`
probe reaches the tick-160 pacer with 273 queued commands, 271 painted and two
pending; it quits OK with no overflow, but drops 31 fields. This establishes
functionality only; C6 still needs matched machine measurements.

The native external-view path h0+$3C286 adds 640 bytes to h0+$1252. C2 now
resets that pointer from the owned base h0+$1256 at every tick, applies the offset
once for a zero-tick repeated picture, and publishes the base rather than the
viewport. Dual-bitmap HUD destinations also use the base. This prevents cumulative
viewport offsets within catch-up batches and shifted copper submissions.

Current VERIFY build:
`607b892640250e433b6e3c4e47182d473d96bc9d08cae523d8d3a06f86066acf`.
The same-build rear-view normal and delayed pairs (`background-rear*`) match all
selected state ranges and all 32,000 completed picture bytes at tick 160. Both
background-clear and background-copy counters are exercised. Delayed enhanced mode
completes 120 dry scene passes and drops 211 fields; the control drops 368. These
are diagnostic workload controls, not a matched performance claim.

Publication audits require actual bitplane DMA ownership, CPU/blitter writes,
one VBL callback per field, at most one submission per field and complete
publication intervals. Current passing windows include PAL live `background-green`
(13 submissions/50 fields), NTSC live `background-ntsc` (11/50), rear view
`background-rear` (10/50), delayed rear view `background-rear-delayed-100` (3/100),
and `background-replay` (13/50, with 13 replay R paints). None writes to the scanned
bitmap. Two earlier delayed 50-field windows had only one publication and failed
the coverage gate. They remain failed; the 100-field window supplies the missing
complete intervals without relaxing the gate.

`c2_sound.py` validates the actual serial-difference handoff to h0+$125C and the
native minimum/max-duration pitch formula at h0+$36288–362AA. PAL live, NTSC live
and delayed rear-view windows pass with nonzero pitch inputs, overrun and short
spacing cases, and one VBL per field. The delayed 100-field window has 12 checked
pitch calculations, three overrun and nine short-spacing cases. An idle-only window
is INCOMPLETE, never accepted as nonzero-pitch coverage. These checks do not claim
audio quality or all sound branches.

The current disabled-feature suite `tmp/b4/c2-final-acceptance.json` passes release,
developer, VERIFY-off and VERIFY-relay controls, each with eight native ticks/draws
in 50 fields and clean quit. Negative checks independently reject all 246 optional
hook bytes, stale metadata, malformed declarations and an enabled relay disguised
as off. Release SHA-256 remains `93dde23f76df6dab0ca3beea3507e29e25fb5e6a6bb3b06dab2e8697c4c75495`.

## Current measurements

`a1200-fast` (68020, 8 MB fast RAM, PAL), three 500-field windows (10 s each) from the
deterministic Quick Race (`tools/race_profile.py`, development doc). Times are emulated;
"work" is a frame's cycles outside the pacer's wait loop, interrupts included.

| Window (anchor) | fps | frame ms mean / p95 / max | work ms mean / p95 / max | pacer wait |
|---|---:|---|---|---:|
| green light | 8.00 | 125.1 / 140 / 140 | 71.7 / 82.1 / 85.2 | 42.7% |
| retirement and towing | 8.02 | 124.8 / 140 / 140 | 96.5 / 106.1 / 127.0 | 22.3% |
| follow camera | 8.03 | 124.6 / 140 / 140 | 84.1 / 103.2 / 128.0 | 32.0% |

- The frame rate is the pacer's cadence (6–7 fields per frame) in all three windows, not
  the machine's limit: no window's mean work fills its frame.
- The per-frame work runs under `h2+280F6` (46–63% of all cycles inclusive), which lives in
  hunk 2. That hunk is declared chip memory, so on this machine 27–34% of all cycles
  execute from chip RAM.
- DMA: about 57–62% of chip-bus slots are free; blitter 1.3–1.8%; bitplanes 22.5%.
  The CPU never stops (`STOP` 0%).
- Function names are hunk offsets of the nearest preceding call target, a heuristic; a
  large entry needs checking against the disassembly before acting on it.

### C3 modal clock boundaries

**C3 is complete.** It keeps native modal ownership while the developer clock is enabled. It uses the
same `CUSTOM2` bit 1 and supplied executable gate as C2. There is no new timer,
fractional update, release option or change to the eight-update schedule.

| Boundary or sequence | Clock ownership and implementation |
|---|---|
| Start lights | Remain live ticks. h0+$3B346 calls the start-state machine +$3B3B0; +$3A750 selects its phase, +$3A764 its native game-time deadline and +$3A73A its tick countdown. No pause/rebase is introduced between red and green. |
| Pit service, tyre UI and pit animation | Stay in native session/car/HUD/renderer tick order. C2 retains the A3 pit phases and dirty-state updates even when an intermediate tick is not painted. Being stationary in the pits is not a clock suspension. |
| Native accelerated time inside the pits | h0+$3BA24 calls the unpaced native loop +$3CA5A. Suspend the outer reserved tick around this call; the native loop advances its own session/car state. On return, exclude its elapsed VBLs and continue that reserved tick once. Never add scheduler updates inside the accelerated loop. |
| Retirement, tow and following another car | Continue the live tick stream. The native car/session/view state machines choose removal, marshal/tow animation and the following camera. These transitions do not start new clock epochs. |
| Live pause | The actual wait entry h0+$3B6DE suspends the clock; the wrapper at +$3C962 resumes it after native +$3B5DE returns. Merely polling the pause key does not rebase. |
| Replay pause | The wait entry +$3B8B4 suspends; the wrapper at +$3CCBA resumes after native +$3B80E returns. Calls from the unpaced reconstruction path retain native ownership. |
| Replay entry | +$3CBD6 closes the live epoch before native replay restoration. +$3CC40 starts a fresh replay epoch, after detecting the actual display rate. |
| Natural replay completion | Native +$3CCB6 branches into +$3C962, bypassing the live loop head. Its wrapper closes the replay epoch before native live pause handling; after resume it reserves a fresh live tick before any car update. The native pause remains visible until the user resumes. |
| Escape, race end and results | +$3CA26 closes the epoch before native interrupt/audio handoff. Pending HUD work is flushed and publication retired. Native menus/results run with enhanced tick and raster gates inactive. |
| Loading, menus and cockpit re-entry | No enhanced tick runs outside live/replay loops. +$3C8D2 closes any old epoch before native one-time cockpit preparation. Re-entry detects display rate and starts from zero credit; the +$3C962 bypass is covered too. |
| Menu accelerated-time batches | The separate +$3CB6A / +$3CB82 path runs after live exit, with the clock inactive. Its native fifty-update batches are unchanged. |

At an in-tick suspension, publish queued UI work, wait for the pending exchange and
its following VBL, and drain the blitter. Observe active time up to this boundary,
then move residual credit into `c3_rebased` and clear credit, phase and batch.
Clear `c2_in_tick`, `c2_draw_mode` and scene-history validity so native modal code
owns its painting. The already reserved tick is neither completed nor repeated.

On resume, acquire an owned bitmap, move `WC_LAST` to the current serial and count
the excluded interval in `c3_excluded`. Restore a normal painted tick, not an
intermediate catch-up pass. Reset the sound interval origin and set h0+$125C to the
reserved interval at +$125A; paused fields must not stretch the next engine-pitch
ramp. Completion of the reserved native tick then uses the ordinary C2 pacer.
The next reservation starts with the first whole PAL/NTSC interval, with no backlog.

Accounting within a continuing epoch is now:
`observed = consumed + credit + dropped + rebased` (unsigned 32-bit counters).
Modal exclusion is separate from overload drops. Suspension and epoch close reuse
the exact `WC_LAST` sample as their excluded-interval origin, so a VBL between
accounting instructions cannot disappear between two samples. At epoch exit, `c3_closed_clock`
retains the 28-byte clock plus rebased fields, the reserved-tick flag, old mode and
reason: 1 restart, 2 replay entry, 3 replay completion, 4 race/menu exit. A reserved
iteration abandoned by a native branch remains identifiable as reserved, not falsely
counted as a completed tick. This is the last closed epoch, not a history ring.
`c3_epochs`, `c3_exits`, `c3_pauses` and `c3_reconstructions` count transitions.

The serial remains owned by the native race VBL callback. If a menu or loading path
removes that callback, elapsed wall/display time there is not observable through this
serial. It is still excluded by epoch entry; `c3_excluded` reports only observable
callback intervals and must not be described as the duration of every menu visit.
The new mode becomes visible only after rate detection and clock initialization.

#### C3 evidence

Current VERIFY build: SHA-256
`330662b72ba7c19d049a0eb68cb522cbe668e27470a9ccfd24df561465273b97`,
source SHA-256 `a5ef57b5535c11637629f0fe492e245c571788427ffbf1e1c0d69871993f8ddd`.
All routes below use pinned deterministic boots, actual loaded hunk addresses and
native input. Each completes with F10 `OK`. Evidence is under `tmp/c3/`.

| Capture | Result |
|---|---|
| `v2-pause` | Two PAL pauses: car state and clock unchanged across each 250-field hold. Exact resume stops retain the pending tick, zero credit/phase/batch and reset the sound interval. 647 callback fields excluded in total; no debt drops. |
| `v2-ntsc` | Same checks at detected 60 Hz; 646 callback fields excluded, no debt drops. |
| `v2-delayed` | Same checks with the 20-field batch delay. 661 callback fields excluded and 76 residual-credit fields rebased. The run has 42 workload debt drops; the exact resume checks require no drop increase during suspension. |
| `v2-a500` | Same checks on the 68000 `a500-1.5m` setup. 647 callback fields excluded, 62 credit fields rebased, no drops in this window. Not a C6 performance result. |
| `v2-menu` | Qualifying Frozen holds cars and clock unchanged for 250 fields; re-entry starts epoch 2 with no debt drops. Only 35 callback fields are observable outside the old epoch; the race callback is inactive for much of the menu/loading interval. |
| `v2-pause-menu` | Escape while paused, frozen-menu dwell, cockpit return still paused, then Space resume. A new live epoch starts without backlog; no free update is inserted on the bypass path. |
| `v2-pit` | Native joystick acceleration enters and leaves +$3CA5A. Car state changes while enhanced clock accounting stays frozen. Return excludes 343 callback fields and rebases 46 credit fields. The existing 161 qualifying overload drops stay 161 through this transition. |
| `v2-replay` | Live pause → replay → replay pause/resume → natural replay completion → live pause/resume. Three epochs, two explicit closes, no debt drops in the final live epoch. |
| `v2-race` | Green lights at completed tick 135, retirement/tow Viewing at tick 817, results after 3071 completed ticks. One live epoch, one exit, zero dropped fields. A further 250-field results hold leaves the clock unchanged. |

These results establish modal ownership and rebasing, not C4 input acceptance, C5's
clock calibration/equivalence or full pit-stop acceptance, C6 performance, or G2's
all-CPU/all-route regression matrix. The native accelerated-time route is not counted
as an eight-Hz world interval. C5's native clock-rate discrepancy remains unresolved.

Failed exploratory captures remain INCOMPLETE rather than being relabelled:
`menu-1` sampled the Entering Cockpit transition too early; `menu-2` caught rate
initialization before the mode-publication adjustment; `race-1` reached results but
missed green with coarse sampling; `pit-1` used a keyboard accelerator while the game
was configured for joystick; `pit-2` incorrectly required stable queue totals during
an active flush. Corrected routes use state/screen anchors, native joystick input and
quiescent accounting checks. Earlier `pause-1`/`replay-1` validate the earlier build
only and are not substituted for the current-build results.

The `v2-pause`/`v2-repeat` pair repeats exactly: pinned configuration/build,
loaded layout, screen route, clock/car snapshots and every corresponding screenshot.
`c3_report.py` verifies retained snapshot hashes and closed-epoch accounting, including
the reserved iteration at replay completion and paused Escape. The native session
snapshot (including game clock state) also stays unchanged during each held pause/menu.

The fresh four-arm suite `tmp/b4/c3-v2-acceptance.json` passes: release, developer,
VERIFY off and VERIFY relay-on, with clean quits, loader checks, and independent rejection
of all 288 optional hook bytes plus the existing malformed/stale/option negative cases.
The release SHA-256 remains
`93dde23f76df6dab0ca3beea3507e29e25fb5e6a6bb3b06dab2e8697c4c75495`.
The C3 static audit checks seven call sites and 405 original instructions, including
an interior-entry negative fixture; the 665-instruction HUD audit and five host clock
tests also pass. Shared AmigaXDev files are unchanged.

The final-build steady window `v2-steady` also passes the C2 regression reducers:
50 VBL callbacks, 12 publications, 11 complete publication intervals, 185448 CPU
bitmap writes and 82284 blitter writes with no writes to the scanned bitmap. All eight
nonzero pitch updates pass the sound formula, including four overrun and four short
intervals. These are window-scoped publication/sound checks, not C5/C6 acceptance.
The combined current-build record is `tmp/c3/acceptance.json`.


### C4 input acceptance — gate passed

The C3 slave still uses the native input readers. Live h0+$3C94A calls h0+$64
once per tick; h0+$3C950 calls the controller reader +$34D24 before control processing
and simulation. Replay scans at +$3CC8E and then restores recorded control input at
+$3CC94. Picture-only repetitions do not scan input. Analog acquisition retains its
VBL ownership described in A6.

View commands use active-low masks and native edge latches h0+$3A915. For example,
raw key `$4F` maps to bit 5 of h0+$1C. h0+$3C0D0–3C10C emits bit 5 of h1+$23E on
a newly sampled press, suppresses it while held, and rearms the latch when a released
state is sampled. The pause path reads the configured key h0+$3A90E through h2+$51C,
waits for release at h0+$3B6E4, and waits for a new press at +$3B7BA. These are state
checks, not queued events.

The keyboard IRQ writes `$B3` on press at h2+$4CE and zero on release at +$4C4 to
h2+$52A indexed by raw key. No pending-press record survives a completed release.
Consequently a press and release between native scans can be missed. Retaining native
sampling and requiring lossless one-shot presses need an explicit policy: buffer the
one-shot events for native consumption, or accept the original short-press limitation.
The user chose buffering.

**The buffer.** Developer/VERIFY builds with `CUSTOM2` bit 1 hold a key change back
until a native per-tick scan has seen the state before it. The slave's existing keyboard
hook at h2+$4AC (after the native decode, with A0 at the key table) keeps a state byte
per raw key: physically down, shown state not yet scanned, release pending, press
pending. A release of a press that no scan has seen, or a press after a release that no
scan has seen, is recorded and the native store skipped (D0=$FF takes the native
handler's existing branch past the store). The live and replay scan calls h0+$3C94A
and +$3CC8E now enter `c4_scan`, which applies at most one pending change per key
before the native scan h0+$64 runs, with the keyboard interrupt masked in INTENA.
A tap is therefore shown pressed for exactly one tick: the scan and every reader in that
tick (the pause check h0+$3C962, view latches) see it, and the next scan sees the
release. A key held across a scan behaves natively. A press–release–press before a scan
is delivered as two presses on successive ticks; further taps before those are shown
merge.

Deferral is live only from a scan until the loop suspends (`c3_suspend`), enters a pause
wait (`c3_pause_begin`) or leaves (`c3_leave`). Each of those flushes every key to its
physical state, so native loops that poll keys without tick scans (pause, menus) never
see a held-over press. With the option off, no scan hook is installed and the keyboard
path is native; release builds contain none of this code and keep their SHA-256.

**Evidence with the buffer.** `tmp/c4/buffered` and `buffered-repeat` run the same probe
on VERIFY `e4cb8540403d2bbf795625d9be02e88bc1a6ec63bc61deac2be37ac0260df9ac` (`CUSTOM2=3`,
`CUSTOM4=3`, `a1200-fast`, PAL). The short `$4F` tap arrives during the forced 20-field
delay at serial 340 with 40 completed ticks; the release IRQ is held back (key table
still `$B3`, one deferral). The scan at serial 361 sees the press and the view consumer
emits bit 5 once. The next tick's scan (41 ticks, serial 364) shows the release (one
applied change), and its consumer emits nothing and rearms the latch. Held view and
joystick checks pass as before. `tmp/c4/buffered-report.json`: acceptance PASS, exact
repeat PASS; both runs quit with F10 `OK`. The four-arm disabled-feature gate passes
again (`tmp/b4/c4-acceptance.json`), rejecting mutations of all 300 optional hook bytes;
`check_modal_hooks.py` checks both scan call sites.

**Before the buffer.** `tmp/c4/input-2/` captures the C3 VERIFY slave (`330662b72ba7c19d049a0eb68cb522cbe668e27470a9ccfd24df561465273b97`)
on `a1200-fast`, PAL, `CUSTOM2=3`, `CUSTOM4=3`. It uses real harness key/joystick
input and read-only breakpoints, with the existing 20-field batch-delay diagnostic.
The probe anchors to completed tick 30; all serial values below are observations from
this capture, never route anchors for another build or machine.

- A held `$4F` command produces exactly one view event across five consecutive ticks,
  including tick-only catch-up passes. The initial IRQ arrives after that tick's mask
  scan, so the command correctly takes effect at the following scan. An initial probe
  (`input-1`) incorrectly demanded an event before that scan; it remains INCOMPLETE.
- The native controller reader records right stick as `$08` and release as `$00` on
  successive catch-up ticks, with completed-tick counts 36 and 37.
- A short `$4F` press is recorded by the IRQ at serial 339 and its release at 340,
  both with 40 completed ticks. The next native scan and view consumer at serial 361
  still have 40 completed ticks: the mask is all released and there is no view event.
  This **fails** the no-lost-one-shot requirement. The event is lost in the native
  state table, not in the harness, and is not an AmigaXDev profiling issue.
- `tmp/c4/input-repeat/` repeats the configuration, route, layout and every saved
  input snapshot exactly. Both captures finish and F10 quits with `OK`. The combined
  result is `tmp/c4/acceptance.json`: exact repeat PASS, C4 acceptance FAIL.
  `tools/c4_report.py` independently
  verifies the saved state hashes, decoded masks/latches, consecutive ticks and event
  result. A successful capture is deliberately distinguished from failed acceptance.

**Acceptance suite on the 68030/50.** `tmp/c4/suite-030` and `suite-030-repeat` run
`--input-suite` on the same VERIFY build (`e4cb8540403d2bbf795625d9be02e88bc1a6ec63bc61deac2be37ac0260df9ac`) on `a1200-030` without an MMU
(effective CPU 68030, MMU 0; `NOMMU`; caches on), PAL, `CUSTOM4=3`. Each tap is a real
press and release between two scans, during the forced delay:

| Check | Result |
|---|---|
| All seven view keys: cursor up/down (previous/next car, request bits 7/6), keypad 7 (player car, 3), cursor right (cockpit, 4), cursor left (TV, 5), Help (rear chase, 2), Del (front chase, 1) | Each mask bit is pressed for exactly one scan, its request bit is set once, and the next tick shows the release and rearms the latch |
| Double tap on cursor left before one scan | Two TV requests on alternate ticks (59 and 61), released and rearmed on 60 and 62 |
| Space (pause) tap | The tick's pause check pauses the game; the flush shows the key released and stops deferral; the native wait holds for 250 fields with the clock unchanged; a new tap resumes and the game does not pause again |
| Cursor left tap in a replay (pause, R) | One TV request in the replay loop, released and rearmed on the next replay tick |

`tmp/c4/suite-030-report.json`: all ten checks PASS, exact repeat PASS (configuration,
route, layout and every saved snapshot); both runs quit with F10 `OK`. Held pause
behavior also has C3 modal evidence. Three or more taps before the buffered ones are
shown merge into those two; this needs taps faster than one per tick during catch-up.
No release bytes, clock cadence or shared tooling changed.

### C5 real-time acceptance

#### C5(a) world-tick rate — passes on the 68030/50 and the A1200

`--rate` runs a whole Quick Race with no input from the cockpit stop to the results and
samples the slave clock and h0+$3A714–3A7D3 every 250 fields (`tools/c5_capture.py`).
Real time is emulated time: every sample sees beam maximum 312, so a PAL field is
313 × 227 colour clocks at 3,546,895 Hz (20.032 ms, 49.92 Hz). The schedule funds
8 ticks per 50 *nominal* fields, so the expected rate is 7.987 per second (−0.16%).
A window between samples fits the CPU if it drops no debt. The rate is measured over
fitting windows; each contiguous fitting run is allowed one second of credit and one
reserved tick of boundary error at either end, and PASS requires the error plus that
bound within ±1%. A run with too little fitting time to measure within ±1% is
OVERLOADED: outside the gate's envelope, neither a pass nor a rate failure.

The displayed race clock is the session accumulator h0+$3A77C (milliseconds) with
fraction word +$3A780; h0+$258A2 adds h0+$3A7DE/+3A7E2 to it once per tick.

VERIFY `e4cb8540403d2bbf795625d9be02e88bc1a6ec63bc61deac2be37ac0260df9ac`, `CUSTOM2=3`,
`CUSTOM4=1`, PAL, Quick Race. Every run repeats exactly and quits with F10 `OK`:

| Machine | Live fields | Ticks | Dropped | Ticks per second | Race clock per tick | Race clock ÷ real time | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| `a1200-030` (68030/50, no MMU, caches on) | 20000 | 3200 | 0 | 7.987 (−0.16%, bound 0.56%) | 128.845 ms | 1.029 | PASS |
| `a1200` (68020, Chip RAM only) | 20000 | 3200 | 0 | 7.987 (−0.16%, bound 0.56%) | 128.845 ms | 1.029 | PASS |
| `a500-1.5m` (A500-equivalent) | 22250 | 2955 | 3756 | 6.63 overall | 128.845 ms | 0.853 | OVERLOADED |

The race clock advances exactly 2111/16384 s per tick on every machine. Its ratio to
real time is 1.0308 × 49.92/50 = 1.029 when the ticks keep up (the native 1.031×
ratio, user decision). On the A500-equivalent the ticks do not fit the 68000: 87 of
89 windows drop debt (17% of the fields), so the world runs at 0.83× real time. The
two fitting windows (77 ticks) are too short to measure. This is the C6 debt-cap
question, not a C5(a) failure.

On the 030, 6263 pictures are published in the 20000 fields (3063 of them repeated
pictures between ticks): about 3.2 fields per picture, so its normal drawing is not
one-field drawing.

Evidence: `tmp/c5/rate-{030,a1200,a500}` with `-repeat` twins, and
`rate-*-report.json`. `rate-a500-old-label` is the same A500 race saved before
OVERLOADED was distinguished from FAIL.
No quick-race car pits (the pit-animation words h0+$3A746–3A74C stay `$8000`), so a
pit stop is not covered by this race.

#### C5(b) tick-aligned state — passes, one difference classified

`--states` stops at every completed live tick's pacer entry until the race closes its
epoch, and saves the ranges the native replay checkpoint (h0+$396AC) copies: car records
and session h1+$368–1955 and h0+$3A714–3A7BB. gdb appends them at each stop and
continues by itself, so a whole race takes about 2.5 minutes. It also records the A1
timing inputs at the route stop: the UI random stream h2+$2A794–2A798 and the gameplay
stream h0+$3A7B0–3A7B4. `tools/c5_compare.py` verifies every record's hash and compares
the runs at each common tick.

All runs use the same VERIFY build, `a1200-030` without an MMU, PAL, Quick Race, and quit
with F10 `OK`:

| Run | Schedule | Ticks | Fields per picture | Catch-up | Dropped | UI stream at route stop | Against normal |
|---|---|---:|---:|---|---:|---|---|
| normal | `CUSTOM4=1` | 3210 | 3.19 | none | 0 | `58b5dea1f1` | reference |
| normal repeat | `CUSTOM4=1` | 3210 | 3.19 | none | 0 | `58b5dea1f1` | identical at all 3210 ticks |
| slowed | `CUSTOM4=3` (20-field batch delay) | 3208 | 27.1 | 2406 tick-only passes, batches of 4 | 1651 | `58b5dea1f1` | identical at all 3208 common ticks |
| one-field | `CUSTOM4=1`, fastest non-cycle-exact CPU | 3194 | 1.37 | none | 0 | `0da44de2c2` | differs from the first tick |

Normal and slowed drawing give identical car and session state at every tick of the
race, including over 2400 undrawn catch-up ticks and dropped debt. The one-field run's
difference is **classified as an A1 timing input not held equal**: its menus run faster
(protection screen at field 635, not 687), so the UI stream, drawn in VBL-bounded menu
busy loops and feeding the simulation through the protection seed byte, enters the race
in a different state. The race itself is therefore a different race, not a drawing
effect. The emulator cannot change CPU speed after the menus, so this run cannot hold the
A1 inputs equal. A faster cycle-exact clock (200 MHz) barely shortens the 030's pictures
(3.0 fields per picture over 160 ticks, `tmp/c5/hz-200`), since Chip RAM and blitter work
bound them; the fastest non-cycle-exact CPU reaches 1.2–1.4 (`tmp/c5/hz-max`).

Evidence: `tmp/c5/states-{normal,normal-repeat,slowed,one-field}` and
`tmp/c5/states-comparison.json`. `tmp/c5/states-v1` holds the first set, without
the recorded A1 inputs, with the same results; `states-normal-stopped` is an
abandoned slower capture that stopped at each tick through the client.

#### C5(c) played through — passes for the accepted scope

The C3 modal routes run again on the current VERIFY build on `a1200-030` without an MMU,
PAL, `CUSTOM4=1`. Each route is captured twice; `c3_report.py` verifies every saved
snapshot and the exact repeat (all PASS), and every run quits with F10 `OK`:

| Route | Result |
|---|---|
| Whole race (`modal-race`) | Green at completed tick 139, retirement/tow Viewing at 701, results after 3215 ticks. One live epoch, zero dropped and zero excluded fields; a 250-field results hold leaves the clock unchanged. The C5(a) races also run cockpit to results. |
| Replay (`modal-replay`) | Live pause, replay entry (new epoch), replay pause held 250 fields with state unchanged, exact resume rebase, natural replay completion back into live pause, live resume. Three epochs, 663 callback fields excluded, zero dropped. |
| Pit (`modal-pit`, qualifying) | Native accelerated time in the pits: car state advances while the clock stays frozen, 50 credit fields rebased, 300 callback fields excluded on return. |

Pit-stop coverage is the user-accepted scope: the practice pit-box start was observed
interactively (tyre choice, fire confirms, the crew steps away and the car is released;
the pit-animation phases stay `$8000`, `tmp/c5/explore/`), plus native accelerated time
in the pits above. A service after driving into the box is not exercised.

**Finding for C6/E:** the 030 does not keep up in the qualifying pit garage. Over the
route's 400-field wait before the pit check it completes 39 ticks, drops 115 fields of
debt, then one more (`modal-pit-a`). Races drop nothing. Earlier `a1200-fast` qualifying
captures dropped 161–1263 fields, so the garage scene is a known heavy case; it is a
performance target, not a C5 rate result.

Evidence: `tmp/c5/modal-{race,replay,pit}-{a,b}` and `modal-*-report.json`.

### C6 slow machines — complete; the 68000 keeps the native pacer

Whole Quick Races with `--rate --scenes` (VERIFY `e4cb8540…`, `CUSTOM4=1`, PAL) classify
each 250-field window by the game's view state h1+$238/+23C: cockpit, the tow (the first
car viewed from outside after the cockpit, the retirement/tow sequence) and following
other cars. Pictures are `c2_pictures` per field. All runs quit with F10 `OK`:

| Machine | Cockpit fps | Tow fps | Follow fps | Ticks per second | Dropped fields |
|---|---:|---:|---:|---:|---:|
| A500-equivalent (`a500-1.5m`) | 1.73 | 1.53 | 1.65 | 6.92 / 6.07 / 6.60 | 13% / 24% / 18% |
| A1200 (`a1200`) | 9.51 | 6.70 | 7.27 | 8.00 | 0 |
| 68030/50 (`a1200-030`), for reference | 16.88 | 16.67 | 15.29 | 8.00 | 0 |

Against the plan's projection: the **A1200 meets it**. It runs at real time throughout,
7.7 fps over the race (6.7 in the tow window), where the original game shows 7.2–7.7 fps
at 0.93× speed. The **A500-equivalent falls far short**: about 1.65 fps at 0.83× real
time, where the projection was 5.2–5.6 fps at 1.0× and the original game shows 5.5–5.8 fps
at 0.70×. Its debt cap drops 13–24% of the fields in every scene, so world time is lost
everywhere, not only in the tow window.

The projection assumed that an undrawn tick costs only the per-car update. A 100-field
A500 profile at tick 300 (`tmp/c6/a500-profile`, `tools/c6_profile.py`) shows otherwise:

| Routine | Calls | Per call | Share of the window |
|---|---:|---:|---:|
| Scene call (raster leaves gated on undrawn ticks) | 12 | 104.1 ms | 62.5% |
| Per-car update h0+$2AC14 | 12 | 38.9 ms | 23.4% |
| `c2_acquire` (32,000-byte front-to-back copy, VBL wait) | 3 | 47.0 ms | 7.0% |
| Everything else in the loop | | | under 3% each |

An undrawn tick still runs the renderer's geometry and visibility, which C2 keeps for the
per-tick side effects (debris visibility, pit phases, shared RNG and camera shake; A3).
Gating the raster leaves saves only about a sixth of the native 124 ms drawing cost, so a
tick costs about 145 ms (7.2 fields) against 6.25 available: the 68000 cannot run the
world at 8 Hz even without drawing. Making it fit would need those side effects
separated from the scene geometry, so that an undrawn tick costs little more than the
car update.

Evidence: `tmp/c6/scenes-{a500,a1200,030}`, `tmp/c6/a500-profile` and
`a500-profile.json`. `tmp/c6/discarded` keeps two runs that classified scenes from
screenshots (Viewing banners are too brief) and lost F10 while the results menu
loaded; the rate capture now waits for that menu before quitting.

**Decision and implementation.** The user chose the original frame-locked behaviour as
the 68000 default. The clock hooks (the former `PL_IFC2X 1` block) are now a separate
patch list, `patch_582992_clock`, applied by a second `resload_PatchSeg` only when
KickEmu's `_attnflags` shows a CPU above the 68000 (AFF_68010), or when the new
developer bit `CUSTOM2` bit 2 forces it for testing. The hooks, their ranges and the
clock's behaviour are otherwise unchanged. Release bytes remain
`93dde23f76df6dab0ca3beea3507e29e25fb5e6a6bb3b06dab2e8697c4c75495`; VERIFY is
`5f7c75cc3b603ebf8e26989613381dc1617fceb328368eef07633e83f9ab31c2`.

| Check (VERIFY `5f7c75cc…`, `CUSTOM2=3` unless noted) | Result |
|---|---|
| A500-equivalent, default (`a500-native`) | Original VBL bytes at h0+$2CC3C (`527900ca668e`); the native pacer runs 62 frames in 500 fields (6.2 fps); F10 `OK` |
| A500-equivalent, `CUSTOM2=7` (`a500-forced`) | Clock installed; whole race identical in counts to C5's A500 run (2955 ticks, 3756 dropped); OVERLOADED |
| A1200 (`rate-a1200`) | Clock installed; 2919 ticks in 18250 fields, no drops, PASS |
| 68030/50 (`rate-a1200-030`) | Clock installed; 3320 ticks in 20750 fields, no drops, PASS |
| Disabled-feature gate (`tmp/b4/c6-acceptance.json`) | B4 PASS: release/developer/VERIFY off arms original, all 300 optional hook bytes independently rejected |

The A1200 and 030 races are shorter or longer than C5's because the changed VERIFY
slave alters the A1 timing inputs; each still runs exactly 8 ticks per 50 fields
apart from one tick at a sample boundary.

## Smooth presentation (D)

### D1 presentation snapshots — complete

Behind the developer bit `CUSTOM2` bit 3 (with the clock, bit 1), `d1_snapshot` runs
at every completed world tick, at `c2_pacer` entry before the tick is counted: after
the tick's last native call (h0+$1272 at h0+$3C9D2), live or replay, drawn or tick-only,
including a resumed tick. It copies the renderer inputs mapped in A4 into the current
buffer of two 2234-byte buffers (2232 before D6 added the covered-road flag); the other buffer keeps the previous tick. It only reads
game memory. The layout, which `tools/d1_snapshot.py` defines independently as the
specification of the slave tables `d1_ranges` and `d1_fields`:

| Part | Bytes | Contents |
|---|---:|---|
| Header | 24 | Field number (`c2_serial` at the tick's exit), tick number, epoch, rebased fields, reconstructions, loop mode, draw mode |
| h1+$224–243 | 32 | Renderer track anchor, pose source +$234, selected car +$238, view code +$23C, requests +$23E, fallback +$240 |
| h0+$3A70C–3A723 | 24 | Chase initialisation +$3A70E and heading +$3A710, controlled player +$3A720 |
| h0+$3A7F8–3A82B | 52 | Published camera, including spring displacement and velocity +$3A820/+3A824 |
| h0+$3A8C2–3A8C5 | 4 | Yaw trig coefficients |
| h0+$3A8F8–3A90F | 24 | TV selection parameters and distances, view height bias +$3A904, chase offset +$3A90C |
| h2+$231D4–231E7 | 20 | Horizon, view pitch bias, viewport +$231E0/+231E4 |
| h2+$231A0–231A1 | 2 | Covered-road flag (D6): +$231A0 bit 7, set by h0+$33FA0 when the anchor's +$26 bit 3 is set; the scene then draws no sky (h2+$27DCE/+27DFC) |
| 27 records × 76 | 2052 | Synthetic camera h1+$256, then the 26 cars h1+$5D6 + i×$C0: +$00–37 (direction, pitch, height, lateral, longitudinal, speed, T, denominator, damage/model bytes +$19/+$25, yaw, corrected longitudinal, fraction, lap segment, world X/Z, velocity), +$48/+$4A steering and correction, +$66 list index, +$72 speed change, +$7E pose flag and +$80 packed lap position, +$8C height offset, +$96 status, +$AC driver, +$B6 cockpit pitch effect |

Records are kept by slot, not by the ranking list, so a car's identity is its slot plus
+$AC. Pointers, flags and identities are recorded for validity only, not for
extrapolation. The header's epoch, rebase and reconstruction counters and the view state
let D2/D4 decide when prev is not a usable history (a new epoch, a resume, a view or
source change). D1 does not decide that.

**Evidence** (VERIFY `8724c100…`, `a1200-030` non-MMU, `CUSTOM4=1`, whole Quick Race,
`tmp/d1/`):

| Check | Result |
|---|---|
| Snapshot = game memory (`states-on`, `d1_snapshot.py`) | PASS. At each of 3162 ticks (6–3167), stopping at `d1_done`, cur equals the A4 fields rebuilt from game memory dumped at the same stop, and prev equals the previous tick's cur (3161 consecutive pairs). Field numbers never decrease (catch-up ticks can share a field). In 24 ticks a VBL fell between the serial read and the stop, so the recorded field number is one below the stop's serial. |
| Negative probes | A flipped snapshot byte, published-camera byte and epoch counter are each rejected |
| Read-only (`c5_compare.py`, `states-comparison.json`) | Option off (`CUSTOM2=3`) versus on (`=11`), same build: identical A1 inputs and identical car/session state at all 3162 common ticks |
| Exact repeat (`states-on-repeat`) | Identical states and snapshot archive (`434cf191…`) |
| Cost (`profile-030.json`, 100 fields from tick 300) | 0.24 ms per tick (0.19% of the window); the car update is 3.07 ms per tick. Emulated 68030 time |
| Pictures over the race | 6203 off, 6183 on (3.18 versus 3.19 fields per picture), no drops in either |
| Disabled-feature gate (`tmp/b4/d1-acceptance.json`) | B4 PASS: release `93dde23f…` unchanged, all 300 optional hook bytes independently rejected; D1 adds no hook, only code reached from `c2_pacer` |

### D2 presentation phase α — complete

With `CUSTOM2` bit 3, `d2_picture` gives every picture a presentation phase α just
before it is drawn. This covers pictures drawn inside a tick (`c2_scene` with draw mode 1,
from the new state) and pictures drawn between ticks (`c2_repeat_picture`, from the
last tick's state). α is an unsigned Q14 fraction of the next tick's interval (the
clock's 7/6/6/6 PAL or 8/7 NTSC table at its current phase):

```
phase  = WC_CREDIT + (c2_serial − WC_LAST)      fields since the current tick fell due
lead   = measured lead of the previous picture of the same kind
period = fields since the previous picture started
α = 0                                   if max(lead, period) > 2 × interval   (latest state)
α = min(phase + lead, 2 × interval) × 2^14 ÷ interval                       (otherwise)
```

- **Phase:** credit is the fields beyond the current tick's due point, so α measures
  from when the tick fell due rather than when it finished running. With no drops the
  two are the same up to the tick's own run time, and α = 1 coincides with the next
  tick's release.
- **Lead:** the "until shown" horizon follows A5's rule. `d2_shown`, in `c2_acquire`,
  records the first field after the copper has taken the submitted bitmap; the lead is
  that field minus the picture's start field. Pictures drawn inside a tick and between
  ticks keep separate leads, because the tick's simulation work makes the former's
  longer. Suspending or leaving the loop discards an unmeasured picture.
- **Long pictures:** when pictures are longer than the two-tick horizon, the picture shows
  the latest state (α 0), as the plan specifies (Red Baron). D9 raised the limit from one
  tick: a single picture just over a tick (6 fields in a pit stop) took α 0 and every car
  in it jumped back about half a tick, and the clamp already limits how far such a picture
  predicts.
- **Clamp at two ticks:** a first build clamped α at one tick (`tmp/d2/clamp1`). On
  the 030, 3123 of 5983 pictures hit that clamp, so the displayed world lagged by up to
  3 fields (p95 2). A picture drawn between ticks starts about two thirds into a tick
  and reaches the screen about 3 fields later, after the next tick is due. The ideal α
  measured over the whole race reaches 1.5 and never exceeds 2. D8's measured errors
  keep the clamp at two ticks.
- **Interval beyond one tick:** α above 1 still uses the next interval; the interval
  after it may differ by one field.

**Evidence** (VERIFY `caffe19a…`, `a1200-030` non-MMU, whole Quick Race, `tmp/d2/`;
`d2_alpha.py` stops after every α, `CUSTOM4=1` unless noted):

| Check | Result |
|---|---|
| Rule (`alpha-on.json`) | PASS: phase, interval, lead, period, α and the latest-state count recompute exactly for all 5984 pictures (3113 inside ticks, 2871 between) |
| Lead against the display | Exact for 5669 of 5983 pictures; ±1 field for 308; ±2 for 6 |
| Displayed world time (tick + α) | Never goes backwards. Its error against the ideal at the first displayed field: p50 0, p95 1 field, maximum 2 fields. The ideal α has p50 1.0, p95 1.33 and maximum 1.5; 2163 pictures are above 1 and none above 2 |
| α distribution | 161 in [0.25, 0.5), 1709 in [0.5, 0.75), 984 in [0.75, 1), 1965 in [1, 1.25), 1037 in [1.25, 1.5), 128 at 1.5; none below 0.25 and none latest |
| Long pictures (`alpha-slowed.json`, `CUSTOM4=3`) | All 778 pictures (27.3 fields apart) show the latest state with α 0 |
| Read-only (`states-comparison.json`) | Option off (`CUSTOM2=3`) versus on (`=11`), the repeat and the slowed run: identical car/session state at all 3114 (slowed 3112) common ticks |
| Exact repeat (`states-on-repeat`) | Identical states, pictures archive (`da337dc9…`) and snapshots. A first attempt is kept in `states-on-repeat-gdb-fault`: a corrupted gdb reply stopped it at an unrelated PC |
| D1 snapshots in these runs | PASS. In the slowed run, two catch-up ticks shared a field, so the D1 check now requires field numbers that never decrease rather than strictly increase |
| Pictures over the race | 6001 off, 5984 on (3.24 versus 3.25 fields per picture), no drops; D1 and D2 together |
| Disabled-feature gate (`tmp/b4/d2-acceptance.json`) | B4 PASS: release `93dde23f…` unchanged, all 300 optional hook bytes independently rejected; D2 adds no hook |

### D3 stage and restore — complete

With `CUSTOM2` bit 3, `d3_stage` runs just before every picture's draw and `d3_restore`
right after it: inside a tick around `c2_scene`'s call of h2+$280F6 (draw mode 1 only;
tick-only passes are never staged), between ticks around `c2_repeat_picture`'s call. The
restore runs before control returns to the native loop (h0+$3C9C0, the tick clocks) or to
`c2_repeat_picture`'s own restore of A3's renderer effects, so no simulation code sees a
staged byte. The stage set is the pose subset of the D1 layout, 1082 bytes (1080 before D6) in the packed
order that `tools/d3_stage.py` defines independently as the specification of the slave
tables `d3_ranges` and `d3_fields`:

| Part | Bytes | Contents |
|---|---:|---|
| h1+$224 | 4 | Renderer track anchor |
| h0+$3A7F8–3A81F | 40 | Published camera: direction, pitch, coarse and full X/Z, height, lateral, yaw, reduced X/Z, lap segment, anchor heading |
| h0+$3A8C2–3A8C5 | 4 | Yaw trig coefficients |
| h2+$231D4, +$231E0, +$231E4 | 6 | Horizon; viewport direction flag and relative heading (written by h0+$33F6E–33F9A) |
| h2+$231A0 | 2 | Covered-road flag (D6) |
| 27 records × 38 | 1026 | Synthetic camera and 26 cars: +$00 direction, +$04 pitch, +$08–0D height, lateral, longitudinal, +$12–17 segment pointer and denominator, +$1A–1F yaw, corrected longitudinal, fraction, +$26–2F lap segment and world X/Z, +$48/+$4A steering and correction, +$8C height offset |

Everything else stays authoritative while a picture is drawn: the view state h1+$234–240,
the camera spring h0+$3A820–3A827 (A3: the shake adds to it during drawing), the mirror
request +$3A828, speed and velocity, and every flag and identity (+$19, +$25, +$66, +$72,
+$7E, +$80, +$96/+$97, +$AC, +$B6). Those discrete fields also select A3's drawing side
effects. The pit-service phases and the shake (h2+$2A2A8, reached from h2+$28066 in the
cockpit view only) test only the selected car's +$67 and +$97, which are not staged. The
debris deadline (h2+$29ACE–29AD8) depends on which cars are drawn, so inside a tick a picture
is not staged if h0+$3A770 is zero and any car has +$19 bit 4. Between ticks `c2_repeat_picture`
already restores that deadline.

Per picture, the history is the D1 snapshot of the tick before the one drawn: cur inside a
tick (that tick's own snapshot is only taken at the pacer), prev between ticks. It is
usable only if its tick number is the drawn tick minus one and its epoch, loop mode,
pose source, selected car and view code equal the current ones. Otherwise the picture
snaps. A picture with α 0 (latest state) uses no history. Within a usable history, a record whose
+$7E bit 0 (explicit pose) differs from the snapshot's keeps its authoritative pose (held).
D4 predicts the camera part of the staged values and D5 the car records (below); the
rest are the authoritative ones. The VERIFY probe `CUSTOM5` bit 1 stages the usable history
instead, drawing one tick late, to prove the mechanism with values that really differ.

VERIFY checks every restore. Before writing back it counts a draw that changed a staged
byte (`d3_written`). Between ticks it compares the restored game with cur, because nothing
has run since that snapshot. Inside a tick, `d1_snapshot` compares the tick's new cur with
the saved bytes at the pacer. Mismatches count as `d3_faults`.

**Evidence** (VERIFY `98b23548…`, developer `7f9262d5…`, `a1200-030` non-MMU, `CUSTOM4=1`,
whole Quick Race in the cockpit view, `tmp/d3/`; `d3_stage.py` stops after every restore):

| Check | Result |
|---|---|
| Probe (`stage-previous.json`, `CUSTOM5=2`) | PASS for all 6088 staged pictures (3226 inside ticks, 2862 between): decision, staged bytes (rebuilt from the D1 history with held records), game equal to the saved bytes after the restore, and saved bytes equal to the independent snapshot (cur between ticks, the drawn tick's own snapshot inside a tick). 6084 pictures used the history and 4 snapped; the staged inputs differed from the authoritative ones in 5791; 587 records were held |
| VERIFY counters | 0 written, 0 faults; 6097 of 6098 restores checked (the last in-tick picture's check was pending when the race ended) |
| Negative probes | A flipped restored camera byte, staged byte, saved byte and snapshot byte are each rejected |
| Authoritative staging (`stage-on.json`) | PASS for all 6089 pictures; staged equals saved throughout |
| Race unchanged (`states-comparison.json`) | Option off (`CUSTOM2=3`), staging (`=11`), the probe and its repeat: identical car/session state at all 3226 common ticks (6–3231); D1 snapshots pass in all three staged runs |
| Exact repeat (`states-previous-repeat`) | Identical states and stage archive (`fa41d9b8…`) |
| Cost (`profile-developer.json`, 100 fields from tick 300) | Developer build: 0.63 ms to stage and 0.20 ms to restore per picture, against 28.9 ms for the scene; 1.4% of the window. VERIFY adds its compares (restore 0.58 ms, `d1_snapshot` 0.49 instead of 0.24 ms). Emulated 68030 time |
| Pictures over the race | 6211 off, 6088 staged, 6087 probe (3.25 versus 3.31 fields per picture), no drops |
| Disabled-feature gate (`tmp/b4/d3-acceptance.json`) | B4 PASS: release `93dde23f…` unchanged, all 300 optional hook bytes independently rejected; D3 adds no hook |

Not exercised by this race: the debris case (it never arose; `d3_debris` 0), and the
TV and chase views, where the pose source is the synthetic camera. D7 covers every view.
A first probe run (`states-previous-tickcheck-d0`) counted a VERIFY fault for every
in-tick picture: the tick check lost the tick number in a register that its comparison walk
reuses. The independent checks passed in that run, and the fixed build reports none.

### D4 camera prediction — complete

For every staged picture with a usable history (D3) and α above 0, `d4_camera` replaces
the camera part of the staged values with a prediction from the published camera at
h0+$3A7F8: `cur + (cur − history) × α`, with cur the tick drawn and α in Q14 up to two
ticks. The product is rounded towards zero, using 68000 instructions only. Since D10 the
prediction is an interpolation, `cur − (cur − history) × w` (D10 below).

| Staged value | Rule |
|---|---|
| Direction +$3A7F8, pitch +$3A7FA, height +$3A7FE, yaw +$3A80C | Extrapolated (interpolated since D10) as wrapped words, so angles take the shortest arc. The published pitch already contains the view bias and the cockpit +$B6 term |
| World X/Z +$3A802/+$3A806 | Extrapolated (interpolated since D10) as longs. World coordinates do not wrap, so the lap wrap only concerns the anchor |
| Reduced X/Z +$3A810/+$3A818, coarse X/Z +$3A7FC/+$3A800 | Derived from the predicted X/Z as h0+$33F32 does (`>> 8`, then `>> 3`) |
| Road anchor h1+$224, anchor heading +$3A81E | The game's own segment search h0+$26406, started at the tick's anchor, for the predicted X/Z. It steps forward or back through the native wrap helpers (+$2679A/+267DA), so it follows the lap wrap. A result in the pit/alternate segments below h1+$53DE keeps the tick's anchor, because native publication (+$26502) would convert it through +$26326, which writes h2+$231EA |
| Yaw coefficients +$3A8C2/+$3A8C4, horizon h2+$231D4, viewport h2+$231E0/+$231E4, covered-road flag h2+$231A0 | Recomputed as h0+$3409E, +$3404C, +$33F6E and +$33FA0 do: the sine table at h0+$222F0, the spring word +$3A820 in the cockpit, the horizon limit h2+$231CC, the anchor heading minus the yaw, and the anchor's +$26 bit 3 (the flag since D6) |
| Lateral offset +$3A80A, lap segment +$3A81C, unused +$3A80E/+$3A814, the synthetic camera record | Stay at the tick. The lateral offset only selects road detail against ±$200 (h2+$24C46); nothing reads the lap segment. The car records are D5 |

At the stage the spring word is the value the native horizon used. Inside a tick the
camera preparation h0+$34028 has just run. Between ticks `c2_repeat_picture` has already
loaded the tick's draw-entry stage, which undoes the shake.

**Snaps** (the picture shows the tick, α treated as 0):
- view, source or target changes, which also cover TV cuts, because a cut clears and sets view-code bit 6 in successive ticks;
- a new epoch, so the first tick after every rebase;
- non-consecutive ticks, and α 0 (D3);
- a camera that moved `D4_JUMP` ($100000) or more in X or Z in one tick. The largest normal movement over the race is 480,408 per tick; the one larger value, 54.9 million, is a reset. D8 keeps the threshold from the measured errors.

VERIFY first recomputes the derived values (coefficients, horizon, viewport) from the
tick's own camera and counts any difference from the game's in `d4_faults`. This checks
the formulas on every predicted picture.

**Evidence** (VERIFY `f1ab3da7…`, developer `77193b5b…`, `a1200-030` non-MMU, `CUSTOM4=1`,
whole Quick Race in the cockpit view, `tmp/d4/`). `tools/d4_camera.py` is the independent
model: it runs the D3 check, then rebuilds each prediction, including the segment search
over the track geometry and wrap pointers dumped at the end of the race:

| Check | Result |
|---|---|
| Prediction (`camera-on.json`) | PASS for all 5992 staged pictures (3210 inside ticks, 2782 between). For every picture the model rebuilds each staged byte exactly: the decision, the extrapolation, the anchor, and the derived values. 5990 pictures are predicted and 2 snap (unusable history). The search moved the anchor in 4108 pictures; it never left the main track, and no camera jumped |
| Derived values | The model's and the slave's recomputation from the tick's camera equals the game's in every predicted picture; `d4_faults` 0 |
| Accuracy against the ideal camera | The ideal is the actual camera interpolated between the ticks around each picture's displayed time, tick + α. Position error, the larger of X/Z, in world units: p50 2290 and p95 29,592 predicted, against 211,308 and 490,302 when the tick is shown. Yaw error: p50 2 and p95 126 against 48 and 882. The largest error in both, about 36.7 million, is the reset |
| Negative probes | A flipped restored camera byte, staged car byte, saved byte, history X byte, staged yaw, staged anchor and staged horizon are each rejected |
| Race unchanged (`states-comparison.json`) | Option off (`CUSTOM2=3`), prediction (`=11`) and its repeat: identical car/session state at all 3210 common ticks (6–3215) |
| Exact repeat (`states-on-repeat`) | Identical states, snapshots and stage archive (`ad6ef28a…`) |
| Cost (`profile-developer.json`, 100 fields from tick 300) | Developer build: `d4_camera` 0.034 ms per picture, including the segment search, inside `d3_stage` (0.66 ms; restore 0.20 ms), against 29.3 ms for the scene. The native camera preparation h0+$34028 costs 0.033 ms per tick. Emulated 68030 time |
| Pictures over the race | 6202 off, 5991 predicted (3.23 versus 3.35 fields per picture), no drops |
| Disabled-feature gate (`tmp/b4/d4-acceptance.json`) | B4 PASS: release `93dde23f…` unchanged, all 300 optional hook bytes independently rejected; D4 adds no hook |

Not exercised by this race: the TV and chase views, whose source is the synthetic camera,
and the pit-lane anchor case. D7 covers every view. In this race the cars were still drawn
at the tick; D5 predicts them. D4 alone is not a smoothness claim; D9 measures smoothness.

### D5 car prediction — complete

For every picture whose camera D4 predicted, `d5_cars` extrapolates each of the 26 car
records in the staged values, `cur + (cur − history) × α`, with the same history, α and
rounding as D4 (since D10 interpolated with D4's weight, D10 below). The renderer reads a car through the pose accessor h0+$26206 (A4), so each
representation is predicted in its own coordinates:

| Car | Rule |
|---|---|
| Track-driven (+$7E bit 0 clear; 95% of car-ticks) | Progress along the track is the signed fraction +$1E (Q14) plus $4000 for every segment stepped from the history's segment to cur's (at most 3; 2 is the most seen in a tick). The predicted progress is placed by stepping on from cur's segment; +$1E becomes the remainder and the corrected longitudinal +$1C follows from it with cur's denominator +$16, the inverse of h0+$2B560. The accessor then derives position, height and pitch natively from the staged segment, +$1C, +$1E, lateral and yaw |
| Explicit (+$7E bit 0 set) | World X/Z +$28/+$2C extrapolated as longs; the segment +$12 found by the game's search h0+$26406 from cur's segment, as h0+$263F6 does |
| Both | Pitch +$04, height +$08, lateral +$0A, yaw +$1A, correction +$4A and height offset +$8C extrapolated as wrapped words; each accessor branch reads its own subset |
| Held at the tick | Steering +$48 (wheel images, D6), direction +$00, uncorrected longitudinal +$0C, denominator, lap segment, the other representation's coordinates, every flag and identity, and the synthetic camera record |

Segments step as the track-driven traversal does (h0+$2B402/+2B4AE through h0+$26626):
the lap wrap at the end pointer h2+$1FAC2, and the pit branch (h2+$1FADE) and join
(h2+$1FAD6 → +$1FAE2) points passed through unless the car is changing pit state.

**Kept at the tick** (per car; the rest of the picture is still predicted): a car whose
pose flag or status word +$96 differs from the history's; a track-driven car whose step
from the history crossed into or out of the pit lane (h0+$26626 would call
h0+$2655A/+265D2, which rewrite its lateral offset; with pit stops on, any marked
segment), crosses more than 3 segments in a tick or 6 in the prediction, or that
would stand before its segment (negative progress: cars on the grid stand slightly before
theirs); an explicit car that moved `D4_JUMP` or more in X or Z. Every record advances every
tick whether or not it is drawn (a stopped track-driven car has speed 0), so a car entering
view needs no snap.

**Exact next pose:** not available. The track-driven advance is the mean of the previous
speed (h0+$2B144) and the speed set earlier in the same tick (h0+$2B34A), so the next
tick's advance depends on a speed that does not exist at the tick's end; explicit cars
integrate physics during the tick in the same way. The prediction stays the plain formula.

**Evidence** (VERIFY `448e0283…`, developer `d3b85bac…`, `a1200-030` non-MMU, `CUSTOM4=1`,
whole Quick Race in the cockpit view, `tmp/d5/`). `tools/d5_cars.py` is the independent
model; it runs the D3/D4 check and rebuilds every car:

| Check | Result |
|---|---|
| Prediction (`cars-on.json`) | PASS for all 5672 staged pictures (3082 inside ticks, 2590 between): every staged byte, camera and cars, rebuilt exactly. 144,157 car records predicted, 113,130 of them on another segment than the tick's; 3263 held: 3069 grid cars before their segment, 158 pose-flag and 27 status changes, 9 pit or segment crossings. The slave's counters agree picture by picture |
| Accuracy against the ideal pose | Each drawn car at the picture's displayed time, tick + α, interpolated between its actual poses (track-driven positions computed as h0+$26286 does); cars whose flag or status changes between those ticks are left out. Position error, the larger of X/Z, in world units: p50 4253 and p95 25,243 predicted, against 245,069 and 493,736 when the tick is shown; maximum 419,106 against 739,072. Yaw: p50 3 and p95 239 against 158 and 871 |
| Camera (D4, same run) | Every prediction rebuilt exactly; p95 position error 28,686 against 500,899; `d4_faults` 0 |
| Negative probes | The seven D4 probes, a staged car fraction, a staged car yaw and a history car lateral are each rejected |
| Race unchanged (`states-comparison.json`) | Option off (`CUSTOM2=3`), prediction (`=11`) and its repeat: identical car/session state at all 3082 common ticks (6–3087) |
| Exact repeat (`states-on-repeat`) | Identical states, snapshots and stage archive (`eb71a344…`) |
| Cost (`profile-developer.json`, 100 fields from tick 300) | Developer build: `d5_cars` 0.72 ms per picture inside `d3_stage` (1.38 ms; restore 0.20 ms, `d4_camera` 0.035 ms). The scene measured 39.9 ms per picture in this window against 29.3 ms in D4's: the layout change gives a different race, and the whole race shows the same drawing overhead as D4 (3.7% more fields per picture than the option off in both). Emulated 68030 time |
| Pictures over the race | 5871 off, 5671 predicted (3.28 versus 3.40 fields per picture), no drops |
| Disabled-feature gate (`tmp/b4/d5-acceptance.json`) | B4 PASS: release `93dde23f…` unchanged, all 300 optional hook bytes independently rejected; D5 adds no hook |

A first build read the fraction as unsigned and drew the grid cars up to three segments
ahead before the start (`tmp/d5/run2-unsigned`, largest error 1.04 million); the model
matched it, so the error measure found it. The remaining large errors (above 200,000 in
27 of 136,717 car-pictures) are cars braking or turning hard at α near 1.5; D8
measures them per class. This race had no TV, chase or pit-stop pictures; D7 covers them. D6 keeps steering at the
tick.

### D6 everything else that moves — complete

D6 decides, for every remaining item that moves, whether a picture between ticks
extrapolates it, holds it at the tick or animates it. The inventory has two sources. The
first is a static scan of the 14,077 renderer instructions reachable from h2+$280F6 (A3),
for absolute addresses the scene reads that other code writes. The second is A3's
green/tow/follow access samples, which give the scene's reads of memory written outside
the scene. Indexed tables were followed from their `lea` sites. Every input that moves is
either in the stage set or listed here:

| Item | Renderer input | Decision and evidence |
|---|---|---|
| Car wheels (front-wheel images) | Steering +$48 → h2+$28168 (h2+$29A58); h2+$28C30 adds it to the wheel's angle, 16 images of $1000 | **Hold.** Steering follows input and reverses abruptly. Over the race (`items.json`), at α = 1 holding puts a wheel more than half an image off in 0.79% of car-pictures and extrapolating in 1.10%; p99 1812 against 2220, worst 21,386 against 30,561. At α 0.5 and 1.5 the result is the same. Extrapolation wins only at p95 (552 against 752), where both stay below half an image |
| Tow truck, smoke and debris | Drawn at fixed offsets from the car's pose (h2+$29D4E, table h2+$29E2C) when +$97 bit 7 or +$19 bit 4 is set | **Follow the car.** The offsets apply to the staged (predicted) car pose, so these items move with it. The flags select them and stay at the tick |
| Marshal flags | Flag state per track sector in h1+$456 (byte +1), written by h0+$39E2C–3A0C2; the post object (kind $20) copies it to h2+$2C3BF | **Hold.** A discrete state |
| Start lights | h0+$3A73A, +$3A750 (h2+$1F77C) | **Hold.** Discrete session state |
| Pit crew and service phases | h0+$3A746–3A74D | **Hold.** A3: tick counters that must not advance at picture rate; C2 stages their tick-entry values. Since D10 the x positions of the pit-stop sprites drawn from them are interpolated (D10 below) |
| Cockpit shake | Spring +$3A820 plus the shared random number stream | **Hold.** A3: random-number draws stay once per tick. The horizon uses the spring of the tick |
| Rear view and pit-lane overlay | The scene's rear viewport (h2+$231E0) and the alternate-carriageway pass h2+$2A450 (the "mirror request" +$3A828) | **Predicted already.** Both read the staged camera, anchor and car records |
| Cockpit sides, hands, sky | Fixed images h0+$3D742, +$3EB32; the sky reads the staged yaw and horizon | **Already consistent** (the sky's on/off flag: next row) |
| Covered-road flag | h2+$231A0 bit 7, from the anchor's +$26 bit 3 (h0+$33FA0); no sky under cover | **Derived** from the staged anchor. D4 moved the anchor but kept the tick's flag, so a predicted picture entering or leaving a tunnel would have drawn the sky wrongly. The flag is now in the D1 and stage sets, and `d4_derive` sets it as h0+$33FA0 does |
| Rev counter | Bar position from +$62 (h0+$3940A), drawn incrementally into both bitmaps by the HUD queue | **Hold.** Of 3257 tick changes, 2261 leave it unchanged and 639 move one of 38 segments. Gear changes jump 12–25 segments, so extrapolation would show wrong values across them. The original game updated it once per frame, which here is once per tick |
| Gear, timing text, banners, blink | HUD queue and the box repeats (C2) | **Hold.** Readouts of the tick's state; A3 keeps their request and blink handling at tick rate |
| Car flags, status, damage, pit garages, race order | +$19, +$23, +$25, +$66, +$7E, +$96/+$97, +$AC; h1+$3BC; h1+$520 | **Hold.** Discrete. They select models and attachments |

Nothing in the inventory calls for a presentation-clock animation: every animated item
is either attached to a staged pose or is a tick state that A3 requires to advance once
per tick.

**Evidence** (VERIFY `9aeaf5d8…`, developer `eedf342e…`, `a1200-030` non-MMU,
`CUSTOM4=1`, whole Quick Race in the cockpit view, `tmp/d6/`):

| Check | Result |
|---|---|
| Prediction (`cars-on.json`) | PASS for all 5886 staged pictures (3258 inside ticks, 2628 between): every staged byte rebuilt exactly, including the covered-road flag; `d4_faults` 0, so the flag recomputed from each tick's own anchor equals the game's. Silverstone has no covered segment (0 of 1280 have +$26 bit 3), so this race never sets the flag |
| Accuracy (same run) | Camera position p95 29,654 predicted against 480,918 at the tick; cars p95 24,906 against 490,493, worst 490,240 against 742,723 |
| Negative probes | The ten D3–D5 probes and a flipped staged covered-road flag are each rejected |
| Item measurements (`items.json`, `tools/d6_items.py`) | Steering and rev counter as in the table, over 3258 ticks and about 84,600 car-pictures per α |
| Race unchanged (`states-comparison.json`) | Option off (`CUSTOM2=3`), prediction (`=11`) and its repeat: identical car/session state at all 3258 common ticks (6–3263); the D1 snapshots pass at every tick |
| Exact repeat (`states-on-repeat`) | Identical states, snapshots and stage archive (`b141e5a2…`) |
| Cost (`profile-developer.json`, 100 fields from tick 300) | Developer build: `d4_camera` 0.036 ms per picture including the flag (D5: 0.035), `d5_cars` 0.66, `d3_stage` 1.33, restore 0.21. Emulated 68030 time |
| Pictures over the race | 6127 off, 5885 predicted (3.32 versus 3.46 fields per picture), no drops |
| Disabled-feature gate (`tmp/b4/d6-acceptance.json`) | B4 PASS: release `93dde23f…` unchanged, all 300 optional hook bytes independently rejected; D6 adds no hook |

Not exercised: a track with covered road such as Monaco (the launcher's routes use
Silverstone), and the TV and chase views, retirements and pit stops in this capture.
D7 covers every view.

### D7 every view — complete

Every view draws from the staged records. The cockpit and the onboard view of another car
are the selected car's own pose, so the D4 camera and the D5 cars cover them. In replays
the loop draws from the replay's records; snapshots, history and epochs work the same way
(a replay and the live race after it each start a new epoch, and their ticks restart at 1).
The A2 walk found no attract mode.

**External views.** In the chase and TV views the game builds the camera from the
followed car each tick, so the D4 straight-line extrapolation of the camera alone moved
the camera along a different path from the D5 car. In corners the followed car slid
sideways in the picture. With D7, `d7_aim` (called from `d4_camera` after the cars and
before the coordinates, anchor and derived values follow the camera) replaces the camera
of an external view with the native placement from the predicted car:

| View | Native code | Staged camera |
|---|---|---|
| Chase (view-code bit 5; front with bit 4) | h0+$398AA–3990C | Heading +$3A710 extrapolated (interpolated since D10) as a wrapped word (the native turn towards the car's direction is rate-limited by +$3A960, so the published heading is extrapolated rather than recomputed). X = car X + (table(\|$4000 − h\|) × L) >> 6 and Z = car Z + (table(\|h\|) × L) >> 6, with h the heading (+$8000 in front), L the distance word +$3A90C and the table h0+$222F0 |
| TV (bit 5 clear, h1+$240 zero) | h0+$39BD0 | The fixed camera position of the tick |
| Both | h0+$39CBE | Yaw and direction from the game's arctangent h0+$256B6 (table h0+$242F4) of the predicted car relative to the camera, both reduced `>> 11` |

The predicted car position comes from the game's own pose accessor h0+$26272, run on a
copy of the followed car's record with the staged pose fields; it writes the scratch word
h0+$25644, which `d7_place` saves and restores. A followed car that is not the view's pose
source, and a track-point TV camera (h1+$240 nonzero), keep the D4 camera. VERIFY first
places the camera from the tick's own car and heading and counts any difference from the
game's published camera in `d7_faults`.

**Pit stops.** While pit stops are on, the game swaps the pit lane (h1+$2BFA–53DD) with
the main-track stretches beside it, [h1+$53DE, join + $2E) and [branch, end + $2E), with
the join, branch and end from h2+$1FAE2, +$1FADE and +$1FAC2. It also moves the wrap
pointers h2+$1FAB8–1FAE7. The capture now saves those ranges with every picture, and the
model searches the track as it was at that picture; the end-of-race dump alone gave the
wrong anchor for a car in the pit lane.

**Evidence** (VERIFY `c0a4590d…`, developer `291772cb…`, `a1200-030` non-MMU,
`CUSTOM4=1`, `tmp/d7/`). The whole Quick Race runs with the view-key schedule of
`--views`. It starts in the cockpit, then goes to TV, rear chase, the replay (R and Space
at tick 1100) in rear chase, then front chase, onboard other cars and back. It includes
Mansell's retirement and tow, and Alesi's pit stop in the onboard view.
`tools/d7_views.py` runs the D3–D6 check with the D7 model and measures each view:

| Check | Result |
|---|---|
| Prediction (`views-on.json`) | PASS for all 5980 staged pictures (3246 inside ticks, 2734 between; 2123 in the race before the replay, 274 in the replay, 3583 after it): every staged byte rebuilt exactly. 3749 external-view cameras placed and aimed from the predicted car; `d7_faults` 0, so the native placement from each tick's own car equals the game's camera in every picture. 148,727 cars predicted and 3477 held |
| Chase consistency | Bearing error of the followed car from the camera centre against the ideal at the displayed time, p95 in angle units ($10000 a turn): rear chase 29 (tick shown 29), front chase 31 (27), TV 60 (57), replay rear chase 28 (25). Aiming the predicted camera at the tick's car instead gives 45, 41, 19 and 40. The camera position error falls as in D4 (rear chase p95 36,332 against 563,642 at the tick) |
| Accuracy (whole run) | Camera position p95 24,918 predicted against 475,247 at the tick, yaw 216 against 1378; cars p95 25,781 against 503,731 |
| Negative probes | The eleven D3–D6 probes, plus flipped game and history chase headings and a staged chase camera X, are each rejected |
| Race unchanged (`states-comparison.json`) | Option off (`CUSTOM2=3`), prediction (`=11`) and its repeat: identical car/session state at all 3246 common ticks across the three epochs; the D1 snapshots pass |
| Exact repeat (`states-on-repeat`) | Identical states, snapshots and stage archive (`addcb9a8…`) |
| Cost (`profile-developer.json`, rear chase, 100 fields from tick 300) | Developer build: `d7_aim` 0.022 ms per picture inside `d3_stage` (1.33 ms; `d4_camera` 0.70 including the cars, `d5_cars` 0.65, restore 0.20). Emulated 68030 time |
| Pictures over the race | 6156 off, 5980 predicted (3.31 versus 3.40 fields per picture), no drops |
| Disabled-feature gate (`tmp/b4/d7-acceptance.json`) | B4 PASS: release `93dde23f…` unchanged, all 300 optional hook bytes independently rejected; D7 adds no hook |

The bearing error is no lower than showing the tick. The game's own chase camera trails the car
by a rate-limited heading, so the car's place in the picture already changes smoothly
between ticks. What D7 removes is the disagreement between camera and car.

**Retirement flashing (open).** While Mansell's lifted car drifts at the TV camera's
switching distance (first race, ticks 783–800), the game clears and sets view-code bit 6
on alternate ticks (h0+$39C48 clears it when the distance grows past h0+$3A8FE;
h0+$39804 chooses the camera again). D4 snaps on every one of those ticks, so those
pictures show the tick. A user watching the prediction run saw blue polygons (the bridge
and wall colour) flashing on the tarmac there. The state is identical with the option
off. Screenshots (`--shots`, then every other field; D9) did not reproduce the scene: plain and per-tick
captures diverge before it (the plain run switches to another car at about tick 790). It is
therefore not established whether the original game draws this, or the repeated drawing
of a tick.

Not exercised: a track-point TV camera, and a track with covered road.

### D8 prediction error — complete

D8 measures how far the prediction is from where things actually go, and sets the snap
thresholds from that. `tools/d8_error.py` takes every tick t of the D7 race whose history
(tick t − 1, same epoch, mode and view) is usable. From the game state at t's first
picture it runs the D4, D5 and D7 models at α = 1, and at α = 2 (the clamp), exactly as the
slave would. It compares the result with the stage set of tick t + 1 (t + 2) from its D1
snapshot; showing tick t is the baseline. Each tick's poses are placed on that tick's own
track, because the pit stops swap track ranges between ticks (epoch 3, ticks 732→733
and 1128→1129). Cars whose pose flag or status changes by the target tick, and ticks
whose view changes by then (a TV cut or a key), have no comparable pose. Each car-tick is
classed from speed +$10 and yaw +$1A at t − 1, t and t + 1:
- **collision:** speed falls by more than 1100 in one tick, beyond the hardest braking
  (speed change +$72 reaches −1024), or the damage byte +$25 changes;
- **braking:** speed falls by 256 or more;
- **steering reversal:** the yaw rate changes sign, with at least 32 on each side;
- **steady:** anything else.

The camera takes the class of the car it is in or follows.

**Evidence** (`tmp/d8/error.json`, from the D7 capture `tmp/d7/run3/states-on`, VERIFY
`c0a4590d…`, `a1200-030` non-MMU; the D3–D7 check passes). 3180 ticks have a usable
history; 3149 are compared at α = 1 (28 view changes, 3 at the end). There are 76,025
car-ticks. Errors are p50 / p95 / maximum. Position is the larger of the X/Z errors in
world units; angles are in $10000 a turn:

| Quantity at α = 1 | Predicted | Tick shown |
|---|---|---|
| Camera position | 1024 / 21,504 / 276,582 | 152,808 / 446,880 / 502,528 |
| Camera yaw | 0 / 188 / 2085 | 96 / 1507 / 8833 |
| Camera direction, pitch, height (p95) | 182, 7, 2 | 1507, 15, 26 |
| Car position | 5120 / 22,784 / 453,632 | 275,200 / 430,080 / 502,528 |
| Car yaw | 3 / 249 / 6361 | 198 / 788 / 6362 |

| Class (α = 1), p95 | Camera position | Car position | Car yaw |
|---|---|---|---|
| Steady (2975 camera ticks, 71,519 car-ticks) | 19,712 (447,744) | 22,272 (431,104) | 225 (789) |
| Braking (143, 3786) | 31,744 (410,424) | 25,856 (403,968) | 309 (725) |
| Steering reversal (31, 719) | 140,422 (501,504) | 27,648 (440,832) | 1125 (727) |
| Collision (0, 1) | — | 20,576 (157,792) | 310 (2705) |

The tick shown is in brackets. By view, the camera's p95 is:

| View | Predicted | Tick shown |
|---|---|---|
| Cockpit | 896 | 129,088 |
| Onboard | 14,592 | 382,208 |
| Rear chase | 29,108 | 474,594 |
| Front chase | 25,384 | 411,904 |
| Replay rear chase | 30,616 | 501,730 |
| TV | 0 | 0 |

The TV camera stands still between cuts.

At α = 2, the prediction p95 is:
- camera position 62,152 against 894,976 when holding; yaw 565 against 2833;
- car position 64,000 against 860,672; car yaw 613 against 1569.

Run on the repeat capture, the measure gives an identical report.

**Worst cases.**
- **Camera:**
  - the largest errors are the front chase stopping dead (epoch 3, tick 252: the camera moves 128,000 in X and then 1500, a steering reversal; 276,582);
  - the start of the race (epoch 1, tick 249, cockpit: the camera's step grows from 24,000 to 144,000 in one tick; 121,062);
  - the first ticks of the replay (100,816).
  - Prediction is worse than holding at 8 of the 2099 ticks where the camera moves.
- **Cars:**
  - the largest errors are cars held while moving (157 car-ticks, up to 453,632, one tick of movement);
  - 115 of those holds come from pit stops: while they are on (epoch 3, ticks 733–1128), the native traversal rewrites the lateral offset at the pit branch and join (h0+$2655A/+265D2), so D5 holds a car whose step crosses them;
  - the other holds are status changes and segment limits.
  - Braking adds little at α = 1 (p95 25,856); at α = 2 the largest braking error is 845,824.
  - Prediction is worse than holding for 61 of the 72,199 moving car-ticks.
- **Collisions:** they rarely reach the comparison, because the game switches the car's pose flag or status in the same tick, and D5 holds such a car (40 pose-flag changes at α = 1).
- **Steering reversal:** yaw extrapolation overshoots and is worse than holding in 718 of 719 car-ticks. A snap cannot see the reversal coming, because the new rate exists only at t + 1. Over all car-ticks extrapolation is still three times better (p95 249 against 788).

**Thresholds** (unchanged; the measurement supports them):

| Threshold | Value | Basis |
|---|---|---|
| Jump (`D4_JUMP`, camera and explicit cars) | $100000 per tick in X or Z | The largest movement in this race is 502,528 per tick (D4's race: 480,408). The prediction error does not grow with movement: camera p95 4608, 24,064, 21,804, 34,708 and 24,320 in the movement bins 0–100k … 400–600k. The only larger movement seen is a reset (54.9 million, D4). The threshold sits at twice the largest normal movement |
| α clamp (D2) | 2 ticks | At α = 2 the prediction is still about 14 times closer than holding. It is worse than holding at 11 of 2090 camera ticks and 66 of 71,453 car-ticks. The ideal α never exceeds 2 (D2) |
| Segments per tick (D5) | 3 per tick, 6 in the prediction | 10 holds for segments outside pit stops in the whole race |
| Pit branch and join while pit stops are on (D5) | held | The largest car errors, but 0.2% of moving car-ticks. Removing the hold means modelling h0+$2655A/+265D2's lateral rewrite. D9 keeps the hold only for a step already taken; a predicted step now stops before the change, which leaves 44 held car-ticks in D9's race |

### D9 smoothness — complete

D9 checks, picture by picture, that what is shown moves forward. The plan names 50 fps on
the 68060; 040/060 work is deferred (user decision), so this runs on the primary target,
the 68030/50, at its own picture rate of about 15 pictures a second. Two measures:

- **Poses** (`tools/d9_smooth.py`, from a whole-race `--states --stage --views` capture).
  The D3–D7 check rebuilds every staged picture. Each picture is placed at the field it first
  reached the screen (its start plus the lead measured at that display, D2), and shows until
  the next picture does: that interval is its frame time. Between consecutive pictures of
  the same epoch, mode and view, the step of the camera (world X/Z, yaw) and of every car
  (world X/Z) is compared with the object's actual motion over the tick interval that
  contains the displayed time, from snapshots with the same view. A step is *backwards*
  when it points against that motion (dot product below zero), *stalled* when it is zero
  while the object moves, and its *evenness* is the step per field divided by the motion
  per field in that interval (1 is perfectly even). The same pictures showing their tick
  are the baseline.
- **Screen** (`--shots`): one screenshot per field, with the slave's counters after each
  field. Each shot of the project server traces one field and saves the field before it,
  so consecutive shots are consecutive fields. The D7 recipe's extra `monitor fields 1`
  had made its "per-field" shots every other field; the capture no longer does that.

**Two fixes.** The first measurement, on the D7 race, found two kinds of backward motion,
both now fixed in the slave and the models:

| Cause | Before | Fix |
|---|---|---|
| D5 held a car whose *predicted* step would cross into or out of the pit lane (with pit stops on, any marked segment). The previous picture had predicted it ahead, so it jumped back to its tick pose | 49 car steps back, up to 369,294 world units, 45 of them while pit stops were on | The predicted step stops at the end of the segment before the change (`.stop` in `d5_cars`; fraction $3FFF). A car whose step from the history already crossed is still held: it is then ahead of the previous picture, not behind |
| D2 gave α 0 to a single picture just over a tick long (epoch 3, tick 902: 6 fields in a pit stop) | All 23 moving cars back by 77,000–157,000 in one picture | α 0 only beyond the two-tick horizon (D2 above) |

The other backward camera steps in that first measurement were the reference motion
spanning a view cut; the measure now requires the same view at both reference ticks.

**Evidence** (VERIFY `e4947db4…`, developer `4f7682b6…`, `a1200-030` non-MMU, `CUSTOM4=1`,
the D7 view schedule, `tmp/d9/`):

| Check | Result |
|---|---|
| Prediction (`views-on.json`) | PASS for all 6266 staged pictures: every staged byte rebuilt exactly; the 14 negative probes are rejected. Car holds: 3284 grid cars before their segment, 235 pose-flag and 41 status changes, 13 segment limits; 24 predicted steps stopped before a pit change |
| α (`alpha-on.json`, `alpha-slowed.json`) | PASS: every α recomputes exactly with the new limit. Displayed world time never goes backwards within a loop mode (ticks restart when the replay starts and ends); p95 error 1 field. Two pictures show the latest state: the first after the replay starts and after it ends, each after a 40-field pause. With `CUSTOM4=3` all 822 pictures (27 fields apart) still show the latest state |
| Race unchanged (`states-comparison.json`) | Option off (`CUSTOM2=3`), prediction (`=11`) and its repeat: identical car/session state at all 3454 common ticks |
| Exact repeat | Identical captures and an identical D9 report (`smooth-repeat.json`) |
| Pictures over the race | 6521 off, 6266 predicted (3.32 versus 3.46 fields per picture), no drops |
| Disabled-feature gate (`tmp/b4/d9-acceptance.json`) | B4 PASS: release `93dde23f…` unchanged, all 300 optional hook bytes independently rejected |

The cost is unchanged: the fixes add a branch per stopped car and one compare per picture.

**Motion** (`smooth-on.json`; 6117 comparable picture pairs). Predicted pictures, with
the tick shown in brackets:

| Measure | Camera (4579 moving pairs) | Cars (139,607 moving car pairs) |
|---|---|---|
| Stalled | 6 (2127) | 153 (62,429) |
| Backwards | 0 (0) | 51 (0), at most 14,734 world units |
| Evenness p5 / p50 / p95 | 0.76 / 1.04 / 1.30 (0 / 1.53 / 2.10) | 0.77 / 1.04 / 1.30 (0 / 1.26 / 2.09) |

- Showing the tick, half the pictures do not move and the others move about twice as far.
  Predicted, each picture moves about as far as the time it covers.
- The 51 backward car steps are small, at most 14,734 world units against about 300,000 a
  tick at speed. 39 are cars pulling away from the grid (epoch 1, ticks 164–204), where
  speed and lateral offset change sharply from tick to tick. The rest are nine steps of two
  cars in the front chase view (epoch 3, ticks 244–276) and three steps under 300 in the TV view.
- The camera yaw steps against the yaw rate in 118 of 3704 turning pairs (49 showing the
  tick). These are the steering reversals D8 measured: extrapolation overshoots a turn
  that is about to reverse.
- The 79 snapped pictures (view and source changes, TV cuts, jumps) show their tick; their
  cars stall for that picture (451 car pairs).

**Frame time** (fields from one picture reaching the screen to the next, whole race):

| View | 2 | 3 | 4 | 5 | 6–7 | 40–41 | Mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| Cockpit | | 691 | 98 | 1 | | | 3.13 |
| Onboard | 56 | 1369 | 27 | 1 | | | 2.98 |
| Rear chase | | 784 | 780 | 27 | 2 | 1 | 3.55 |
| Front chase | | 267 | 563 | 12 | 2 | | 3.70 |
| Replay rear chase | | 141 | 147 | 2 | | 1 | 3.65 |
| TV | | 530 | 401 | 359 | 2 | | 3.87 |
| Whole race | 56 | 3782 | 2016 | 402 | 6 | 2 | 3.46 |

The 40-field intervals are the pauses around the replay.

**Screen** (`shots.json`; 200 fields from tick 320 in the cockpit, 500 in TV, 900 in rear
chase, and 500 from tick 778 through the retirement in TV; prediction off and on):

| Window | Fields between changes, off | On | Pictures that change the view, off | On |
|---|---|---|---:|---:|
| Cockpit | 6–9 (mean 6.16) | 3–4 (3.25) | 50% | 98% |
| TV | 5–10 (6.26) | 5 (5.00) | 80% | 98% |
| Rear chase | 4–8 (6.19) | 3–5 (3.92) | 60% | 100% |
| Retirement (TV) | 3–44 (7.24) | 3–28 (4.47) | 51% | 84% |

With the option off a picture between ticks repeats the last one, so the view changes once
a tick. With prediction every picture moves. In the retirement window D4 snaps on alternate
ticks while view-code bit 6 alternates (D7), so those pictures show the tick.

**Blue patch.** In the retirement window, right after the cut to Patrese (fields 385–391),
both arms show light blue filling the run-off beside the tarmac, with blue specks along the
road edge. The pictures are the same with prediction off, so the prediction does not cause
it. Whether the original frame-locked game draws it is not established (D7's open item).

### D10 play-test — complete

The first play-test, on the 040 (`a1200-040`, the developer build, `CUSTOM2=11`), found two
problems:

- **Horizon over the 3D** about every 25 fields while standing still, with the option
  off as well. This is fixed (C2 above): a repeat drew without the scene's blit-queue drain.
- **Steering jumps from extrapolation**: the first steered picture turned too far, the yaw
  sprang back after the steering was released, and right-hand corners jumped. Extrapolation
  carries the last tick's rate past a reversal (D8). The user chose interpolation.

**Interpolation.** A picture now shows the pose between the history (the previous tick)
and cur, `cur − (cur − history) × w` with the history's weight `w` in `d2_weight`, unsigned
Q14. The camera words and X/Z (D4), the cars (D5) and the chase heading (D7) use it. A
track-driven car steps again from the history's segment, by its progress to cur times
`1 − w`. D2 computes the weight after α:

- A picture is shown a tick plus the longer of the two measured leads (tick and repeat)
  late. The fraction is (fields since the tick fell due + this picture's lead − longer
  lead) / interval, and `w` is 1 minus that fraction.
- Below 0 the picture shows the history. At or beyond one tick, and at α 0, it shows cur.
- Interpolating at α alone (shown one tick late) held cur in 55% of the 030's pictures,
  because display times run 0.4–1.6 ticks after the tick. Motion then paused at the end of
  every tick (evenness p5–p95 0.27–1.74). The user chose the even, adaptive delay instead
  (user decision): lag is one tick plus the lead, about half a tick more than the original
  game on the normal-speed 030 and a sixth of a tick on the 040.

In the second 040 play-test the user found steering smooth, without jumps, the chase, TV
and onboard views fine, and nothing wrong at the replay cuts or the pit entry. A snapped
or latest picture still shows cur. A held car keeps its tick pose, which is now ahead of
the interpolated pictures around it. After the pit-stop sprites below the user accepted
D10 as complete, the extra lag included (user decision).

**Pit-stop sprites.** During the player's stop, the block at h2+$2A2A8 draws three
sprites through h0+$147C for the viewed car's +$97 bits 3–5: $AA (sign), $A9 and $AE.
Each x position comes from a routine that advances a pit-service counter and turns it
into a position through the sine table: h2+$2A0FA (h0+$3A748), +$2A19E (+$3A746) and
+$2A226 (+$3A74A); the counters are A3 tick state (D6 holds them). The three calls at
h2+$2A2C8, +$2A33A and +$2A38A are hooked (`d10_pit_a`–`c`): the native routine runs
unchanged, its x is kept per tick and epoch, and a picture whose camera is interpolated
(`d3_source` 2) shows x between the previous tick's and cur's with `d2_weight`. No game
memory changes, so the race and the counters stay native. The quick race has no player
pit stop (the counters stay $8000), so the hooks are not exercised by the captures; the
user checked the stop in the 040 play-test and found it fine. With the hooks the whole
race is again identical with the option off at all 3422 common ticks, every staged
picture is rebuilt exactly, the negative probes are rejected and B4 passes (release
`93dde23f…` unchanged).

**Evidence** (VERIFY `4ebc2d32…`, developer `5d302a49…`, `a1200-030` non-MMU, `CUSTOM4=1`,
the D7 view schedule, `tmp/d10/`):

| Check | Result |
|---|---|
| Interpolation (`views-on.json`) | PASS for all 6212 staged pictures: every staged byte rebuilt exactly; the 14 negative probes are rejected. The history chase heading probe now uses a picture below one tick (picture 1701), because at a tick or more the history has no weight |
| α and weight (`alpha-on.json`, `alpha-slowed.json`) | PASS: every α and weight recomputes exactly. 5179 pictures interpolate and 1030 show the history; the shown time, tick − w, never goes backwards within a loop mode, except twice after the α-0 picture at an epoch start (a cut). With `CUSTOM4=3` all 814 pictures show the latest state |
| Race unchanged (`states-comparison.json`) | Option off, interpolation and its repeat: identical car/session state at all 3422 common ticks |
| Exact repeat | Identical captures and an identical D9 report (`smooth-repeat.json`) |
| Pictures over the race | 6381 off, 6212 interpolated (3.36 versus 3.45 fields per picture), no drops |
| Disabled-feature gate (`tmp/b4/d10-acceptance.json`) | B4 PASS: release `93dde23f…` unchanged |

**Motion** (`smooth-on.json`, 6118 comparable pairs; the reference is the motion from T − 1
to T, between which a picture of tick T is interpolated). D9's extrapolation in brackets:

| Measure | Camera | Cars |
|---|---|---|
| Moving pairs | 4419 | 142,441 |
| Stalled | 5 (6) | 128 (153) |
| Backwards | 1 of 234 world units (0) | 23 (51), at most 19,282 world units |
| Yaw backwards (turning pairs) | 25 of 3714, at most 895 (118 of 3704, at most 1932) | |
| Evenness p5 / p50 / p95 | 0.89 / 1.04 / 1.07 (0.76 / 1.04 / 1.30) | 0.88 / 1.04 / 1.08 (0.77 / 1.04 / 1.30) |

- 20 of the 23 backward car steps follow a held car: the held picture shows cur, the next
  interpolated one is behind it. Four are in the cockpit at the start (epoch 1, ticks
  138–142), the others groups of cars in the TV view in epoch 3; the largest is 6982.
- The other three are two steps of one car leaving the grid (19,282 and 982 world units)
  and one of 2366 in the TV view.
- The shown time never goes backwards (α and weight above), so the 25 yaw steps are not
  pictures out of order; they have not been analysed one by one.

**Screen** (`shots.json`; the D9 windows on this build's race, and 150 fields standing on
the grid on the 040 from tick 205):

| Window | Fields between changes, off | On | Pictures that change the view, off | On |
|---|---|---|---:|---:|
| Cockpit | 4–9 (mean 6.19) | 3–4 (3.18) | 49% | 100% |
| TV | 6–9 (6.30) | 3–4 (3.06) | 46% | 100% |
| Rear chase | 4–24 (7.27) | 4–24 (5.08) | 55% | 81% |
| Retirement (TV) | 4–16 (6.83) | 4–12 (5.37) | 58% | 74% |
| 040, standing | 6–7 (6.26) | 1–3 (1.04) | 16% | 99% |

This build's race differs from D9's (the slave is larger, so the boot timing and the race's
random seed differ). In its rear-chase and retirement windows the view stands still for up
to 24 fields with the option off as well. On the 040 the interpolated pictures change the
screen every field.

## Performance (E)

### E1 caches — complete for the current scope

E1 is B5 (above): `CUSTOM2` bit 0 requests the caches, menus and whole races pass with
them on every required CPU, and A7 records the 020/030 per-window figures. E1 adds the
gain on the primary target with the C2 loop and D10's interpolated presentation, where it
shows as pictures per field: two whole Quick Races on `a1200-030` non-MMU, the D7 view
schedule, `CUSTOM4=1`, the same slave and four-hunk layout, caches on (`CUSTOM2=11`) and
off (`CUSTOM2=10` plus WHDLoad `NoCache`, as the B5/A7 controls):

| Build | Caches | Ticks | Fields | Pictures | Fields per picture | Picture rate on/off |
|---|---|---:|---:|---:|---:|---:|
| Developer `8782ad32…` (`tmp/e1/dev-on`, `dev-off`) | on | 3454 | 21,654 | 6319 | 3.43 | 1.127 |
| | off | 3469 | 21,751 | 5633 | 3.86 | |
| VERIFY `54355e0d…` (`tmp/d10/pit/states-on`, `tmp/e1/states-nocache`) | on | 3422 | 21,455 | 6210 | 3.45 | 1.139 |
| | off | 3469 | 21,749 | 5533 | 3.93 | |

Caches on draw 13–14% more pictures over a race. No run drops a field of debt; the
uncached VERIFY race runs one catch-up tick without a picture. Every run quits with F10 OK,
and the uncached VERIFY race rebuilds every staged picture exactly (`smooth-nocache.json`).
The two arms are different races: uncached, the menus run slower (race entry at field 1602
against 1358 after the route command), so the UI random stream differs at the start, as in
C5(b)'s one-field run; both uncached races are the same race. The comparison is therefore
over the same route, view schedule and whole race (`c5_compare.py` schedules), not tick by
tick.

Caches stay opt-in in the slave: with every `CUSTOM` bit zero the original CPU request and
bytes remain (B4), so a release turns them on through its icon's `Custom2=1` tooltype (G1).
No 040/060 gain is claimed (deferred; see B5).

### E2 hunk 2's code in fast RAM — complete for the current scope

Behind developer `CUSTOM2` bit 4, hunk 2's main code runs from a copy in fast RAM, while
all of its data stays in chip. Hunk 2 can't simply be loaded into any memory, because it
holds data that DMA reads: the copper list at `h2+0000–0FFF` and the audio samples at
`h2+18000–1DFFF`. Moving it whole would mean finding every DMA consumer in every screen and
redirecting every reference to them; copying the code instead keeps a wrong guess
correct, only slower.

**Which code.** `tools/e2_tables.py` (run by the build) disassembles hunks 0 and 2 by
recursive descent from the program entry and the slave's hunk 2 code targets
(`c2_target_h2`, `c2_hud_targets`). A routine entered through a redirected absolute
`JSR`/`JMP` runs from the copy together with everything it reaches PC-relatively
(branches, `BSR`, PC-relative `JSR`/`JMP` and `LEA`/`PEA` of code). Such a closure must
not contain a hazard: a PC-relative `LEA`/`PEA` of data, a PC-relative read of data that
anything else references or writes, a PC-relative computed jump, or code written through
an absolute address. The game barely uses PC-relative addressing: the descent finds
11,498 hunk 2 instructions, and only six are hazards:

| Hazard | Why |
|---|---|
| h2+$520 | reads the keyboard table h2+$52A, which the level-2 handler writes |
| h2+$21AE6, +$21AEA | read a table after h2+$21AFC that code also addresses absolutely |
| h2+$24308 | reads a table at h2+$24310 that h2+$21A16 addresses |
| h2+$2C430, +$2C456 | `LEA` of h2+$2FB44 (data then written through A6) and of a jump table |

Of 256 absolute entries into hunk 2, the four whose closures reach these stay in chip, as
do the 8 below h2+$1D000 (copper, interrupt, keyboard and audio code, h2+$EC–$936). The
other 244 are redirected. The copy covers their closures, h2+$1D820–$2A640 (52,768
bytes, 46,926 of them instructions), and the patch table lists 467 relocated `JSR`/`JMP`
operands: 151 in hunk 0 and 316 in hunk 2. The tables contain offsets derived from the
game and are generated under `tmp/`.

**At run time.** Developer builds are WHDLoad 20 slaves (`slv_Version` 20) with one
alternative memory configuration: `MEMCONFIG=1` adds `E_AREAS` (`$25000`, 148 KB) of ExpMem
for E2's copy, E3's picture and E4's shadows. The default stays the release's
(`FASTMEMSIZE` `$80000`), because a chip-only 2 MB A1200 cannot allocate even about 32 KB
more (WHDLoad's "Can't allocate ExpMem"), whether in ExpMem or in the slave, and the
game leaves only about 24 KB of ExpMem free in a race. After patching, on a 68020 or
later whose fast memory header lies in real fast RAM (at or above `$200000`) and spans
more than `FASTMEMSIZE` (the spare is present), `e2_reserve` takes the top of it with
`AllocAbs`, where the game never allocates. `c2_capture.py` passes `MEMCONFIG=1` with
`--e2`/`--e3`/`--e4` on machines with fast RAM (`--memconfig` overrides). At the first live epoch, `e2_enable` copies the span and flushes the caches.
It then adds the copy's offset to each listed operand that still holds `JSR`/`JMP`
absolute with a target in the span, in the chip original and, for hunk 2 operands in the
span, in the copy, and does the same for the slave's own targets in the span. Finally it
flushes again. The seven operands that the clock's own patches replaced keep their slave
targets (h0+$3C9BC, +$3CCEA, +$3CCFC; h2+$1E154, +$2A2CA, +$2A33C, +$2A38C), so 460 move.
Return addresses and pointers already held keep pointing at the chip code, which stays
valid: both copies run the same instructions against the same data. Switching at a tick
leaves the menus at their original speed, so the race is the same race as with the option
off; with the switch at boot the faster menus would change the race's random seed (E1).

**Evidence** (`a1200-030` non-MMU, caches on, `CUSTOM4=1`, the D7 view schedule; VERIFY
`85615275…`, developer `2a889458…`, `tmp/e2/`):

| Check | Result |
|---|---|
| Race unchanged (`states-comparison.json`) | VERIFY with staging: off, on and its repeat identical at all 3117 common ticks. Developer (`dev-comparison.json`): off and on identical at all 3485 |
| Every picture rebuilt (`views-on.json`) | PASS for all 7676 staged pictures; the 14 negative probes are rejected |
| Enabled | VERIFY logs `E2 copy=009859E0 operands=460` (`whdl_log.txt`); the off arms log no E2 line |
| Without real fast RAM (`a1200-e2`) | Not enabled (ExpMem lies in chip); runs and quits OK |
| Disabled-feature gate (`tmp/b4/e2-acceptance.json`) | B4 PASS, all 318 hook bytes rejected; release `93dde23f…` unchanged |

| Build | E2 | Ticks | Fields | Pictures | Fields per picture | Picture rate on/off |
|---|---|---:|---:|---:|---:|---:|
| Developer | off | 3486 | 21,854 | 6736 | 3.24 | |
| | on | 3485 | 21,849 | 8875 | 2.46 | 1.318 |
| VERIFY | off | 3118 | 19,555 | 5876 | 3.33 | |
| | on | 3117 | 19,548 | 7674 | 2.55 | 1.306 |

On the 68030/50 the same race draws 31–32% more pictures, with no dropped field and no
catch-up tick. The VERIFY build's race differs from the developer build's (another slave
size), as before. The 040/060 gain is not claimed (deferred), nor the 68020 (current
scope).

Limits: E2 needs the clock patches (`CUSTOM2` bit 1), because it switches on at the first
live epoch. Code reached only through stored pointers (the interrupt handlers, menu code
reached through tables) and the four unsafe entries stay in chip; in the follow and green
windows of an earlier capture (`tmp/raw/`), 98.4% of the executed hunk 2 instructions lie in
the code the descent finds.

### E3 drawing in fast RAM — complete for the current scope

Behind developer `CUSTOM2` bit 5, the race picture is drawn in fast RAM and copied to the
chip back buffer when it is published. With E2 alone, a picture's acquire waits for the
previous exchange (the pending byte h2+$1DAB0), then for a VBL, and then copies the front
buffer into the back one, chip to chip. In a 100-field profile window on the 030
(`tmp/e3/profile-e2`) those three take 44.3% of all cycles (copy 22.5%, pending wait 12.0%,
VBL wait 9.8%), so the CPU spends most of a picture waiting for the display.

**Design.** `e3_reserve` allocates a 32,000-byte buffer F with `AllocAbs` below E2's copy
(or at the top of real fast RAM), under the same conditions as E2 (`MEMCONFIG=1`'s spare
ExpMem in real fast RAM, 68020 or later); with E4 the same block also holds E4's two
shadows. F always holds the last published picture.

- *Acquire* (`e3_acquire`, from `c2_acquire`) drains blits queued before the picture,
  chooses the chip back buffer as the one not submitted last, and points the renderer's
  destinations h0+$1252/$1256 at F. It doesn't wait and doesn't copy. After native code has
  owned the bitmaps (a modal, replay or menu handoff, `e3_leave`), the first picture first
  copies the front buffer into F.
- *Blits on F* run on the CPU. A new hook at h2+$27D62 (`e3_scene_wait`) skips the scene's
  pending-exchange wait and selects the game's own CPU path for the sky and ground fill
  (flag 0, the h2+$1E13C clear). Blits queued through h2+$1E6CC (`c2_blit_queue`) run in
  `e3_blit`, a software blitter. It handles channels A–D, shifts, first and last word
  masks, modulos and any minterm in ascending mode, and has a dedicated loop for the
  sky band ($07CA with A unshifted). Anything else counts as unsupported. In the race
  only the fill and the sky band occur.
- *Publish* (`e3_present`, from `c2_publish`) waits until the chip back buffer is no longer
  displayed (`e3_free`), copies F into it with `MOVEM` (800 × 40 bytes), and restores the
  native chip addresses before the native submission. Outside the window from acquire to
  publication, every pointer is what it would be with the option off.
- *D2's lead.* The next picture starts before the previous one is displayed, so the lead
  is measured by a VBL watch (`e3_vbl` in `c2_vbl`) from the submitted picture's saved
  start field and kind.

**Pixel twin (VERIFY `CUSTOM5` bit 2).** Each fill (`c2_clear`) and each queued block
(`e3_queue`) runs twice. First F is copied into the free chip back buffer and the
operation runs there on the real blitter. Then it runs on F on the CPU, and the two
pictures are compared byte for byte (`e3_compare`; on a difference `e3_fault` counts it,
and `c5_capture.py --twin` saves both pictures in `twin-faults.bin`). Chip bitmap checksums
at acquire and before every overwrite and publication catch stray writes into chip while
the picture is in F. A twin of whole scenes isn't exact: the renderer keeps caches in h0,
h1 and h2 across draws (for example the track record's clipping nibbles), so a second
draw of the same scene differs in a few bytes even with the CPU on both passes.

**Evidence** (`a1200-030` non-MMU, caches on, E2 on in every arm, `CUSTOM4=1`, the D7 view
schedule; VERIFY `d2d1fe4a…`, developer `78a15488…`, `tmp/e3/`):

| Check | Result |
|---|---|
| Pixel twin (`states-twin`, `slave-end.bin`) | 14,062 operations twinned in 4093 pictures: 0 faults, 0 stray chip writes, 0 unsupported blits |
| Race unchanged (`states-comparison.json`) | VERIFY with staging: off, twin and on identical at all 3389 common ticks. Developer (`dev-comparison.json`): off and on identical at all 3373 |
| Every picture rebuilt (`views-off/twin/on.json`) | PASS for all staged pictures in all three arms (17,197 with E3 on); the 14 negative probes are rejected |
| Enabled | VERIFY logs `E3 buffer=0097BCE0 … blits=26780 unsupported=0` at the epoch close; the off arm logs no E3 line |
| Without real fast RAM (`a1200-e3`) | Not enabled (`e3_buffer` 0); runs and quits OK |
| Disabled-feature gate (`tmp/b4/e3-acceptance.json`) | B4 PASS, all 324 hook bytes rejected; release `93dde23f…` unchanged |

| Build | E3 | Ticks | Fields | Pictures | Fields per picture | Picture rate on/off |
|---|---|---:|---:|---:|---:|---:|
| Developer | off | 3373 | 21,148 | 8435 | 2.51 | |
| | on | 3373 | 21,148 | 17,477 | 1.21 | 2.072 |
| VERIFY | off | 3389 | 21,250 | 8371 | 2.54 | |
| | on | 3389 | 21,248 | 17,194 | 1.24 | 2.054 |

On the 68030/50 with E2, the same race draws 2.05–2.07 times as many pictures, with no
dropped field and no catch-up tick. In the profile window (`profile-e3`) the pictures per
100 fields rise from 49 to 90. The remaining cost of E3 is the copy (22.5% of cycles, now
fast to chip), then the blits on the CPU (3.7%) and the wait for the back buffer (3.2%).
The twin arm runs every operation twice and draws far fewer pictures (5.20 fields per
picture, one catch-up tick); it checks correctness, not speed.

Limits: E3 is developer-only and needs the clock patches (`CUSTOM2` bit 1) and real fast
RAM. It was measured only together with E2. The 68020 and 040/060 gains are not claimed
(current scope and deferred work). Menus and modal screens keep drawing in chip.

### E4 hot routines — complete

**Re-profile with E1–E3 on** (030, E2 and E3, `CUSTOM4=1`): the top entry was E3's own
copy into chip (22% of cycles with the player on the grid, 15% in a rear-chase window).
The game's self time is spread thin (no routine above about 2.5%). Its largest inclusive
routine is the polygon filler h0+1F388 with the edge tracer h0+1EABA. The filler waited
on chip data at 27–50 cycles per access (moved below).

**The copy (done).** Behind `CUSTOM2` bit 6, each chip bitmap has a fast shadow of the
picture last copied into it. Publication compares the fast picture with the shadow
(`CMPM.L`/`DBNE`, about 9 cycles a long) and writes only the longs that differ, to chip
and shadow. An unknown bitmap (after native code owned the bitmaps) is copied whole. The
shadows follow F in E3's block (`MEMCONFIG=1`).

| Check | Result |
|---|---|
| Every copy compared (`states-check`, VERIFY `758dc84a…`, `CUSTOM5` bit 3) | Whole race: 5271 copies, 0 faults, 4 full copies, 3,409,343 longs written (8.1% of the picture on average) |
| Chip-only A1200 (`a1200`, default memory) | E2–E4 not enabled; runs and quits OK |
| A500-equivalent (`a500`, default memory, clock forced) | Reaches the race; quits OK |
| Disabled-feature gate (`tmp/b4/e4-acceptance.json`) | B4 PASS, all 324 hook bytes rejected; release `93dde23f…` unchanged |

Rear chase, 100 fields from tick 870, developer `e4347819…` (`profile-rear-e3/e4`): with
E4 the publication (mostly the copy) falls from 18.5% to 11.4% of cycles, and the window
draws 75 pictures instead of 68 (+10%). E4 changes only the copy, so the race and the
staged pictures are not re-compared.

**The renderer's data (done).** Behind `CUSTOM2` bit 7, the renderer's CPU-only chip
data moves to fast RAM at the first live epoch. f1gp loads hunks 2 and 3 into chip memory
(their hunk flags). Per-instruction cycles in the profile, grouped by the chip area each
absolute operand names (`tmp/e4/chipcost.py`), showed which areas the CPU waits on:

| Region | Use | Cycles before the move |
|---|---|---|
| h3+$112F8–$14F84 | Edge pool: the tracer (h0+1EABA, stepping at h0+1EF54–1F030) writes each edge's X list from the cursor h0+$1F03A (reset at h2+$28112, limit h3+$14D90 plus one edge); the filler reads it. The standings sorts at h0+28FF6, h0+29168 and h0+29E4E use its start as scratch. | the filler's and tracer's 27–50-cycle accesses |
| h3+$200–$704 | Span masks and word offsets for X 0–320 (built by h2+$1E936), read through A5 | (with the pool) |
| h2+$1E804–$1E810 | The fillers' jump-offset words h2+$1E804 and h2+$1E80E | (with the pool) |
| h2+$23126–$2327E | Scene variables: camera, horizon and viewport, object lists, flags (976 operands) | 11.8%, 50 cycles an access |
| h2+$28168–$281AE | Projection variables, with the pool cursor's saved copy (150 operands) | 4.5%, 42 cycles an access |

No other chip area costs more than 0.4%. The hunk 2 blocks lie between pieces of code
(their ends, h2+$2327E and h2+$281AE, are JSR targets).

`tools/e4_tables.py` lists every relocated long that holds an address inside a region
(1162 in hunks 0 and 2) plus the run-time cursor h0+$1F03A. It reports the end bounds it
leaves alone: h3's clear (h2+$24A), JSRs to h2+$1E810, h2+$2327E and h2+$281AE, and the
next table at h3+$704. It fails the build if a hunk 2 region holds a known instruction or
a known instruction reaches it PC-relatively (from E2's recursive descent). All other
accesses use those addresses or pointers derived from them. The slave copies each region
into a block below E3's picture (17,264 bytes; `MEMCONFIG=1`'s spare grows to $29000),
then moves each listed long, in the copy when it lies in a region, by the distance when it
points into one. This runs before E2's copy, so the copy holds the moved operands.
Pointers already stored elsewhere keep the chip original, which still holds the same
bytes. The slave's own accesses map through `e4_map`: the bitmap stride h2+$231DA (E3 and
C2 acquisition), the horizon clamp h2+$231CC (D4), the HUD box flag h2+$231EA, and D1's and
D3's game ranges. `c2_capture.py` overlays the moved bytes on its hunk dumps, so the
comparators read the live values. The per-tick probes (`--states`, `--rate`) still read
chip offsets and refuse `--e4-data`.

The move changes only where the data lives, so the check is the same tick's picture and
state with the move off and on (developer `8fcb7009…`, rear chase, `--publish` at tick
900, `paint-off/on`): the picture is identical (0 of 32,000 bytes differ) and so are the
selected A3/A4 ranges (`c2_compare.py`). With `CUSTOM4=1` (`profile-rear-data2`), D1's
snapshot of h2+$231D4 holds the live values while the chip original keeps those of the
first live epoch, so the slave reads the moved variables.

**The race depends on the build.** Different developer builds reach different races
from the same route (at tick 900 one build's player is racing, another's stands retired
beside a marshal), probably through startup timing; within one build `CUSTOM2` bits 7 and
8 leave it unchanged. Profiles of different builds therefore draw different pictures, and
a change's gain comes from a same-build pair with its bit off and on. Two windows:
rear chase (`--views`, 100 fields from tick 870) and the grid at the start lights in the
cockpit (100 fields from tick 60; the player fourth, cars ahead), at one picture per field.
In the grid window publication absorbs any saving as the wait for the field (`e3_free`),
so the scene's time per picture is the measure in both.

Same-build pairs, developer `4e94a858…` (`rear-b0/b7`, `profile-rear-r8`,
`grid-b0/b7/b8`), scene ms per picture:

| Window | Bit 7 off | Bit 7 | Bits 7 and 8 |
|---|---:|---:|---:|
| Rear chase (pictures) | 22.98 (68) | 16.92 (88) | 16.39 (89) |
| Grid, cockpit (pictures) | 13.47 (100) | 10.05 (100) | 9.58 (100) |

In this build's rear-chase window the player's car stands retired, so pictures change
little (about 370 longs each). The figures in earlier notes (19.7, 18.0 and 16.6 ms)
compared different builds' windows and so different pictures.

**Exact faster routines (done).** Behind `CUSTOM2` bit 8 (hooks applied above the 68000):

- *The tracer's X-major steps* (h0+$1EF74, h0+$1EFDE). Natively a Bresenham loop runs
  once per pixel of X, about 31 iterations an edge in rear chase, and stores X only when Y
  steps (3–5 stores). With dx = q·dy + m, the first store comes q/2+1 pixels in, with
  the error term ((q odd ? dy : 0) + m)/2 + 1 − dy, and each further one q or q+1 pixels
  on as the term passes zero: one `DIVU` and dy steps store the same values. The form
  matches the loop exactly for every dx up to 1099 and dy ≤ dx (`tmp/e4/dda.py`) and
  follows algebraically for all. D3.W ends as natively, ~(dx/2); D4 and D6 end at the
  last X so the native loop exits at once, and its exit restores D4–D7.
- *The sky band's strip* (h3+$704–$1704). h2+$1F320 builds it at a session's setup
  (called only from h0+$20E) and only the band's blit at h2+$1F41E reads it, at most 8
  rows of 128 bytes and 106 bytes into each. E3's CPU blit read it from chip at 36 cycles
  a word. After each build the slave copies it to fast RAM, and the band reads the copy
  while E3's blits run on the CPU (`e3_soft`); the native blitter keeps the chip strip.
  The copy matched the strip at the end of the profile. The VERIFY blitter twin cannot
  follow the copy, so `c2_capture.py` refuses `--twin` with `--e4-routines`.

The check is the same tick's picture and state with the bit off and on (`p8-off/on`,
rear chase at tick 900): identical picture and `c2_compare.py` PASS. The B4 gate
(`tmp/b4/e4r-acceptance.json`) passes with the new ranges; release `93dde23f…` unchanged.
Rear chase: the tracer falls from 6.73% to 6.21% of cycles inclusive and `e3_blit` from
2.60% to 1.73%; in the grid window the tracer falls from 5.96% to 5.06% and `e3_blit` from
4.01% to 2.57%, while the copy's share stays at 7.35% (the same pictures).

**Where the time goes now** (`profile-rear-r8`, inclusive): the scene 73%; the car
models h2+29C16 16.3%; the filler h0+1F388 15.8%; the point projection h2+$23290 9.0%
(about 410 cycles a call, 248 calls a picture; its four `MULS.W` and two `DIVS.W` take
about 200, and its 306 bytes exceed the 030's 256-byte instruction cache); the copy 7.9%;
the scaled objects h0+147C 6.8%; the tracer 6.2%; the slave's own code 23%. No single
instruction exceeds 0.9%. The grid window adds the copy's compare loop (7.4%, no longs
written) and D3's staging walk (about 3.5%).

### E5 AGA 32-bit fetch — measured, not kept

The game sets the display once, at startup (h2+$182–1B8): `BPLCON0` $4200, display
window and data fetch from h2+$2A648–2A64F (`DDFSTRT`/`DDFSTOP` $38/$D0, 20 words a
line), modulos 0. Its copper lists at h2+0 and the menus' list (h2+$3632E) load only
plane, colour and sprite pointers, so an `FMODE` change applies to every screen. The
trial wrote `FMODE` 1 and `DDFSTOP` $C8 (the last of ten 2-word fetches starts 8 colour
clocks earlier) at h2+$1A8 when `LISAID` read $F8. The emulated A1200 is AGA. `DDFSTOP`
$C8 without `FMODE` 1 drops the last fetch, so identical pictures show the 32-bit fetch
was in effect.

Same-build pairs on the 030 (E2–E4 on, 100 pictures each): the same tick's picture is
identical, and a picture's scene goes from 9.58 to 9.55 ms on the grid and from 16.54 to
16.51 ms in rear chase (−0.3% and −0.2%). After E3 and E4 the CPU's chip traffic is the
copy's writes into free bus slots, so halving bitplane DMA leaves little to recover, and
64-bit fetch (`FMODE` 3, 8-byte-aligned buffers) can recover no more. The global display
change was not kept.
