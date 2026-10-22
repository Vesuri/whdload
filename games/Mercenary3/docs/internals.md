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
(for the options in the splash window), reads `Custom1` through `resload_Control` and keeps
the shipped patch list. It asks for 4 KB of expansion memory (`ws_ExpMem`) for bit 2. With every option off it runs the shipped slave's code paths.

| Option | Effect |
| --- | --- |
| `Custom1` bit 0 | `_dmaon` enables copper and bitplane DMA on its first call only, after the vertical blank, and completes the frame's 34-byte copy (the three replaced moves, then the original code from `$A85E`) |
| `Custom1` bit 1 | On AGA (Lisa's ID `$F8` in `LISAID`), 64-bit bitplane fetch: `FMODE` = 3 and `DDFSTOP` `$B8` in the two in-game copper lists (Disk.1 `$56780`, `$567CC`), the only ones that set the fetch window. Buffers and planes are 8-byte aligned, rows 40 bytes, modulos 0 |
| `Custom1` bit 2 | The supervisor stack in a 4 KB expansion block (fast RAM when fitted) instead of the top of chip RAM: the three `lea $7fffa,a0` / `unlk a0` stack setups (Disk.1 `$5DE66`, `$5DE88`, `$5DEEA`) get its top. The game uses less than a page of stack |

The `VERIFY` build (`make verify`) adds instruments; it has none yet besides its name.

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
- **Main loop** (head `$5E992`, one pass per frame):
  1. per-frame calls `$5E992..$5EA04` (not yet classified; together about 7,000 cycles);
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

`make check` verifies both input archives and their extracted files; `make original`
reproduces the shipped slave byte for byte. A1 has not met its done criterion.

The selected native emulator identifies its base revision as
`b70b1180b44ab25b97cd66466c70879897d8a362`, with the shared core, frequency, harness,
register-observer and input-observer patches. Its effective `a1200-030` configuration
selects 68030, 50 MHz, MMU 68030, data-cache emulation and cycle-exact CPU/memory timing.
These are configuration facts, not validated hardware timing measurements.

AmigaXDev's standalone WHDLoad playbook, section 5, documents the missing 68030 instruction
trace. In the inspected shared FS-UAE source, the MMU selection dispatches to
`m68k_run_mmu030` before the non-MMU cycle-exact loop; that MMU loop has no Barto
`cpu_profiler` scope. This explains why changing an anchor alone cannot satisfy the
instruction-profiler part of A1. It does **not** establish why the entry breakpoint is
missed: breakpoint processing is separate from instruction recording.

Bounded probes with the shipped slave have not yet confirmed gameplay:

- With entry (`Disk.1` `$4EDB0`) and publication (`$5E4DE`) breakpoints armed, a request
  to advance 1,200 fields did not complete within 60 host seconds.
- With no breakpoints, a request for 600 fields did not complete within 45 host seconds.
- A control with `--uae_mmu_model=0` also failed to reach the entry breakpoint within
  45 host seconds. Disabling MMU emulation alone did not resolve the bounded boot probe.
- An asynchronous continue followed by interrupt did not yield a confirmed stopped
  target; reads were rejected as target-running and are not counter observations.

The logs end around directory-drive startup. This is a boot-observation failure, not
proof that either game breakpoint cannot fire, that cache contents are stale, or that the
game itself is hung. No route frame count, first-frame offset or performance result was
obtained. Diagnostic source and logs remain under ignored `tmp/a1/`; emulator cleanup
uses the shared process helper and the project's recorded PID.

Resolve the A1 prerequisite in the plan before implementing the proposed counter anchor.
Its equivalence to the entry anchor on `a1200-fast` remains untested. A2's counter checks
below do not resolve that anchor or establish screenshot equivalence.

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
hash too. Only the entry anchor is supported until A1 is resolved; 030/040/060 route
completion is not established by this A2 validation.

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
