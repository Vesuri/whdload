# Phase 7 VERIFY scaffolding — complete

The normal 1.5b slave remains byte-identical. `simulation-verify.s` is included only
under VERIFY; the Windows dependency list includes it. Normal builds have none of
these options, helpers or private state. Build with `VERIFY=1 tools/build.sh`.

## Instruments

- CUSTOM3 retains the phase-4 fixed seed/beam-free RNG and demo-selection reset.
  Four visual call sites in h4 use a private signed-word LCG stream. The player
  anchor resets gameplay and visual seeds to $1234. Traffic/radar calls retain
  the original gameplay RNG and log their kind/result in a bounded 256-entry
  private log. Overflow is counted explicitly; no silent circular overwrite.
- CUSTOM4 adds ten graphics.WaitTOF waits before view publication while the
  player-race anchor is active. Only the caller waits; CLI simulation and VBL
  continue. This deliberately exposes the original shifter/drawing dependency.
- CUSTOM5 bit 0 starts the first race in player mode and enables a field-based
  joystick/fire tape through the existing slave input hooks. Bit 4 chooses the
  straight acceleration/braking tape; otherwise short right/left inputs are
  included. Bits 1 and 2 inject one nonfatal crash at elapsed field >=450 and one
  police pursuit at >=900, using one-shot bits rather than equality to a field.
  Thus 17 selects straight driving, 19 adds crash, and 23 adds crash and radar.
  Injection happens in VERIFY game code, never through debugger memory writes.
  Bit 3 is reserved for the later zero-fraction rendering oracle, not implemented
  or exposed as an option before a fractional renderer exists.
- CUSTOM1 bit 1 acknowledges the original crash after 100 fields at the original
  acknowledgement loop. The original penalty, animation and recovery remain.
  With it clear the original blocking acknowledgement path remains unpatched.
- The assembly assertion runner uses TD2's count/failure/first-failure protocol,
  adapted to TD helpers. Twenty-two assertions exercise actual tape boundaries and
  signed visual LCG results and early-acknowledgement timer cleanup before PatchSeg. Phase-8 arithmetic tests must extend
  this runner when the corresponding simulation routines exist.

C2 is not implemented yet. The normal slave is the original gameplay path plus
its documented always-on fixes. In VERIFY, C3/C4/C5 deliberately affect behavior
independently of C2. All-zero VERIFY options leave every optional game range
original; the assembly unit runner still executes on private data.

## Overlay lifetime and anchors

Before PatchSeg, VERIFY captures the data-hunk address from the root seglist.
After overlay-load restores the original registers, it identifies h4 through
DATA+$29C's JMP export and the original entry signature, then applies the local
patch list and flushes before returning. An already-patched h4 is not repatched;
a newly reloaded h4 is. No patch is installed in h4 when all instruments are off.

H4:$4 starts a new race fixture; $F6 establishes its first player epoch. Re-entry
through $F6 after a crash does not reset the tape or one-shot event bits. H4:$3D4
clears activity before exit. Field counts use the original VBL long, not host
time or renderer publications. Raw fixture state and exact source/listing/binary
are retained with validation evidence under `tmp/phase7/`.

## Tools and scope

`verify_capture.py NAME --preset a500|a1200 --fields N --c1 N --c3 N --c4 N --c5 N`
boots a fresh disposable game copy, stops at a guarded first-race anchor, runs
assembly checks, and records read-only VBL state, RAM, machine config and slave.
An existing output or active server is refused. The calibrated h4 location is a
local harness detail guarded by its instruction signature; changed allocation
requires recalibration. No host accessibility input is used.

`audit_simulation.py` checks whole-instruction ranges, overlaps, the declared
patch inventory and all word-aligned direct incoming branch candidates. Indirect
control flow is not statically proven. `check_disabled.py CAPTURE` compares all
declared ranges with original bytes or the exact option-selected helper targets.
It also checks the normal slave's pinned SHA-256. This is not evidence of a
future C2 implementation; phase 8 must add all its ranges and disabled checks.

`check_units.py code.bin` requires the expected completed assertion count, zero
failures and no first-failure index. `check_verify_tools.py` deliberately corrupts
assertion state and patch bytes, duplicates a range and introduces a branch into
a displaced instruction to prove that the checkers reject bad evidence.

`verify_state.py A B` compares selected core fields at equal elapsed VBL counts
and the common traffic/radar RNG prefix. `--expect-equal` makes any selected core
state difference fail; phase 8 must pass this gate outside deliberately original
blocking intervals. Zero-length RNG prefixes are not an RNG acceptance result.
No same-period enhanced-state equality or fractional rendering is claimed here.

## Acceptance

`tools/verify_matrix.sh` reproduces the twelve final fixture captures and the
explicit unload/reload check, then runs `check_phase7.py` and the checker sabotages.
It requires fresh output names; preserve or relocate a previous evidence set first.
`check_phase7.py` rechecks retained evidence without booting the emulator.
The `final-*` directories are authoritative for this build; `initial-validation/`
and the earlier pilot captures are diagnostic predecessors, not acceptance evidence.

Both A500 and A1200 pass all 22 pre-PatchSeg assembly assertions. Straight driving
and braking run for 1,300 fields with C3=1/C5=17, with and without C4. Renderer
updates are 108 versus 59 on A500 and 214 versus 80 on A1200, while each run has
259 counted simulation updates. Cross-CPU clutch and speed differences and the
slow-renderer saved-x difference are explicitly retained as negative controls;
this phase does not fix original simulation dependencies.

C1=2/C3=1/C5=23 captures cover 1,800 fields on each CPU: one nonfatal crash,
exactly one 240-unit penalty, five chances becoming four, automatic recovery,
and a forced police pursuit reaching the original stopped/ticket counter of 30.
The C1=0/C5=19 capture remains on the crash acknowledgement path with its clock
blocked. No radar-release timing claim is inferred from the 1,800-field window.

The two 1,400-field C3-only demos log the same nonempty gameplay draw sequence:
traffic 39648, traffic 38509, radar 35756. Their final visual seeds differ,
proving different visual consumption without changing that gameplay prefix.
The player fixtures independently confirm their reset at the player-race anchor.
The all-zero option run preserves every optional original patch range.

`final-reload-confirmed/` captures h4's actual unloaded BSR export, then stops at
the next race entry and verifies the freshly installed patch targets. The first
reload diagnostic assumed the intro overlay was also resident; that resolver
assumption was corrected without a slave change. Five deliberate checker
sabotages are rejected: missing unit execution, a failed assertion, overlapping
ranges, a branch into a displaced instruction and an altered installed hook byte.

Final normal SHA-256:
ca765222b4257e060e684b80581ed45506d8167c98c016c6d088ad066d6750d4
Final VERIFY SHA-256:
5ba1814bc46e7938d2e462f8297332454a68883ec610a1898a777018e94ad9b1

Normal remains byte-identical to the hardware handoff. Real A1200/68040 testing
is deferred by the user. NTSC, enhanced same-period state equality, all-car
handling and the zero-fraction renderer oracle remain later-phase work.
