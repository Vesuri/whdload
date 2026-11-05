from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];report=json.loads((r/'manifest/step5-b5-validation.json').read_text());assert report['status']=='passed'
p=r/'docs/STEP5_CAPACITY.md';s=p.read_text();assert '### B5 acceptance' not in s
s=s.replace('6. **B5 – 020 helper tuning.**','6. **B5 – 020 helper tuning. Passed (candidate).**')
s+='''

### B5 acceptance (2026-10-12)

B5 is passed as a **default-off candidate** under `FF1_HELPERS_020`.
The Fast player `conv_helper` mean is **6,998.35 → 4,968.00 cycles**
(**29.01% lower**), meeting the 5,000-cycle gate by **32 cycles** in the
prescribed matched 20-update window. This is a narrow measured pass, not
broad capacity headroom. B6 peak/debt gates and B8 presented FPS remain open.

| Matched lean metric | 020 + Fast B4 | 020 + Fast B5 | Chip-only 020 B4 | Chip-only 020 B5 |
|---|---:|---:|---:|---:|
| Player conversion helpers | 6,998.35 | 4,968.00 | 10,461.55 | 8,609.80 |
| Complete player segment | 49,977.00 | 47,110.60 | 58,947.70 | 56,589.00 |
| Complete update mean | 124,247.60 | 122,144.50 | 138,214.30 | 135,320.50 |
| Worst rolling five | 126,642.00 | 124,019.60 | 143,617.60 | 137,489.20 |
| Peak update | 337,188 | 341,092 | 375,364 | 372,924 |

Whole-update Fast mean improves 1.69%; the peak increases with this layout
and still exceeds B6's future 283,750-cycle pulse gate. Chip-only adapted
mode remains diagnostic; its selected production design is the unchanged
native 100 ms coarse path. Measurement uses `capture_step5_profile.py`,
loop-125 matched starts, the first installation interval omitted, then 20
complete updates. Only repeated unsuccessful pacing polls are excluded.
Owner, per-car and classification totals agree exactly; the per-car analyser
now records unrounded category means so the gate is not decided by rounding.

Implementation:

- Shared 1,024-word integer seed table (2,048 bytes). U32 uses exact lookup
  below 1,024 and a bucket seed plus one `DIVU.L` Newton step otherwise.
  U64 uses `BFFFO` normalization, interpolated upper seed, one 64/32 `DIVU.L`
  Newton step and full-width square correction. The result is exact floor
  square root throughout both unsigned domains. The native bounded square
  root and native exact-CCR division helpers are unchanged.
- `FF1SpeedRate20` forms its signed 64-bit numerator with `MULS.L`, uses
  `DIVSL.L` only when the high half is the low half's sign extension, and
  retains the wide fallback, overflow rejection, clamping and carry rules.
- Rotation retains full 64-bit `MULS.L` products. Checked word shifts replace
  the longer bit-shift sequence; both outputs still commit atomically.
  Register saves follow actual clobbers, including the feedback, derivative,
  projection, carry-rotation and tyre-limit helper entries.
- Re-profiling showed that the named sqrt/rate/rotation changes alone missed
  the gate (v1: 6,621; v2: 5,823.9 Fast helper cycles). The conversion-helper
  phase therefore also removes temporary copies in `FF1VelocityApply20`
  using checked signed 32-bit division, and uses an exact 0..255 quotient/
  remainder lookup in wear/fuel with a full-domain unsigned division fallback.
  These preserve aliasing, atomic failure, invalid-input and saturation
  contracts. No B6 native call-site transformation was included.

Validation:

- Existing guest suites retained: 1,003 feedback, 408 U64 sqrt, 3,216 rotation
  cases (inside the 9,090 velocity suite), and 130 scalar-rate cases.
  Another 3,216 carry-rotation and 56 continuous-response cases pass.
- Added/expanded: 1,942 U64 seed-endpoint cases; 2,383 wide-tyre cases including
  every small-root input 0..1023; 4,244 wear cases covering every lookup
  numerator, carry, saturation and the 255/256 boundary; 1,264 scalar cases
  including 32/64-bit division selection and signed overflow boundaries.
  Independent models check 3,073,730 U64 and 1,065,536 U32 inputs. Maximum
  observed Newton correction is four and one respectively.
- On both 020 profiles, VERIFY and lean match B4 at all **101 native semantic
  checkpoints**, with the exact-state inventory unchanged, and all seven
  normalized player fractional-state blocks agree. Native opponents inherit
  the B3 native-control proof through the exact B4/B5 comparison.
- Elapsed and full arithmetic/event replay pass on both profiles: 100 player
  updates, 20 native pulses, 2.000 simulated seconds in 2.02322059 elapsed
  seconds (101 PAL fields). Field-granular traced timing is not a CPU-cost
  measurement or B6 scheduler/debt acceptance.
- Direct scalar/heading hook fixtures pass 80 cases per VERIFY/lean arm per
  profile, checking every D0-D7/A0-A6 register, CCR, native output and carried
  state. Scheduling audits retain four pulse updates, native 28/7 pair counts,
  zero simulation blits, zero opponent conversion and zero context lookups.
- B5-disabled VERIFY/lean binaries are byte-identical to committed B4.
  Authoritative ordinary source and release hashes are unchanged. New mode
  remains default-off; no CUSTOM2=0 or coarse-path behavior is activated.

The first large VERIFY builds failed to load on chip-only 020 with WHDLoad
**DOS error 103 (not enough memory)**; the live run was diagnosed and its log
retained, not accepted as a game result. The final isolated VERIFY build uses
4,000 scalar trace records instead of the default 4,096, with allocation and
its overflow guard controlled by the same `FF1_SPEED_RECORD_CAPACITY` constant.
Only 200 records are used. Its 779,640-byte slave fits; all checkpoints and
replay assertions remain. Exported unused trace padding is normalized to the
old file ABI. Default trace capacity/bytes are unchanged, and the compact
fixture's lean binary is byte-identical to the measured lean binary.
The rejected v3 word-shift experiment failed the rotation oracle and is not
part of acceptance; v4 corrected it before further profiling.

Evidence: `manifest/step5-b5-validation.json`, its linked oracle/profile
reports, `tmp/step5/*-b5-v5-matched-*`, `tmp/step5/*-b5-v5-matrix-*`,
`tmp/build/step5-b5-v5/lean`, `tmp/build/step5-b5-v5-compact/{verify,lean}`,
and `tmp/step5/b5-verify-startup/whd-output.txt`. Reproduce with
`build_step5_b5_compact.py`, `profile_step5_b5.py`,
`capture_step5_b5_matrix.py`, the `test_step5_b5v5_*` guest oracles,
`analyze_step5_b5_{states,elapsed,replay,profiles,scalar_hooks}.py`,
`check_step5_b5_disabled.py` and `accept_step5_b5.py`.

**Next: B6**, ordered native exact-output work with its unchanged average,
pulse and debt gates. B5 does not complete step 5 or rendered-game acceptance.
'''
p.write_text(s)
p=r/'manifest/project.json';d=json.loads(p.read_text());status='B5 passed as default-off candidate. Fast player conversion helpers 6998.35 -> 4968.00 cycles (29.01% saving; 32-cycle gate margin); whole update 124247.6 -> 122144.5 (1.69%). Exact seed/Newton roots, checked scalar/rotation/velocity/wear helpers; both profiles pass unchanged 101-checkpoint native/player state, elapsed/replay and direct-hook register/CCR checks. Required guest arithmetic suites and expanded boundary tests pass. Compact VERIFY trace capacity solves diagnosed chip-only load-memory failure without relaxing checks. B5-disabled B4 binaries and ordinary release remain exact. Chip-only adapted run diagnostic. Next B6.'
d['step5_b5_status']=status;d['step5_b5_validation']='tmp/dev/manifest/step5-b5-validation.json';d['step5_status']='S0/S2/S3/B3/B4/B5 passed as candidates; S1 CCR diagnostic validated. '+status
d['next_steps'][0]='Step 5: B5 passed. Next STEP5_CAPACITY.md B6 native exact-output work; average <= 145600 Fast cycles, pulse <= 283750, debt below one quantum within five.'
d['next_steps'][1]='20 ms path remaining: B6 native exact-output work, B7 MEMF_PUBLIC placement, B8 opponent interpolation and presented FPS. Retain per-phase gates and matched oracles.'
p.write_text(json.dumps(d,indent=2)+'\n');print('B5 plan and project manifest updated')
