# OCS implementation plan — phase 13 investigation complete

Phase 13 delivers this plan and the [static evidence](internals.md#phase-13-ocs-static-investigation).
It does not implement or validate an improved OCS slave. **P13A1 is complete**;
the remaining work items below are pending, in dependency order. Further work needs a subsequent goal;
CD32 E1 and phase 12 remain paused. The supplied English executable is the first
supported target; unavailable revisions and German must not inherit its patches.

## Design decisions and unresolved choices

- Retain native four-plane blitter C2P as a supported candidate. Its DMA source
  must remain in Chip RAM. Do not replace it simply because a CPU converter exists.
- Provide a genuinely 68000-safe CPU candidate. For the CPU backend, start with
  Kalms' four-plane word-write routine on 68000/68010 and longword-write routine
  on 68020+. This is a candidate policy, not a measured performance result.
- Select **blitter versus CPU** using measured CPU/memory profiles, independently
  of the word/longword choice inside the CPU backend. A 68020 with no true Fast
  RAM may still favour blitter conversion. The crossover is not established.
- Retain Chip RAM chunky storage for the blitter path. Move only audited CPU-only
  surfaces to true Fast RAM for a CPU path. A Fast-to-Chip staging copy is a third
  candidate only if measurements justify it; account for the entire copy.
- Share timing, prediction, input-history semantics, ownership rules and test
  machinery with CD32. Keep variant addresses, native ABIs, assets, loader,
  palette/depth, hardware publication and scene definitions separate.
- Target 10 Hz authoritative updates for OCS gameplay and its world-based intro,
  with renderer-only extrapolation between ticks. Confirm the native OCS units
  and event ownership before enabling it. Extra pictures depend on available CPU
  time; there is no unmeasured 25/50 FPS promise for an Amiga 500.
- Amiga 500 with 512 KiB Chip RAM and true Fast RAM is the required baseline.
  Start development with a nominated 4 MiB Fast configuration, then measure and
  document the actual minimum, including WHDLoad/preload overhead. This is a test
  target, not a claim that the finished install fits it. Do not quietly require
  more Chip RAM. No-Fast accelerated configurations are comparison/fallback cases,
  not a relaxation of the required A500/Fast target.

## A — Establish a trustworthy OCS baseline

**P13A1 — Reconstruct the supplied OCS slave (complete).**
Use the pinned install and installer, reconstruct into `tmp/`, and require
byte-for-byte equality with the original 5,324-byte slave before adding hooks.
Preserve its Kickstart 1.3, relocation, cache, language, cheat and start-mission
behaviour. Decode all three revision selectors, but implement enhanced hooks only
for the verified English CRC `00e8`, guarded by SHA and displaced bytes.
Deliverable: reproducible OCS reconstruction and negative revision checks.
Gate passed: identical original bytes; unexpected input rejected without modifying it.
See [results and limits](internals.md#p13a1-byte-identical-ocs-reconstruction) and
[commands](development.md#p13a1-ocs-slave-reconstruction).

**P13A2 — Finish the native display and allocation contract.** Depends on A1.
Trace each QBlit phase, completion flag, source lifetime, plane pointer, row
padding, buffer transition and direct planar writer from the offsets in the
internals notes. Establish pixel nibble/bit order from distinct-colour fixtures
and the native converter; do not infer it from an almost-black intro frame.
Inventory allocation sizes, memory flags, consumers and free paths. Distinguish
the two display buffers from the third, shared conversion workspace.
Gate: native output is reproduced by an independent pixel oracle, and every
DMA-read source has a named owner and safe release point.

**P13A3 — Add the OCS launcher and live-layout discovery.** Depends on A1.
Make install selection explicit in setup, runtime inputs and launcher; keep OCS
and CD32 files separate. Supply the A500 Kickstart/RTB through existing user-input
conventions. Discover OCS hunks and A4 from their own signatures/relocations.
Boot original and reconstructed slaves on a 68000/OCS machine with 512 KiB Chip
and true Fast RAM; compare intro, menu and simulator/name-prompt endpoints.
Gate: matching native state/pixels, working controls and project-owned cleanup.
Do not treat selecting an A500 preset in the current CD32 launcher as OCS support.

**P13A4 — Measure the short native baseline.** Depends on A2–A3.
Use one repeatable intro/asteroid window and one flight/fire window, with a turn
only if it materially changes costs. Record displayed pictures/s and interval
percentiles, completed world updates/s, drawing, conversion submission-to-completion,
CPU waiting, publication delay, source-change fraction and Chip/Fast high-water
usage. Separate conversion service time from waits inserted by the native queue.
Gate: recorder/independent display-counter agreement and observer-off state/pixel
agreement. Label emulator results; do not borrow CD32 or sibling performance.

## B — Share mechanisms without imposing a newer CPU

**P13B1 — Extract compile-time variant definitions.** Depends on A1–A2.
Introduce separate OCS/CD32 maps for hooks, relocated hunks, native entry points,
A4 fields, object limits, bitmap layout and scene rules. Extract shared algorithms
incrementally; avoid runtime variant branches in hot loops. Extend build and
analysis tools to accept an explicit variant instead of silently using CD32.
Gate: unchanged CD32 output where possible; otherwise equal-size native controls
and the existing focused timing/pixel checks. Original OCS reconstruction remains
identical. Do not fold this refactor into an unreviewable OCS patch dump.

**P13B2 — Make shared execution paths 68000-safe.** Depends on B1.
Replace or select alternatives for long multiply/divide, scaled indexing, long
branches and flag preservation. `MOVE CCR` is unavailable on 68000; indiscriminate
`MOVE SR` is not a safe replacement on later CPUs in user mode. Audit startup,
interrupts, exceptional exits and diagnostics as well as hot code. Reuse native
math only after signedness, overflow, rounding and register contracts are tested.
Gate: base-ISA assembly plus executed arithmetic/flag boundary tests on 68000,
and unchanged results on 68020+. Keep accelerated implementations where useful.

**P13B3 — Share instrumentation and validation interfaces.** Depends on B2, A4.
Port the frame-statistics schema with a 68000-safe recorder and OCS publication
observer. Add variant-aware native state/pixel, allocation and ownership checks.
Gate: separate counts for world ticks, rendered pictures and actually displayed
pictures; bounded observer overhead and a working uninstrumented control.

## C — Choose conversion from measured CPU and memory behaviour

**P13C1 — Build interchangeable experimental converters.** Depends on A2, B2–B3.
Keep native QBlit conversion. Pin and adapt the two Kalms four-plane candidates
listed in `manifest/ocs-c2p-candidates.tsv`; honour width/alignment/stride, plane
order and destination padding. Cover every native view size with enclosing-window
or native fallbacks where necessary. Do not copy Legends of Valour's high-nibble
or 192-byte-stride modifications into Wing Commander.
Gate: native-versus-independent-oracle-versus-CPU pixels match with all 16 colours,
nonzero unused nibbles, edge widths, row canaries and alternating destinations.
Experimental CPU conversion does not become the default yet.

**P13C2 — Establish the blitter/CPU/memory crossover.** Depends on C1.
Run matched short windows with identical source content, world state, display DMA,
audio, buffer ownership and publication policy. Compare these arms:

| Arm | Drawing/source storage | Conversion |
|---|---|---|
| Native | Chip RAM | Native blitter, including all queue waits |
| CPU/Chip | Chip RAM | CPU word/longword candidate |
| CPU/Fast | Verified true Fast RAM | CPU candidate into Chip planes |
| Staged, only if useful | Fast RAM plus Chip staging source | Copy plus native blitter |

Start with 68000/OCS plus Fast RAM, 68000 without true Fast RAM if the stock memory
requirements can be met, 68020/OCS without true Fast RAM, and the same 68020 with
Fast RAM. A no-Fast test that cannot boot is an unsupported memory case, not a
conversion result. Use representative 7 MHz 68000 and documented 68020 clocks;
expand to another clock/memory width or 030 only where the winner changes or the
margin is inconclusive. Distinguish slow expansion RAM from true Fast RAM using
actual allocation addresses/attributes, not an emulator preset's label.

Measure end-to-end displayed frames/s and frame tails as well as conversion time,
CPU draw/world time, CPU/blitter overlap, queue stalls and Chip bus contention.
First preserve native scheduling; isolate unnecessary native pacing only in a
separate arm. An isolated blitter throughput result cannot choose the backend.
Deliverable: a small CPU/clock/memory/backend table, reproducible runs, and an
explicit crossover range or uncertainty. Gate: retain blitter wherever it wins;
no claim of a universal CPU threshold from one emulator configuration. Do not
require a broad calibrated-040 matrix to finish this decision.

**P13C3 — Install conservative backend selection and fallback.** Depends on C2.
Select once from measured CPU/memory profiles, retain a user override for unknown
accelerators, and fall back safely when the required memory is unavailable.
Within the CPU backend select the tested word-write 68000/68010 and longword-write
68020+ paths, unless C2 establishes a better rule. CPU capability and chipset are
independent: an accelerated OCS machine still needs four-plane OCS output.
Gate: forced and automatic choices select the same tested path; unsupported
profiles keep a safe native option. Preserve cache policy and flush patched code.

**P13C4 — Apply backend-specific memory ownership.** Depends on C3.
For blitter conversion retain its Chip source and shared workspace, with waits
before reuse. For CPU conversion move only proven CPU-only source/work buffers
to Fast RAM and bypass all obsolete QBlit consumers before reclaiming workspace.
Keep planes, Copper lists and every remaining DMA consumer in Chip RAM. Account
for histories, prediction snapshots, code, ROM and preload in the memory budget.
Gate: allocation failure/partial setup/exit work on both backends, no stale DMA
reads, and the documented A500 minimum follows measurements. A staging backend,
if selected, retains both source lifetimes through the final asynchronous read.

**P13C5 — Publish completed images safely on both backends.** Depends on C4.
Share the pending/drawing/displayed ownership model with CD32 while retaining
OCS-specific completion events, Copper setup and publication deadline. Verify
blitter completion before publishing or reusing its source; CPU completion alone
does not certify a blitter frame. Preserve native direct-plane updates and view
transitions. Do not copy CD32 FMODE or its scanline deadline.
Gate: no tearing, old rows or mixed frames across intro, view changes and flight;
actual display fields agree with ownership and forecast records.

**P13C6 — Evaluate changed-block conversion only where it helps.** Depends on C5.
Measure comparison/history cost against full CPU conversion and retained blitter
conversion. Include both destination histories and invalidations for direct
planar writes, palettes, clears, resizing and modal transitions. Keep a full or
native path when comparison is slower or costs too much memory on 68000.
Gate: identical pixels and an end-to-end improvement on the selected profile.
Otherwise close this item with the simpler backend and documented measurements.

## D — Share the gameplay and intro timing model

**P13D1 — Complete the OCS timing/side-effect map.** Depends on A3–A4, B1.
Map the CD32 FR-01–FR-23 responsibilities to actual OCS functions and state fields.
Verify speed/range units, field clock, input ownership, audio and every world- or
render-driven timer. Include damage, AI, weapons, explosions, random calls,
simulator score/death/name entry, autopilot, menus and scene resets.
Gate: every responsibility has an OCS owner and executable test or a named
excluded scene; analogous code is not accepted as proof of an identical ABI.

**P13D2 — Port the shared 10 Hz authoritative clock.** Depends on D1, B2–B3.
Preserve native OCS units while separating world updates from presentation.
Count completed ticks, handle PAL/NTSC fractions, bounded catch-up and modal
rebasing. Test slow-frame and wraparound cases. If the A500 cannot sustain the
world budget, report the overload and optimise the measured cause; do not silently
change game speed or describe skipped simulation as correct timing.
Gate: equal elapsed-time world/event results at deliberately varied render rates,
plus measured normal-load world cadence on the required A500 target.

**P13D3 — Port responsive input and renderer-only prediction.** Depends on D2, C5.
Reuse player/camera and world-pose algorithms, native inertia and selective
backup/restore with OCS field definitions and 68000-safe arithmetic. Predict to
the actual backend's publication time, including pending work. Carry over the
new-projectile constructor certificates and the gun-cooldown/reset distinction
for all native player/AI spawning paths. Do not invent motion before identity is
known or let presentation consume authoritative randomness/allocations.
Gate: world state restores exactly, first-interval shots move, slot reuse and
view cuts reject stale history, and prediction stays within the shared bound.
Measure overhead on 68000; avoid useless extrapolation work when no intermediate
picture can be displayed without changing authoritative simulation policy.

**P13D4 — Apply the same model to the OCS world-based intro.** Depends on D3.
Port the shared title/asteroid world clock and prediction with OCS script data:
296 title updates, 15 credit pages, and native text/music deadlines. Move
render-side asteroid creation to its authoritative owner so credits retain visible
asteroids even when world ticks suppress drawing. Map any other cinematic route
separately; do not assume the Origin logo or ending uses this intro path.
Gate: short motion/state checks plus one full 15-page cycle and repeat, correct
asteroid visibility, native music/credit pacing, and clean transition to gameplay.

## E — Focused acceptance and hand-off

**P13E1 — Close measured A500 bottlenecks.** Depends on C6, D4.
Profile the remaining world/drawing/composition/conversion cost and optimise only
what prevents the accepted A500 timing or selected backend from working. Retain
shared optimisations where their cost pays off; do not impose cached-030 region
copying or full-image comparison on a 68000 without evidence.
Gate: report displayed frames/s, interval tails, world cadence and memory on the
required A500/Fast target and representative 020/Fast configuration. Document
heavy-scene gaps instead of promising CD32 smoothness on a 7 MHz CPU.

**P13E2 — Complete compatibility and functional checks.** Depends on E1.
Exercise native-blitter and CPU backends on 68000/OCS and 68020/OCS, then a short
accelerated AGA/cache-enabled regression and PAL/NTSC checks. Cover intro, combat,
all views, controls, save/load, pause/resume, simulator/name prompt, repeated scene
changes, quit and low-memory fallback. Retest shared CD32 code with its existing
focused gates. Unavailable languages/revisions remain explicitly unsupported by
enhancements, with original behaviour or a clear rejection instead of blind hooks.
Gate: pixels/ownership/state pass, options have defined semantics, no expanded
hardware matrix without a failure that needs it. Real hardware feedback is useful
when available and is labelled separately from model evidence.

**P13E3 — Document support and prepare the later release hand-off.** Depends on E2.
Record supported revisions, CPU/memory/backend selection, minimum RAM, options,
reproducible checks and remaining gaps. Keep OCS and CD32 installers distinct;
share packaging machinery, never game assets. Propose the preinstalled archive
and release checklist for a subsequent authorised release step. Do not implicitly
resume the paused CD32 phase 12 work or restore its save/load stash.
Gate: a reviewable OCS candidate and an explicit support/limitations table.

## Next gate

P13A1 is complete. Start **P13A2** only when requested. The first backend decision
is **P13C2**, not the current investigation. In particular, neither “68000 must use
CPU C2P” nor “68020 must abandon the blitter” has been established. Keep the
blitter implementation available through the comparison and acceptance gates.
