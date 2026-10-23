# Internals

Addresses are offsets in `Disk.1` unless marked as slave patch-list offsets. The game
image loads to a fixed chip address, so the slave's absolute addresses map to `Disk.1`
by one constant (below).

## Slave

`Mercenary3.Slave` (1,148 bytes, Harry, Graham and Wepl, version 1.2, 29.07.2004) is
identical in the full install and the official installer. The installer's
`src/Mercenary3.slave.asm` is an earlier state of its source: the shipped slave also
has the `PL_W $716` and `PL_P $A858` patches below, a `_waitvb` subroutine where the
source expands the `waitvb` macro inline, and the build date. `src/Mercenary3.islave.asm`
is the RawDIC imager.

`whdload/original/Mercenary3.slave.asm` is the reconstruction: the installer source
with those additions and with Barfly's optimised encodings written out (`moveq`, short
branches, PC-relative `lea`, `cmpi` and an `abs.w` operand). vasm `-no-opt` rebuilds the
shipped slave byte for byte (`make original`).

| Field | Value |
| --- | --- |
| `ws_Version` | 10 |
| `ws_Flags` | `NoError`, `Disk`, `EmulTrap` |
| `ws_BaseMemSize` | `$80000` (512 KB, all chip) |
| `ws_ExpMem` | 0 |
| KickEmu | none: a direct (no-OS) game |
| `ws_keyexit` | raw `$41` (Backspace; the source comment says F10). Raw `$78` also quits |
| Options | none |

Boot sequence in `_boot`:

1. `resload_DiskLoad` `Disk.1` `$0..$7D80` to chip `$4000`: a title picture whose
   palette and four planes are shown for one second (`resload_Delay 50`).
2. Clear chip `$100..$80000`, then load `Disk.1` `$9000..$767B0` to chip `$5350`.
   A chip address `A` in the game image is therefore `Disk.1` offset `A + $3CB0`.
3. Point four game variables at the slave's keyboard bytes (chip `$8`/`$9`). On a 68040
   or later only, rewrite eight code locations to use vectors at chip `$C0..$CC`.
4. If the word at `Disk.1` `$5DE60` is `jsr abs.l` (`$4EB9`), this is the copy-protected
   version and the slave replaces the call with three `moveq #0,d0`. The supplied install
   is that version.
5. `resload_Patch` with base `$50000`, `resload_SetCACR` with the instruction cache on,
   then jump to `Disk.1` `$4EDB0` with SR `$2700`.

Patch list (offsets relative to `$50000`; add `$53CB0` for the `Disk.1` offset):

| Offset | Patch | Purpose |
| --- | --- | --- |
| `$716` | `PL_W $8200` | the operand of the game's `move.w #$8380,dmacon`: enable master DMA only, without copper and bitplanes |
| `$1E30` | `PL_S 8` | skip a ROM access |
| `$205A` | `PL_P _subd0` | replace an empty `dbf` delay with a raster-line wait |
| `$29A6`, `$29BC`, `$29C6` | `PL_P _patch_aud1` | AUD1 interrupt exits: poll the keyboard, acknowledge, `rte` |
| `$2AC0`, `$2C9E` | `PL_P _patch_vertb` | VERTB interrupt exits: the same |
| `$5E8A` | `PL_P _loadgame` | load `Mercenary3.saveN` from the install directory |
| `$5F26` | `PL_P _savegame` | save `$2056` bytes from chip `$5550` |
| `$A858` | `PL_P _dmaon` | enable copper and bitplane DMA after a vertical blank, then copy six bytes and return |

`$A858` is inside the frame publication routine (below): every frame it copies 34 bytes
from chip `$7CC0` to the pointer at `$72B4` with an unrolled `move.l (a1)+,(a0)+` run, and
the patch replaces its fifth to seventh moves. `_dmaon` then copies six bytes and returns, so
each frame copies 22 bytes instead of 34: the moves at `$A85E` and `$A860` never execute
(0 of 75 frames in the profile window). `_dmaon`'s body (`move.l`, `move.w`, `rts`) matches
the copy's last six bytes at `$A85E`, so the patch looks placed for a layout 12 bytes
different, probably the other supported version. `_dmaon` also rewrites DMACON and waits
for a vertical blank on every frame, not once.

The slave installs its own level-2 handler at `$68` for the keyboard. Its keyboard
poll (`_checkkeyboard`) busy-waits three raster lines for the handshake and stores the
key code at chip `$8`, with `$FF` at `$9`.

## Performance slave

`whdload/Mercenary3.slave.asm` starts from the reconstruction. It declares WHDLoad 17
(for the startup control), reads options through `resload_Control` and keeps
the shipped patch list. The release exposes **Enhanced framerate**, default On
(`Custom5=1`), which selects all feature bits below. Off (`Custom5=0`) clears them;
release builds ignore `Custom1`. The VERIFY build accepts `Custom1` as the individual
feature mask with `Custom5=0`. Historical measurements below name those feature bits. It asks for an optional 200 KB of expansion memory (`ws_ExpMem`):
4 KB for bit 2's stack, 4 KB for bit 5's hot code, 28 KB for bit 6's lookup tables and
20 KB for bit 4's presentation restore buffer, 36 KB for bit 9's renderer copies and
96 KB for bit 10's aligned staging bitmap and 12 KB for bit 11's object histories.
If allocation fails, the stack, code and
tables retain their chip paths; presentation falls back to logic gating. With every option off it runs the shipped slave's code paths.

| Option | Effect |
| --- | --- |
| `Custom1` bit 0 | `_dmaon` enables copper and bitplane DMA on its first call only, after the vertical blank, and completes the frame's 34-byte copy (the three replaced moves, then the original code from `$A85E`) |
| `Custom1` bit 1 | On AGA (Lisa's ID `$F8` in `LISAID`), 64-bit bitplane fetch: `FMODE` = 3 and `DDFSTOP` `$B8` in the two known in-game copper lists (Disk.1 `$56780`, `$567CC`). Buffers and planes are 8-byte aligned, rows 40 bytes, modulos 0; vehicle, flight, lift and A-to-Z panel coverage is recorded under P3 |
| `Custom1` bit 2 | The supervisor stack in a 4 KB expansion block (fast RAM when fitted) instead of the top of chip RAM: the three `lea $7fffa,a0` / `unlk a0` stack setups (Disk.1 `$5DE66`, `$5DE88`, `$5DEEA`) get its top. The game uses less than a page of stack |

`Custom1` bit 3 gates walking logic to at most 12.5 passes/s (L1 below).
Bit 4 adds walking presentation frames and includes that gate (P1 below).
Bit 5 moves numeric helpers and projection code to fast RAM on 68020+ (M1 below).
Bit 6 copies their read-only lookup tables to fast RAM (M2 below).
Bit 7 accelerates horizontal span interiors on 68000 and fast-RAM 68020+ (R1 below).
Bit 8 copies the full presentation restore set with bulk moves (S2 below).
Bit 9 moves the remaining hot renderer blocks and their private mutable data to fast RAM (S3 below).
Bit 10 stages the 3D bitmap in fast RAM and copies the view before publication (S4 below).
Bit 11 interpolates object geometry with bit 4 and real fast RAM on 68020+.
Bit 12 extends logic gating and presentation to vehicle/surface flight and space flight
(P3); requires bit 4 for presentation.
Bit 13 requests the data cache through WHDLoad (R4 below).
The `VERIFY` build adds the presentation restore markers and displayed-frame counter;
release builds keep only the game's logic-pass counter.

### O1: existing options

Expansion memory is optional (`ws_ExpMem = -$1000`); a zero returned pointer leaves
all three chip-stack setups untouched. Allocation failure was not forced in these runs.
Same-build, same-session `fps.py` results over the 500-field route:

| Custom1 | a1200-fast fps | a500-1.5m fps |
| --- | --- | --- |
| 0 | 7.50 | 3.70 |
| 1 (DMA) | 9.00 | 4.10 |
| 3 (DMA + FMODE) | 9.40 | 4.10 |
| 5 (DMA + stack) | 9.40 | 4.10 |
| 7 (all three) | 9.60 | 4.10 |

Options off matches the shipped slave's 37 A500 frames. On `a1200-fast`,
`sim_speed.py PER_FRAME=1 CUSTOM1=7` gives walking displacement `-6 × dt` and
turning `2 × dt`, with dt 4–6 fields. Route, Help, save/load and Quit Situation
screens were played and inspected with all three options on: loading restored the
saved view, heading and clock; Quit Situation moved to Eris and walking continued.
No display fault was seen. Map, vehicle and flight screens (and any separate fetch
windows there) are deferred by user decision. Evidence: `tmp/o1/`.

### L1: walking logic gate

`Custom1` bit 3 redirects the six-byte `jsr` at Disk.1 `$5DF92`. In walking mode
(chip `$7122 = 1`), it waits until four VERTBs have elapsed since the previous accepted
pass, stores the true elapsed count in chip `$52954`, then runs the original callee
(`$5DF48`). A separate word timestamp handles counter wrap without disturbing the
publication stamp. The original 4..8 tick clamp remains. The first pass keeps native
timing; another mode clears the timestamp's validity and otherwise runs unchanged.

Same build/session, `fps.py`, 500 fields, `Custom1=7 → 15`:

| Machine | Gate off | Gate on |
| --- | ---: | ---: |
| a1200-fast | 96 / 9.60 fps | 96 / 9.60 fps |
| a500-1.5m | 41 / 4.10 fps | 41 / 4.10 fps |
| 060-50 emulator cell | 198 / 19.80 fps | 125 / 12.50 fps |

The fast-cell reduction is intentional: rendering still accompanies each logic pass
until P1. Its counts are not hardware speed predictions. `sim_speed.py PER_FRAME=1`
shows the 060 gate-off walk advancing 24 units and turn 8 heading units per 2–3 fields;
gate-on gives exactly 24 and 8 every four fields. On the 020, gate-on motion is
`6 × dt` and `2 × dt`, dt 4–6. The word now measures pass-start intervals, rather than
the previous publication interval. No waits are needed when a pass already takes four
or more fields; the slow-machine 8-tick cap remains.

Options-off and shipped both give 37 A500 frames. The fastest-cell idle, walk, turn and
stop screenshots show an intact scene and panel, and the view stays still after stopping.
Builds and input checks pass. O1's deferred map/vehicle/flight coverage remains deferred.
Evidence: `tmp/l1/`. No new instruments or emulator changes.

### P1: player presentation frames

`Custom1` bit 4 replaces spare walking waits with a saved-state redraw. It includes
L1's gate. The staged pose is the committed pose plus the last pass's displacement
scaled by elapsed fields / that pass's clamped tick count. Angles wrap at 1024;
collision rollback, discontinuities and mode changes suppress extrapolation. A stopped
pass gives zero displacement. Other modes and special screens retain their native path.
With one field left, a redraw starts only if the last presentation fitted one field
(initial estimate: two); this avoids a measured one-frame loss on the 030 MMU cell.

Camera/view setup precedes publication; back-buffer setup and drawing follow it, in
native order. Disk.1 `$5E0BA` is an inline block, not a callable routine. The redraw
includes `$469C8` and `$5765E`, omitted from the initial plan sketch, and never calls
collision or main-loop logic. A 17,366-byte expansion-memory buffer restores scratch, drawing
variables, object-selection tables and self-modified words, including the 040 indirect
vectors. Copper state and bitmap output remain live. Chip `$7180` counts logic passes;
a separate displayed-frame counter exists only in VERIFY.

Same VERIFY build/session, `fps.py` through `matrix.sh`, 500 fields, `Custom1=15 → 31`:

| Machine | P1 off | P1 on |
| --- | ---: | ---: |
| a500-1.5m | 40 / 4.00 fps | 40 / 4.00 fps |
| a1200 | 94 / 9.40 fps | 94 / 9.40 fps |
| a1200-fast | 96 / 9.60 fps | 96 / 9.60 fps |
| 030 default / MMU | 116 / 11.60 fps | 116 / 11.60 fps |
| 040-25 emulator cell | 125 / 12.50 fps | 141 / 14.10 fps |
| 060-50 emulator cell | 125 / 12.50 fps | 153 / 15.30 fps |
| 040-8 advisory cell | 125 / 12.50 fps | 139 / 13.90 fps |

The 040/060 increases are emulator frame counts, not hardware speed predictions.
There is no measured gain on the lower cells; faster drawing remains necessary there.
Both matrices complete. Release options-off and shipped both give 37 A500 frames.
Release `sim_speed.py PER_FRAME=1` skips staged poses: held walking is `-6 × dt`,
turning `2 × dt`, with dt 4–6 on both 020 and 060. The route's 32 VERIFY presentation
restores have identical masked SHA-256 hashes. Exclusions are display state and the
identified live interrupt updates, including startup panel bars and text scrolling;
these updates are not rolled back. The check caught and corrected a missing renderer
selection-table restore at chip `$AA6E..$AF65` and its selection word `$5447E`.

Release idle, walking, 20 successive turning publications and stopping screenshots
were inspected. Intermediate views appear between logic frames, without visible scene
or panel faults. After stopping, position and heading modulo 1024 stay fixed across
81 fields. This is route coverage, not the deferred map/vehicle/flight coverage.
Inputs, three builds and 17 existing tool tests pass. Evidence: `tmp/p1/final-off/`,
`final-on/`, `restore-route.json`, `world-020.json`, `world-060.json`, `play/`,
`options-off.json` and `shipped.json`, all under `tmp/p1/`.

### P2: other-object interpolation

`Custom1` bit 11 requires bit 4, a 68020+ and real fast RAM. It uses 12 KB of
optional expansion memory for 256 pose histories. Object XYZ are the longword arrays
at chip `$581C`, `$5C1C`, `$601C` (four-byte stride); vehicle slots 1–27 use byte
headings at `$6C1C + 4 × slot`, wrapping at 256. `$AF36` and `$B31E` are drawing
scratch, not world poses. The visible-object list is at `$7423`, count `$71E6`.

Disk.1 `$577BE` captures native-pass poses. Both logic and presentation drawings use
the previous/current pair and elapsed fields at drawing time; delaying only the extra
frames would rewind objects. Geometry is staged at `$57C36`, after the native distance
and nearest-object tests, and restored before each model returns. Collision, distance
ordering, object selection and simulation keep committed poses. New/reappearing objects,
scene/model changes and per-axis jumps over 32,767 units snap; stationary objects skip
staging. The player proxy remains with P1. This works with the S3 copy or chip renderer.

Near the Eris bus crossing (HELP, F10, 150 fields walking), 20 consecutive 030 draws
advance the bus by 256 units every two fields; committed motion stays 512 per four-field
logic pass. Inspected off/on screenshots show the intermediate positions rather than
repeated frames. Same-build/session 500-field `Custom1=2047 → 4095` measurements:

| Cell | P2 off | P2 on |
| --- | ---: | ---: |
| A500 | 4.10 fps | 4.10 fps |
| 020-fast | 12.50 fps | 12.50 fps |
| 030/50 reference | 24.80 fps | 24.80 fps |
| 040-25 run check | 24.90 fps | 24.80 fps |

The gain is smoother object motion, not more frames. The 040 cadence check shows two
isolated one-field frames becoming two-field frames, not a startup difference; with P2,
all intervals after the first are two fields. This emulator cell is a run check under
S0, not a hardware-performance acceptance target. The reference 030 count is unchanged.

World-speed checks pass all 79/80 walking and turning intervals on 020/030. Options-off
and shipped each give 37 A500 frames. Restore hashes pass 124 route presentations,
63 beside moving buses, and another 28 there with S3 off. The check's live-interrupt
mask now covers all six cached clock digits at chip `$52BF0..$52BF5`: the field handler
writes them at Disk.1 `$568E4..$5693C`; the old one-byte exclusion failed with P2 off too.
Evidence: `tmp/p2/final/`. Vehicle/flight/map coverage remains for P3.



### P3: vehicles, flight and lifts

`Custom1` bit 12 extends the four-field logic gate to matching committed/render modes
0 (vehicle/surface flight) and 2 (space). Presentation follows their native drawing
paths, Disk.1 `$5E280..$5E3BA` and `$5E3CE..$5E440`, without running movement,
input or collision again. Space stages the navigation pose at chip `$702A..$7035`
as well as the player pose. Bit 11 also interpolates objects in those modes.
Boarding/leaving resets history; transport, scene, planet and floor changes snap.
Transport displacements over 32,767 units per axis also snap to avoid signed-word
arithmetic overflow. Enclosed rooms retain native drawing.

Lifts already use walking mode and the tick timer at Disk.1 `$5A644`: the camera
changes height at arrival, not continuously during travel. P3 preserves that behaviour
and suppresses extrapolation across floor changes. The restore set grows from 17,366
to 17,912 bytes within its existing 20 KB allocation, covering navigation scratch,
star colours, sorting and the entry-delay timer mixed into planet drawing. The restore
check exposed live sound-envelope updates; its interrupt exclusions now include the
callback at chip `$4B390` and envelope state `$4B39A..$4B39F` (field-handler code at
Disk.1 `$4F202..$4F22A`, `$4FC96..$4FCB8`, callback writer `$4FCCC`). These remain
live rather than being restored.

Play with options 0–12 enabled covered the Eagle key pickup, B to board, powered
surface flight, stopping, landing, L to leave, escape to space, and planetary arrival.
Dooberry's and ETA House lifts reached floor 9; the floor-9 transporter connected them.
The A-to-Z computer was collected and activated at ETA House. It uses the normal
navigation panel (Disk.1 `$511C4`), not a separate full-screen copper/fetch-window path;
vehicle, flight, lift and navigation screenshots showed intact views and panels with
FMODE 3. This closes O1's deferred coverage for the reached screens; the earlier
assumption of a separate full-screen map was unsupported by the supplied manual.


Same final VERIFY build/session, `fps.py`, 500-field standard route,
`Custom1=4095 → 8191`: A500 **4.10 → 4.10 fps**, 020-fast **12.50 → 12.50**,
030/50 **24.80 → 24.80**, existing 040-25 run check **24.80 → 24.80**.
The loaded Eagle/open-flight route gives **50.00 → 50.00 fps** over 500 fields.
With P3 on, all 31 sampled logic intervals are four fields, advancing XYZ by
362/60/159 units per pass at fixed power/pitch. This preserves 50 fps presentation
while reducing the previously frame-driven logic from 50 to 12.5 passes/s in that view;
it is not a claim that every flight scene reaches 50 fps. All 650 lift samples match
exactly off/on: the ground-floor arrival changes height at field 316. Space also
keeps four-field logic spacing in all 28 sampled within-mode intervals; planetary
entry resets the gate for its first surface pass, then resumes four-field spacing.

Options-off and shipped each give **37 frames / 500 fields** on A500.
Walking/turning retain 6/2 units per field in all 79/80 checked 020/030 intervals.
Restore hashes pass 124 walking, 188 surface-flight, 187 space-flight and 392 lift
presentations. Evidence: `tmp/p3/final2/`, `tmp/p3/restore-space-3.json`; play screenshots
and the locally saved Eagle, lift and A-to-Z situations are under `tmp/p3/`.


### M1: hot code in fast RAM

`Custom1` bit 5 copies 2,710 bytes at boot: the numeric helpers at Disk.1
`$4EDE4..$4EF92` and projection kernels at `$5B030..$5B918` (exclusive ends).
These cover the two leading instruction-fetch regions in the existing bus profile.
The first 4 KB of the optional expansion allocation holds the stack;
the second holds the code copies. Relocation requires 68020+ and an allocated block in
Zorro-II fast RAM or the 32-bit expansion address range. Chip/slow RAM and allocation
failure keep the original code.

Copy both blocks before installing seven entry jumps. The long-input conversion
entry at `$4EE84` retains its first two instructions, then falls through the relocated
entry at `$4EE88`, avoiding overlapping patches. All relative branches stay within
their copied block; data references remain absolute or register based. No external
PC-relative fixups are needed for these blocks. The self-modifying drawing sites
remain in chip RAM with their existing 040 patches. The subsequent `resload_SetCACR`
flushes the caches before game entry. No runtime copying or new instrumentation.

Same VERIFY build, `Custom1=31` versus `63`, the 500-field route in one session:

| Cell | M1 off fps | M1 on fps |
| --- | ---: | ---: |
| a500-1.5m | 4.00 | 4.00 |
| a1200 | 9.40 | 9.40 |
| a1200-fast | 9.50 | 10.90 |
| 030 default / MMU | 11.60 | 12.40 |
| 040 25 MHz | 14.10 | 14.60 |
| 060 50 MHz | 15.30 | 16.00 |
| 040 8 MHz sanity | 13.90 | 14.30 |

A1200-fast gains 14.7%, with no measured loss in the matrix. The 040/060 figures
remain emulator counts, not hardware-speed predictions. Evidence:
`tmp/m1/matrix-off/`, `tmp/m1/matrix-on/`; an initial A1200-fast pair also gave
95 versus 109 frames.

The release slave with all options off matches the shipped slave at 37 A500 frames
in this session (`tmp/m1/options-off.json`, `shipped.json`). With bit 5 enabled,
per-logic-publication samples on A1200-fast and the 060 cell retain walking at
6 units and turning at 2 heading units per field (`world-020.json`, `world-060.json`).
Release route play with M1 off/on shows intact cell, exterior, turning view and panel,
then a stable stopped pose (`tmp/m1/play-off/`, `play-on/`). O1's deferred map,
vehicle and flight coverage remains open.

### M2: read-only lookup tables in fast RAM

The post-M1 `bus_audit.py` run reports 10,057 chip-data reads per gameplay field.
The numeric/trigonometric region at chip `$60000..$66000` (exclusive end) accounts
for 364,337 reads over 325 fields: 11.1% of data reads, with no writes to that region
on the route (`tmp/m2/bus.txt`, `table-reads.txt`, `profile/`).

`Custom1` bit 6 copies chip `$60000..$66104` at boot and redirects 77 explicit
table-base loads
for chip `$60000` and `$64000`. The original data remains available to other readers.
The same CPU/fast-memory guard as M1 applies; this option also works without M1.
The optional expansion allocation is now 36 KB, retaining the stack and code slots.
The copy includes the angle lookup at chip `$66002..$66102`: the MMU check exposed
its use by Disk.1 `$5231E` beyond the main 24 KB tables. The allocation is rounded
to WHDLoad's required 4 KB pages.
The existing post-patch cache flush covers the changed operands. No per-frame work
or new guest instrumentation is added. The corrected post-M2 bus census gives
8,501 chip-data reads per field (`tmp/m2/final-bus.txt`); the remaining drawing
costs are examined together with R1.

### R1: horizontal span interiors

The sixteen colour variants share a word-at-a-time, four-bitplane fill loop.
Before the rewrite, their full-word interiors account for 7.18% of the A500 profile
(`tmp/m2/r1-000/`); colour 14 alone is 3.57%. The post-M1 A1200-fast profile spends
4.96% there (`tmp/m2/profile/`). These loops do not use the moved lookup tables:
they repeatedly fetch store instructions and write the chip bitplanes.

`Custom1` bit 7 replaces their interiors at Disk.1 `$4978C + colour*$B6`.
The original clipping and left/right masks stay in place. The 68000 variant writes
pairs of words with long stores and handles an odd word separately. The 68020+
variant requires fast RAM, first aligns the destination, then uses an 80-byte routine
with a compact
paired-store loop; an odd final word remains a word write. Both advance the same
pointer by the same amount and preserve the native edge-mask inputs. The chip-only
020 keeps the native loop: a measured 9.40 → 9.20 fps regression
showed the call/alignment overhead was not worthwhile there. No blitter or
change to buffer layout is involved. In the same VERIFY build, the A1200-fast
route spends 5.14% of CPU time in the original interiors versus 4.32% in the patched
calls and replacements (`tmp/m2/final-profile-020-off/`, `final-profile-020-on/`).
The smaller FPS gain reflects the remaining drawing cost and field-boundary waits.

M2 and R1 were completed together by user decision. Final same-build, same-session
500-field measurements (`Custom1=63` versus `255`):

| Cell | Both off fps | Both on fps |
| --- | ---: | ---: |
| a500-1.5m | 4.00 | 4.10 |
| a1200, no fast RAM | 9.40 | 9.40 |
| a1200-fast | 10.90 | 11.30 |
| 030 default | 12.40 | 12.40 |
| 030 MMU | 12.40 | 12.50 |
| 040 25 MHz | 14.60 | 16.50 |
| 060 50 MHz | 15.90 | 16.90 |
| 040 8 MHz sanity | 14.10 | 16.50 |

The same final build with only M2 added (`Custom1=127`) gives 11.20 fps on
A1200-fast: M2 contributes 0.30 fps, R1 another 0.10 fps. The earlier corrected
same-build pair repeated those counts, and R1 raised A500 from 4.00 to 4.10 fps.
Evidence: `tmp/m2/accepted-off/`, `accepted-on/`, `accepted-020-data-only.json`,
`020-v2-*.json`, `000-v2-*.json`. No measured matrix losses remain. The 040 frequency
sanity remains advisory; 040/060 counts are not hardware-speed predictions.

All options off and shipped both give 37 A500 frames. The release world-speed checks
on A1200-fast and 060 retain 6 walking units and 2 heading units per field. Release
route screenshots with the span option off/on show intact edges, scenery and panel;
the stopped poses remain stable. A500 route screenshots also show intact drawing.
Evidence: `tmp/m2/options-off.json`, `shipped.json`, `world-*.json`, `play-off/`,
`play-on/`, `final-profile-000-on/`. Deferred map, vehicle and flight coverage remains.

## Running

The title picture is followed directly by gameplay: the prison cell on Metis, with the
on-screen clock running from `00-00-00` and the chief prison officer's scripted messages.
There is no attract demo. Walking uses the port-1 joystick (up walks, left and right turn);
`R` toggles running. The cell door opens on the game clock from about two seconds after the
entry; walking into it earlier gives "LOCKED".

## Frame loop and game time

Offsets are `Disk.1` offsets; chip variables are BaseMem addresses, which do not move.

- **Frame publication** (`$5E4B0`): writes `COP1LC` with one of two copper lists, waits
  for the VERTB counter at chip `$529F4` to change (`$5E4D6`), counts the frame in chip
  `$7180` (`$5E4DE`), and stores the fields since the previous frame in chip `$52954`
  (`$5E4F0`). Then the copy that the slave's `_dmaon` patch interrupts.
- **Main loop** (head `$5DF92`, one pass per frame):
  1. per-frame calls `$5DF92..$5E004` (not yet classified; together about 7,000 cycles);
  2. a snapshot of the player pose (chip `$7146..`, `$7038`, `$7040` to `$70D2..`);
  3. the world ticks below;
  4. per-frame calls after the ticks (`$5E084..`), the frame publication call (`$5E0E2`),
     drawing and the instrument panel;
  5. a collision test (`$5E18A..`): on a hit it restores the pre-tick snapshot, undoing
     the pass's ticks of player movement, and draws again from `$5E0E6`.
- **World ticks** (`$5E040`): the fields since the previous frame, clamped to 4..8, are
  stored in a word inside the code (`$5DF46`); the loop `$5E060..$5E082` runs that many
  ticks (`$5A644`, `$5C8F8`, `$5F724`, `$5F328`). One tick is one field of game time:
  walking moves the player (chip `$714E`) 6 units, turning changes the heading (chip
  `$7156`, 1024 per turn) 2 units. A separate path at `$5C9EA` adds velocity times the
  unclamped field count to the position.
- **In-game clock**: chip `$57B0..$57B3`, the displayed seconds in `$57B3` and a 16-bit
  fraction in `$57B0`. It advances by the same amount every field (`$A790` per 25 fields,
  about 1.31 game seconds per real second) whatever the frame rate.

So game speed depends on the frame rate outside 6.25..12.5 fps:

| Frame rate | Fields per frame | Ticks per frame | World speed |
| --- | --- | --- | --- |
| below 6.25 fps | over 8 | 8 | slower than real time |
| 6.25 to 12.5 fps | 4 to 8 | equal to fields | real time |
| above 12.5 fps | under 4 | 4 | faster than real time |

Measured with `tools/sim_speed.py`, same input on the same fields: in the walk the
A500-equivalent published a frame every 13–14 fields and moved 48 units per frame
(8 ticks); `a1200-fast` every 5–7 fields and moved 30–42 (5–7 ticks). Over the route the
A500-equivalent walked at 62% and turned at 71% of `a1200-fast`'s speed while the clock ran
identically. No measured frame was shorter than 5 fields, so the lower clamp is read from
the code, not observed.

## A1 anchor investigation

A1 is complete without changing the 68030 MMU backend. The original entry breakpoint
(`Disk.1` `$4EDB0`) works on `a1200-030`; the previous failure occurred before gameplay.
No counter fallback or route shift is necessary. The entry check requires a breakpoint
stop at the expected PC and a zero initial frame counter.

The failure is the combination of deterministic directory I/O and the preset's indirect
UAE board. A bounded probe with `DETERMINISTIC=1` stalled at directory-drive startup.
A host stack sample placed the emulator thread in
`filesys_hsync → filesys_iteration → trap_get_bytes → call_hardware_trap_back`, waiting
on a semaphore. The installed build's source runs deterministic filesystem work on the
emulation thread; the indirect access waits for a guest callback that needs that thread
to advance. With only `DETERMINISTIC=0` changed, the same binary and preset reached the
entry and completed the route. This diagnoses a boot-I/O scheduling problem, not a
missing game breakpoint or evidence of stale instruction-cache contents.

`route_runtime.py` shares checked entry anchoring, PAL validation, bounded boot/route
execution and owned-process cleanup across the three tools. For `a1200-030` it explicitly
prints and records the default `DETERMINISTIC=0`; other setups retain 1, and explicit
environment values are honored. The 030 still uses 50 MHz, MMU model 68030, CPU/data-cache
emulation, cycle-exact CPU/memory/blitter settings and `uaeboard=full+indirect`.
These are effective configuration facts, not a hardware-timing calibration or proof of
WHDLoad translation-table state. No emulator, shared installation or slave code changed.

Instruction recording is a separate limitation. The selected MMU loop has no Barto
`cpu_profiler` scope. `route_profile.py MODE=counter` explicitly delegates to `fps.py`
and writes counts/fps with no instruction costs. Normal profiling rejects unsupported
CPU backends instead of reporting missing instruction records as zero cost. Per the
user's request, A1 acceptance now requires untraced route/state completion on the 030
and preservation of the 020 reference, rather than an impossible 030 instruction profile.

Validation, the same 175/185/140-field wait/walk/turn route:

| Setup / build / options | Instrument | Frames | Fields | Full-window fps |
| --- | --- | ---: | ---: | ---: |
| `a1200-030`, shipped, no extra WHDLoad options | `MODE=counter` | 89 | 500 | 8.90 |
| same, independent boot | `sim_speed.py`, every 5 fields | 89 | 500 | 8.90 |
| same, publication-aligned input | `fps.py PER_FRAME=1` | 89 | 504 | 8.83 |
| `a1200-fast`, performance, `Custom1=1` | `fps.py` | 90 | 500 | 9.00 |
| same, independent boot | instruction markers and endpoint counter | 90 | 500 | 9.00 |

The 030 state samples show z changing by −1,116 units during the walk and heading by
+278 during the turn. Its entry counters are zero; after 500 harness fields the VERTB
counter is 499 and frame count 89. The initial partial field and harness convention are
unchanged from the entry-anchored route. Both independent 030 tools agree on endpoint
frame/VERTB counts and their recorded build, route, options and machine settings.
This does not establish that arbitrary threaded boots or all intermediate states are
identical; A6 still owns repeated committed-state equivalence.

The 030 publication breakpoint (`Disk.1` `$5E4DE`) also works: 88 complete stored
intervals span 5..7 fields, mean 5.614. Publication-aligned inputs overshoot the requested
route by 4 fields, so this is a cadence diagnostic, not an exact-field comparison.
The 020 counter and instruction markers both preserve A2's 90-frame reference; the
profiler's first-to-last-publication rate remains 9.06 fps. No performance gain is claimed.

The native emulator and WHDLoad hashes are unchanged from A2. Additional SHA-256 identities:

- Shipped slave: `e1d0dc878ff941a03d8a2685d0e2a2ed353381f065a5d8e013aece956dedf76d`.
- Shared launcher: `4e05e36d4a121fde37f4f371effbb82c7a3d2bf450126964c84fb2dd39c26f83`.

Inputs verify and the original build is byte-identical. Ten offline checks cover the
counter/cadence boundaries, stop and deadline validation, boot-mode defaults/overrides
and refusal of unsupported instruction profiles. The failing deterministic probe reached
its 90-second deadline and cleaned up the owned emulator. Generated evidence is ignored
under `tmp/a1-finish/`. The historical A500 38-frame/picture gate remains unresolved as
recorded in A2; A1 changes no game behavior. A3 below subsequently validates route completion, but its frequency sanity fails.

## A2 frame counting without traces

`tools/fps.py` counts chip `$7180` at the entry and at the end of the same route used
by `route_profile.py`, with no instruction capture. Counter subtraction wraps at 16 bits.
The default route advances exactly 500 whole harness fields after the entry's partial
field, just as the profiler does. Full-window fps is frames × 50 / fields; it includes
startup and the unfinished interval at the end. The profiler's existing fps instead uses
the interval from the first to the last publication, so those fps values need not agree.

`PER_FRAME=1` stops at publication (`Disk.1` `$5E4DE`) and records chip `$52952`, `$52954`,
`$529F4` and `$7180`. At this instruction the current frame increment and elapsed-field
store have **not** executed: sample i's elapsed count belongs to publication i−1. The
report excludes the startup interval and the final unobserved store, and checks each
remaining elapsed count against the difference between stored field stamps. This mode
moves input boundaries to publications and reports segment overshoot explicitly; it is
not the exact-field route used for the count comparison.

Validation with the current shared runtime:

| Setup / build / options | Method | Frames | Fields | Full-window fps |
| --- | --- | ---: | ---: | ---: |
| `a1200-fast`, performance, `Custom1=1` | untraced counter | 90 | 500 | 9.00 |
| same | profiler markers and endpoint counter | 90 | 500 | 9.00 |
| same, publication-aligned input | `PER_FRAME=1` counter | 91 | 507 | 8.97 |
| `a500-1.5m`, performance, all options off | untraced counter | 37 | 500 | 3.70 |
| `a500-1.5m`, shipped | untraced counter | 37 | 500 | 3.70 |

The cadence run yielded 90 complete stored intervals, 4..8 fields each, mean 5.522 fields;
its three segments overshot by 1, 1 and 5 fields. The exact-field profiler reported
9.06 fps between its first and last publication. A second traced comparison with counter
reads between chunks also counted 90; omitting those reads left the marker count and
traced cycle total unchanged.

The old 89-frame `Custom1=1` reference and 38-frame A500 reference are not reproduced.
The current performance slave still has the same SHA-256 as those stored reference
runs. The cause of the reference drift is unresolved; those old reports did not record
an emulator or WHDLoad binary hash. No optimization or performance gain is claimed.
The A500 counter matches the shipped slave on the current runtime, but the historical
38-frame regression target and the picture comparison are **not** declared passed.
Resolve that baseline discrepancy before using the optimization regression gate.

Runtime identities for these checks (SHA-256):

- Performance slave: `4a4492b58fdf01346680715311c9420bf949ef76db01b9423e79946e33669ca9`.
- Native emulator: `5e18f89c3440bb12378b4df1a079efd72dc28d64b402a1859a904816d3e0f9f0`.
- WHDLoad: `e904dbe9494f85475fedf926b53ee8597dcdf581209f00122d7baf7b7df4cd8e`.

Boot/attachment/anchor have one wall-clock deadline (default 120 seconds), and the route
has another (180 seconds). A real 3-second boot-deadline check on `a1200-030` exited with
failure, stopped the recorded project emulator through the shared helper, and produced
no success JSON. Six offline checks cover wraparound, rejected reads, wrong stops,
previous-publication stamp alignment, PAL configuration and deadline handling. Inputs and the original
byte-identical build also pass. Slave code is unchanged.

Results and diagnostics are ignored under `tmp/a2/`. New reports retain slave, emulator
and WHDLoad hashes, effective machine settings, input events and both counters. Existing
output files are refused. The profiler now retains its endpoint counter and emulator
hash too. A1 subsequently validates the same entry anchor on the 030; A3 below records 040/060 route completion and its failed frequency sanity.

## A3 machine matrix

`tools/matrix.sh SLAVE "WHD_ARGS..." OUTDIR` runs `fps.py` sequentially for each target,
then an extra 8 MHz 040 sanity cell. All results use the same entry-anchored
175/185/140-field route and counter delta over 500 fields (10 nominal PAL seconds).
Each cell retains its log and JSON; `table.md` and `matrix.json` aggregate the results.
Missing or invalid results are failures, never zero fps. The runner validates effective
CPU/MMU, frequency, memory, cache-emulation and timing configuration, and rejects a
changed slave or runtime between cells. It returns failure if any cell fails. The frequency sanity is advisory by user decision. `--report-only` revalidates the captured JSON without another emulator run.

The 030 cells both retain the full 68030 emulator backend. The default WHDLoad mode on
030 disables its MMU use; the second cell adds `MMU` to enable it. This follows the
installed WHDLoad manual (`Docs/en/mmu.html`, User control); `NoMMU` is not substituted
for the default. The runner rejects caller MMU/NoMMU overrides to preserve this pairing.
The 040/060 use the `a1200-030` preset with explicit `--cpu=68040-NOMMU` /
`--cpu=68060-NOMMU` and frequency overrides. They retain CPU/memory/blitter cycle-exact
flags, data-cache emulation and the indirect UAE board. All these 030-derived cells use
`DETERMINISTIC=0` for boot I/O as in A1; the three lower-end presets use 1.
These are configuration flags, not the guest's actual cache state.

Shipped slave, no caller WHDLoad options, one boot per cell:

| Cell | CPU / configured MHz | WHDLoad option | Frames | Full-window fps |
| --- | --- | --- | ---: | ---: |
| `a500-1.5m` | 68000 / 7.094 | none | 37 | 3.70 |
| `a1200` | 68020 / 14.188, chip only | none | 75 | 7.50 |
| `a1200-fast` | 68020 / 14.188, 8 MB fast | none | 75 | 7.50 |
| `030-default` | 68030 / 50 | none | 89 | 8.90 |
| `030-mmu` | 68030 / 50 | `MMU` | 89 | 8.90 |
| `040-25` | 68040-NOMMU / 25 | none | 118 | 11.80 |
| `060-50` | 68060-NOMMU / 50 | none | 127 | 12.70 |
| `040-8-sanity` | 68040-NOMMU / 8 | none | 118 | 11.80 |

**Frequency sanity failed.** The two 040 results have identical segment frame counts
(35, 47, 36), ending frame count 118, VERTB 501, stamp 500 and elapsed count 4. Their
recorded frequencies are 8,000,000 and 25,000,000 respectively; other recorded machine
settings and runtime hashes match. The 500-field denominator is the harness route,
not a claim that the game's VERTB counter is exactly 500 at the endpoint.

Read-only inspection of the installed emulator's source finds the non-MMU cycle-exact
040/060 selection uses `m68k_run_3ce` in `newcpu.cpp`. That loop executes instructions
without a per-instruction clock charge; if no cycles advance, its fallback charges one
fixed `CYCLE_UNIT` after four such instructions. Frequency sets `cpucycleunit` elsewhere,
and some memory paths use it, so this is not a claim that every execution path ignores
frequency. It does explain why the cycle-exact flags alone are insufficient evidence
of realistic 040/060 instruction timing. This route has not demonstrated the required
frequency response. The 040/060 figures are diagnostic emulator counts, not validated
hardware-speed baselines or evidence of optimization gains. The user accepts this known
emulator limitation: A3 is complete without a timing fix. The report
retains the failed sanity as an advisory; no alternate timing mode or emulator patch was used.

Runtime SHA-256 identities:

- Emulator: `e4beb4588634ecc4b41b833a76f37ea859ced77c1128de43d4d302089d1df264`.
- Shipped slave: `e1d0dc878ff941a03d8a2685d0e2a2ed353381f065a5d8e013aece956dedf76d`.
- WHDLoad: `e904dbe9494f85475fedf926b53ee8597dcdf581209f00122d7baf7b7df4cd8e`.
- Shared launcher: `4e05e36d4a121fde37f4f371effbb82c7a3d2bf450126964c84fb2dd39c26f83`.

The installed emulator hash differs from A1/A2; this work did not rebuild or change it.
All eight cells used the same current hash. The A500 remains at 37, so the historical
38-frame/picture gate remains unresolved. No slave code or shared project was changed.
Input verification and the byte-identical original build pass. Fifteen offline tests
pass, including rejected machine/build/route mismatches, absent-MMU serialization,
strict frequency sanity and failed-cell rendering. The report validator was corrected
for UAE's omitted zero MMU setting and its 256 KB slow-memory units, then the same
captured results were revalidated without rerunning any cell. Ignored evidence is under
`tmp/a3/shipped/`.

## A6 committed-state recorder

`tools/state_trace.py` stops at the main-loop head, `Disk.1` `$5DF92`, before its
first `jsr`. The former `$5E992` in the plan was a transcription error: that offset
is a `movem` inside the screen-clear routine. The existing profiler's loop marker
and disassembly agree on `$5DF92`; the per-frame call range ends at `$5E004`.

Each stop reads chip `$5350..$67FFF` once, then derives the pose bytes
`$7142..$7161`, clock bytes `$57B0..$57B3`, words `$7180`, `$52952`, `$52954`,
`$6F56`, and `$529F4`, and a SHA-256 of the entire read. Nothing is masked from
that hash, including stack, display-control state and self-modified code; the bitmap
buffers themselves lie outside it. Object data is recorded as raw bytes in two
provisional 1,000-byte windows, `$AF36..$B31D` and `$B31E..$B705`. These cover the
known table writes; their ends are capture boundaries, not established table extents.
P2 must map and extend them. The full image hash also detects changes beyond them.
The instrument is entirely host-side; no guest instrumentation or slave code changed.

The entry anchor remains `Disk.1` `$4EDB0`. At each loop head the recorder captures
state committed by the preceding pass, with a zero-based record index. Joystick
changes occur **after** the capture at the first head reaching each cumulative route
boundary (175, 360, 500 fields). `held` describes the input leading into the sample.
The route therefore differs from the exact-field FPS route and must not be used as
its performance baseline.

Two independent deterministic `a1200-fast` boots of the shipped slave, with no WHDLoad
options, produced **75 identical records**, including all 75 full-image hashes:

| Observation | Both boots |
| --- | --- |
| First head | record 0, field 11, frame counter 1 |
| Walk starts after capture | record 23, field 179 |
| Turn starts after capture | record 52, field 365 |
| Last head | record 74, field 501, frame counter 75 |
| Last publication stamp / elapsed word | 494 / 7 |
| Final clock bytes | `bb18000a` |
| Comparison | identical, exit status 0 |

Evidence: `tmp/a6/boot-a.json` and `tmp/a6/boot-b.json`. The emulator, shipped slave,
WHDLoad and shared-launcher hashes match the A3 identities above, and the effective
configuration matches A3's `a1200-fast` cell (68020, 14,187,580 Hz, 2 MB chip, 8 MB fast,
cycle-exact PAL, no JIT). The repeat boots are the explicit A6 exception to the
plan's no-reruns rule. A sandboxed launch could not attach to the debugger; a first
capture attempt exposed GDB's filename quoting limitation, fixed with a relative
scratch filename before the successful pair. Neither failed attempt yielded a trace.

`--compare` checks the trace definition and every record field, reports the first
unequal pass and field names, and rejects unequal lengths or empty evidence. It compares
records rather than machine/build metadata, allowing later option comparisons; callers
must check those identities when claiming same-build repeatability. A6 establishes
repeatability on this 020 setup only, not on threaded 030 boots, across CPU speeds or
between different slave options. It makes no performance or A500 picture-parity claim.

## Renderer inputs and writes

From `tools/write_audit.py` over 175 fields of the route (walking and turning; executed
paths only). Chip addresses are BaseMem addresses; code is named by `Disk.1` offset.

- **Camera derivation** (`$5D844`, called before and after the ticks): copies the pose
  block chip `$7142..$7161` (mode `$7142`, X `$7146`, Y `$714A`, Z `$714E`, angles
  `$7152..$7156`) to the render copy `$7122..$7141`, wraps the position's high words to
  12 bits, and writes the camera-relative position `$70C2..$70CD` (pose minus `$6F4A`/`$6F4E`),
  the projection value `$704A..$7051` and the view angles `$7132..$7136`. Everything the
  renderer knows about the player passes through it.
- **View setup after the ticks**: `$5E0BA` (sky heading `$42C6C`), `$5DA50` (`$70CE`),
  `$5A91E` (`$700E..`, `$7084..`, `$7162..$7179`, `$42C08..`), `$469C4`/`$469C8` (`$42C20..$42C67`
  and palette source words near `$7CF2`).
- **Frame publication** (`$5E458`): copper list pointers `$72B2`/`$72B6`, the buffer toggle
  `$42C01`, `COP1LC`, the frame counter `$7180`, the field stamps `$52952`/`$52954`, and the
  palette copy into the copper list. The renderer reads `$7180` for blinking (`$57A4E`).
- **Drawing**: `$5E840` clears the back buffer; `$5410E` (palette allocation, with `$5765E`),
  `$593A6`, `$5AFAA` and `$577BE` draw. Besides the display buffers they write render scratch
  below the game image (`$0340..$4000`), variables such as `$719E`, `$71AE..$71E9`, `$7220..`,
  `$727C`, object-table areas at `$AF36..` and `$B31E..`, and code words at `$459BA`,
  `$4F700..` and `$4F9C2..` (self-modifying drawing code).
- **Collision**: `$5AAB0..$5ADAA` (called at `$5E186` only when `$6F56` is set) sets
  `$6F56`; on a hit the main loop restores the pre-tick snapshot and draws again.
- **Other movement modes**: when the mode copy `$7122` is not 1 the loop takes `$5E214`
  or `$5E3CA` instead of the tick loop. Those paths move one step per frame and publish
  through their own calls, so their game speed follows the frame rate natively.

## Measurements

Same route, `a1200-fast`, frames in the 500-field window:

| Slave | Options | Frames | fps | `_waitvb` share |
| --- | --- | ---: | ---: | ---: |
| shipped | | 75 | 7.51 | 14.7% |
| performance | none | 74 | 7.40 | 14.5% |
| performance | `Custom1=1` | 89 | 8.98 | 0.2% |

Compare options only within one build: the performance slave without options differs from
the shipped one by a frame (a different slave changes WHDLoad's layout and timing).

The options against each other, one build (with bits 1 and 2), same route and machine:

| `Custom1` | Frames | fps | Bitplane slots | CPU slots | Game's VERTB wait |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 89 | 8.93 | 22.3% | 39.2% | 7.3% |
| 3 (+ FMODE 3) | 94 | 9.45 | 5.6% | 40.8% | 8.0% |
| 5 (+ stack in fast RAM) | 94 | 9.49 | 22.3% | 37.5% | 7.2% |
| 7 (all) | 96 | 9.62 | 5.6% | 39.3% | 9.6% |

On `a500-1.5m` (500 fields): the shipped slave and the performance slave without options
both draw 38 frames (3.82 fps); `Custom1` 1, 3, 5 and 7 all draw 42 (4.28 fps). Bit 1
stays off without AGA, and bit 2's expansion memory is slow RAM there, on the chip bus.

The gains don't add: frames are published on whole fields (the game waits for the VERTB
counter after each `COP1LC` write), and the saved time partly moves into that wait. A
frame is about 1% of the window. The pictures match; frame-timed animation (the panel logo)
and the scene position differ with the frame rate.

### Where the CPU's chip-bus time goes

`tools/bus_audit.py` over the gameplay fields 175..500 of the `Custom1=1` route
(325 fields): 27,800 CPU chip accesses per field, against 284,200 CPU cycles, and
31,900 instructions per field (97 KB of instruction bytes, about 9 cycles each).

| Kind | Region | Per field | Share |
| --- | --- | ---: | ---: |
| instruction fetch (32-bit) | game image | 13,830 | 49.7% |
| data read | game image | 5,270 | 18.9% |
| write | display buffers | 4,060 | 14.6% |
| data read | display buffers | 1,500 | 5.4% |
| write | stack (top of chip) | 1,010 | 3.6% |
| data read | stack | 1,000 | 3.6% |
| data read / write | below the image | 730 | 2.6% |
| write | game image | 410 | 1.5% |
| custom chip registers | | 26 | 0.1% |

- Only the display accesses (20%) need chip RAM; the other 80% go to code and CPU-only
  data that could sit in fast RAM.
- The instruction cache is on (the slave's `resload_SetCACR` with `CACRF_EnableI`) but
  hits only about 43% of the longwords: 97 KB of executed instructions need 13,800
  fetches. The hot code is concentrated: 80% of the fetches come from 8.8 KB of code
  (256-byte pages), 95% from 18.5 KB, 99% from 31.5 KB. The hottest pages are chip
  `$4B100..$4B2FF` (15%) and `$57900..$57CFF` (24%).
- 28% of the image's data reads are the publication's spin on the VERTB counter
  (page `$52900`), which costs nothing that matters.
- No longword access is misaligned (address 2 mod 4).
- In the 200 bitplane lines the CPU gets 37.5% of the slots (bitplanes 35.2%, free
  25.2%), outside them 42.1% (free 55.7%): display DMA slows the CPU's chip accesses but
  never starves them.
- The blitter is never used; all drawing is by the CPU. The panel below row 140 gets
  almost no writes per frame: it is not redrawn.
- The level 3 handler, once per field, costs 1.6% of the CPU's cycles; no other
  interrupt ran on the route.

The rest of this section is the shipped slave's profile.

`a1200-fast` (68EC020 14 MHz, 2 MB chip, 8 MB fast, cycle-exact), the 500-field route of
`tools/route_profile.py` from the game entry. Two boots gave identical call stacks,
per-field totals, frame timestamps and final screenshot; three adjacent instructions
differed by 3 cycles in total.

| Item | Share of CPU cycles |
| --- | --- |
| slave `_waitvb`, from `_dmaon` once per frame | 14.7% |
| game's wait for the VERTB counter (`$5E4D6`) | 6.3% |
| other game code (all in chip RAM) | 78.8% |
| WHDLoad outside the slave | 0.2% |

- 75 frames in 500 fields: 7.51 fps, 6.66 fields per frame.
- Chip-bus DMA slots: CPU 38.8%, bitplane 22.3%, refresh 1.8%, audio 0.3%, copper 0.1%,
  free 36.8%. No `STOP`.
- The game and its data sit in the slave's 512 KB chip BaseMem, so on this machine every
  game instruction fetch and data access competes with display DMA; the fast RAM holds
  only WHDLoad and the slave.
- Cycles per main loop pass (71 complete passes, interrupts included): before the ticks
  7,100; the ticks 11,600 (6.6 per pass, 1,770 per tick); after them 1,893,500. The
  costliest call sites after the ticks:

  | Call site | Callee | Cycles per pass | Role |
  | --- | --- | ---: | --- |
  | `$5E1E2` | `$577BE` | 887,000 | main 3D drawing (by cost and call tree; not yet confirmed) |
  | `$5E0E2` | `$5E458` | 421,000 | frame publication: its field wait and the slave's `_waitvb` |
  | `$5E150` | `$5410E` | 245,000 | not yet classified |
  | `$5E1DE` | `$5AFAA` | 228,000 | not yet classified |
  | `$5E1DA` | `$593A6` | 101,000 | not yet classified |
  | `$5E0E6` | `$5E840` | 57,000 | not yet classified |

  World logic, ticks included, is therefore about 1% of a frame; drawing is about
  1.4 million cycles (5 fields on this machine).
- The game is assembly with one supervisor stack for its main loop and interrupts, so the
  reconstructed call tree roots everything under interrupt frames; use the self-cycle
  tables. Outside the waits no single routine exceeds 1.5%.

### Routine 040 performance check

The routine measurement set now includes the existing `040-25` matrix configuration:
`a1200-030` with `68040-NOMMU`, 25 MHz and `DETERMINISTIC=0`. The separate
`a1200-040` preset is not substituted (user decision).
Same VERIFY build/session, standard 500-field route: all options off (`Custom1=0`)
gives 117 frames / 11.70 fps; current options on (`Custom1=255`) gives 165 frames /
16.50 fps. Effective machine settings, route and runtime/build hashes match.
Evidence: `tmp/040-check/off.json`, `on.json`. These remain emulator measurements
with the accepted frequency-timing limitation, not predicted hardware frame rates.

The 040 bottleneck is not yet measured by component. Likely remaining costs are
renderer instruction fetches and bitplane writes in chip RAM, the CPU back-buffer
clear, publication's next-field wait, and presentation save/restore work. M1 moves
selected numeric routines, M2 moves lookup tables, and R1 changes horizontal span
interiors; the rest of the drawing path remains largely native. These are candidates,
not a measured ranking on the 040. The roughly 1% world-logic cost and 7–10%
publication wait were measured on the 020 and must not be assigned to the 040.
The 12.5 Hz logic gate is not a rendering cap: the measured 16.50 fps includes
presentation frames. Before choosing further renderer work over R2's blitter clear,
measure drawing, clearing, publication waits and presentation overhead separately
on the existing 040 cell, retaining the emulator timing caveat.

### Frame budget toward 50 fps

Current checkpoint: [S6](#s6-budget-checkpoint). S1–S4 reach one-field no-draw and
two-field full frames on the reference 030/50 after startup; R3 is closed by user
decision, retaining double buffering.

The `VERIFY` build's `Custom2` bits make drawing routines return at once (bit 0 the 3D
drawing `$577BE`, 1 the clear `$5E840`, 2 `$5410E`, 3 `$5AFAA`, 4 `$593A6`). The 030 and
040 cores record no profile ("Protocol error" on `monitor profile`), so this elimination is
the frame-cost instrument there. Before S2: `fps.py`, 500-field route, `Custom1=255`, one session:

| `Custom2` (skipped) | a1200-fast | 030/50 | 040-25 cell |
| --- | ---: | ---: | ---: |
| 0 (none) | 11.3 | 12.5 | 16.5 |
| 1 (3D drawing) | 17.4 | 24.8 | 24.9 |
| 2 (clear) | 11.6 | 12.6 | 18.4 |
| 4 (`$5410E`) | 11.3 | 12.5 | 16.5 |
| 8 (`$5AFAA`) | 11.6 | 13.7 | 19.1 |
| 16 (`$593A6`) | 11.0 | 12.4 | 16.7 |
| 31 (all five) | 25.4 | 37.0 | 49.6 |

Frames land on whole fields, so single bypasses under a field change little. Before S2,
without any drawing, frames took two fields on `a1200-fast` and about 1.35 on the 030. The
profile of that case (`tmp/prof/nodraw/`) shows why:

- The CPU waits 43% of the time in the publication's field wait: presentation work that
  spills past the field boundary costs a whole second field.
- P1's save and restore copy the 17,366-byte restore set word by word, both ways, on every
  presentation: about 17% of all cycles, roughly 200,000 cycles (0.7 field) per presentation
  frame on the 020. Most of the set is render scratch at chip `$0340..$4000`.
- Scene setup (`$5765E`, not bypassed) is 15.5% inclusive, about 0.3 field per frame.

With all options on (`tmp/prof/b255/`, a1200-fast), the 3D drawing is half of a logic pass
(625,000 of 1,245,000 cycles), `$5410E` 15%, `$5AFAA` 13%, publication 11% (mostly its
field wait), `$593A6` 7%, the clear 4%, logic 1.3%. The CPU still makes 10,400 instruction
fetches per field from chip RAM; 95% come from 20 KB of code, led by Disk.1
`$524B0..$53AB0` (33%, containing the self-modified words at `$533B0..`), `$48DB0..$4A5B0`
(25%, the span fills and the word at `$4966A`), `$5B8B0..$5C4B0` (12%) and `$575B0..$580B0`
(11%). Display buffers take 4,500 CPU writes and 1,900 reads per field, much of it
read-modify-write.

### S1: presentation restore buffer in expansion memory

The restore buffer occupies a 20 KB page-rounded slot in the optional expansion block;
without it, bit 4 retains L1 gating and skips presentation frames. Release slave size is
5,596 bytes (VERIFY 5,716, previously 23,052). The 040 route exercises 43 presentations;
all restore hashes pass. Same-build `Custom1=239 → 255` gives 11.20 → 11.20 fps on
`a1200-fast`, 4.10 → 4.10 on A500, 12.40 → 12.40 on 030/50 and 12.50 → 16.50 on
040-25. This tests presentation off/on, not a speed gain from moving the buffer.
Options-off and shipped both give 37 A500 frames. Walking remains 6 units/field and
turning 2 heading units/field; route screenshots show no scene or panel faults.
Evidence: `tmp/s1/`.

### S2: bulk presentation restore

`Custom1` bit 8 copies the full 17,366-byte set in 32-byte `movem` groups, with longword
and word tails. The 020 no-draw profile measures 185,845 → 114,790 copy cycles per
presentation (0.65 → 0.40 field). Scene setup stays: `$5765E` projects objects relative
to the staged camera, so its inputs change between presentations.

Removing scratch was rejected. Matched-cost VERIFY poison on/off comparisons first
differed at pass 75: chip `$0340..$2000` changed the recorded object window even at equal
field counts; `$2000..$4000` also failed, with timing differences. No scratch range is
omitted. The test uses `Custom2=64` (read/write unchanged) versus `96` (complement words),
with `Custom3`/`Custom4` as optional start/end chip addresses; defaults are `$0340..$4000`.
It runs only after presentations and exists only in VERIFY.

Same-build/session `Custom1=255 → 511`, with `Custom2=31` (no drawing):

| Cell | Off fps | On fps |
| --- | ---: | ---: |
| A500 | 12.30 | 16.20 |
| 020 chip-only | 24.80 | 25.30 |
| 020 fast | 25.40 | 35.90 |
| 030/50 | 37.30 | 49.60 |
| 030 MMU | 36.90 | 49.60 |
| 040-25 | 49.60 | 49.60 |
| 060-50 | 49.60 | 49.60 |

Full drawing: A500 4.10 → 4.10, 020 fast 11.30 → 11.30, 030/50 12.40 → 12.40,
040-25 16.50 → 16.80 fps. All 45 full-drawing 040 restore hashes pass. Options-off and
shipped both give 37 A500 frames. World speed on 020 and 030 remains 6 walking units and
2 heading units per field; route screenshots show no scene or panel faults.
The 030 no-draw cadence has one two-field startup interval, then 495 one-field
intervals (mean 1.002). Evidence: `tmp/s2/`.


### S3: renderer code in fast RAM

`Custom1` bit 9 moves 23,762 bytes in four renderer blocks into a 36 KB fast-RAM
area, on 68020+ with real fast RAM. Relocation includes absolute operands, external
branches, colour-span tables and mutable drawing state. The indirect-call variant
avoids the four cached call-operand writes; P1 restores the relocated state. Flush
the instruction cache after installing the entry jumps.

Same build/session, `Custom1=511 → 1023`, full drawing:

| Cell | Off fps | On fps |
| --- | ---: | ---: |
| A500 | 4.10 | 4.10 |
| 020 chip-only | 9.40 | 9.40 |
| 020 fast | 11.20 | 12.40 |
| 030/50 | 12.40 | 20.30 |
| 030 MMU | 12.50 | 19.90 |
| 040-25 | 16.80 | 19.10 |
| 060-50 | 17.50 | 19.50 |

World speed remains 6 walking units and 2 heading units per field on 020/030;
options-off and shipped both give 37 A500 frames. Complete-field route screenshots
show intact drawing and panel, including turning and stopping. A suspected missing
wall in the first field captured after an untraced advance prompted checks: later
fields draw correctly and all 74 presentation hashes of the relocated workspace
pass on the 040. Use the last of two captured fields for still screenshots.
Evidence: `tmp/s3/accepted/`, `tmp/s3/play-complete/`, `tmp/s3/fast-restore-040.json`.


### S4: stage the view bitmap in fast RAM

`Custom1` bit 10 redirects view writers and clearing to fast RAM on 68020+ with
real fast RAM. Publication copies four 5,440-byte planes (136 rows, 21,760 bytes)
with `movem`, then runs the native buffer flip. The panel, IRQ text and full-screen
copies keep the native chip pointer. Special screens bypass staging. The drawing's
low-word address arithmetic requires bitmap alignment at `$8000`; a 96 KB slot
holds the 32 KB bitmap plus alignment slack, making optional workspace 188 KB.
The original 140-row estimate copied four uninitialised rows over the separator;
136-row copies give pixel-identical off/on still screenshots.

Same-build/session `Custom1=1023 → 2047`, full drawing:

| Cell | Off fps | On fps |
| --- | ---: | ---: |
| A500 | 4.10 | 4.10 |
| 020 chip-only | 9.40 | 9.40 |
| 020 fast | 12.40 | 12.50 |
| 030/50 | 20.00 | 24.80 |
| 030 MMU | 19.90 | 24.80 |
| 040-25 | 19.10 | 24.90 |
| 060-50 | 19.50 | 24.90 |

Without S3, bit 10 also gains: 020 fast 11.30 → 11.60, 030/50 12.40 → 14.40 fps.
It therefore remains independent. The 030 full-drawing cadence has one three-field
startup interval, then 248 two-field intervals; no-draw has one two-field startup
interval, then 495 one-field intervals (49.60 fps). The VERIFY clear bypass also
omits staging/copying, so the no-draw budget excludes bitmap work.
World speed remains 6 walking units and 2 heading units per field on 020/030.
Options-off and shipped both give 37 A500 frames. Walking, turning and stopping
screenshots retain the view and panel. Help, return to game and Quit Situation also
show intact screens, with walking continuing on Eris. Evidence: `tmp/s4/accepted/`,
`tmp/s4/still-fixed-{off,on}/`, `tmp/s4/play-final/`, `tmp/s4/cadence-030-*.json`.


### S5: publication wait after staging

With `Custom1=2047`, the 020 instruction profile assigns 16.39% of route cycles to
Disk.1 `$5E4D6`'s field wait. Beam-position samples at wait entry/exit measure 17.0%
including interrupt time, averaging 0.675 field per publication. The same sampling
on the 030/50 measures 36.4%, averaging 0.731 field per publication over 502 fields.
This is a measured 030 wait cost, not an inference from the 020 profile. It is large
enough to bring R3's triple-buffer decision to the user; the steady two-field target
already holds without it. The user rejected triple buffering; R3 is closed without
implementation and the native publication wait remains.

The unchanged S4 build passes the three guards: options-off equals shipped (37 A500
frames), native 6/2 world rates on 020/030, and intact route/menu screenshots.
Evidence: `tmp/s4/profile-020/`, `tmp/s4/wait-a1200-{fast,030}.json`.


### S6: budget checkpoint

`matrix.sh`, `Custom1=2047`, all eight cells pass (same VERIFY build as S4/S5).
Full-drawing fps: A500 **4.10**, 020 chip-only **9.40**, 020 fast **12.50**,
030/50 and 030 MMU **24.80**, 040-25 and 060-50 **24.90**. The 040 8 MHz sanity
cell gives 24.80: its one-frame difference from 25 MHz does not establish reliable
frequency scaling. The 040/060 results remain run checks, not hardware predictions.

Same-build/session drawing-bypass budget, fps:

| `Custom2` (skipped) | 020 fast | 030/50 | 040-25 |
| --- | ---: | ---: | ---: |
| 0 (none) | 12.50 | 24.80 | 24.90 |
| 1 (3D drawing) | 24.80 | 49.60 | 49.60 |
| 2 (clear / staging) | 12.50 | 24.00 | 22.70 |
| 4 (`$5410E`) | 12.50 | 24.80 | 24.90 |
| 8 (`$5AFAA`) | 13.80 | 25.60 | 27.00 |
| 16 (`$593A6`) | 12.50 | 24.80 | 24.90 |
| 31 (all five) | 49.50 | 49.60 | 49.60 |

Bit 1's clear bypass also skips staging and its copy, leaving subsequent drawing in
chip RAM. That row does not isolate clear cost. Whole-field publication and changed
presentation admission also mean bypass gains are not additive cost percentages.

Remaining limits:

- A500 and chip-only 020: drawing still dominates; skipping all drawing gives 16.20
  and 25.30 fps. Skipping only the clear gives 4.30 and 9.60, so R2 has modest measured
  headroom on this route. The remaining no-draw work still exceeds one field.
- Fast-RAM 020: main 3D drawing is the leading measured cost (433,063 cycles per logic
  pass in the S5 profile); bypassing it doubles route fps. Fixed work now approaches
  50 fps with all drawing bypassed. Publication waiting remains 16.39% of profile cycles.
- 030/50, including MMU: full frames occupy two fields. Bypassing the main 3D drawing
  reaches 49.60 fps, identifying it as the next reduction needed for one-field frames.
  The measured 36.4% publication wait stays by the decision to close R3.
- 040-25: the same 3D bypass reaches 49.60 fps in the emulator. 060-50 reaches 49.60
  with all drawing bypassed; no component ranking is measured for that cell. Real
  040/060 speed and cache behaviour remain unverified.

S0 checkpoint: the unchanged build's 030 cadence has 495 consecutive one-field
no-draw intervals and 248 consecutive two-field full-drawing intervals. In each
run the preceding startup interval is one field longer; the steady-route targets
hold, rather than a strict bound covering startup. World checks on 020/030 retain
6 walking units and 2 heading units per field. Route, turning, stopping, Help and
Quit Situation screenshots remain valid for the identical build; no new behaviour
was introduced in S5/S6. Fresh options-off and shipped runs both give 37 A500 frames.
The existing deferred map/vehicle/flight coverage gap remains. Evidence: `tmp/s6/`,
S4's same-build cadence/world/play checks, and S5's 020 profile.

### WHDLoad launch configuration

WHDLoad 20.1 rejected the comma in the first Custom1 checkbox label; labels cannot
contain commas. The corrected label and config terminator boot without the warning
(shell inspected after exit). Runs now explicitly pass `CACHE PRELOAD`; PRELOAD was
already present. `NOCACHE` still overrides CACHE for cache-off comparisons, and route
results record the complete launch command. Fresh 500-field checks give 37 frames
for both options-off and shipped on A500; `Custom1=2047` gives 12.50 fps on 020-fast,
24.80 on 030/50 and 24.90 in the 040-25 emulator cell. These match the S6 counts;
no speed gain is claimed. Evidence: `tmp/p2/launch-check/`, `tmp/p2/config-runs/`.

### R2: blitter clear

Tested and rejected. A temporary `Custom1` bit 13 replaced Disk.1 `$5E840` with
four destination-only blits: 136 × 40 bytes per plane, 8,000-byte plane spacing,
three zero planes and one all-ones plane. Each blit completed before the next;
the last completed before returning to drawing. S4-active configurations kept
the CPU clear. A second candidate gave the blitter priority while clearing and
restored the previous priority afterward. Neither candidate is retained.

Same-build/session `fps.py`, `Custom1=8191 → 16383`, 500-field standard route,
`CACHE PRELOAD`:

| Setup | CPU clear fps | Blitter clear fps |
| --- | ---: | ---: |
| A500 | 4.10 | 4.10 |
| 020 chip-only | 9.40 | 9.20 |
| 020 fast (S4 active) | 12.50 | 12.50 |
| 030/50 (S4 active) | 24.80 | 24.80 |
| 040-25 (S4 active) | 24.80 | 24.80 |

The priority candidate repeated the A500 and chip-only 020 pairs twice with
identical counts (41/41 and 94/92). These synchronous clears provide no measured
gain and regress on chip-only 020; retain the native CPU clear. This does not
measure a future design overlapping clearing with other work. The 040 result is
an emulator run check, not a hardware speed prediction.

Candidate checks: A500 and chip-only 020 still screenshots are byte-identical
off/on; help, return, Quit Situation and subsequent walking show intact views and
panels. World speed is 6 walking units and 2 heading units per field on 020 fast
and 030/50. Options-off and shipped both give 37 A500 frames. Evidence and rejected
candidate sources remain ignored under `tmp/r2/{first,priority,checks}/` and
`tmp/r2/{shared-bus,priority}.asm`. No game code changes remain from R2.

### R4: data cache

`Custom1` bit 13 asks `resload_SetCACR` for `CACRF_EnableD` alongside the
instruction cache. With it off, the shipped instruction-only request is unchanged.
WHDLoad handles CPU/MMU differences, cache flushing and `NOCACHE`; no direct CACR
writes or emulator changes are needed. Its existing cache policy for the slave and
expansion memory is retained. Hardware inhibits data caching of chip memory and I/O;
this request does not make display memory safe for copy-back caching.

Same build/session, `fps.py`, 500-field route, `CACHE PRELOAD`,
`Custom1=8191 → 16383`:

| Setup | Data-cache request off → on, fps |
| --- | ---: |
| a500-1.5m | 4.10 → 4.10 |
| a1200, chip only | 9.40 → 9.40 |
| a1200-fast | 12.50 → 12.50 |
| a1200-030, reference 030/50 | 24.80 → 24.80 |
| existing 040-25 cell | 24.80 → 24.80 |
| 060 NOMMU, 25 MHz | 24.90 → 24.90 |

No measured route gain or regression. Retained by the user's cache-support decision,
not as a demonstrated speedup. The 040/060 counts are emulator run checks, not
hardware performance predictions. Real-hardware cache behaviour remains unverified; X1 was accepted without hardware
testing because no hardware was available.
The existing WHDLoad `BRANCHCACHE` switch also completed the 060 route at
24.90 fps with bit 13 enabled. It remains available through WHDLoad; R4 does not
force 060-specific CPU settings.

Checks: options-off and shipped A500 both 37 frames; native walk/turn rates
(6 units and 2 heading units per field) on 020-fast and 030; all 124 presentation
restore hashes passed. Still-scene screenshots match off/on on 030. Inspected
walking, Help/return and Quit Situation on 030, plus loaded Eagle vehicle/flight
views on 030/040/060. The cache option alone also passed the menu/walking play
check on 030/040. Input verification and original/release/VERIFY builds passed.
Evidence: `tmp/r4/`.

### X1: release

The single player control is the **Enhanced framerate** checkbox, enabled by
CUSTOM5=1 in the installed icon. Omission or zero leaves it unchecked. `Custom5=1` selects feature bits 0–13; `Custom5=0` turns them all off. The release
ignores legacy Custom1 settings. VERIFY retains individual bits with
`Custom5=0 Custom1=<mask>`. CPU/chipset/memory guards are unchanged. The README covers
installation, WHDLoad 17+, 512 KB chip RAM, the optional 200 KB workspace and CACHE/PRELOAD.

Same-session, same VERIFY build, 500-field `fps.py` route, enhancement Off → On:

| Setup | Off → On, fps |
| --- | ---: |
| a500-1.5m | 3.70 → 4.10 |
| a1200-fast | 7.50 → 12.50 |
| reference 030/50 | 8.90 → 24.80 |
| existing 040-25 | 11.70 → 24.80 |
| 060-50 | 12.80 → 24.90 |

The default-on matrix passed every cell, including explicit 030 MMU (24.80 fps)
and chip-only A1200 (9.40 fps). The known 040 frequency advisory remains: both 8 and
25 MHz give 248 frames. These 040/060 numbers do not predict hardware speed.

Release Off and shipped A500 both give 37 frames. Release world-speed checks on
020-fast and 030 give 6 walking units and 2 heading units per field. Release play
checks on 68000/020/030/040/060 covered Help/return, Quit Situation and walking;
030/040/060 also loaded the Eagle save, boarded, flew and returned from Help.
Screenshots were inspected, including the startup control showing Enhanced framerate
enabled. All 124 VERIFY presentation restores passed.
Input verification and original/release/VERIFY builds passed. Evidence: `tmp/x1/`.

No real hardware is available (user decision). X1 is complete without hardware tests;
real-cache behaviour with relocated/self-modifying code and 040/060 speed remain
unverified. No hardware-performance claim is made.
