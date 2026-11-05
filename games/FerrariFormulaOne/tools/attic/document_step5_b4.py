from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];d=json.loads((r/'manifest/step5-b4-validation.json').read_text());assert d['status']=='passed'
p=r/'docs/STEP5_CAPACITY.md';s=p.read_text();s=s.replace('5. **B4 – Player hook consolidation.**','5. **B4 – Player hook consolidation. Passed (candidate).**',1)
s=s.replace('segment ≤ 50,000 Fast (from 66,008).','segment ≤ 50,000 Fast (old projection 66,008; measured B3 60,959.5 → B4 49,977.0).',1)
s+='''

## B4 acceptance: compact player state and consolidated hooks

B4 passes as a **default-off candidate**, selected at build time with
`FF1_PLAYER_HOOKS` alongside `FF1_PLAN_B`, for the mode-8 player path. The
ordinary slave does not include these modules. Gate profile: 14 MHz 020 + Fast;
chip-only 020 is a diagnostic comparison and retains its selected coarse design.

The player has one **64-byte primary state block**, checked by the assembler:
velocity 0..11, position 12..23, heading 24..35, scalar 36..41, steering history
42..51, steering cursor 52, fuel carry 53, steering last quantum/raw 54..59,
and four tyre carries 60..63. Cursor and condition carries have the complete
unsigned domain 0..4, so byte storage loses no information. Steering reset and
sampling preserve the adjacent fuel byte. Working arithmetic scratch, temporary
scalar/position values, scheduler metadata and saved contact position workspace
remain separate; this is not a claim that all candidate memory fits in 64 bytes.
Dormant opponent conversion arrays are no longer part of the compact candidate.

Player hooks address the state directly, with **zero context-lookup executions**
in the measured windows. Adjacent native load callbacks at $671e6/$6720e/$6721c
share the $67280 callback; stores at $68546/$68576/$685a6 share $6860e. Their
native instructions and install-time signature checks remain. The lean build
uses narrower register saves, direct scalar/wear/fuel callbacks and pulse-only
event dispatch; it omits the feedback hook whose lean body only checked state.
Heading hooks combine axis selection and wrapper work around the unchanged
signed increment helper. The scalar sites $672f0..$676e0 remain at their native
control-flow points: branches and engine calls between them prevent treating
that entire range as one straight-line block. Their wrappers are specialized.
VERIFY retains the established record ABI and independent component callbacks.
No B5 arithmetic algorithm or B6 native calculation optimization is included.

### Measured capacity

| Profile | B3 player | B4 player | B3 whole update | B4 whole update |
| --- | ---: | ---: | ---: | ---: |
| 020 + Fast (gate) | 60,959.5 | **49,977.0** | 136,587.4 | **124,247.6** |
| Chip-only 020 (diagnostic) | 72,287.4 | 58,947.7 | 151,972.1 | 138,214.3 |

All values are mean emulated cycles over 20 complete lean updates. Fast player
cost falls **18.02%**, whole-update cost **9.03%**. Fast worst rolling five is
126,642.0 cycles and peak is 337,188. The player gate passes by **23 cycles only**;
record this as a narrow pass in the measured window, not substantial headroom
or acceptance of later B6/B7, contact debt or rendered-FPS gates.

The matched A/B uses the same controlled loop-125 demo state, excludes the first
installation interval, and removes only repeated unsuccessful pacing polls.
The exact native start-state inventory is unchanged. Owner, per-car and classify
analysers agree on each update total; the player mean is stored unrounded.
Instruction audits confirm four native pulses, cars 7..0 on pulses/car 0 on
other quanta, 28/7 pair bodies, no opponent conversion, no context lookups and
zero native simulation blits. Intermediate Fast player costs were 53,429 after
the first hook pass and 50,624 after merging; both remained below the 58,000
abort threshold before the next consolidation.

### Semantic and boundary checks

- Both profiles: B3 versus B4 VERIFY/lean agree at all **101 native checkpoints**,
  including all **20 opponent pulses**, with the unchanged semantic blocks,
  gear, instrument phase/rates and flag counter. All seven live player state
  components agree after expanding the packed byte representation. Removed
  dormant opponent fractions are not runtime state; native opponent arrays
  remain compared exactly. B3's independently validated native-opponent control
  supplies the existing reference for this transitive comparison.
- Elapsed and full player arithmetic replay pass: **100 quanta, 2.000 simulated
  seconds, 20 pulses**, with velocity/scalar, position, heading, steering,
  wear/fuel, event/RNG, clocks, counters, boost/audio/gear and healthy recovery.
- **112 contact cases per profile** pass against native control: all pairs,
  both directions and pulse phases, including lateral impulses and exact
  player fractional resets. Fixture-only wide result buffers preserve the
  established oracle format while live candidate state uses the compact block.
- **1,008 recovery/refill and 128 contact-counter cases per profile** pass.
- **254 wear and 80 steering guest boundary cases** pass on chip-only 020,
  including invalid byte carries/cursors, saturation, gaps, wraparound and
  adjacent-byte canaries. The fuel byte survives steering operations.
- **80 direct hook cases per VERIFY/lean arm per profile** cover all ten
  specialized scalar sites and all four heading sites. Independent arithmetic
  expectations, D0-D7/A0-A6, CCR, native output and carried state agree exactly.

Final builds are `tmp/build/step5-b4-v4/{verify,lean}`. VERIFY is byte-identical
to v3, so its final capture records explicitly reuse that evidence. The final
macro cleanup compiles byte-identically to both v4 binaries. With B4 undefined,
both B3 binaries remain byte-identical. Ordinary source/release hashes remain
unchanged and ordinary CUSTOM2=0 remains legacy-exact.

Final captures: `tmp/step5/{a1200,a1200-fast}-b4-v4-matrix-{verify,lean}-fine`,
`{profile}-b4-v4-matched-b3`, and `{profile}-b4-v4-matched-b4-retry1`.
The first final Fast profile could not save because the filesystem was full;
it is not accepted evidence. Duplicate B4-created baseline traces were verified
by SHA-256 and hard-linked, and superseded v2/v3 candidate traces were losslessly
gzipped with round-trip hash verification. Storage actions are recorded in
`tmp/step5/b4-trace-storage.json`; decompress those older traces before replay.
The profile harness now guarantees emulator cleanup even if saving its log fails.

Aggregate acceptance: `manifest/step5-b4-validation.json`, with source/build
hashes, exact-cycle report, state/elapsed/replay/hook/contact reports, fixtures
and schedule audits. Harness, reports, captures and builds remain ignored.
Full renderer, physical input/modal acceptance, rendered FPS, coarse integration,
and 030/040/060 analysis remain outside B4. **Next: B5 helper tuning**; its Fast
player conversion-helper gate remains ≤5,000 cycles.
'''
p.write_text(s)
p=r/'manifest/project.json';m=json.loads(p.read_text());status='B4 passed as default-off candidate. Fast player 60959.5 -> 49977.0 cycles (18.02% saving; 23-cycle gate margin); whole update 136587.4 -> 124247.6 (9.03%). Compact 64-byte primary player state, zero context lookups, merged load/store callbacks, specialized hot hooks. Both profiles pass 101-checkpoint exact native/player state, elapsed/replay, 112 contacts, 1008 recovery, 128 counters and 80 direct hook cases per arm. Byte-boundary fixtures pass; B4-disabled B3 binaries and ordinary release unchanged. Chip-only run diagnostic. Next B5.'
m['next_steps'][0]='Step 5: B4 passed. Next STEP5_CAPACITY.md B5 020 helper tuning (player conversion-helper segment <= 5,000 Fast cycles).'
m['step5_status']='S0/S2/S3/B3/B4 passed as candidates; S1 CCR diagnostic validated. '+status
m['step5_b4_status']=status;m['step5_b4_validation']='tmp/dev/manifest/step5-b4-validation.json';p.write_text(json.dumps(m,indent=2)+'\n')
print('Updated STEP5_CAPACITY.md and project.json')
