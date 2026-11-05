# Ferrari Formula One execution map (step 2 complete: automatic demo)

Scope: SPS 0481, release baseline, A500 68000 PAL, 512 KiB Chip / 1.5 MiB Slow.
No performance change has been made. Absolute addresses below are calibration
values for this configuration; identities are executable HEADER file offsets and
hunk numbers. They must be resolved again for a different memory layout.

## Evidence and reproducibility

`tmp/step2/native-a` and `native-b` are independent fresh boots of the same
release. No keys or mouse events were injected. Startup used warp. All 512 KiB
of Chip RAM agree byte-for-byte at completed update 100 and 124. The first race
update has countdown 35; update 50 has countdown 0, segment 822, speed 131;
update 75 has segment 833, speed 272. This is a deterministic no-input route for
this exact artifact/profile, not a promise about another loader or machine.
The original shipped/rebuilt cross-loader RNG difference from step 1 remains.

`explore_step2.py` records the loader before/after hooks, completed updates and
24 fields of bitplane DMA. `overlay_map.py` decodes the actual hunk table,
including BSS. Its code-byte mismatch count includes mutable tables embedded
in CODE hunks; it is not yet an immutable-code acceptance test.

## Main loop and publication

Race HEADER file:$22f30, hunk 160 begins at calibrated $64a68. Main loop is
race:$070c ($65174). Control-key read at race:$0880 ($652e8) calls resident
hunk 6 ($227f8), which translates keyboard.device raw keys through its table.

| Boundary | Race-relative location | Meaning |
| --- | --- | --- |
| Wait for prior render | $0a7e ($654e6) | WaitBlit after the previous loop, including the final instrument drawing |
| Request display | $0a8e ($654f6) | Calls resident hunk 21+$28a ($2428a), selecting the old draw buffer for LoadView |
| Select new draw buffer | $0aa4 ($6550c) | XOR buffer index with $66fa4; update two plane-table pointers |
| Read driving controls | $0ada ($65542) | Calls race hunk 177 ($6ab88), native mouse position/buttons |
| Update eight cars | $0b98 ($65600) | Calls race hunk 167 ($67120); all eight car slots processed 7 down to 0 |
| Completed car update | $0b9e ($65606) | Return from hunk 167; projection and rendering still follow |
| Geometry preparation | $0d22 ($6578a) | Calls hunk 188 ($6b368), then hunk 173 ($6a2d0) |
| Existing slave wait | $589c ($6a304) | Inside geometry preparation, before the 25 track-section transform loop |
| Final drawing | $14d8 ($65f40) | Calls instrument drawing ($6694e), then branches to main-loop entry |

Graphics wrappers: $2a11c is LoadView (-222), $2a130 WaitBlit (-228),
$2a260 OwnBlitter (-456), $2a270 DisownBlitter (-462). The game owns the
blitter during most drawing and explicitly waits for beam VPOS high bit at
$65728. A safe artificial draw delay must follow the next-loop WaitBlit and
precede publication; delaying inside OwnBlitter would test a different condition.

The completed-car-update boundary is not completion of *all* game state:
clocks and instrument/audio state also change later in the loop. Snapshot both
that boundary and publication. Do not move those writers out of drawing until
step 4 has established their time model.

The presentation marker is a changed displayed plane set following LoadView,
not VBL count, an unconditional pointer write, or the timing hook. The two
three-plane banks are $2ae60/$2d6b0/$2ff00 and $6f2a0/$71af0/$74340 here.
In native-a/display.bin, fields 0–9 fetch the first bank, fields 10–23 the second.
The first visible fetch is base+4. The cropped game-image hash changes at exactly
the same field and is constant within each run of repeated fields. Captured
screens show actual racing and nearby opponents, not a title or stationary grid.
This cross-check uses DMA addresses and rendered pixels independently.
In the final instrumented 32-field captures, DMA banks change at fields 11 and
25, while pixels change at 10, 11, 24 and 25. Thus image changes alone are not
a frame counter. Bank transitions coincide with new images, but extra image
changes may reflect visible writes or capture phasing; resolve their cause before
making a tearing or exact pixel-latency claim in step 3.

## Native input decoder

Contrary to the old fixture comment, **right mouse is accelerator, left is brake**.
The decoder returns 1 for left, 2 for right, 3 for both (clutch). This agrees with
the local manual and simulation branches: 1 decelerates, 2 accelerates, 3 revs.

Raw $64 (Left Alt) and $67 (Right Amiga) both translate to game code 1, downshift.
Raw $65 (Right Alt) and $66 (Left Amiga/Commodore) both translate to game code 3,
upshift. They are alternatives, not chords. The gear branch requires control
mode $1c1c2 == 1 and player slot 0. It clamps the gear from 1 to the configured
maximum. ESC raw $45 maps to space ($20), used by the pause loop. Raw $27 maps
K/tow; raw $19 maps P/passenger pit; number keys select boost 0–9.

Mouse VBL server (resident hunk 30+$44, $2481c) reads JOY0DAT and handles
8-bit wrap by signed deltas, updates/clamps X/Y and increments a 16-bit field
counter. X/Y are at $24aa8/$24aaa, previous counts $24ace/$24ad0, field counter
$24ad2. GUI Y is inverted: stored 196 corresponds to screen y=3. Race input
bounds differ from GUI bounds. Native sampling must be retained when testing
field-driven controls. Task and IRQ work must be separated by stack ranges;
Barto's saved SR is stale and cannot establish context.

## Preliminary state inventory

Addresses are calibration values, not safe patch addresses. Array stride is two
unless stated otherwise. Physical units not proven by code/UI are deliberately
left as game units.

| State | Representation | Ownership / writers |
| --- | --- | --- |
| Car track segment | $6a60a, 8 words | race hunk 167; committed at $68584 |
| Car lateral / segment coordinates | $6a61a / $6a62a, 8 signed words each | hunk 167, $68532 / $68546; bounds tested against track section widths |
| Car heading components | $6a66a / $6a67a, 8 words | $68568 / $6855a; projection masks angle to 1023 (1024 units/revolution) |
| Speed | $2275a, 8 words | $68576; signed arithmetic, displayed interpretation still to be calibrated |
| Steering | $1c6a2, 8 signed words | player native X copied at $67492; other modes use AI writers in hunk 167 |
| Buttons | $66f92 word, previous $66f90 | native input wrapper $6ab88; sampled once/main iteration |
| Manual gear | $66c3c word | $6d6c8 decrement, $6d6ec increment, clamps; $6f272 working gear, $6f0e8 byte array committed at $6d85a |
| Boost | $1bf52 word | number-key decoder $654ce, range 0–9 |
| RPM working value | $6f270 word | hunk 203, gear/speed calculation; copied to $6f0f4 |
| Demo/control/difficulty | $1bee8 / $1c1c2 / $1c1c4 words | native takeover bookkeeping $236d8; demo begins 1/0/3 |
| Countdown | $66f94 word | init $64efa and optional random add $64fb6; decremented once/car-update pass at $67174 |
| RNG | $24f60..$24fcf (56 words), pointers $24fd0/$24fd4 | resident hunk 35, two cycling pointers and XOR; title loop also advances it |
| Race / session clocks | $226c0 and $226ca structures | $22c3a called after drawing; full layout/units still to be established |
| Race status per car | $2268e, 8 signed words | collision, tow and race-exit logic; nonzero/negative states require full decoding |
| Car-condition accumulators | $66c3e..$66c72 | setup words expanded by 14 bits at race init; engine/gear/tyre assignment still to be proved |

## Demo acceptance results

Final captures are `tmp/step2/verified-demo-a`, `verified-demo-b` and `slow-demo`.
They use separately named diagnostic slaves; normal release code is unchanged.
Two fresh boots have identical complete 512 KiB Chip RAM at completed update
125 and identical decoded DMA/pixel observations for the following 32 fields.
The diagnostic field counter is 32-bit; the game's GUI counter can reset.

Warp is enabled through startup, then disabled through the private emulator's
native action queue. Readback checks actual emulation-frame warp state, not only
preferences. The ordinary arm switches at field 1707 and captures from field
1776 (69 settling fields), through field 1808. Profiling metadata and scratch
bytes are restored before capture and checked byte-for-byte. No breakpoints
remain inside the 32-field recording. This validates the capture procedure,
not FPS or real-hardware performance.

At the anchor the ordinary arm has 125 car updates, 125 completed-draw barriers,
125 publication requests and 124 geometry calls. The recording adds 2, 2, 2 and
3 respectively: its endpoints cut across iterations. Do not infer different
steady-state rates from partial-loop counts. The barrier includes initialization
on its first visit; it is not an independent proof that every request is visible.
Static flow puts the existing two-WaitTOF hook once in each geometry preparation,
before the section loop. Timing and complete-cycle costs remain step 3 work.

The slow arm inserts three WaitTOF calls after completed drawing, before display
publication. It reaches update 125 at field 2100 instead of 1776. All sampled
state blocks, including eight-car positions/headings/speeds and RNG, agree at
that update. The comparator also rejects a later demo state and a deliberately
changed speed byte. This supports update-coupled behavior in this sample; it
is not proof of all clock semantics, long-run equivalence or correct real-time
speed. `manifest/step2-state-checks.json` records the exact checks.

`manifest/step2-overlays.json` maps only active resident/race/stub identities at
the demo anchor. Inactive slots are not decoded using a stale base. Relocation
records are read without dropping repeated target groups. Code-difference counts
are diagnostic only: embedded mutable tables and diagnostic hooks are included.
Immutable-code equivalence is not inferred from those counts.

## Deferred coverage and corrected evidence

At the user's direction, menu/pit exploration stops here. Interactive input
tapes, contact, season transitions and save/load are not demo acceptance gates;
add them when the proposed implementation needs them. The preliminary state
inventory is intentionally incomplete: full units/writers belong to step 4.
Other versions, layouts and machine profiles need fresh address resolution.

The old step-1 input fixture had an unbalanced MOVEM. Its generator is corrected,
but former passing captures cannot prove register preservation. It also applied
the brake where its comment said accelerator. Do not use those fixtures as an
input or performance oracle. Ancillary native-input experiments are retained
under `tmp/step2/native-drive-*`, separate from the no-input demo acceptance.
Failed guest warp-switch experiments are retired; the builder rejects WARP_OFF=1.
