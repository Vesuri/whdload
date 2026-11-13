# Test Drive harness internals

Phase 2 is complete as a static identification inventory. `TD:$xxxxx` means a
root-code-hunk offset; `TD:h3+$xxxxx` and `TD:h4+$xxxxx` mean offsets inside the
numbered overlay code hunks. File offsets are explicitly marked. These are not
absolute RAM addresses. Overlay offsets must never be put in a root PL patch.

## Evidence and reproduction

Run `python3 tools/identify_game.py` from the harness using the shared Python.
It verifies `manifest/phase2-inputs.sha256`, parses all hunks with amitools,
checks all 11 normal and six root VERIFY patch entries against the current slave
source, audits 11 h4 VERIFY ranges, resolves 107 root jump stubs and both overlay nodes, and writes the inventory plus disassemblies
to `tmp/phase2/`. `*-excerpts.txt` starts at known instruction entries; full
linear disassemblies also decode strings/tables as instructions and are search
material, not proof of instruction boundaries. The shared `amigaxdev.disasm`
module uses the installed 68000 objdump. `hunks.json`, `jump-table.json`,
`overlay-nodes.json` and `inventory-check.json` retain exact structural evidence.

The comparison reference is TD2's routine inventory in its `docs/game.md` and
this fork's `T/TestDrive2/usr/source`; the overlay donor is pinned in
`manifest/overlay-reference.commit`. TD2 offsets are used only to name analogous
functions. TD evidence below comes from the pinned TD executable, slave source,
NDK LVO definitions and the retained phase-1 live captures.

## Slave and existing patches

The normal slave uses KickEmu 1.3, BOOTDOS, CACHE, SEGTRACKER, BLACKSCREEN,
DOSASSIGN and HDINIT. CHIPMEMSIZE=$80000, FASTMEMSIZE=$20000; IOCACHE=10000,
NUMDRIVES=1, WPDRIVES=0, FONTHEIGHT=8. The optional CHIP_ONLY build instead uses
$A0000 chip, no expansion allocation and HRTMON; it is not the normal build.
WHDLoad interface version 17, flags NoError|Examine|ClearMem, exit key $5D (keypad
asterisk), no normal-build configuration options. VERIFY adds the C1/C3/C4/C5 test instruments described in phase7.md. Version is 1.5b.

`_bootdos` clears address zero, installs the level-2 keyboard hook, preserves
BCPL registers/stack, requires `devs/system-configuration`, checks TD's file
size (90112), assigns `TEST DRIVE:`, and LoadSegs `TD` from `data` with argument
`p\n`. `patch_main` applies PatchSeg then trackdisk interception. VERIFY first reads its
options and runs private assembly assertions; its load-end helper patches freshly
loaded h4 code before the final cache flush. `load_exe`
flushes caches before entering the root segment, restores the calling context,
and UnLoadSegs on return. Missing files/load failures abort through resload;
normal return reaches TDREASON_OK. The size test is not an executable hash test;
the local harness additionally pins the full hash.

The 11 normal-build patch sites are unconditional. Five root VERIFY entries
implement CUSTOM3 as described in phase4.md; CUSTOM4 adds the root:$7AAA
view-publication delay. The 11 h4 ranges and their option gates are declared
beside their patch list in simulation-verify.s and documented in phase7.md.
The table below describes the normal build:

| Root offset | Patch | Original and effect |
|---|---|---|
| $01CBC | PL_R | RTS replaces entry `move.b #$7f,$BFD100`; bypasses CIAB drive-select writes and DSKLEN=$4000 stop at $1CCC |
| $01D10 | PL_R | RTS replaces `or.w #$8000,d0`; bypasses the two DSKLEN writes at $1D14/$1D18 that start disk DMA |
| $00434 | PL_L $DFF002 | Address operand of $432 `move.w $BFF002,d0`; corrects the DMACONR access; masks bit $400 and saves it at -22498(a4) |
| $00444 | PL_L $DFF096 | Address operand of $440 `move.w #$8400,$BFF096`; corrects the DMACON write setting blitter-priority bit. Original restore at $456 still contains $BFF096 and is not patched. C2 now independently saves/restores the pre-game priority in the slave wrapper; C2-off retains the original behavior |
| $0059A | PL_S $52 | Branch to $5EC, skipping disk/protection measurements and comparison code through $5EA; $5EC sets local word to 910. Existing NOPs in this decrypted input are not new slave patches |
| $01872 / $05402 | PL_PS read_fire1 | Each replaces six-byte `move.b $BFE001,d0`; preserves physical fire and makes space ($40) act as active-low fire bit 7 |
| $0188A / $0541A | PL_PS read_joydat | Each replaces six-byte `move.w $DFF00C,d0`; preserves joystick and merges arrows $4C/$4D/$4E/$4F into JOY1DAT quadrature bits |
| $06390 | PL_P overlay_unload_end | Six bytes `movem.l (sp)+,a2-a3/a6; rts`; flushes rewritten stubs before identical restore/return |
| $06916 | PL_P overlay_load_end | Six bytes `movem.l (sp)+,d0-d2/a0-a4; rts`; same purpose after load |

Non-PL hooks: `_bootdos` replaces the level-2 vector at $68, retaining the old
handler. `kbint_hook` reads CIAA SDR ($BFEC01), rotates/inverts the raw code,
records press/release in the first 128 entries of its 256-byte keyboard table
and chains the old handler.
It avoids reading ICR (which would acknowledge interrupts). `read_fire2` exists
but is not referenced by this patch list.

`_patch_trackdisk` opens trackdisk.device and replaces the address operands of
Exec DoIO and SendIO vectors, saving their old targets. `_doio` skips **all**
requests to that device (the subsequent seek comparison is unreachable).
`_sendio` skips only command $800A for that device. Skips clear io_Error at $1F
and return d0=0; other requests chain to the original functions. These library
vector hooks have no TD hunk offset.

## Hunk layout and overlay nodes

Supported `data/TD`: 90112 bytes, SHA-256
`dd5b9608d64de145a6138c99d175f148939bd8e8c37d793631314a50c9d606db`.
Root HUNK_HEADER declares table size 5, initially loaded hunks 0..2.

| Hunk | Payload file offset | File-backed / allocated bytes | Purpose |
|---|---:|---:|---|
| 0 CODE | $28 | $7C0C / $7C0C | startup, libraries, blitters, sound, overlay manager |
| 1 DATA | $7C74 | $1E94 / $32A4 | jump stubs and a4 globals; trailing allocation zero-filled |
| 2 BSS | no payload; tag $9F20 | 0 / 4 | separate BSS segment |
| 3 CODE, node 1 | $9F78 (header $9F58) | $1A28 / $1A28 | three exported overlay entries |
| 4 CODE, node 2 | $B9DC (header $B9BC) | $A61C / $A61C | twenty exported entries; gameplay and Road Drawer |

Root has seven ABSRELOC32 entries (three to hunk 0, four to hunk 1).
Data relocation lists are in `hunks.json`; hunk 3 has one relocation at +$1952
to hunk 1, hunk 4 has none. The latter uses a4 globals and PC-relative code.

HUNK_OVERLAY is at file $9F2C. Its size word is 8, followed by 36 bytes:
count 2, two eight-byte node records, then terminated (hunk, stub-count) lists.
The phrase “49,364 bytes of overlay data” means **the entire file suffix from
$9F2C**, including headers, relocation/control records and the table. Actual
code payload totals 49,220 bytes. It is not a 49,364-byte overlay table.

| Node | Header file offset | First stub in DATA | Descriptor offset from table's first node | Hunk / stubs |
|---|---:|---:|---:|---|
| 1 | $9F58 | $284 | $10 | 3 / 3; entries +$0, +$A16, +$175E |
| 2 | $B9BC | $29C | $18 | 4 / 20; exact targets in overlay-nodes.json |

Each unloaded stub is eight bytes: BSR.w, displacement, node byte and 24-bit
entry offset. Loading turns it into JMP absolute plus the saved displacement;
unloading reconstructs BSR and the node/offset fields. TD:$68B4 indexes the
nodes, $68D4/$68D8 uses the stub/list offsets, $68E4..$68F8 resolves a hunk BPTR.
The unload routine $62E0 walks the nodes backwards, unlinks/frees segments and
rewrites stubs at $637E..$6386. Load entries $6892/$68A4 share the rewrite loop
$6908..$690E and exit $6916. The cache fix and its incoming-branch audit are
separately documented in development.md.

In a loaded DOS seglist, `hb` points to the first code byte; the long at `hb-4`
is the next BPTR. Thus `db = 4*BE32(hb-4)+4`, then the next link before db leads
to BSS. TD:$6422 loads a4=db+$7FFE through a DATA relocation. The stored a4 at
$18AE and VBL interrupt data pointer independently corroborate this in phase-1
live captures. `td_report.py` excludes WHDLoad's PRELOAD copy before following
this chain. Do not locate mutable data by matching its pristine contents.

DATA +$0..$281 holds 107 six-byte JMP stubs into root, relocated by LoadSeg.
Examples: -32298(a4) -> AddTask wrapper $7892; -32130 -> WaitTOF $7B9A;
-32442 -> RNG $530E; -32688 -> blitter wait $D44; -32610 -> shape blitter $10C4.
These links let overlay calls be resolved without assuming TD2 addresses.

## TD2 routine correspondence

“Confirmed” below means static instruction/call evidence for the stated role,
not validation as an FPS marker or a simulation model. “Not found” is explicit
where TD2's exact algorithm has no established match.

| TD2 role | TD location / status | Evidence |
|---|---|---|
| Ticks VBLInt / game field source | Confirmed root $180E registration, $18B2 handler, $18BA increment | Named interrupt, AddIntServer(INTB_VERTB=5), data pointer -31782(a4); live counter increments once per field |
| Sfx VBLInt | Confirmed root $2304 setup, $26AE handler, $26B6 counter | Named Sfx server, registration in setup; separate sound counter -31548(a4) |
| Road Drawer creation | Confirmed h4+$8594; AddTask call +$8622 | Allocates 2000-byte stack and $5C task, type 1, priority -1, name at +$862E; data -22292(a4); calls root $7892 -> Exec -282 |
| Main CLI priority | Confirmed h4+$859E calls root $17E8 with 4 | FindTask(NULL) then SetTaskPri (-300); phase-1 task dump also reports 4 |
| Drawer entry / loop | Confirmed h4+$869A -> +$B84; renderer +$A92 -> +$10CC | Restores saved a4, waits on -23376(a4), renders, WaitTOF at +$C14, increments -22312(a4). Drawing ownership is confirmed; its shifter/geometry writes feed CLI decisions (phase 5) |
| WaitTOF | Confirmed root $7B9A | graphics base -31786(a4), JMP -270; exported via a4-$7D82 |
| RNG | Confirmed root $530E..$5342 | 16-bit seed -25640(a4), initialized from VHPOSR once; signed multiply 6907, add 130253, retain low word, XOR VHPOSR at $5334/$533A. TD2 shares constants, not these globals |
| Overlay unload/load | Confirmed root $62E0 / $6892,$68A4 | Node/BPTR/stub logic above; exits $6390/$6916 |
| Buffer publication | Validated LoadView marker root $7AAA | h4+$C0E calls h3+$175E; Views alternate and next-field DMA reads the selected five-plane buffer. WaitTOF follows at h4+$C14. See phase4.md |
| Road walker / projection | Confirmed TD road traversal h4+$1A14..+$1B58, lookup +$A2A | Up to 40 iterations (30 with -28800(a4) set); d7 steps forward/backward, byte index selects four-byte road record. Calls span processing +$3828; +$7DFA consumes signed byte 1 into a long accumulator. TD2's complete-segment 8.8 walker and 52-byte row layout **not found** |
| Span fill | Confirmed horizontal blitter span h4+$3796..+$3826 and caller +$3828 | Clips x endpoints, derives word width/masks, waits via root $D44, programs BLTDMOD/BLTAFWM/BLTALWM/BLTDPT/BLTCON0, writes BLTSIZE at +$3822. TD2's CPU five-plane inner loop **not found** |
| Shape blitter | Confirmed root $10C4..$11E4; related $E88/$1432 | Clip/setup then five plane pointers -29714..-29698(a4), per-plane BLTSIZE and $D44 waits; h4+$3C40/$3D38 call through -32610(a4) |
| Blitter busy poll | Confirmed root $D44 | DMACONR bit 6 loop with counter -31926(a4); phase-1 trace observes it |
| Object projection/draw dispatch | h4+$3B10 and +$3B56, structural match | Queues/dispatches object codes, scales coordinates and selects shape data, calls shape blitter; precise traffic geometry deferred |
| Back-buffer clear | Confirmed primitive root $D72..$DBC | BLTCON0=$100 destination-only clear, BLTSIZE and wait; complete TD2 clear-site counterpart **not found** |
| Masked word copy, line blitter, mountains | TD2-specific counterparts **not found** | Root/overlay drawing families inspected; no verified one-to-one match assigned. Do not borrow TD2 $9588/$F91A/$8C90 |
| Simulation deadline / fixed period | Confirmed five fields, CLI | h4+$42 period; $F6/$192 deadline; $130 vehicle, $134 road, $164 traffic; phase5.md has traces and frame snapshots |

RNG calls exist in the root and both overlays. Root $230 calls its JMP stub;
h4+$1F76 is on the renderer's +$1ED2 path. This supports multiple call paths,
with full caller attribution and later-window divergence now established in phase5.md.

Phase 10 maps h4:$1114 to the main view (x=0..320,y=0..117) and h4:$11A2
to the mirror (x=240..320,y=26..43), on the same five destination planes.
The h4:$1A14 walker streams up to 40 / 30 rows; it has no TD2-style 52-byte
record table. Camera/curve recurrence already carries fractions. Root:$2108
is a full 16.16 interpolated sine, not the TD2 tangent helper. `phase10.md`
contains the native map, missing fractional paths, clipping and exact cache.

## VBL sampler and seed variables

`Ticks VBLInt` registration is at TD:$0180E: data pointer -31782(a4), code pointer
TD:$018B2. The handler saves registers at $018B2, restores a4 from $018AE at
$018B6, and increments `(a1)` at $018BA. Thus sampling before $018BA gives an
unambiguous field boundary with the game's a4 established. Every capture checks
that the counter increments by exactly one between snapshots.

| Tool name | d16(a4) | Size | Evidence / interpretation |
|---|---:|---:|---|
| `vbl` | -31782 | 4 | Ticks VBLInt data pointer; `(a1)` increment at $018BA |
| `joystick_direction` | -31762 | 2 | decoded joystick result stored at $018E8 |
| `mode_a818` | -22504 | 2 | raw selector set/cleared at $00186/$001BC/$001C4; gameplay semantics not yet assigned |
| `selection_a81c` | -22500 | 2 | raw selection initialized to -1 at $00020 and consulted at $001D6/$001FE |
| `blitter_calls` | -31922 | 4 | increment at $00D46 on entry to polling helper |
| `blitter_busy_loops` | -31926 | 4 | increment at $00D54 while DMACONR BBUSY is set |
| `sound_vbl` | -31548 | 4 | Sfx VBLInt counter increment at $026B6; handler $026AE |

`state_writers.py` identifies the executed VBL, sound and blitter stores in the
retained three-field A500 trace. It handles simple register-indirect and d16(An)
destinations; it does not reconstruct complex effective addresses or prove the
absence of other writers. `state_watch.py` confirms a chosen live writer with a
breakpoint/watchpoint; the VBL case also checks an increment of one.

`compare_state.py` compares this TD-specific table and, with `--raw`, every byte
of the data hunk. It rejects missing samples and mismatched window/machine/game
metadata. VBL/sound counters are epoch-normalized for equal-window comparisons;
raw comparison is not normalized. `--allow-different-window` is an explicitly
unaligned diagnostic. There is no full physics `--assert-core` claim yet.

## Exec tasks

The startup's FindTask(NULL) call at TD:$0005A stores the current process pointer
at -22432(a4). `task_state.py` follows that pointer and independently finds the
Exec task whose node name is `Road Drawer`, rather than reusing TD2's cached offset.

The retained A500 driving dump shows `Initial CLI` (NT_PROCESS, priority 4) and
`Road Drawer` (NT_TASK, priority -1). The drawer's saved SP is inside its stack
bounds. The CLI's saved SP is outside its original tc_SPLower/tc_SPUpper bounds;
the parser reports this fact and does not use those bounds to infer current game
stack ownership. Task ownership and the time model are verified in phase5.md; CLI physics and
renderer mutation sites occupy distinct traced stack contexts.

## Frame marker and baseline

Phase 4 is complete; `phase4.md` contains the frame-cost table, commands and exact
repeatability limits. The validated publication marker is root $7AAA, called via
h3+$175E after Road Drawer finishes a frame. The fixed window starts at first
h4+$F6 after reset, then captures 100 fields of the first attract race. VERIFY
CUSTOM3 makes its car and initial RNG state the same on all three CPUs. The normal
slave and hardware A/B package are unchanged. The phase-5 time model and state writers are documented below.

The initial seed and beam operand patches are root $5314/$5334. The demo-selection
hook at $230 resets the seed, calls the original RNG and replays SWAP. All five
VERIFY patch-list sites are included in identify_game.py; audit_rng.py checks
instruction boundaries, installed on/off bytes and the normal build hash.

Phase-1 ANCHOR=$18BA remains a VBL diagnostic, not a race benchmark. Arbitrary demo
captures are diagnostic only. Later race windows need their own reproducibility
check because phase 5 demonstrates draw-rate-dependent RNG consumption and
physical-state divergence. The full selected state model is documented below.

## Phase-5 time sources and state writers

Phase 5 establishes a five-field CLI loop with drawing dependencies; see
`phase5.md` for field-indexed evidence, event measurements and reproduction.
All offsets below are h4 code offsets unless explicitly prefixed root/h3.
Globals are signed displacements from a4, not absolute guest addresses. W=16,
L=32 bits; Q16.16 values have their integer word at the lower address. In
particular RPM's storage is a **long**, although decisions/display read its
integer word. A word-only RPM read is useful telemetry, not the complete state.

| Time source / owner | Storage | Writers and behavior |
|---|---|---|
| PAL fields / interrupt | -31782 L | root $18BA increments once per VBL through a1; independent of rendering |
| Simulation period / CLI | race frame -16(a5) L | $42 stores 5; nominal 10 Hz on PAL |
| Deadline / CLI | race frame -12(a5) L | $F6 initializes; $16A..$190 waits remaining fields through WaitTOF; $192 resets to current VBL. No catch-up queue: an overrun loses time |
| Physics / CLI priority 4 | call chain | $130 -> $43B0 -> $3F26 speed/RPM, $7F4C steering; $134 -> $1C3A road crossings; $164 -> $14EA traffic/police |
| Drawing / Road Drawer priority -1 | -22312 L frame count | $B84 task loop, $C14 WaitTOF, $C18 increment. Renderer snapshots state at $B04..$B56 under Forbid/Permit |
| Race time / CLI | frame -36(a5) L | initialized 1 at $56, $156 increments after nonzero gear latch; crash +240 at $272. Display divides by 12 at $36C: 5/6 nominal PAL rate, not VBL elapsed time |
| Average-speed numerator / CLI | frame -44(a5) L | $52 zero, $152 adds speed integer mph; $396 divides by race count, so crash penalty also lowers average |
| Tick counting enabled / CLI | frame -52(a5) W | $70 clear at start/recovery, $13E set once gear is nonzero; paused while waiting for crash acknowledgement |
| Race diagnostic epochs | frame -20/-24 L, -28/-32 L | $E6/$244 VBL, $EC/$24A blitter-call epochs; not the scoring clock |
| Sound VBL | -31548 L | root $26B6 independent sound interrupt count |
| Radar lamp display | -29238 L epoch, -29240 W phase | $23B4/$23FA store VBL; $23AE/$23F4 phase, 8-field off and variable on interval. Display work, not pursuit timing |
| Crash animation delay | DOS Delay(2) | root $75EA -> dos.library -198, called $33CC/$34DC seven times in all; drawing work adds CPU-dependent duration |

The main frame is valid only during that invocation. Stack offsets cannot be
used with the renderer's or another function's a5. `timing_samples.py` saves the
main-frame pointer at the $F6 anchor and samples that fixed frame address.

| State / representation | a4 displacement | Reviewed writers / ownership |
|---|---:|---|
| Longitudinal road position Q16.16 | -22352 L | $4A initializes 30; $4372/$4458 add displacement, $15B2 traffic avoidance correction; CLI |
| Speed mph Q16.16 | -22360 L | $84/$790/$81E2 resets; $3FDE torque/drag addition; $3F46/$3F80 braking, $3F5E neutral loss; $3E9A integer-word clutch conversion; $1E20 roadside and $8172 skid losses; associated zero clamps $1E2A/$3F50/$3F8A/$3FFA/$817C; CLI |
| RPM Q16.16 | -26340 L | $3E78 multiplies speed by ratio into full long; $3ED2 halves integer word, $3F00 restores saved word, $3F3C decay, $3F6C +500 integer RPM, $3FE8 clamp; reset $88/$794; CLI |
| Gear / ratio | -26336 W / -26334 W | $24D6 add selected shift; $24E0/$24EE clamp; alternate pattern $2588; ratio table stores $2542/$25DA; reset $92; CLI |
| Throttle/brake decision | -26332 W | $43B4 clears then $444C input-table result; shift paths $431E/$4378/$4394 clear; $78 initialization. Used by next speed update |
| Per-tick road displacement Q16.16 | -22344 L | $3FF4 speed>>6, $3FFE/$80 zero; CLI. Do not scale both this value and its addition twice |
| Steering Q16.16 | -22356 L | $8040/$804A input deltas, $8074 neutral steering snap, $81DE reset; CLI |
| Lateral position Q16.16 | -22376 L | $8008 demo/assisted centring integer-word step up to 10; $8014 copies computed result; $8070 assisted step; $81D6 initializes 100; CLI |
| Heading Q16.16 degrees, modulo 360 | -22328 L | $13EA adds signed road byte 1 /8 per whole road segment; $13F4/$1404 wrap integer word; $81CE reset; CLI road crossing, not time-scaled per road iteration |
| Road curvature traversed / neutral steering | -26196 L / -26182 L | $1C44 clear, $7F44 partial/full segment accumulation; $7F88 derived neutral steering; CLI |
| Steering geometry intermediates | -26192 L, -26204 L, -26200 L, -26186 L | $7F54..$7FDE and $8108..$81C0; lateral candidate, curvature-minus-turn, turn, skid/yaw contribution; not interchangeable with heading |
| Road-edge collision/steering widths | -29290/-29288 W | renderer $1CFA/$1D00 on first road-walker row, consumed by CLI $1236/$1DA6/$80CC. Simulation needs its own road-width lookup |
| Wall collision's saved x | -22372 L | renderer $B10 snapshots current x; CLI $1240/$127A consumes it. Enhanced mode must decouple this input |
| Clutch busy | -22786 W | CLI $255A/$260A set, $256E reset/no shift; $5CE clears only after display handshake |
| Shift per-buffer desired / acknowledged | -29902/-29901 B / -29900/-29899 B | CLI $254E/$2554 request; renderer $3AF8 toggles indexed acknowledgement. $472 checks both bytes before advancing/ending shift. Setup/recovery also restores flags |
| Shift animation hold | -23364 W | $4322/$437C/$4398/$5BA set 7, $5D8 decrements; cadence is CLI but progress gated by drawing |
| Forward traffic positions (six; slot 5 police) | -29584 +4i L | reset indexed $42A; spawn integer word $12CE/$12D2; move/correct/delete through a0 at $155A/$15DA/$15DE/$15EA/$15F2. Police $2354/$2358 spawn, $167A/$16CA/$16CE scripted correction |
| Forward traffic speed/displacement | -29548 +4i L | road speed setup indexed $13C6 and $13D0; $126E first slot; police slot -29528 at $235E/$2370/$16D2/$168C/$169A/$1624 |
| Forward traffic lateral records | -29500 +4i W, +2 flags W | renderer $184C writes road-origin plus lane; $181E/$183E move lane offsets per draw. CLI $153E/$1548 also requests avoidance; $1562 clears/$15CA sets following flags through a2. Renderer-written origins feed CLI collision: another draw-rate dependency. Records are not Q16 x |
| Oncoming traffic positions (five) | -29452 +4i L | reset $44A; spawn $12F6/$12FA; indexed correction/move $170C/$1740/$1744 and cull $1750 through a0 |
| Oncoming displacement / lateral records | -29418 +4i L / -29398 +4i W | displacement setup $13C8; renderer $18EC writes road-origin minus 224 into lateral word, consumed by CLI $1716. Following word is not fractional x |
| Police seen / pursuit age / stopped ticks / phase | -29320/-29318/-29322/-29316 W | resets $45A..$466/$1604..$1610/$163C..$1640; increments $1648/$1662/$16A4; phase $1686/$16AA. Thresholds 70,60,90,30 are simulation ticks, not VBLs |
| Radar encounter distance Q16.16 | -29248 L | $1320 activates integer word, $232E adds displacement>>5; $2384/$1620/$46A clear; CLI |
| Crash/event code | -22480 W | $124A/$1284 wall, $15B8 traffic, $15C2 police collision=2, $173A oncoming, $43CE over-rev=1; $7C/$1EC clear; CLI |
| Chances | -23352 W | $18 sets 5, $27E decrements, $28A game-over zero; root $47EC +2 at successful stage |
| Stage / gas approach / end road unit | -23346 W / -29904 W / -26234 W | stage $32 initializes 0 player/3 demo, $3BA increments; $6C/$1D2 approach; $45BE stage end from road length. No separate consumed fuel state identified |
| Accumulated score | -26350 L | reset root $2A/$1A6/$276 and h4 $22; $34C adds stage score from $C60 |
| Stage score baseline / reference / multiplier | -26224 L / -26220 L / -26216 W | $45CE/$45D8 table lookup; $45AA stage+4. See phase5.md for exact formula |
| RNG seed / initialized flag | -25640 W / -25638 W | root $5314/$531C initial; $5330 LCG low word and $533A beam XOR; VERIFY changes initial seed/beam and resets at demo selection. Shared by CLI and drawing; caller table in phase5.md |

Arrays with indirect writes are not covered exhaustively by the simple direct
writer scanner. Their ranges, strides and writer loops above are reviewed from
instruction-aligned routines. No claim of an exhaustive map of every renderer
scratch byte or all indirect control-flow targets is made. The state oracle
includes full DATA bytes, while the selected physics map distinguishes semantic
state from renderer snapshots, pointers, counters and storage aliases.

## Blitter option (phase 9)

`render.s` wraps the existing loaded-program call in `load_exe`. CUSTOM2 saves
DMACONR BLTPRI and INTENAR BLIT, enables priority and disables the unused BLIT
interrupt. Program return restores the saved enables. No new original-code
hook is installed; the root/h4 patch inventory is unchanged. The existing
root $434/$444 corrections already enable priority during gameplay, so phase-9
measured gains are attributed to IRQ suppression. `phase9.md` has the paired
FPS table, native-helper evidence, normal C2-off/on checks and their limits.

## Drawing rate (CUSTOM2)

C2 shortens the blitter waits (root $D5E, NOPs at root $DB6, $E08, $F8E and $11D8, and
`blit_plot_wait` at h4 $1D8C) and adds a third screen buffer for the Road Drawer
(`buffers.s`: h4 $B88 hold, $AEA buffer index, $C0A swap, $3AE4 gear lever, $4238/$4246
cluster cache, $240A/$2450 steering-wheel image). `draw-rate.md` has the design, the
per-buffer state, the measurements and the checks.
