# Ferrari Formula One performance measurements

Current qualification (2026-10-14): emulator release qualification and calibrated
030/040/060 analysis pass; see STEP5_CAPACITY.md's release closure,
manifest/release-qualification.json and the tracked RELEASE_QUALIFICATION.md.
The opt-in local RC1 is reproducible. Human playtesting and real Amiga hardware
are deferred; historical measurements below retain their original scope.

Step 3 is complete for the requested 68000, 68020 and 68020 + Fast scope.
030/040/060 analysis is deferred at the user's direction. All measurements use the automatic no-input
demo, SPS 0481, the release rebuild and PAL emulation. Startup uses warp; measured
windows verify warp is off. No game performance change has been made.

## Method

Each matrix cell is two fresh boots, each anchored after completed car update
125, after requesting warp off at update 120. Record the actual settling fields
rather than a host-time sleep. Capture 1,000 consecutive fields with no debugger
breakpoints inside. Count changes to the bitplane DMA bank actually displayed,
not calls to LoadView or screenshot differences. Use the emulator's reported PAL
field rate (49.9204102 Hz on the current profiles), not an assumed 50 Hz.

The read-only private observer streams DMA counts, first visible plane addresses
and aggregated CPU costs. It adds no guest instructions. CPU profiling and
DMA-only observation on the same A500 window give identical complete anchor and
final Chip RAM and identical presentation sequences. The accounting check is
recorded instruction cost / elapsed field cost. The instrument rejects missing
DMA or missing fields. Its source patch, binary hashes and reproduction commands
are retained locally.

The first and last presentation intervals can be partial. Count-based FPS has
about one presentation / window edge uncertainty (0.050 FPS for 1,000 fields).
Interval percentiles use only complete intervals. Costs use the first 500 fields
of each long CPU trace. Inclusive phase measurements exclude incomplete calls;
never add nested inclusive times. Unsupported CPU traces are unavailable, not
zero cost. No result is a real-hardware measurement.

Both CUSTOM1=0 (existing two-WaitTOF fix) and CUSTOM1=1 (diagnostic bypass) retain
the same release binary. At matched completed updates their state is compared;
when one arm executes more updates per elapsed field, its later scene differs.
Native initialization can differ across machine profiles. Therefore comparisons
between machines are native-demo baselines, not identical-pose speedup claims.
The rendering omission experiment uses a separately named equal-size control.


## Results

Two fresh boots agree exactly in anchor memory, final memory and displayed-bank
sequence for every cell below. All measured caches are disabled (CACR = 0).
No extra memory was silently added to make a profile boot.

| Machine | Memory (Chip / Slow / Fast) | Fix on FPS | Fix off FPS | Fix-on p50 / p95 / max interval (ms) |
| --- | --- | ---: | ---: | --- |
| A500, 68000 ~7.09 MHz | 512 KiB / 1.5 MiB / 0 | 3.494 | 3.994 | 280.4 / 300.5 / 300.5 |
| A1200, 68EC020 ~14.19 MHz | 2 MiB / 0 / 0 | 5.541 | 6.989 | 180.3 / 180.3 / 180.3 |
| A1200, 68EC020 ~14.19 MHz + Fast | 2 MiB / 0 / 4 MiB | 5.541 | 7.089 | 180.3 / 180.3 / 200.3 |
| A500 + Fast (additional completed baseline) | 512 KiB / 1.5 MiB / 2 MiB | 3.494 | 3.944 | 280.4 / 300.5 / 300.5 |

The timing-fix bypass is diagnostic. Within each machine all sampled state
blocks agree at completed update 125, but the faster arm completes more updates
in the same fields. These FPS increases are not accepted gameplay improvements.
The long windows also contain different later poses; do not price a small routine
change from these aggregate ratios.

## Completed-call timing

The 500-field detailed captures reproduce the exact first 500 fields of the
corresponding ordinary-release baseline, including per-PC costs. Means below are
from complete calls; road time includes the two-WaitTOF span. Work excludes the
union of observed WaitTOF, explicit beam-wait and WaitBlit spans, but includes
interrupt service and unbracketed stalls.

| Machine / fix | Complete loops | Loop ms | Work ms | Car update ms | Road preparation + drawing ms | Two WaitTOF ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| a500 / on | 34 | 281.26 | 207.15 | 70.11 | 104.18 | 34.43 |
| a500 / off | 40 | 244.61 | 207.30 | 69.66 | 70.02 | 0.00 |
| a1200 / on | 54 | 180.36 | 116.42 | 45.24 | 72.36 | 35.79 |
| a1200 / off | 69 | 143.53 | 117.20 | 45.54 | 36.69 | 0.00 |
| a1200-fast / on | 54 | 180.36 | 113.90 | 44.49 | 71.39 | 35.63 |
| a1200-fast / off | 70 | 140.56 | 115.12 | 44.78 | 35.57 | 0.00 |

Detailed files retain call counts, maximum times, work p95, instruction-cost
units, self costs by hunk, IRQ costs, DMA distributions and counter boundaries.
The first/last incomplete iterations are excluded from completed-call timings.
One render/publication per steady loop is consistent with the traced boundaries;
partial windows can differ by one count and are not evidence of extra simulation.

## Rendering ceiling on 68020 + Fast

These are separate 500-field diagnostic arms. The matched control and road-line
omission slaves have identical size and differ only in the patched instruction
word. The omission replaces race:$61e2 ($6ac4a) with RTS: it skips blitter edge-line
setup/drawing, preserving the outer frame bookkeeping. Its picture is deliberately
incomplete and must never be shipped. All arms match sampled game state at update
125. Instant blits are switched on only at this settled anchor and confirmed
enabled in the effective emulator preferences. Enabling them from boot changed
the RNG/trajectory; that preliminary capture is retained as
`instant-at-boot-rejected` and excluded from comparisons.

| Diagnostic arm | Displayed FPS | Complete-interval mean (ms) |
| --- | ---: | ---: |
| ceiling-control-c0 | 5.491 | 180.66 |
| ceiling-control-c1 | 7.089 | 140.51 |
| ceiling-no-road-lines | 7.388 | 135.56 |
| ceiling-instant-blitter | 8.486 | 118.28 |

Compare each omission with `ceiling-control-c1`, not the normal release: the
control adds one patch instruction and has a different loader layout. These gains
do not add. They estimate opportunity in this demo, not a playable target.

## Ranked opportunities

1. **Correct pacing, after step 4's time model.** The two-WaitTOF routine costs
   about 34–36 ms per loop on all three machines. Bypassing it changes sampled
   cadence from 3.49 to 3.99 FPS on A500 and 5.54 to roughly 7 FPS on 68020.
   Completed-loop work remains about 207 ms on A500 and 114–117 ms on 68020.
   A safe solution must preserve game speed before claiming that cadence gain.
2. **Blitter latency and the volume of small operations.** The matched 68020 Fast
   instant-blitter arm rises from 7.09 to 8.49 FPS (about 19.7%). The A500's first
   500 fields execute 15,266 blitter dispatches versus 500 VBL dispatches in the
   level-3 handler; all interrupt-stack work costs about 16.3% of elapsed cycles.
   The existing KickEmu WaitBlit poll deliberately reads CIA four times before
   retesting busy. Investigate fewer operations, batching or suitable CPU paths;
   do not blindly remove waits or interrupt dependencies.
3. **Software arithmetic.** Resident hunk 130 ($293d0) implements signed 32-bit
   division with a 32-pass shift/subtract loop. It costs about 10.8% of A500 elapsed
   cycles. Measure exact-output fast paths and a 68020 specialization; preserve
   zero-divisor, signed overflow, remainder and register/flag behavior. The
   sine/cosine scale helpers in resident hunk 38 add about 4.4% on A500.
4. **Road edge-line work is a smaller, bounded opportunity.** Omitting it saves
   about 10.15 ms in the road routine on 68020 Fast, but the main loop saves only
   4.98 ms because the beam wait grows. Visible FPS rises only 4.2% (7.09 to 7.39).
   A real exact-output replacement can recover only a portion of this ceiling.
5. **Placement/cache investigation, not just adding RAM.** The current game stays
   in Chip RAM and has caches disabled. Extra Fast RAM alone produces no clear
   baseline benefit. Any relocation or cache change needs an overlay-lifetime,
   executable-write and DMA-ownership audit first; these measurements do not
   establish that enabling caches or moving arbitrary data is safe.

These opportunities overlap. The instant-blitter and line-omission gains must
not be added, and removing all drawing is not a playable optimization.

## Calibration, scope and evidence

A500 fields contain 142,102 trace units; 68020 fields contain 284,204.
These agree with 313 × 227 colour clocks and the respective CPU clock ratios.
The field clock is 3,546,895 / 71,051 = 49.920410 Hz. Instruction accounting is
checked against those independently recorded field totals. CPU vs DMA-only
observation produces identical A500 state and presentation sequences. Negative
controls reject missing DMA and skipped fields.

Game code, globals and both three-plane screen banks remain in the slave's
512 KiB Chip region in these configurations. Extra Fast RAM changes the host/loader
environment, not automatic placement of the game's hot code. Native boot seeds
differ across profiles, so the table does not claim identical-trajectory cross-CPU
speedups. Same-profile repeats and timing-fix arms have matched-update checks.

No contact-specific worst case or season behavior was measured; the user selected
the automatic demo. Nearby opponents are visible in retained captures. Fixdelay
is a loader/startup delay outside these settled windows. Full game-time semantics,
handling, cache coherency, Irek and hardware validation remain later work.

030/040/060 work was stopped when the user deferred it. Initial 030 captures
are exploratory evidence only; they are excluded from this completed scope.
Unsupported instruction traces are unavailable, never zero-cost claims.

Reproduction: `profiling.md`. Exact checks: `manifest/step3-checks.json`,
`manifest/step3-negative-checks.json`, `manifest/step3-detail-checks.json`.
Per-run inputs, configuration, emulator/slave hashes, state and field records are
in `tmp/step3/<name>/`. All artifacts and tools remain ignored; tracked source
and the ordinary release slave are unchanged.

### Accelerated release observations (2026-10-14)

Calibrated 030/040/060 emulator analysis is complete. Enabled production reaches
16.640 FPS over 300 presentations and 0.0409% error over 60 simulated seconds.
Original v1.01 observations range from 5.491–5.691 FPS (CUSTOM1=0) or
6.540–7.139 FPS (CUSTOM1=1), with only 54.9–71.4% real-time calendar advance.
These are separate native demo observations, not matched-workload speedup ratios
or physical-hardware timing predictions. See tracked
docs/RELEASE_QUALIFICATION.md and
manifest/release-original-observations.json for per-profile evidence and scope.
