# Phase 9: blitter priority and interrupts — complete

Accepted as PAL emulator beta 1.7b. CUSTOM2 enables the option. Real A1200/68040
results remain deferred; NTSC is unvalidated. The original 1.5b/1.4 hardware
handoff is unchanged. Phase 10 (fractional rendering) is next.

## Implementation and original code

`render.s` ports TD2's option/restore helpers around the slave's loaded-program
call. It saves DMACONR BLTPRI and INTENAR BLIT, sets priority and clears BLIT.
Normal program return restores those enables. All writes are gated by CUSTOM2.
D0/A0 and all other registers are preserved on entry; restore preserves D0.
No original game instructions are overwritten by phase 9; existing hook audits
and disabled-byte checks still cover 66 declarations (four exclusive aliases).
WHDLoad handles its own quit/abort restoration separately.

TD root $432/$440 already saves/enables BLTPRI via the existing slave's
$434/$444 operand fixes. Root $D44 polls BBUSY, including five-plane shape waits
at $10EC/$115A/$117C/$119E/$11C0/$11D8. Phase-4 traces attribute 11.36%/6.64%
of A500/A1200 time to blitter IRQ service: Kick-relative dispatcher $D14,
blitter branch $D38, handler $6DFA. TD2 game offsets are not reused.
The measured additional benefit is interrupt suppression; priority is already
set during both control and enabled gameplay.

VERIFY C1 bit 3 disables only the new hardware option, leaving CUSTOM2 simulation
active. This measurement control is absent from normal builds. Both build modes
assemble; final 1.7b differs from the measured candidate only at three version
string bytes per slave (`tmp/phase9/version-equivalence.json`).

## Fixed-window results

Evidence is under `tmp/phase9/`. `comparison.json` checks the same VERIFY binary,
C2=1/C3=1/C5=17 and C1=8 (control) versus C1=0 (enabled), with two 1,000-field
windows per fresh boot. The original LoadView marker supplies frame counts;
nominal PAL 50 Hz converts them to FPS. No instruction-cycle FPS estimate is
used, including on the 68030. The second window starts at the next VBL boundary;
this is not claimed to be one contiguous 2,000-field trace.

| Preset | Control FPS | Enabled FPS | Gain |
|---|---:|---:|---:|
| A500 | 4.05 / 4.05 | 4.70 / 4.80 | +0.65 / +0.75 |
| A1200/68EC020 | 7.45 / 7.55 | 8.30 / 8.35 | +0.85 / +0.80 |
| A1200/68030 25 MHz | 10.15 / 10.00 | 12.50 / 12.50 | +2.35 / +2.50 |

The short straight tape accelerates/brakes, then remains stopped. These are
finite-window scene measurements, not whole-race averages. Every gain exceeds
the +0.15 FPS noise floor. All selected gameplay values at the starting and both
ending checkpoints match within each pair. Hardware reads show BLTPRI set in
both arms, and BLIT disabled only in the enabled arm; other stable interrupt
enables match. All 668 native assertions and installed patch-byte checks pass.
The A1200 enabled cockpit/road/mirror screenshot was inspected.

Capture names: `candidate-{a500,a1200,a1200-030}-{off,on}`; the A1200 control is
`candidate-a1200-off-retry`. The original control attempt ended at boot due to
host disk exhaustion and is not acceptance evidence. The retry occurred only
after process inventory confirmed its emulator had terminated.

## Native helpers and normal player build

`candidate-lifecycle-a1200-retry/enable.json` and the bounded follow-up verify
actual game-entry register/stack preservation and the hardware transition.
Native Control-C did not set the original game's quit flag within 100 polls;
no natural game-return validation is claimed from those probes.

`return-fixture/difference.json` proves the isolated fixture differs from the
measured slave only by replacing the four-byte game call with two NOPs. Both
helper bodies and their calls remain unchanged. This makes the program return
immediately, without manufacturing host-side register/memory state.
`candidate-return-fixture-a1200/result.json` verifies native enable and restore,
all D0–D7/A0–A6 values, return PC and stack, and restoration of the original
priority and interrupt bits. The fixture returns through WHDLoad to AmigaDOS.
This is helper-return coverage, not a claim of a natural player exit.

`final-normal-a1200-c2-{0,1}` smoke-test the exact normal 1.7b slave through
startup and 400 fields of the driving demo. `normal-check.json` proves the
normal helper is inactive and BLIT remains enabled with C2=0; all optional
ranges retain original bytes. C2=1 activates the helper, clears BLIT and installs
the intended simulation hooks. No VERIFY options are enabled. The C2-on final
cockpit, road and mirror screenshot was inspected.

## Reproduction and acceptance

From the game directory, source `tools/env.sh` and use its Python:

- Build: `tools/build.sh`, then `VERIFY=1 tools/build.sh`.
- Each measured arm: `tools/blitter_capture.py NAME --preset PRESET --c1 8|0
  --c5 17`. It refuses existing outputs or an active server. Exact slaves,
  listings, machine configuration, start/end state, register masks and
  breakpoint publication logs are retained.
- `tools/check_blitter.py` rechecks all retained pairs. `tools/test_blitter.py`
  rejects inconsistent FPS, corrupt counts and changed gameplay.
- `tools/blitter_normal_capture.py NAME --preset a1200 --c2 0|1 --fields 400`
  captures the final normal build. `tools/check_disabled.py CAPTURE` checks bytes.
- `tools/audit_simulation.py` and `tools/identify_game.py` validate unchanged
  game hook boundaries/incoming candidates, signatures, hunks and exports.
- `tools/blitter_return_fixture.py NAME` uses the preserved measured-build
  fixture; it requires its exact matching listing/address calibration. See
  `return-fixture/` for source and the four-byte difference proof. No general
  hardware or branch-indirect proof is inferred from this test.

`acceptance.json` maps phase-9 requirements to checked evidence.
`acceptance-manifest.json` pins phase-9 source/builds, local tools, reports and
capture metadata. Generated material remains ignored; only source, Makefile,
ReadMe and the tracked plan are committed. No push is authorized.

Two historical phase-4 diagnostic traces (`a1200-1/trace.bin` and
`a1200-2/trace.bin`) were losslessly gzip-compressed to recover disk space.
Decompressed SHA-256 values were verified before removing the redundant
uncompressed files; `archived-diagnostics.json` records both. Restore with
`gzip -dk` before using tools expecting those paths. Accepted phase-4 `base-*`
captures and all original inputs remain unchanged.
