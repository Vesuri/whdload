from pathlib import Path
import json
r=Path(__file__).resolve().parents[1]
def read(n):return json.loads((r/'manifest'/n).read_text())
equal=read('step5-selection-equal-validation.json');entry=read('step5-selection-entry-validation.json');profile=read('step5-selection-profile-validation.json');elapsed=read('step5-selection-elapsed-validation.json');replay=read('step5-selection-elapsed-replay-validation.json')
assert not entry['rng_equal'] and not entry['countdown_equal']
assert len(equal['profiles'])==4 and equal['status']=='passed'
assert profile['status']==elapsed['status']==replay['status']=='passed'
for name,row in equal['profiles'].items():
 assert row['passed'] and not row['mismatches']
 for arm,capture in row['captures'].items():
  selected=capture['selection'];c=capture['custom2']
  expected=0 if arm.startswith('control') or c==0 else (2 if name=='a1200-fast' else 1)
  assert selected['path']==expected and selected['interval']=={0:0,1:100,2:20}[expected] and selected['enabled']==0
report={'status':'passed','scope':'S0 candidate selection and controlled native exact-state gate; production activation remains off','selection_boots':16,'matched_state_comparisons':24,'startup_timing_effect':{'rng_bytes':120,'control_countdown':14,'selector_countdown':29,'controlled_by':'Equal work at startup; selector result discarded in control, no RNG rewrites'},'evidence':['step5-selection-entry-validation.json','step5-selection-equal-validation.json','step5-selection-profile-validation.json','step5-selection-elapsed-validation.json','step5-selection-elapsed-replay-validation.json'],'next':'S2 VERIFY split'}
(r/'manifest/step5-s0-validation.json').write_text(json.dumps(report,indent=2)+'\n')
p=r/'docs/STEP5_CAPACITY.md';s=p.read_text();marker='### S0 accepted: equal-work comparison'
if marker not in s:
 s+='''

### S0 accepted: equal-work comparison

**S0 passed.** All 16 boot cases pass: four profiles, CUSTOM2=0/1, control and
selector. All 24 matched-state comparisons (125/150/175 native loops) are exact
across the unchanged semantic block inventory. Report:
`manifest/step5-selection-equal-validation.json`; aggregate:
`manifest/step5-s0-validation.json`.

The first-race capture confirms the uncontrolled chip-only divergence was the
known startup-timing RNG effect: different 120-byte RNG regions and countdowns
14/29 before the first race:+$589c call. Matching countdown alone was insufficient.
The accepted control performs the identical tag query and selector call, storing
its result in a discard slot; no RNG rewriting or relaxed comparison was needed.
Historical failed captures remain as evidence of the uncontrolled comparison.

CUSTOM2=0 selects legacy on every profile. CUSTOM2=1 selects native 100 ms on
68000, A500+Fast and chip-only 020, and player-20/opponents-100 on 020+Fast.
Selection is readable; activation remains off pending the later gates.
The ordinary release is unchanged. Existing S0 elapsed/replay and equal-layout
profile A/B evidence also pass: 631,121.2 cycles chip-only and 521,269.12 Fast,
identical control/selector cycle sequences and start/end semantic state.
These are all-car diagnostic costs, not Plan B or coarse acceptance.

Next is S2: put diagnostics behind VERIFY while preserving arithmetic scratch
storage. In particular, velocity_records holds live intermediate values used by
conversion helpers; it cannot simply be deleted with the trace output. Retain
necessary scratch values, remove diagnostic work, prove VERIFY equivalence and
measure the untraced gates before moving to S3.
'''
 p.write_text(s)
p=r/'manifest/project.json';d=json.loads(p.read_text());d['step5_s0_validation']='tmp/dev/manifest/step5-s0-validation.json';d['step5_status']='S0 passed: all four profiles select correctly, 16 boot cases and 24 equal-work matched-state comparisons exact. Uncontrolled chip-only divergence confirmed as title/menu startup RNG consumption (first-race countdown 14/29); no RNG rewriting needed in accepted control. S0 elapsed/replay and cycle-identical A/B pass. S1 CCR diagnostic validated. Continue S2 VERIFY split; S3, B3-B8, C1-C3 and default-off production integration remain outstanding. New paths not activated.';d['next_steps'][0]='Step 5: S0 selection passed and S1 CCR diagnostic validated. Continue STEP5_CAPACITY.md S2 VERIFY split, then S3 simulation/presentation separation, with required A/B and oracle gates.';p.write_text(json.dumps(d,indent=2)+'\n')
print('S0 accepted; step 5 remains active, next S2')
