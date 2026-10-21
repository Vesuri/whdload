# Gunship hybrid timing design

This describes the current TIMING_RUNTIME implementation as of 2026-10-21.
[PERFORMANCE_PLAN.md](PERFORMANCE_PLAN.md), section C's refocus, defines release
acceptance and the five remaining blockers C-R1–C-R5. C is not complete.
Implementation history and superseded experiments are in git.

## Activation and scope

**Enhanced framerate** is the default-off CUSTOM1 boolean. The slave ignores
it below 68020. Every framerate patch, including blitter changes, shares that
gate; existing baseline compatibility and protection fixes remain baseline.
The hybrid flight loop is currently installed for the 0658 executable in
TIMING_RUNTIME builds. This is not a claim of timing support for every game
version. The ordinary build and CUSTOM1=0 retain native timing.

`timing-slave.i` resolves loaded hunks, reads the display's 50/60 Hz frequency,
allocates/prepares the runtime, and installs the flight entry hook last.
Prepared native code is signature-checked; the loader's cache flush covers it.
The current arena is 30,436 bytes and production runtime text is 48,190 bytes.
The CPU renderer separately allocates 18,000 bytes of fast RAM.
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
native endpoint, including displacement. A press/release within the interval
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
random tail-rotor heading impulse is eased over 8 PAL fields (160 ms) or
10 NTSC fields (167 ms). Normal steering uses the latest field pose without
that delay. Gameplay heading, targeting, collision and RNG are unchanged.
Small-bank asymmetry remains native: +0943A's signed byte shift maps +1..+3
to zero and -1..-3 to -1.

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

## View drawing and display exchange (D2, E1)

`timing-display.i` replaces only the enhanced flight swap at +044B4.
The task waits for the last blit, finds the current copper list's ten BPLxPT
moves, copies the selected bitmap into Screen.BitMap, and publishes the new
plane pointers. The game's VBL server exchanges those words and acknowledges
completion before the task may reuse the old front buffer. This retains
synchronous double buffering; D3/D4 remain separate work. FrontScreen waiting
yields through WaitTOF. Native/modal paths still rebuild their screen normally.
Palette moves and the flash-effect pointers found by +00AB8 stay intact;
there is no unchanged per-frame palette copy or MakeScreen/RethinkDisplay.

`timing-cpu-render.i` is installed only for enhanced 0658 flight when an
18,000-byte MEMF_FAST allocation succeeds; failure retains the blitter path.
Native geometry, clipping and edge-to-span tables are reused. The CPU draws
320×90 pixels into five contiguous fast-RAM planes: lines select an unrolled
four/five-plane pen routine once, polygons fill spans directly without a mask,
and sky/ground bands use MOVEM. Native polygon right-edge word rounding is
retained for pixel equality, including its word-aligned endpoint quirk.

The horizon routine also draws the attitude instrument below the view. Those
primitives keep their native chip/blitter path; the mask is cleared after a
native polygon, not for every CPU polygon. The five completed view planes
(18,000 bytes) are copied once to the chip back buffer before native cockpit
overlays. Subsequent native effects and cockpit work retain their ordering.
The fast buffer is freed with the timing runtime. Compatibility blitter hooks
are installed first so native trampolines retain their corrected pixel waits;
the existing LoadSeg cache flush covers the prepared hooks and trampolines.

A same-state diagnostic rerender compared all five CPU planes with the real
blitter on 163 takeoff/banking frames: zero differing words. Allocation and
no-fast-memory fallback checks passed. Full-MMU 68040 with CACHE passed normal
startup and takeoff. The ordinary slave remains byte-identical.

The existing 500-field PAL window reports 11.7 fps on a1200-fast and 25.0 fps
on a1200-060, each with 30 world ticks (3.00 Hz). Input-to-next-completed-frame
samples are 20–80 ms (median 60) and 20 ms respectively; these timestamps do
not prove visible response or scanout latency. Evidence is under ignored
`tmp/dev/tmp/step7-e1-{pixels3,fps020,fps060,040-cache}/`; D2's short profile is
in `step7-d2-profile/`. This completes refocus step 7, not C-R1–C-R5.

## Known demo regression (C-R1)

Unattended normal startup enters a recorded demo. Native input decoding at
+04E3C calls the tape reader +053F2 and maps any key to exit when hunk 6 +45CC
indicates playback. Enhanced flight instead consumes live field input and
bypasses both behaviors. This is diagnosed, not fixed.

One normal-startup PAL a1200-fast run per toggle confirms the difference over
an approximately 20-second observation window. Native advances 85 world ticks,
moves from (29871,21920) to (31025,18752), and advances the tape by 96 bytes.
Enhanced advances 61 ticks but remains at (28416,28672), with zero altitude,
RPM and attitude, and its tape pointer stays at base+4. Space exits native to
the T-74 screen but leaves enhanced in the demo cockpit. The world is running;
recorded flight controls and the special exit behavior are missing.

## Evidence and remaining acceptance

The step 3 normal-startup comparison used one run per CPU/toggle, the same
binary and 500-field PAL control window. Native/enhanced fps were 10.4/11.5
on a1200-fast and 16.3/16.7 on a1200-060. Enhanced world spacing estimated
3.008/3.012 Hz. Input-to-next-completion medians were 60/40 ms (ranges 20–80 /
20–60 ms). Those timestamps do not prove visible response, and the short PAL
windows do not complete ordinary-play PAL/NTSC world-rate acceptance.
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
| Demo comparison | `step5-demo-{native,enhanced}/`: `demo.json`, start/end/exit screenshots |

The demo JSON's `demo` field reads an unrelated offset and is not evidence;
use tape progress, player state and screenshots. The user's matching screenshot
is `tmp/dev/tmp/play-a1200-040/.run/shots/FS-UAE_Full_261021-1356_00.png`.

For an existing measurement rerun, the harness builds with VERIFY=1 and
TIMING_RUNTIME=1; `REFOCUS=1 MACHINE=<machine> CUSTOM1=<0|1> SLAVE=<built-slave>`
selects the existing `tools/fps.py <out>` comparison under its environment.
Use separate run directories and exclude host input. Debugger guest-memory
writes are unsupported by the shared harness; previous guest probes were
compiled diagnostics, not play-build behavior. No new proof fixtures or gates
are required by this document. Current release work is exactly C-R1–C-R5.
