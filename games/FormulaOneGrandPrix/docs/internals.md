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
F10 quit hook. No performance changes are installed. The old CPU mask is retained;
B5 has not enabled caches. DOS BSTR assign names are explicitly longword-aligned.
The shared kit is consumed in place, rather than copying WHDLoad source into this repo.

B2 build checks: bash 3.2, ordinary and spaced output directories produce identical
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
window length. The current slave SHA-256 is
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
| Keyboard in the race | Level-2 handler h2+$2D4 calls +$47E; +$488 reads CIAA ICR and +$4A8 reads SDR. The original slave's hook at +$4AC decodes the key and handles F10. The routine records pressed/released state in the key table h1+$52A. h0+$64 scans that table once per loop pass to form gameplay key masks. This is asynchronous acquisition with frame-rate consumption, not a once-per-VBL keyboard poll. |
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
