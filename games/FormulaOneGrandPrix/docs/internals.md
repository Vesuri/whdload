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

`whdload/F1GP.s` builds with slave version 17 and the pinned shared kick13 source.
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

### B5: gated cache pilot — gate not passed

`CUSTOM2` bit 0 requests instruction/data caches through `resload_SetCPU`, with
BaseMem write-through and ExpMem/Slave copyback. The 030 write-allocation disable bit
is clear because the game runs in user mode. This follows WHDLoad's documented Amiga
hardware inhibition of Chip/IO data caching; it is not permission to cache DMA buffers
on arbitrary hardware. WHDLoad's `NoCache` override remains effective. All CUSTOM bits
zero retain the old CPU request and original hooked game bytes. Caches remain opt-in
until B5 passes; no simulation/presentation patch is enabled.

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

**Gate: not passed.** The 030/040 startup stalls were an emulator deadlock, now fixed
(next section). All six 030/040/060 setups start with caches on and repeat exactly under
deterministic mode. Whole-race pairs now pass on all six 030/040/060 setups (see below).
A7's matrix is complete under its explained-failure gate. B5 still lacks matched
040/060 work gains because their CPU traces are empty; A8 remains partial below. Disabling data-cache emulation is
not an accepted substitute. AmigaXDev TOOL2 (the launcher refuses unknown CPU names) and
TOOL3 (failed captures leave no image or trace) are also fixed and installed. F1GP's
runner keeps its own effective-CPU and fresh-trace checks as extra guards.

### Current B5/A7 validation

The current emulator is pinned by `manifest/runtime-inputs.json`; its SHA-256 is
`950f14c966ba852372d382dec8e40544f1c49184eb9f2c24e901f352ecd9b048`.
It retains TOOL1 and adds the shared window-title change. Earlier evidence keeps its
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
all runs use the currently pinned emulator and launcher. Each capture records actual
four-hunk bases, full effective configuration, build/runtime/tool hashes and cache audit.
No game or trace bytes are tracked. Reproduce with the development matrix recipes.

### A8 developer ceiling gates — partial result

Developer and VERIFY builds expose `CUSTOM3` bit 0 (replace the four-byte pacer branch
at `h0+$1288` with NOPs) and bit 1 (RTS at polygon filler `h0+$1F388`). Release omits
both options and patches; its binary SHA-256 remains
`93dde23f76df6dab0ca3beea3507e29e25fb5e6a6bb3b06dab2e8697c4c75495`.
The filler walks the edge lists, loads the back buffer through `h0+$1252`, and writes
four bitplanes. Its scratch is classified as presentation by A3. These are measurement
options with native frame/world coupling; no-wait intentionally speeds up the game.

All-off captures `tmp/b4/a8-release-off`, `a8-developer-off` and `a8-verify-off` pass
all eight loader/name checks, original optional-range bytes, and clean quit. The actual
VERIFY relay-on control passes separately. The checker supports declared PL_PS, PL_NOP
and PL_R hooks and its negative tests reject mutations of all 12 optional-hook bytes,
wrong gates/layout/source and a falsely labelled enabled relay.

All ceiling arms use the same VERIFY binary (SHA-256
`084d897ceb94d431646dad4ffa41e5fafabe49df6eb5c27a51600454b60c4bd8`) and the native
start-state transition at `h0+$3B4FA`, followed by the next full field. This avoids
relying on painted lights in the no-fill arm. The breakpoint is removed before the
100-field timed window. The new binary is not the earlier B5/A7 VERIFY baseline.

| Machine | Normal pacer fps | No wait fps | No wait + no fill fps | No wait + instant blits fps | Four-arm audit |
|---|---:|---:|---:|---:|---|
| A500-equivalent | 5.81 | 5.81 | 6.82 | 5.93 | PASS |
| A1200, Chip only | 7.98 | 11.52 | 13.60 | 11.56 | PASS |
| 020 + Fast | 7.98 | 17.15 | 20.05 | 17.31 | PASS |
| 030/50 + Fast | 8.01 | 25.30 | 28.05 | unavailable as matched comparison | FAIL: instant arm changes Fast placement |
| 040/25, 060/50 | unavailable | unavailable | unavailable | unavailable | CPU instruction records missing |

The accepted A500/A1200 evidence is `tmp/a8/{a500,a1200}-{arm}-{a,b}`; 020 and the
rejected four-arm 030 comparison are in `tmp/matrix-workers/a8-anchor/tmp/a8/` with
the same naming. Arms are `control`, `no-wait`, `no-fill`, `instant`. All use
`CUSTOM1=1` to skip the frontend in every arm. Accepted rows pass exact repeated
screenshots and reductions, common build/layout, actual enabled/disabled hook bytes,
effective blitter settings and clean quit. The A500 has no CPU caches; the cache-on
request logs zero as expected. These figures cover this start window with native
simulation coupling, not every scene or a real-time presentation implementation.

The original-route 020 instant pair changes h2/h3 placement by 168 bytes and startup
timing: its 17.31 fps cannot be compared with the original-route no-wait 16.84 fps.
Skipping the frontend produces the accepted 020 common-layout row above. On the 030,
frontend skipping still leaves the instant arm's h0/h1 24 bytes higher, although the
h2/h3 bases and menu route agree. Its measured 25.29 fps is retained as an unmatched
observation, not evidence that the blitter has no cost. The common-layout 030
control/no-wait/no-fill arms remain valid. Both failed layout audits are retained.

The enabled combined no-wait/no-fill arm also passes fresh functional repeats on
030-MMU, 040-MMU and 060-MMU: both hook byte sequences, cache audits, four PNGs,
profile reductions and F10 quit agree. Evidence is
`tmp/matrix-workers/a8-anchor/tmp/a8-mmu/{030,040,060}-mmu-{a,b}`. These are MMU
functional checks, not timing results.

The off-state acceptance report is `tmp/b4/a8-acceptance.json`; regenerate it with
`slave_gate.py --check --prefix a8-`. **A8 is incomplete:** the 030 instant-blitter
allocation difference and 040/060 missing CPU traces prevent all-machine acceptance.
The user has chosen to keep shared AmigaXDev fixes deferred. No fallback core or
synthetic zero timing is accepted in place of these measurements.

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

The installed native emulator now hashes to
`950f14c966ba852372d382dec8e40544f1c49184eb9f2c24e901f352ecd9b048`.
Its source-revision record retains the TOOL1 determinism patch and adds AmigaXDev's
window-title patch (`d5ce108`); both patch hashes match the shared sources. The launcher
pin is unchanged. Earlier startup evidence above belongs to its recorded build.

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
presentation is not classified yet.

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
| h0+$125E: h0+$1272, +$127C; h2+$232, +$27E98 | Presentation/hardware: elapsed work, frame wait, keyboard handshake timeout, renderer work/wait decision. h0+$2CC3C increments once per VBL; h0+$128C and h2+$222 clear it. |
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
