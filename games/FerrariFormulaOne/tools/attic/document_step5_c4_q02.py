from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
counts={'position':56,'velocity-v2':56,'contact-v2':56,'work':432,'work-v2':96,'cross':72}
report={'status':'passed','scope':'C4-Q02 independent ownership, contact, multi-segment movement and bounded catch-up on A500 and A500+Fast','cases_per_profile':counts,'profiles':{},'candidate_base_commit':'aab718602c8a8767fd0616d549e057806b8470d0','runtime_changes':False}
for profile in ('a500','a500-fast'):
 evidence=[]
 for kind,n in counts.items():
  p=r/f'manifest/step5-c4-q02-{kind}-{profile}.json';j=json.loads(p.read_text());assert j['status']=='passed';assert len(j['cases'])==n
  raw=r/f'tmp/step5/c4-q02-{kind}-{profile}-candidate/result.json';v=json.loads(raw.read_text());assert v['status']=='complete' and v['state']['error']==0 and v['state']['C1Completed']-v['start']['C1Completed']==20 and v['context'][7]==200
  assert v['slave_sha256']==hashlib.sha256((r/f'tmp/build/step5-c4-q02-{kind}/000/candidate.slave').read_bytes()).hexdigest()
  evidence.append({'manifest':str(p.relative_to(r)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'candidate_sha256':v['slave_sha256']})
 p=r/f'tmp/step5/c4-q02-debt-{profile}-candidate/result.json';j=json.loads(p.read_text());assert j['status']=='complete' and j['contact']['error']==0 and j['recovery_steps'] is not None
 report['profiles'][profile]={'evidence':evidence,'cases':sum(counts.values()),'ordinary_updates_after_each_suite':20,'debt_result':str(p.relative_to(r)),'peak_pending_intervals':j['peak_pending_intervals'],'recovery_steps':j['recovery_steps'],'wall_hits':j['contact']['C2WallHits']}
report['fixture_corrections']=['Original contact model omitted native sideways impulse; corrected expected integer and independently checked preserved tail.','Initial crossing frame overlapped native SP+16 scratch with fixture local angle; enlarged fixture frame, unchanged mathematical oracle then passed.','Combined 528-case work fixture overflowed signed public_bindings-FF1VelocityRotate000 offset (0x8f04); isolated added 96 off-road cases and added signed-offset guard. Original 432-case suite retained.','Forced-wall native boundary can be visited more than once per step: verify exact steps 11..20, actual hits and full elapsed/consumed accounting, not a fixed injection count.']
p=repo/'Games/FerrariFormulaOne_Coarse200Motion.s';s=p.read_text();old='; native integer. These checks do not replace wall/multi-segment/modal tests.';new='''; native integer. Final Q02 checks also cover scalar-speed resets/exchange,
; 432 work/wall/recovery writers, 96 off-road writes and 72 full multi-segment
; paths on A500 and A500+Fast: 768 cases per profile, each suite restored before
; 20 ordinary updates. Bounded forced-wall debt is accounted without deletion.
; Evidence: tmp/dev/manifest/step5-c4-q02-validation.json. Real modal Q03 remains
; separate; these ownership checks do not establish keyboard or menu behavior.''';assert old in s;p.write_text(s.replace(old,new));report['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()}
report['harness_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((r/'tools').glob('*step5_c4_q02*')) if p.is_file()}
(r/'manifest/step5-c4-q02-validation.json').write_text(json.dumps(report,indent=2)+'\n')
p=r/'manifest/step5-c4-open-cases.json';j=json.loads(p.read_text());q=next(x for x in j['cases'] if x['id']=='C4-Q02');q['status']='closed';q['resolution']={'evidence':'manifest/step5-c4-q02-validation.json','scope':'768 independent cases per A500/A500+Fast plus 50-update bounded wall/debt episode each; restored state, no runtime changes'};p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'manifest/project.json';j=json.loads(p.read_text());j['step5_c4_q02_validation']='tmp/dev/manifest/step5-c4-q02-validation.json';j['step5_c4_q02_status']='Closed: 768 independent ownership/contact/movement cases per A500/A500+Fast, restored state, 20 ordinary updates after each suite; bounded 50-update wall/debt episodes pass. Q03 remains open.';j['next_steps'][0]='Complete C4-Q03 actual keyboard delivery and pause/menu/pit/session transitions. Q01 and Q02 are closed with independent evidence.';j['step5_status']=j['step5_status'].replace('C4-Q01/Q02/Q03,','C4-Q03,');p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'docs/STEP5_CAPACITY.md';s=p.read_text();assert '### C4-Q02 correctness closure' not in s
s+='''\n### C4-Q02 correctness closure (2026-10-14)

Q02 is closed on final R3g, on A500 and A500+Fast. Each profile passes 768
independent cases: 56 position save/reset/restore, 56 vector/scalar cold writes,
56 contacts (all 28 car pairs, both directions), 432 working wall/recovery
writers, 96 off-road writes and 72 complete multiple-segment paths. Every suite
restores native code/state and shadows, then completes 20 ordinary updates with
error zero and the 200 ms interval. No game-code defect was found.

The contact oracle checks native reference arrays plus independently seeded
scalar and vector fractions/carries, sideways integer impulses and position-tail
assignment. Work writers check every non-target owner. The segment oracle
models integration and per-product native Q15 rounding through two or more
actual native segment transitions, for straight, constant-turn and alternating
turn tracks with three transverse velocities, on every car. It is independent
of optimization A/B equality; lap wrap is outside these directed cases.

Both profiles also complete 50 warp-off updates with wall forcing restricted
to steps 11..20. Actual wall hits, all elapsed/consumed units and the return
below one pending interval are recorded; no pause exclusion or debt deletion
is used. This establishes recovery for the bounded episode, not an arbitrary
worst-case catch-up guarantee.
'''
for profile,v in report['profiles'].items():s+=f"\n- {profile}: {v['wall_hits']} wall hits; peak pending {v['peak_pending_intervals']:.9f} intervals; recovered {v['recovery_steps']} update(s) after forcing ended.\n"
s+='''
Fixture failures remain documented: the initial contact model omitted sideways
impulses; the first crossing frame overlapped a native stack scratch slot; and
the combined work fixture exceeded a signed 16-bit binding-table offset. The
corrected fixtures use the same independent expected behavior. The work suite
is split into its original 432 cases and 96 added off-road cases, with a size
guard. Repeated native boundary visits are counted within the exact forcing
window rather than assuming one injection per update.

Evidence: `manifest/step5-c4-q02-validation.json` contains all suite manifests,
binary/harness hashes and debt result paths. Game-source edits are comments
only. Existing R3g exact-state/frame/elapsed/legacy gates remain applicable to
the byte-identical production candidate. Q03 actual input/modal coverage and
Step 5 production acceptance remain open; default-off and no fallback remain.
''';p.write_text(s)
(r/'tmp/step5/q02-commit-message.txt').write_text('Document complete C4 native ownership and movement checks\n\nRecord 768 independent cases on each 68000 memory profile and bounded\nforced-wall debt recovery. Preserve the separate actual-input/modal gate.\nNo executable game instructions change.\n')
print(json.dumps(report['profiles'],indent=2))
