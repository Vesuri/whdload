# Phase 4 — frame marker and baseline

Measurement work is complete. The normal 1.5b slave is unchanged; the comparable
baseline uses its VERIFY build with CUSTOM3=1. The complete timing/state model and
the overall playbook §12 “ready to improve” gate are now completed by phase 5.

## Publication and anchor

The Road Drawer renders through h4:$A92, then h4:$C0E calls the loaded h3:$175E
buffer-exchange helper through data export -32106(a4). That helper calls the root
LoadView wrapper at TD:$7AAA and updates front/back view pointers. TD:$7AAA is the
frame marker in frames.py and swap_fields.py. The next instruction, $7AAE, exposes
the new View in a1. WaitTOF at h4:$C14 follows publication; $C18 increments the
diagnostic drawn-frame counter.

For every publication in the A500 and A1200 baseline traces, presentation_check.py
follows View → ViewPort → RasInfo → BitMap, checks five planes, and proves that the
next field's 20,000 bitplane DMA fetches come from the selected buffer. The two View
addresses alternate. First/last shots and contact sheets show the cockpit, road,
mirror and subsequent movement. No TD2 copper address is assumed. Menus also use
LoadView: this marker is a gameplay FPS measure only inside a gameplay window.

The anchor is the first execution since reset of h4:$F6, immediately before the
physics deadline copies -31782(a4), after the initial position/speed/gear and frame
counter are initialized. BOOT_BREAK is armed at reset, with opcode guards. Capture
starts at the next profiler field boundary and lasts 100 fields. This is the first
**attract race**, mode 1 / stage 3, not the first player stage. The playbook prefers
the game's own demo when available. No keys, mouse events or game-state writes are
used. The slave fixture is the only deliberate change to gameplay inputs.

## Reproducible fixture

The normal RNG at TD:$530E seeds from VHPOSR and mixes VHPOSR into every result.
Its intro call count also depends on CPU speed. Therefore VERIFY + CUSTOM3:

- patches TD:$230 with a six-byte JSR hook; verify_demo_rng resets the word seed
  to $1234, calls the original RNG through its a4 export and replays displaced SWAP;
- replaces the eight-byte initial seed load at $5314 with the same fixed seed;
- replaces the six-byte VHPOSR operand load at $5334 with CLR.W D0 and two NOPs.
  The high word of D0 is preserved. The original signed multiply, addition, seed
  store and final return remain in place.

Every measured preset reaches the anchor with car parameter 0 (Porsche), seed
$1DC9, position 30.0, speed 0, gear 0 and frame count 0. The menu-selection variable
is -1 in demo mode and is **not** the active car; race_car is read from 8(a5).
This fixture provides the fixed initial window. It does not prove cross-CPU RNG
call ordering or simulation determinism later in a race; phase 5 establishes the divergence and phase 7 must extend the fixture.

The RNG audit checks pinned original bytes, complete instruction boundaries,
installed patches/helper bytes, the unchanged rest of the RNG, and option-off
original bytes. No word-aligned direct branch candidate enters either rewritten
RNG instruction or the demo hook interior; indirect targets are not proven.
The normal build SHA-256 remains
`ca765222b4257e060e684b80581ed45506d8167c98c016c6d088ad066d6750d4`.
The measured VERIFY build is
`d1b3a400a7a20bb7d78ee9745b815351fee6373f552a536b311076df6046fb07`.
The hardware A/B package retains the normal slave.

## Repetition checks and limitations

The authoritative captures are tmp/phase4/base-{preset}-{1,2}; the matching
base-{preset}-swaps-* runs use read-only breakpoints. Each is a fresh boot with
its exact slave, RAM, configuration, start/end state and source hash retained.
DETERMINISTIC=1, JOY0=none and joystick_port_0_mode=nothing are set. All 12,964 game
data bytes at both endpoints match within each preset, as do the displayed game
pixels in every field. The A500/A1200 instruction PCs and individual cycle costs
also match in every field. Trace and breakpoint publication patterns match exactly.
The 68030 breakpoint pattern repeats on two independent boots.

Raw-trace equality is not claimed for the controlled fixture:

- A500/A1200 have a differing RBF bit (bit 11) in INTREQR reads. Only D0 at
  TD:$2630 differs; the following AND.W #$0780 discards it. DMA differences are
  the same bit in CPU reads at INTREQR, including the byte-read alias. The
  comparator permits only this exact site/bit and rejects other changes.
- A500 raw screenshots differ in far-right padding (x=751..753), outside the
  640×400 doubled game display at (74,36)..(714,436). All pixels through x=749
  and all game pixels match; raw screenshots are preserved without alteration.
- The 68030 backend emits no instruction records and its blitter-cycle-exact
  setting is false. CPU costs, interrupt service costs and blitter DMA shares
  are unavailable, not zero. Its raw DMA also varies in JOY0DAT/hidden cursor
  sprite data; only game-state, displayed-pixel and breakpoint-frame repetition
  are claimed on this backend. No 68000 percentage is transferred to it.

The unprefixed and rng-* directories are discovery/fixture-development evidence,
not the final comparable baseline. In particular the unmodified first demo chose
a different car on the 68030. Do not combine those numbers with base-* results.

## Measured frame-cost table

All figures are for the 100-field controlled-car window. FPS uses nominal PAL
50 Hz, matching the reference convention; it is a finite-window count, not a
steady-state or whole-race average. The emulator reports about 49.92 Hz. Percentages
use each backend’s own traced CPU cycles; raw cycle units differ between CPUs.

| Measurement | A500 | A1200/68EC020 | A1200/68030 25 MHz |
|---|---:|---:|---:|
| Publications | 8 | 17 | 20 |
| Nominal PAL FPS | 4.0 | 8.5 | 10.0 |
| Blitter-wait routine | 21.16% | 34.63% | unavailable |
| Blitter IRQ service | 11.36% | 6.64% | unavailable |
| STOP idle | 3.12% | 2.08% | unavailable |
| Blitter IRQ dispatches | 2724 | 5385 | unavailable |
| Clear root $D72 (self / inclusive) | 0.28% / 5.65% | 0.15% / 9.55% | unavailable |
| Fill root $DBE (self / inclusive) | 0.11% / 1.95% | 0.06% / 3.17% | unavailable |
| Shape root $10C4 (self / inclusive) | 5.99% / 15.26% | 1.99% / 13.74% | unavailable |
| Span h4+$3796 (self / inclusive) | 3.57% / 8.01% | 4.24% / 7.18% | unavailable |
| Span setup h4+$3828 (self / inclusive) | 4.45% / 12.58% | 4.32% / 12.16% | unavailable |
| Projection h4+$3B10 (self / inclusive) | 0.91% / 0.91% | 0.88% / 0.88% | unavailable |
| Object dispatch h4+$3B56 (self / inclusive) | 1.08% / 16.77% | 1.36% / 15.26% | unavailable |
| Road walker h4+$1A14 (self / inclusive) | 4.27% / 36.24% | 5.55% / 37.70% | unavailable |

Inclusive call-tree costs overlap and have boundary attribution limits; do not
add them into a budget. The wait row includes the complete root $D44 routine,
including its repeated clear-bit checks and bookkeeping. Blitter IRQ service
is timed from the live level-3 entry through its matching RTE, for intervals
taking the bit-6 dispatch; no partial intervals occur in these captures. The
Kick image dispatcher is +$D14, with the blitter branch at +$D38. The handler
target in these captures is Kick+$6DFA. STOP idle includes time charged to STOP.

| DMA slot share | A500 | A1200/68EC020 |
|---|---:|---:|
| Free | 28.33% | 42.13% |
| Refresh | 1.76% | 1.76% |
| CPU | 34.40% | 14.98% |
| Copper | 0.41% | 0.41% |
| Audio | 0.31% | 0.22% |
| Blitter | 5.92% | 11.60% |
| Bitplane | 28.15% | 28.15% |
| Sprite | 0.72% | 0.76% |

The measured span path is a blitter span, not TD2’s CPU span loop. In this window
the large costs are blitter waits, drawing setup and blitter interrupt service.
These measurements do not yet establish the benefit or safety of any proposed
enhancement. All three traces show the same starting scene/car; their endpoint
states are not assumed to represent identical simulation progress.

## Timing observations resolved in phase 5

Both traced CPUs call road processing at h4:$134 in fields 4,9,...,99: 20 calls, five fields
apart. The setup writes period 5 at -16(a5), the deadline is -12(a5), and the clock
source is the root VBL counter at -31782(a4). Drawing runs separately. This is a
window-specific observation, not the complete timing model. Endpoint speed and
position differ across CPUs because of the rendered shifter/clutch handshake.
The vehicle integrator is $130 -> $43B0/$3F26; $134 processes road crossings.
Phase5.md establishes the deadline, clock, score, RNG and event models.

## Commands

From the game directory, with tools/env.sh sourced:

```sh
VERIFY=1 tools/build.sh
TD_SETUP=a500 tools/fixed_window.sh tmp/phase4/new-a500-1
TD_SETUP=a500 tools/fixed_window.sh tmp/phase4/new-a500-2
TD_SETUP=a1200 tools/fixed_window.sh tmp/phase4/new-a1200-1
TD_SETUP=a1200-030 SWAP_ONLY=1 tools/fixed_window.sh tmp/phase4/new-030-1
python3 tools/check_phase4.py
```

The default fixed window uses the pinned VERIFY slave, CUSTOM3=1, 100 fields and
manifest/race-anchor.json. Changed slaves, runtime manifests or machine overrides
require recalibration with race_capture.py --calibrate and an explicit --h4 value.
ANCHOR remains the root-hunk diagnostic path; ANCHOR=0x18ba is not the race benchmark.
frames.py writes trace.frames.json; td_report.py provides per-routine self and
inclusive costs; compare_race.py retains both raw differences and the narrowly
validated measurement comparison. presentation_check.py checks next-field DMA.


The reproducible phase-4/5 baseline uses the retained phase-4 slave above. The
current VERIFY build has phase-7 instruments and is a different fixture; use
`verify_capture.py` for it. Do not replace historical capture binaries or pins.
