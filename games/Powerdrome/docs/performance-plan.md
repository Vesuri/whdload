# Powerdrome performance implementation plan

Project status: Phases A–D and E1 are complete. Phase E2 stopped at the steady A500 handling gate; Phase E remains incomplete.
See the [current handoff](open-work.md) for completed checks, open gates and resume priorities.

The optional implementation and its completed measurements are documented in
[performance implementation](performance-implementation.md). `CUSTOM1=1` enables it;
the option remains off by default. This document retains the design rationale and gates
for further expansion of the accelerated path. The completed local edge/span investigation
is tracked step by step in the [raster improvement report](raster-improvements.md).

The first faster-CPU experiment should render the existing planar scene into genuine fast
RAM, then copy the completed scene to the native chip-RAM back buffer. This is feasible
while retaining the existing four-plane representation and polygon rasterizer. It directly
addresses the repeated bitmap accesses in the hottest drawing loops. Benefit is plausible
on accelerated machines, but must be established by timing the complete render-and-copy
path on each CPU and memory configuration.

The existing simulation is sufficient for this work: movement already uses an elapsed-time
delta. It runs in the same main loop as rendering, but its core displacement is time-scaled.
Preserve its delta calculation, clamps, update order and once-per-loop side effects. The
implementation scope is faster planar rendering and presentation; simulation scheduling
and physics behavior remain native.

## Evidence and current constraints

The [practice profile](practice-profile.md) measures the 500-field A500 departure run.
Its track phase spends 54.27% of recorded cycles on polygon edges and spans, 8.45% on
background filling, 5.25% on viewport clipping and 10.98% on camera geometry, projection
and visibility. Track WaitBlit is only 0.17%; VBL handshake polling is 1.89%.
These percentages identify targets; they are not faster-CPU cost estimates.

Additional analysis of the same trace establishes:

| Observation | Result |
| --- | --- |
| Player movement updates / scene-render entries | 70 / 70 |
| Renderer returns / post-render updates / presentation entries | 69 / 69 / 69 |
| VBL callbacks during the track phase | 309 |
| Distinct draw-buffer addresses | 2 |
| Background clear per plane | Bytes 760–5999, rows 19–149 inclusive |
| Polygon span writes | Reach rows 19–153 inclusive |
| Recorded timestep values | 12, 16, 20, 24, 28 and 32; no clamping in the 69 sampled track presentations |
| Resource decrements at `$d94a` | 69, each subtracting 1 before any conditional extra decrement |

The last render is incomplete. Traffic calculations below use the stream through the last
of the 69 complete renderer returns. The three other entry counters have one more hit
because the next iteration begins before the capture ends. The outer call at `$bc4e` has
69 captured hits because phase accounting begins at the first callee entry `$ca3e`.

`tools/analyze_pipeline.py` produces the event sequence, timestep samples, clear bounds,
span-write rows and traffic counters. Game addresses in this plan are code-hunk offsets;
state fields are relative to the state base at game `$a6e`. The supplied game binary and
captured instruction stream are the primary evidence for the game-specific findings.

Two setup details matter for accelerated tests. The unmodified development baseline defined
`FASTMEMSIZE=0`, so extra host fast RAM was not exposed as ordinary guest fast memory by
its interface-17 KickEmu setup. The baseline A1200 title test consequently executes
the game from chip RAM. Also, none of KickEmu's `CACHE`, `CACHECHIP` or `CACHECHIPDATA`
build symbols is defined. Standard WHDLoad user cache options remain available. Adding
host RAM or selecting a faster CPU alone does not test the proposed rendering architecture.

## Simulation and rendering are coupled

### The driving sequence

The regular loop is structurally:

```text
$bc4a  ancillary work
$bc4e  call $ca3e
         $ca74  control and speed update through $cef6
         $ccf2  scale player movement by the stored timestep
         $cdc4  write position, then camera state
                  other game and opponent updates
         $cee8  call scene renderer $10df2
         $ceec  call $d8ea: HUD drawing AND gameplay/resource updates
         $cef0  call $f0dc: timer and other display work
$bc7c  call $8056
         $7f7a  sample clock, compute the NEXT timestep, exchange buffers
                  LoadView and clear VBL handshake
$bc86  increment per-loop counter
         process further state/input and repeat
```

This structure is confirmed dynamically: movement and rendering occur one-for-one in this
track segment. `$ca3e` is a combined update-and-render routine, not a standalone physics
function. The VBL routine `$5684` independently samples input, updates the clock periodically,
increments the VBL count and signals the renderer. It does not run the main movement step.
Clock/input interrupts continue while the main task draws.

This conclusion applies to normal driving. The title demo and cockpit-departure paths can
render without this player-update sequence. Opponent movement at `$d56c` also uses the
stored timestep, but that instruction was not reached in this Practice trace; opponent
behavior needs a race fixture.

### Elapsed time only covers part of the behavior

`$59b6` differences CIA-A TOD readings, multiplies the difference by four and adds it to
clock `$f96`. `$7f7a` subtracts the previous timestamp at `state+$218`, clamps the result
to **8–50**, then stores it at `state+$21c`. The updated value is used by the next loop.
Player movement at `$ccf2` multiplies speed by this delta and divides by 24 before applying
orientation. Opponent movement at `$d56c` uses the same delta with divisor 26.

Across all 68 adjacent sampled track presentations, the raw clock delta equals four times
the PAL-field separation. The 69 observed deltas are:

| Delta | Count |
| ---: | ---: |
| 12 | 17 |
| 16 | 23 |
| 20 | 19 |
| 24 | 3 |
| 28 | 5 |
| 32 | 2 |

For this PAL setup, the lower bound of 8 corresponds to two fields, or 40 ms; the upper
bound corresponds to 250 ms. If presentation reaches one update per field, a raw delta of
4 would become 8. The delta-scaled displacement would then represent twice the elapsed
time, all else equal. Conversely, long stalls above 250 ms lose elapsed simulation time
through the upper clamp. These are consequences of the code and measured clock scale,
not results of an accelerated gameplay experiment.

There are additional dependencies on iteration count:

| Site | Behavior | Timing implication |
| --- | --- | --- |
| `$cf86–$cf90`, `$cfca–$cfd4` | Move speed toward a target by one eighth of the difference | Response depends on update frequency; these branches were not reached in the recorded route |
| `$d00a`, `$d01e`, `$d25e` | Subtract speed increments in particular control/engine states | No explicit `state+$21c` scaling at these sites; exercise each state |
| `$d93a–$d9a0` | Decrement resource `state+$1ba`, using a speed/coefficient calculation with a minimum of 1 | Executed once per completed iteration in the trace; coefficient `state+$458` is set to 58, 34 or 18 at `$12762/$1277c/$12796`, not the frame delta |
| `$cd60` | Increment falling-state counter | Conditional per-update behavior; not reached here |
| `$cdb4–$cdc0` | Advance impulse counter and halve components | Conditional decay depends on updates; not reached here |
| `$53f6`, called from control/effect paths | Advance the shared random seed | Different update/render call counts can change random sequences |
| `$112ec/$112f0` inside the renderer | Decrement an effect counter and generate an effect | Rendering itself is not side-effect free |

The semantic label of `state+$1ba` should be confirmed against the cockpit display before
calling it fuel in user-facing behavior tests. Its per-update decrement is established
regardless of that label. These findings describe existing behavior. They do not expand this performance work into a
simulation rewrite or frame-rate cap.

## Fast RAM rendering design

### Retain the native planar layout

Each native bitmap has four planes, 40 bytes per row and an 8,000-byte plane stride, or
**32,000 bytes** for 320×200 pixels. The CPU rasterizer obtains the draw base through
`state+$3ba`; the background loop, span loop and several other CPU primitives use it.
The back/front bitmap descriptors are at game `$4696` and `$46be`. Buffer exchange at
`$7f7a` updates the draw/display bases and descriptor references at `state+$3b2/$3b6/$3ba/$3be`.

Allocate one aligned 32,000-byte fast-RAM staging bitmap with the same layout, plus guards.
Preserving the original plane stride avoids changing dozens of fixed plane offsets. A
single staging bitmap is enough while CPU rendering and copying run serially. Two chip
buffers remain necessary for the existing display scheme; a second fast bitmap is useful
only if later design work proves a need for retained per-buffer contents or pipelining.

The custom chips require chip-resident data. Consequently the final transfer from fast
RAM must be performed by the CPU; the Amiga blitter cannot copy directly out of fast RAM.
Display bitplanes, copper lists, audio data and blitter source/destination buffers retain
their chip-memory requirements. [Amiga programming memory rules](https://wiki.amigaos.net/wiki/Programming_in_the_Amiga_Environment#Two_Kinds_of_Memory)

### Wrap only the scene renderer first

The first hook candidate is the complete four-byte BSR at `$cee8`, which calls `$10df2`
and returns to `$ceec`. Verify its bytes and incoming branches before installing a hook.
Use an out-of-line wrapper that preserves the original calling convention, live registers,
condition codes and state restoration:

1. Confirm the route/view is supported, fast memory is genuine and allocated, and the native
   draw destination is the inactive chip buffer. Otherwise call the native renderer normally.
2. Finish any outstanding native blitter operation that could access the destination.
   Seed the staging pixels whose old contents the renderer preserves or reads.
3. Save the native `state+$3ba` and point that field to the fast bitmap. Keep the native
   display and bitmap-descriptor pointers unchanged.
4. Call `$10df2` exactly once, preserving its original non-pixel side effects.
5. Restore `state+$3ba`, copy the validated scene extent to the native chip back buffer,
   and return to `$ceec`.
6. Let `$d8ea` and `$f0dc` draw the cockpit/timer and perform their existing updates on chip
   memory. Let the normal `$8056` perform the only buffer exchange for this iteration.

This presents one completed scene per native presentation. “In one go” is a batched CPU
transfer before presentation, not an atomic hardware operation. For the partial-height
scene there are four contiguous per-plane copies. Do not copy to the displayed buffer,
swap early, add another `$8056` call, or hold interrupts disabled during the copy.

A global redirect is unsafe. Some code uses `state+$3be` bitmap descriptors or fixed native
buffer pointers rather than `state+$3ba`. For example, the conditional background at
`$112cc` calls `$176c6`, and effects through `$16de6` can reach the same sprite/blitter path.
A chip write during fast rendering could otherwise be overwritten by the final copy.
The four watched conditional renderer sites were absent in this track capture, which is
a useful initial whitelist but not general correctness evidence. Initially keep pit,
menus, title inset, alternate backgrounds/views, crash/effect states and unverified paths
on native rendering. Expand coverage with explicit fixtures and pointer/write audits.

### Copy bounds and preserved pixels

A copy of only the cleared area would be wrong. The background clears rows **19–149**,
but executed polygon writers also modify rows **150–153**. The initial verified candidate
rectangle is therefore all 320 pixels of rows **19–153**, or 135 rows:

```text
per plane: source/destination offset 760, length 5,400 bytes
plane stride: 8,000 bytes
four-plane transfer: 21,600 bytes
```

Rows 150–153 are not fully cleared by the background loop. Seed those four rows from the
current chip back buffer before each render: 160 bytes per plane, **640 chip-read bytes**
in total. This preserves mask-operation inputs and untouched pixels in those rows when
the copy writes their entire width. Rows 19–149 are fully cleared on the observed path.
Rows above and below the transfer remain native, including the timer and much of the HUD.

This is a measured candidate extent for this view, not a universal rectangle. The first
correctness prototype should seed and compare a full 32,000-byte bitmap, record every
read/write outside the proposed rectangle, and shrink to the 21,600-byte transfer only
after the pixel checks pass. Reinitialization, camera/view changes and unusual effects
must either invalidate/reseed the fast image or select native rendering. Do not depend
on a one-time seed when alternating two native destinations.

### Why it may pay off

Through the last of 69 complete track renders, the measured background and span blocks
perform the following logical CPU data accesses to bitmap memory. This excludes instruction
fetches, edge tables, geometry, other drawing and DMA display fetches.

| Access | Bytes |
| --- | ---: |
| Background writes | 1,446,240 |
| Polygon destination writes | 1,122,642 |
| Polygon destination reads for AND/OR updates | 543,002 |
| Total | 3,111,884 |
| Mean per complete render | 45,099.8 |

The proposed partial transfer and tail seed use `(21,600 + 640) × 69 = 1,534,560` chip data
bytes for these operations, a **50.69% reduction** from the counted native traffic. The
rasterizer still performs its writes in fast RAM, and the copy must read that fast RAM.
This is not a halving of frame time, total bus traffic or CPU instruction count. It is a
reason to prototype on CPUs that can execute efficiently from fast RAM/cache and stream
stores to chip memory. Hardware bus widths and instruction implementation affect the result.

Use the measured break-even condition:

```text
T_native_scene > T_fast_scene + T_seed + T_fast_to_chip + T_wrapper + T_extra_sync
```

Measure each term at equivalent scene state and clock/cache settings. For scale, the
following are hypothetical transfer times, not measured Amiga bandwidths:

| Measured effective fast-to-chip copy bandwidth | 21,600-byte scene copy | 32,000-byte full copy |
| ---: | ---: | ---: |
| 1 MB/s | 21.60 ms | 32.00 ms |
| 2 MB/s | 10.80 ms | 16.00 ms |
| 4 MB/s | 5.40 ms | 8.00 ms |
| 8 MB/s | 2.70 ms | 4.00 ms |

MB means one million bytes here. Seed reads, wrapper and synchronization are additional.
At 25 presentations/s the partial copy alone writes 540 KB/s; at 50 it writes 1.08 MB/s.
Those are required payload rates, not guarantees that copies fit their deadlines. Avoid
claiming benefit from the A500 percentages or from nominal CPU MHz alone.

### Memory placement and cache safety

Prototype memory provision separately from rendering. The implemented interface-17 KickEmu build exposes 128 KiB of additional guest expansion
through `FASTMEMSIZE`; the original reconstructed slave remains available separately. Query the actual allocation size. Reserve
the guest fast pool before loading `pd`, retaining it as a private arena, so the unflagged
single game hunk does not silently move into fast RAM during the buffer-only experiment.
Suballocate the staging bitmap and audited scratch areas from this reservation. Do not
mistake an expansion allocation backed by slow memory for genuine fast RAM.

The initial budget should allow at least 128 KiB for a staging bitmap, guards, scratch,
verification state and later replacement code. VERIFY needs additional storage for reference
pixels and state snapshots. The exact header request includes KickEmu's own 256 KiB and
must be tested independently. Preserve the native 512 KiB chip pool, game allocator and DMA
assets. If the arena cannot be safely provided, leave rendering native. Memory configuration
and release compatibility are a separate commit from the rendering wrapper.
[WHDLoad memory and control API](https://www.whdload.de/docs/autodoc.html)

Next compare independently: fast scratch only, fast code only, fast bitmap only, and their
combinations. Do not blanket-change the game's chip allocator at `$5a32/$5a92`, or relocate
the entire mixed code/data hunk without auditing DMA references. Its private pool is shared
by bitmaps/assets and CPU data. The edge table referenced by game `$12` is an attractive
small fast-memory candidate after its size, lifetime and consumers are confirmed.

The polygon dispatcher rewrites branch displacement words at `$16080/$1608a` for each
polygon. Simply enabling an instruction cache risks stale code. Prefer replacing that
frequently modified dispatch with cache-safe static/indirect dispatch, then test its cost
on each CPU. Use cache flushes for installation-time changes; do not assume flushing the
whole cache per polygon is a performance solution. Keep DMA-visible chip data coherent.
Leave cache selection to the user through WHDLoad; do not configure CPU caches in the
game-specific patches.
[WHDLoad cache handling](https://www.whdload.de/docs/en/cache.html)

## Implementation stages and acceptance gates

### Stage 1 Establish timing and presentation baselines

Add a Practice presentation marker at the normal `$bc7c` path and separate departure/race
markers. Validate completed displayed frames using both trace events/screenshots and the
independent breakpoint counter; `$8056` alone also counts non-racing work. Repeat the full
500-field A500 capture across fresh boots. Add fixed-state scene fixtures for a simple
straight, a dense bend, close/clipped walls, and effects, plus a race with opponents.

Extend VERIFY logging to record VBL index, clock, raw/clamped delta, player position and
speed, orientation, control state, collision state, `state+$1ba`, RNG seed, opponent state,
draw/display identities and frame/update counters. Log in a preallocated ring and dump at
a stopped boundary; avoid per-frame disk writes. Tests for the existing route should
reproduce the 70 movement/render entries and 69 completed iterations established here.

Capture a 68020 Practice baseline and compare accelerated configurations below. Verify that
the original clock/delta path still runs once per presentation, including the time spent
in the final copy. Renderer equivalence tests use identical input state; end-to-end tests
allow the native elapsed-time logic to advance the scene at the new rendering cadence.

**Gate:** repeated baseline, validated display counter, measured clock behavior, known state
fields and the original/rebased-slave equivalence issue resolved or explicitly isolated.

### Stage 2 Provide fast memory and measure transfer cost

Provide a guarded memory configuration and reserve the private arena as described
above. Record actual code, scratch and bitmap memory placement in reports. Add a standalone
VERIFY copy benchmark inside the game display mode: native front-buffer DMA active, the
same waits, aligned source/destination and both warm and cold cache cases.

Compare a straightforward aligned longword loop and a register-block `MOVEM` copy. Add
CPU-specific alternatives only where they measure better. Benchmark 21,600 and 32,000 bytes,
as well as the 640-byte chip-to-fast seed. Measure wall time in PAL fields/finer available
timing and CPU costs within one backend; do not compare raw trace-cycle scales across CPUs.

**Gate:** proven memory type and bounds, clean fallback, no change to native allocation or
presentation when disabled, and measured copy/seed overhead by machine.

### Stage 3 Verify planar staging before tuning it

Implement the `$cee8` wrapper for the normal cockpit route only. Begin with conservative
full-image seeding/copying and guards. Redirect only the CPU scene destination and restore
it before post-render HUD/resource code. Add a diagnostic for any DMA operation referencing
fast memory or any rendering write outside the intended destination.

Compare the native and staged scene from identical pre-render inputs, including all planes,
untouched pixels, registers, condition codes and side effects. Running `$10df2` twice on
live state is unsafe because it changes counters/RNG and can trigger effects. Either save
and restore every audited dependency or twin smaller pure drawing blocks using identical
captured inputs. Keep physics/effects once-only. Vary preserved tail pixels deliberately to
catch stale-seed bugs.

Once equivalent, narrow to rows 19–153 with the 640-byte tail seed for the validated mode.
Measure the wrapper, fast renderer, seed and final copy separately, then together. The
conservative full-image prototype is a correctness baseline, not an expected winning mode.

**Gate:** pixel/state equivalence on all enabled paths and a repeatable end-to-end scene-time
reduction large enough to matter, initially at least 3%. Unsupported routes fall back before
any partial fast render. Exclude boundary-partial calls from per-call means.

### Stage 4 Optimize the remaining hot CPU loops

First move audited CPU-only edge/geometry scratch to fast RAM. Then implement and verify
cache-safe span dispatch and relocate replacement drawing code into fast memory. Measure
these separately from staging so their benefit is not incorrectly credited to the bitmap.

Prioritize span setup/writers (39.84% of A500 track cycles), then edge stepping (14.43%).
Investigate reusable endpoint/mask/address work, narrow versus wide spans and loop overhead.
The two fixed-point extraction shifts alone cost 3.44% on the A500; preserve negative-value
rounding and overflow semantics. Background filling is 8.45%; on the native chip route a
blitter-fill experiment is separate from the fast-RAM route, where CPU filling is required.
Completion-plan Phase D rejects the pipelined native-chip fill: 104/494 = 10.526 fps
versus 104/456 = 11.404 fps, with 3.88% higher mean frame-cycle cost. Its early display
wait consumes the clear saving; no blitter optimization is retained. See
[Phase D measurements](internals.md#phase-d-a500-measurements-and-decisions).

Keep geometry arithmetic/clipping changes behind separate switches. They are smaller than
the scanline work and require signed/overflow equivalence models. Keep planar bitmap
staging as the rendering architecture throughout these experiments.

**Gate:** exact loop twins and independent A/B benefit on each enabled machine class. Retain
the native path on CPUs where a replacement loses or gives no meaningful benefit.

### Stage 5 Preserve native simulation integration

Keep the native combined loop. Invoke the player/control/opponent updates exactly where
and as often as the original does. Call the scene renderer once, including its original
non-pixel side effects, then the post-render gameplay/HUD code and the single native
presentation. Preserve `$7f7a`'s elapsed-time sampling and 8–50 clamp. Include staging/copy
time in the normal elapsed interval; do not replace it with a constant delta or compensate
for the copy by artificially changing the game clock.

At matched pre-render state, the staged and native render paths must produce the same
non-pixel state changes and consume the same gameplay random values. At full speed, compare
control operation, timed movement, resources and collisions through ordinary gameplay, but
do not demand identical per-field positions from builds that render at different rates.
Different trajectories from the game's existing update-frequency dependencies are not a
reason to add a new scheduler to this rendering patch.

**Gate:** original timing path and update counts remain structurally intact; no duplicated
simulation/effect calls from verification wrappers, no extra buffer exchanges, and no
accidental clock changes. No new physics scheduler, timestep policy or frame cap is planned.

### Stage 6 Choose defaults and release coverage

Use developer switches for memory placement, staging, each loop replacement
and copy extent. The shipping choice should be a simple acceleration option or automatic
selection among verified paths, with clean native fallback. CPU type alone is insufficient:
require genuine fast RAM, supported view/state and measured benefit. Cache selection belongs
to standard WHDLoad user options; do not add a game-specific cache policy.
Do not dynamically benchmark during play or add simulation steps when switching a
renderer. Test option-off byte/state equivalence and allocation failure explicitly.

| Configuration | Purpose and initial expectation |
| --- | --- |
| 68000, original chip/slow setup | Compatibility reference; native rendering remains the default |
| 68020 with chip RAM only | Measure loop/cache work; staging is unavailable |
| 68020 with genuine fast RAM | First feasibility test; copy overhead may erase savings |
| 68030 with fast RAM | Test CPU-local code/data and cache effects; staging is a strong candidate |
| 68040/68060 with fast RAM | Measure CPU/copy costs in the emulator; physical-board validation is outside scope |

For every supported class record displayed FPS, simulation ticks/s, frame-time distribution,
completed scene cost, copy/seed cost, memory use, state/pixel comparisons and enabled options.
Use the title demo as a separate rendering fixture, not as simulation validation. Require
longer gameplay sessions covering pit re-entry, restarts, pause, all views, opponents,
collisions and effects before widening the accelerated path. Emulator traces establish
where work goes; the acceleration option remains off by default. The completed
[coverage campaign](gameplay-coverage.md) passes 30,623 staged twins with observed native
view/effect fallbacks. Its bounded routes do not justify widening those guards.

## Recommended first implementation batch

Implement Stages 1–3 as the first batch: validated Practice timing, explicit fast-memory
provision and a guarded planar staging prototype. Its deliverable is a measured yes/no
answer per CPU configuration with exact pixel checks and separately timed copy cost.
Follow with scratch/code placement and cache-safe dispatch. Preserve the existing
elapsed-time simulation throughout.

Reproduce the added read-only analysis without launching the emulator:

```sh
python3 tools/analyze_pipeline.py tmp/prof/practice-continuous-10s \
  > tmp/prof/practice-continuous-10s/pipeline.json
```
