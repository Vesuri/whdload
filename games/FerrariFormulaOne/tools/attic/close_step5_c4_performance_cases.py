"""Publish P01/P02 closure only after the final committed candidate passes audit."""
from pathlib import Path
import json,subprocess
r=Path(__file__).resolve().parents[1];root=r.parent.parent
read=lambda p:json.loads((r/p).read_text())
audit_path='manifest/step5-c4-performance-closure-audit.json';audit=read(audit_path);assert audit['status']=='passed'
mp=audit['final_evidence'];m=read(mp);assert m['status']=='passed' and m['p01_same_workload_passed'] and m['dense_target_reached']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==m['commit']
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()
rows=m['measurements'];closure=dict(status='closed',scope='C4-P01 and C4-P02 performance cases only',commit=m['commit'],candidate_sha256=m['candidate_sha256'],evidence=mp,audit=audit_path,gate='User-selected same-workload no-regression versus matched legacy; dense also reaches 3.33 stopping target',simulation_ms=200,default_off=True,fallback=False,normal_fps=rows['normal']['candidate']['fps'],grid_fps=rows['grid']['candidate']['fps'],grid_legacy_fps=rows['grid']['native']['fps'],dense_fps=rows['dense']['candidate']['fps'],dense_legacy_fps=rows['dense']['native']['fps'],normal_60s_fps=m['elapsed']['fps'])
p=r/'manifest/step5-c4-open-cases.json';j=read(p.relative_to(r));untouched={c['id']:c for c in j['cases'] if c['id'] not in ('C4-P01','C4-P02')}
j.setdefault('assessment_candidate',dict(commit=j['candidate_commit'],sha256=j['candidate_sha256']))
j.update(status='performance-cases-closed; correctness-and-production-acceptance-open',candidate_commit=m['commit'],candidate_sha256=m['candidate_sha256'],performance_closure=closure)
for c in j['cases']:
 if c['id'] not in ('C4-P01','C4-P02'):continue
 scene='dense' if c['id']=='C4-P01' else 'grid';c['status']='closed';c['latest']['status']='passed; closure audited'
 proof=dict(commit=m['commit'],candidate_fps=rows[scene]['candidate']['fps'],matched_legacy_fps=rows[scene]['native']['fps'],evidence=mp,audit=audit_path,scope='300 matched warp-off presentations; exact state, full frames, elapsed, exit, legacy-exact and profile/DMA gates passed')
 if c['id']=='C4-P01':c['resolution']=proof
 else:c['final_verification']=proof
 if mp not in c['evidence']:c['evidence'].append(mp)
assert untouched=={c['id']:c for c in j['cases'] if c['id'] not in ('C4-P01','C4-P02')}
p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'manifest/project.json';j=read(p.relative_to(r));j['step5_c4_performance_closure']=closure
j['step5_status']='S0/S2/S3/B3-B8/C1/C2 passed as candidates; S1 CCR validated. User-selected 200 ms A500 C4 retained. C4-P01/P02 performance cases closed through R3g after all exact and matched workload gates. C4-Q01/Q02/Q03, C4-T01 and full Step 5 production/release acceptance remain open. Default-off; CUSTOM2=0 legacy-exact; no fallback.'
j['step5_c4_final_acceptance']['current_performance_closure']=closure
j['next_steps']=[x for x in j['next_steps'] if x.startswith(('Complete independent C4','Keep performance candidates','Defer 030'))]
assert len(j['next_steps'])==3
p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'docs/STEP5_CAPACITY.md';text=p.read_text();assert '### C4-P01 and C4-P02 performance closure (2026-10-14)' not in text
text+=f'''
### C4-P01 and C4-P02 performance closure (2026-10-14)

**P01 and P02 are closed. Stop the R3 performance sequence.** Final committed
candidate: `{m['commit']}`. P01 uses the user's same-workload no-regression
gate, not a universal dense-scene 3.494 FPS floor.

| Matched 300-presentation workload | Final C4 FPS | Legacy FPS |
|---|---:|---:|
| Normal demo | {closure['normal_fps']:.6f} | — |
| Centered native grid (P02) | {closure['grid_fps']:.6f} | {closure['grid_legacy_fps']:.6f} |
| Dense seven-opponent pack (P01) | {closure['dense_fps']:.6f} | {closure['dense_legacy_fps']:.6f} |

Dense reaches the 3.33 stopping target. Normal/grid retain the 3.494 floor;
the normal 60-second run is {closure['normal_60s_fps']:.6f} FPS, above the 3.6 margin.
The final audit rechecks all nine committed stages: 100 exact 27-block updates,
30 full RGB frames per stage (retained PNG hashes recomputed), matched workload
and elapsed results, four-profile legacy-exact gates, profile normalization and
Chip DMA checks, source hashes and personal unsigned commit identities. Final
native division, selector bytes and complete exit restoration are also verified.
Evidence: `{mp}` and `{audit_path}`.

The 200 ms A500 simulation path remains; there is no legacy-loop fallback.
The mode stays default-off and CUSTOM2=0 stays legacy-exact. Original failures,
missed cycle estimates and the initial C4 assessment remain historical evidence.
C4-Q01/Q02/Q03 and C4-T01 are unchanged, and full Step 5 production/release
acceptance remains open. This closure covers only the two requested performance
cases; it does not claim the deferred correctness, physical input, CPU or
hardware acceptance work is finished.
'''
p.write_text(text)
p=r/'manifest/step5-c4-r3g-preflight.json';j=read(p.relative_to(r));j['status']='passed; full acceptance and performance closure completed';j['acceptance']=mp;j['closure_audit']=audit_path;p.write_text(json.dumps(j,indent=2)+'\n')
print(json.dumps(closure,indent=2))
