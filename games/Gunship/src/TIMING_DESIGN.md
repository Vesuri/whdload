# Gunship hybrid timing design

This describes the 2.0b (21.10.2026) hybrid timing implementation.
[PERFORMANCE_PLAN.md](PERFORMANCE_PLAN.md), section C's refocus, defines release
acceptance. C-R1 and C-R2 are complete; C-R3–C-R5 remain open. C is not complete.
Implementation history and superseded experiments are in git.

## Activation and scope

**Enhanced framerate** is the default-off CUSTOM1 boolean. The slave ignores
it below 68020. Every framerate patch, including blitter changes, shares that
gate; existing baseline compatibility and protection fixes remain baseline.
The release build includes the hybrid flight loop. `Gunship.slave` selects
0658 offsets; `GunshipNTSC.slave` selects 1489 offsets (`GUNSHIP_NTSC`). Both
compile the same implementation with `timing-offsets.i`; the installer selects
the slave by executable release, independently of display frequency.
CUSTOM1=0 retains native timing. Other recognized executables retain native
timing and are explicitly untested for this beta. `GUNSHIP_NATIVE` permits a
small native-only regression build. CUSTOM4 chooses CPU (0, default) or native
blitter (1) rendering, subordinate to CUSTOM1 and the 68020 CPU gate.

`timing-slave.i` resolves loaded hunks, reads the display's 50/60 Hz frequency,
allocates/prepares the runtime, and installs the flight entry hook last.
Prepared native code is signature-checked; the loader's cache flush covers it.
The arena is 30,436 bytes for 0658 and 30,428 for 1489; each release slave
has 49,840 bytes of text (49,876-byte hunk executable).
The CPU renderer separately allocates 36,010 bytes of fast RAM: 18,000 for
the view and 18,010 for cached cockpit artwork and its mask.
`timing-core.i` defines the included implementation. Exact guided forecast,
selector certification and forecast tapes are absent from runtime inclusion
and allocation; historical helper files still present are not active paths.

## Timing and state ownership

| Owner | Cadence | Responsibilities |
|---|---|---|
| Input producer | Each active display field | Filtered controls, buttons/edges, accepted keyboard command positions and RNG input-event timestamp |
| Player consumer | Each retained field | Responsive attitude, heading, speed, position and derived flight quantities |
| World | Three deadlines per second | Native AI, launch, damage, contact, reserves, mission clock, RNG and discrete effects |
| Field gameplay | Each consumed field | Native countdowns, guidance progression, effect animation, gauge slew and map coordinates |
| Renderer | As often as drawing allows | Current player camera/instruments, bounded world-object prediction, buffer repaint and aiming graphics |

The VBL is a producer, not the player integrator. The foreground consumes its
history in order, so input arriving during a long draw is not collapsed into
one sample. Hardware/display duties remain in the VBL; gameplay bytes owned
by the consumer are excluded from the native VBL path while enhanced flight
owns them. Drawing cannot advance gameplay RNG, effect lifetime or targeting.

## Clock, input and foreground loop (C1–C3, C8)

`timing-clock.i` adds three units per active field and consumes 50 or 60 units
per world deadline. PAL intervals repeat 17/17/16 fields; NTSC uses 20.
The display frequency, not executable region, selects the schedule. The native
elapsed-time conversion still divides the world tick counter by three.

`timing-history.i` holds 128 records of 40 bytes in a bounded ring (5,140
bytes including its header). The interrupt producer publishes only complete
records; the consumer copies a record before releasing its slot. Full history
preserves unread records and reports loss. Duplicate/missing stamps latch
faults. `timing-live-input.i` supplies the native capture hooks. The command
queue has separate player and world acknowledgements, so an accepted command
is not lost or applied twice when its effects have different owners.

The foreground path is `timing-live-loop.i` → `timing-runtime-loop.i` →
`timing-runtime-batch.i` / `timing-flight-consumer.i`. It processes ordered
commands and player fields, completes each due world before later fields,
and draws only at a valid presentation boundary. A fresh snapshot catches
fields arriving during world work before drawing. At most four world updates
are caught up between draws; exhausting that allowance yields with pending
history and phase retained. Oversized snapshots use explicit, accounted
excess recovery, not silent time loss on ordinary slow frames.

Lifecycle transitions exclude producers while changing queue/clock ownership.
Native pause, display/menu boundaries and script modal continuations suspend
sampling; resumption rebases phase, fractions, delayed controls, interval
anchor and preview cache so paused time creates no simulation debt. Retained
boundary work completes or cancels once. Flight end retires prediction and
player history and returns to native cleanup. A failed enhanced transaction
aborts rather than falling into the old tick loop with partly applied effects.
The existing map display still receives field-owned coordinate refreshes.

## Player motion and world hand-off (C4–C5)

The field/writer classification lives in
[PLAYER_STATE_INVENTORY.md](PLAYER_STATE_INVENTORY.md). Its earlier standalone
checkpoints are historical; the installed ownership is described here and in
`timing-core.i`. Motion is implemented by `timing-endpoint-player.i`,
`timing-endpoint-motion.i` and `timing-scheduled-endpoint.i`, with native
arithmetic prepared by `timing-motion-preview.i` / `timing-motion-stages.i`.

At the beginning of an interval the owner anchors the continuous player state.
Each field previews a native motion contribution using that anchor and fresh
controls/current non-motion inputs, then distributes the contribution across
the actual 16/17/20-field interval. Fractional shadow values preserve native
rounding, saturation and wrap. A complete held-input interval reproduces the
native endpoint, including displacement, except for the intentional enhanced-mode
bank-rounding correction below. A press/release within the interval
contributes immediately; its result need not equal a native tick which never
sampled that input. This is not delayed interpolation between world poses.

`timing-player-cache.i` caches pure native previews by their complete inputs;
it does not cache authoritative player state. The endpoint owner commits
motion only after the candidate succeeds. Delayed-control history preserves
the native previous-control time horizon. World-generated random impulses
are retained once for their deadline and applied with native boundary order;
field previews do not draw new gameplay RNG.

Ground/contact effects, collision, flight-end decisions and discrete player
state remain world-owned. The world reads the latest field result and does
not integrate the same motion again. The scheduled world opening, weapons,
damage, script, reserves and tail wrappers run the native discrete work once
per deadline. Weapon triggers retain both edges and held fire, but launches
use the next world tick's pose: the selected C5c option (a), up to 333 ms.

The native deferred destroyed-target result at hunk 0 +C756 is consumed by
`timing-world-start.i` before the next weapon update can clear it. The copied
+05874..+05884 bridge calls native +07CB2, preserving removal, mission
bookkeeping and notification. This fixes explosions without target removal;
missile strength is unchanged. All offsets here refer to 0658.

## Committed geometry and drawing (C5d, C6–C7)

Target selection and player contact use committed geometry at world deadlines.
`timing-scene-private.i`, `timing-scene-target.i` and the scheduled world scene
path share native geometry work. An empty candidate view skips the additional
visibility raster only when no projectile, scripted helicopter or pending-fire
terrain-pixel consumer needs it. Otherwise the committed native raster remains.
Renderer-side capture follows the world-selected target identity in the current
view; panel drawing borrows its projected coordinates and restores committed
targeting afterward. Rendering cannot commit a new target, lock or hit.

`timing-runtime-actors.i` captures completed world poses. The six shared actor
slots use `timing-actor-present.i`; the scripted helicopter uses
`timing-script-present.i`. Prediction extends the last consecutive committed
displacement by a fraction bounded to one tick. First captures, changed
allocation generations, types, lifetime/impact state or lifecycle discontinuities
snap instead. A guided-release cache anchors the first release fraction without
re-anchoring unrelated actors. Predicted coordinates and scripted heading are
renderer-only; they never feed world collision, targeting or RNG. There is no
speculative future-world execution. Visible prediction defects should be
judged in play; G is the later fallback if needed.

`timing-runtime-present.i` builds the latest player camera and instruments,
then publishes one native frame through the guarded render handoff. Gauges
slew per consumed field; needles derive directly from current instrument
angles. Per-buffer saved backgrounds and two-buffer repaint counters remain
drawing-owned. Negative vertical speed at zero height displays as zero to
prevent the grounded needle jitter; positive lift and airborne readings keep
native conversion, and physics is unchanged.

Damage-induced yaw is the one deliberate camera easing: only the retained
random tail-rotor heading impulse is spread over the full following world
interval: 16/17 PAL fields or 20 NTSC fields. The previous half-tick easing
caused a repeated turn/pause; recovering the phase at the impulse stamp makes
the new ramp meet the next deadline without an extra boundary jump. Only
the damage contribution is spread: normal steering uses the latest field
pose immediately. Gameplay heading, targeting, collision and RNG are unchanged.
Assembled PAL/NTSC checks cover 350 field cases and 350 same-field steering
responses, plus 17 consecutive intervals per release with reversals and zero
impulses. For maximum damage impulses, observed per-field camera increments
are at most 32/26 angle units (about 0.176/0.143 degrees); no half-tick stops
remain. Grounded/repaired/invalid/stale samples leave the camera alone.
Evidence: `tmp/dev/tools/test_damage_rotation.py` (ignored harness). Visual
confirmation in damaged-tail play remains part of C-R4/C-R5; fewer completed
frames under host CPU starvation still reduce the visible sampling rate.
Enhanced heading now divides signed bank by four towards zero. Native
+0943A floors negative banks: +1..+3 produce zero turn but -1..-3 produce -1.
`heading_step` removes that left bias in its replacement heading/track
calculation; positive banks and exact multiples of four are unchanged. This
is an intentional handling correction authorized after beta play-testing,
not a camera adjustment. CUSTOM1=0 retains native handling. Both release
binaries pass 1,536 assembled heading cases each, plus 651 PAL and 780 NTSC
field updates through small-bank reversals without heading/track drift.
Evidence: ignored `tmp/dev/tools/test_left_drift.py`.

Effect construction belongs to world deadlines; countdown/animation and slot
release progression belong to consumed fields. Native speed-toggle command
12 is acknowledged without changing enhanced cadence or resetting phase.
Map refresh follows player fields, while bitmap/sprite repaint stays with
native display work.

## Blitter ownership and 68040 correctness

D1 is implemented in the enhanced flight ownership wrappers. After native
OwnBlitter and WaitBlit, only BLIT interrupts are masked. The incoming BLIT
enable is restored before DisownBlitter, including modal/exit handoffs; other
interrupt sources are untouched. Native calls contain no QBlit/QBSBlit use.

`blitter.i` also makes module BltClear calls wait before their buffers are
reused. The former asynchronous clear raced LZW dictionary use and caused
68040 corruption; full-MMU/CACHE startup and flight pass with the fix. It
is not necessary to disable MMU or CACHE for that issue. See
[CACHE_AUDIT.md](CACHE_AUDIT.md) for cache details.

## View drawing and display exchange (D2–D5, E1–E3)

`timing-display.i` replaces only the enhanced flight swap at +044B4.
The task waits for the last blit, finds the current copper list's ten BPLxPT
moves, copies the selected bitmap into Screen.BitMap, and publishes the new
plane pointers. The game's VBL server exchanges those words and acknowledges
completion before the task may reuse the old front buffer. Submission returns
immediately; bitmap binding waits only if an exchange is still pending. Native
swaps and DisownBlitter drain pending work before handing back ownership. VERIFY
logs VBL exchanges rather than task submissions. D4 is closed by user decision:
retain double buffering. FrontScreen waiting yields through WaitTOF.
Native/modal paths still rebuild their screen normally.
Palette moves and the flash-effect pointers found by +00AB8 stay intact;
there is no unchanged per-frame palette copy or MakeScreen/RethinkDisplay.
The VBL restores COLOR00 from the selected bitmap's saved palette when the
field-owned hit timer (+4296) is zero. This replaces the restoration formerly
provided by native palette rebuilds, preventing the last red/orange damage
flash from persisting. Active flashes, native/modal ownership and retained
boundaries are untouched; both native copper colour orders are supported.
Restoration also runs without a pending frame and writes only on a mismatch.
The shared hook applies to both renderer choices. Assembled PAL/NTSC checks
cover 384 combinations of ownership, timer, bitmap, colour and copper order
(`tmp/dev/tools/test_damage_colour.py`, ignored harness). Full-MMU 040 CACHE
startup succeeds. Debugger-triggered hit attempts did not produce a flash,
so they do not establish live flash/expiry acceptance; that remains a
play-test check.

`timing-cpu-render.i` is installed only for enhanced 0658/1489 flight when an
36,010-byte MEMF_FAST allocation succeeds; failure retains the blitter path.
Native geometry, clipping and edge-to-span tables are reused. The CPU draws
320×90 pixels into five contiguous fast-RAM planes: lines select an unrolled
four/five-plane pen routine once, polygons fill spans directly without a mask,
and sky/ground bands use MOVEM. Native polygon right-edge word rounding is
retained for pixel equality, including its word-aligned endpoint quirk.

The horizon routine also draws the attitude instrument below the view. Those
primitives keep their native chip/blitter path; the mask is cleared after a
native polygon, not for every CPU polygon. The five completed view planes are copied once to the chip back buffer,
clipped/composed at the cockpit edges as described below. Subsequent native
effects and cockpit work retain their ordering.
The fast buffer is freed with the timing runtime. Compatibility blitter hooks
are installed first so native trampolines retain their corrected pixel waits;
the existing LoadSeg cache flush covers the prepared hooks and trampolines.

A same-state diagnostic rerender compared all five CPU planes with the real
blitter on 163 takeoff/banking frames: zero differing words. Allocation and
no-fast-memory fallback checks passed. Full-MMU 68040 with CACHE passed normal
startup and takeoff. The native-only build was unchanged by that renderer change.

The existing 500-field PAL window reports 11.7 fps on a1200-fast and 25.0 fps
on a1200-060, each with 30 world ticks (3.00 Hz). Input-to-next-completed-frame
samples are 20–80 ms (median 60) and 20 ms respectively; these timestamps do
not prove visible response or scanout latency. Evidence is under ignored
`tmp/dev/tmp/step7-e1-{pixels3,fps020,fps060,040-cache}/`; D2's short profile is
in `step7-d2-profile/`. This completed refocus step 7; later release-item status is in PERFORMANCE_PLAN.md.

## Demo playback and input semantics (C-R1, C3d)

The unattended demo uses a tick-indexed recorded input tape. At flight entry,
`timing-live-loop.i` checks the native playback byte (hunk 6 +45CC == 1)
and dispatches that flight to the original +0563A loop (mapped for NTSC).
This preserves the tape reader, native control decoder and any-key exit.
It deliberately keeps the demo's original frame-dependent timing. Ordinary
play still enters the enhanced field-history loop and its 3 Hz world clock.
No owner is activated for playback: the shared input, display, effect and
renderer hooks retain their existing native paths. This is an entry-time
choice, never recovery from a partly executed enhanced transaction.

Normal-startup a1200-fast checks with current PAL and NTSC release slaves,
CUSTOM1 off/on, observe 1,000 fields without input, then inject Space.
Both enhanced demos fly, advance their tapes and return to the vehicle
identification screen. The PAL enhanced window advances 104 ticks and 116
tape bytes; native advances 84 ticks and 96 bytes. NTSC enhanced advances
82 ticks and 92 bytes; native advances 77 ticks and 76 bytes. These are demo progression checks, not 3 Hz gameplay
measurements. Evidence: `tmp/dev/tmp/demo-fix-{pal,ntsc}-{off,on}/`.
The production-entry check also covers demo-to-ordinary-play selection and
register/stack preservation in both releases.

C3d retains the original sampler before publishing field history: native
mouse filtering and input-mode selection are not reimplemented. The consumer
uses the sampled low-byte directions, not accumulated raw mouse deltas.
Accepted command words retain modifier bits and FIFO order, with separate
player/world acknowledgements. Native pause/menu handlers keep ownership
while enhanced sampling is suspended. Existing production-binary checks
cover sampler ABI, direction decoding, command classification, target changes,
engine-mode ordering, queue ownership and retained boundaries. The bounded
checks use 222 native target comparisons, all 41 native command words, 48
engine-mode tapes and 16 queue-dispatch tapes per release; the native sampler
ABI check has 452 cases. Direction/command differential tests use the shared
PAL decoder as reference; sampler installation checks use each release's own
executable. They do not claim full-mission or visible-input acceptance.
The intentional enhanced-mode exceptions remain: field-rate control response,
weapons at the next world tick, and the obsolete speed-toggle key has no speed
effect. Demo playback now uses the original filtering/command path in full.

## Evidence and remaining acceptance

The step 3 normal-startup comparison used one run per CPU/toggle, the same
binary and 500-field PAL control window. Native/enhanced fps were 10.4/11.5
on a1200-fast and 16.3/16.7 on a1200-060. Enhanced world spacing estimated
3.008/3.012 Hz. Input-to-next-completion medians were 60/40 ms (ranges 20–80 /
20–60 ms). Those timestamps do not prove visible response, and the short PAL
windows alone did not establish PAL/NTSC world-rate acceptance. The F release
checks now measure 3.00 Hz on 020/060 with both PAL and NTSC executables.
Native and enhanced control routes also reach different world states because
native simulation runs faster. Full-mission acceptance remains a user check.

Existing checks show held-input native endpoints. Targeted fix checks include
768 ground-instrument comparisons and 100 live grounded samples; 220 damage-yaw
camera cases plus 1,792 angle cases and 40 live draw samples; and 560 world
opening checks plus 90 native target-removal comparisons and a live pending-hit
probe. The last probe clears the target's alive bit; it does not replay the
user's exact Bradley/BMP-1 attacks. These checks do not substitute for C-R4/R5.

Retained local evidence is ignored under `tmp/dev/`, not shipped in git:

| Purpose | Path under `tmp/dev/tmp/c/` |
|---|---|
| Step 3 fps/rate/completion | `refocus-step3-d1-{a1200-fast,a1200-060}/`, matching `refocus-step3-d1-off-*` |
| Pause/exit and BLIT restoration | `refocus-step3-d1-pause-exit/` |
| Grounded needle | `ground-gauge-{before,after}/gauge.json` |
| Damage yaw | `step4-damage-yaw-live/damage-yaw.json` |
| Deferred target removal | `step4-pending-kill-live/kill.json` |
| Original demo regression | `step5-demo-{native,enhanced}/`: `demo.json`, start/end/exit screenshots |
| Demo fix and input regression | `demo-fix-{pal,ntsc}-{off,on}/`, `c3d-release-checks.log`; tools `check_demo_fix.py`, `test_demo_owner.py`, `check_c3d_release.py` |

The original step-5 demo JSON's `demo` field reads an unrelated offset and is not evidence;
use tape progress, player state and screenshots. The user's matching screenshot
is `tmp/dev/tmp/play-a1200-040/.run/shots/FS-UAE_Full_261021-1356_00.png`.

For release builds, run `source/build.sh` with the shared AmigaXDev toolchain.
It writes `Gunship.slave` and `GunshipNTSC.slave` under the ignored
`tmp/dev/tmp/build/release/`; `BUILD_DIR` overrides that destination. Ship both
slaves with the updated Install/ReadMe and the original package's manual and
icons. No game files, ROMs or generated binaries belong in git. VERIFY builds
are diagnostics, not distribution files; the older verifier targets 0658.

For an existing measurement rerun, the harness builds with VERIFY=1 and
TIMING_RUNTIME=1; `REFOCUS=1 MACHINE=<machine> CUSTOM1=<0|1> SLAVE=<built-slave>`
selects the existing `tools/fps.py <out>` comparison under its environment.
Use separate run directories and exclude host input. Debugger guest-memory
writes are unsupported by the shared harness; previous guest probes were
compiled diagnostics, not play-build behavior. No new proof fixtures or gates
are required by this document. Remaining release work is C-R3–C-R5.

## Completed D5 drawing overhead work

`timing-draw-overhead.i` removes the trailing polygon wait at +08D7A while
preserving its completed-wait flags. The waits protecting blitter registers,
CPU mask/pixel access and display publication remain. It initializes the span
table once, then clears only the previous polygon's clipped Y range. Both the
CPU path and native +08818 use this helper. Native text enters at +08842 and
resets the shared bounding box, so that entry clears pending span rows too.

The CPU/native view comparison matched all 18,000 bytes in each of 173
normal-startup/takeoff/banking frames. The final existing 500-field PAL window
measured 12.5 fps on 020 and 25.0 fps on 060, both at 3.00 world ticks/s.
A BLTPRI diagnostic measured 12.7 / 25.0 fps; its small 020-only gain does not
justify a bus-priority change, so production preserves the incoming setting.
These are short emulator windows, not full-mission or real-hardware acceptance.
Full-MMU 68040 CACHE startup/takeoff and native pause/exit with blitter-interrupt
restoration also passed. D5 evidence is under ignored
`tmp/dev/tmp/d5-initialized-pixels/`, `d5-final-{fps020,fps060,priority020,priority060}/`,
`d5-040-cache/` and `d5-pause-exit/`. The native-only build was unchanged by that renderer change.


## Cockpit work (E2/E3)

The top five view rows are wholly opaque cockpit art and are left untouched.
Rows 5–89 copy their middle 288 pixels with MOVEM and compose their edge words
using bitmap 3's plane-4 mask and cached artwork. The native right strip wraps
one word into the next row; both edges preserve that footprint. Row 90 is
outside the CPU view and stays untouched. This removes the first two restores
at +0AA80. The third restore, the attitude-instrument bezel below the view,
remains native. Art is cached in fast RAM and invalidated by native screen
swaps and module installation. Modal rendering retains the original overlay.
The CPU still fills the rectangular fast-RAM view; clipping its final copy
avoids chip traffic without complicating native geometry.

`timing-cockpit.i` caches the three native needle inputs independently for the
two back-buffer indices. Unchanged values skip both the erase at +0AC14 and
draw at +0ACF0. Native screen swaps invalidate both entries. Before +0AA80
consumes its eight panel-restore counters, any pending restore invalidates
the needle entries: rotor-warning artwork overlaps a needle even when its
angle is unchanged. Modal/native ownership always uses the original routines.
This optimization requires the CPU renderer's allocation and overlay hook;
allocation failure retains all native cockpit work. Text, scope and tapes
remain native, including their existing conditional updates.

Validation: a same-state native redraw diagnostic found zero differing words
across 423 cockpit-edge frames (18,010 bytes each) and 95 skipped-needle frames
(all 40,000 screen bytes each), including takeoff, banking and panel refreshes.
Focused assembled-code checks covered both back buffers, changed inputs,
panel restoration, native-swap invalidation and modal fallback. Allocation
failure checks passed. Full-MMU 040 CACHE startup/takeoff and native pause/exit
with D1 interrupt restoration passed. The native-only build was unchanged by that renderer change.
Evidence: ignored `tmp/dev/tmp/e23-pixels-final2/`, `e-040-cache/`,
`e-pause-exit/`; harness checks `test_cockpit_e.py` and
`test_cpu_render_install.py`.


## World-rate acceptance (C-R2, C9b)

Both items are complete against refocus criterion 1. The saved F release-slave
samples were rechecked directly against their result summaries: elapsed display
fields and the native world-tick counter give the following rates.

| Release | CPU | Fields | World ticks | World Hz |
|---|---|---:|---:|---:|
| 0658 / PAL | 68020 | 500 | 30 | 3.00 |
| 0658 / PAL | 68060 | 500 | 30 | 3.00 |
| 1489 / NTSC | 68020 | 500 | 25 | 3.00 |
| 1489 / NTSC | 68060 | 500 | 25 | 3.00 |

Rate is ticks × video field rate / elapsed fields (50 PAL, 60 NTSC); all
four meet 3.00 Hz ±1%. These are ordinary startup/takeoff windows with CUSTOM1=1,
using `play_port_f.py` and the existing flight route, not unattended demos.
Evidence: ignored `tmp/dev/tmp/f-{pal,ntsc}-{020,060}/samples.json` and
`result.json`. This is an audit of the existing F measurements, not a fresh
emulator run. Subsequent bank-rounding, damage-colour, damage-camera and demo
fixes have not changed the ordinary-play world scheduler. Visible input response
and full-mission acceptance remain separately open as C-R3–C-R5.

## Remaining blitter work and measured outcome (E4/E5)

E4 is closed by the user's measurement-based decision: do not introduce an
interrupt-driven queue when the 060 meets 25 fps. D1 and double buffering stay
in place. The E2/E3 060 cycle profile measured 25 fps, 39.8% STOP idle, and
33.2% chip-bus share. Inclusive remaining costs included map copy 7.3%, scope
2.7%, tapes 2.5%, and the retained overlay path 3.4%; these overlap and must
not be added. This profile predates the final panel-invalidation correction.

Final 500-field PAL completed-swap runs after that correction measured:
020 125 frames / 12.5 fps, 030 at 50 MHz 250 / 25 fps, and 060 at 50 MHz
250 / 25 fps. Every run completed 30 world ticks / 3.00 Hz. The eight injected
stick events reached the next completed frame in 40–80 ms, 20 ms and 40 ms
respectively. These field-phase samples are not evidence of visible input
response or scanout latency. The old prediction that only geometry would
remain is not confirmed: copies, native blits and display pacing still matter.
No 68000 work was done. No full-mission or PAL/NTSC acceptance is implied;
Release support and current regression results are recorded under F in
PERFORMANCE_PLAN.md. Full-mission acceptance and known beta issues remain in C.
Evidence: ignored `tmp/dev/tmp/e-final-fps{020,030,060}/`,
`e-aprof-baseline060-current/` and `e-aprof-final060/`.
