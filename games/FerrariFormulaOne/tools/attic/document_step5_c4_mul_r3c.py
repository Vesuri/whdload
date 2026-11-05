from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];mp=r/'manifest/step5-c4-mul-r3c-validation.json';m=json.loads(mp.read_text());assert m['status']=='passed'
rows=m['measurements'];fmt=lambda x:f'{x:.6f}'
table='\n'.join('| '+n+' | '+fmt(rows[k]['baseline-render']['fps'])+' | '+fmt(rows[k]['candidate']['fps'])+' | '+(fmt(rows[k]['native']['fps']) if 'native' in rows[k] else '—')+' |' for n,k in [('Normal demo','normal'),('Centered native grid','grid'),('Dense pack','dense')])
passed=m['p01_same_workload_passed'];more=m['r3d_required']
text=f'''
### R3c accepted (2026-10-14)

Three histogram-selected native multiply calls ($675a6, $6ea30 and $6cd5c)
now use guarded word/long products. The patch spans include the next overwrite
of D1; every register, stack value, low-32 product and XNZVC agrees at that
boundary. Nonpositive or out-of-range operands retain the previous multiply.
Native signatures are checked before patching, and the existing whole-hunk
ledger restores every changed byte on exit. All code uses the public owner.
One installation selector selects equal-layout arms. The compile flag absent
build exactly reproduces accepted R3b. The largest diagnostic hosts use an
existing near code anchor to keep installer references in 68000 PC-relative range.

| 300 presentations, warp off | R3c-disabled C4 | R3c | Legacy |
|---|---:|---:|---:|
{table}

187776 native comparisons pass: 5868 operand/register cases at all 32 input
CCR combinations, checking D0-D5, SP and full CCR after the original D1 overwrite.
Cases include signed-word limits, wide range misses, zero/negative fallbacks,
independent D2 inputs and cross-product carries. All 100 updates match the
unchanged 27-block state inventory; all 30 full RGB frames, native exit restoration
and four-profile CUSTOM2=0 checks pass. The 60-second test has
{m['elapsed']['error_percent']:.7f}% elapsed error and {m['elapsed']['fps']:.6f} FPS.

Matched 100-field logic excluding presentation falls from
{m['logic_cycles_control']:.4f} to {m['logic_cycles_candidate']:.4f} cycles/update:
{m['logic_saved_cycles']:.4f} cycles ({m['logic_saved_ms']:.5f} ms). The planned
12000-cycle saving is {'met' if m['plan_target_met'] else 'NOT met'}. All three analyser totals, normalization and
Chip DMA gates pass; traces are verified compressed. Evidence:
`manifest/step5-c4-mul-r3c-validation.json`. Default-off, 200 ms and no fallback
remain unchanged. P02 remains closed. P01 same-workload gate: {'passed' if passed else 'not passed'}.
{'Dense remains below 3.33; continue with R3d in histogram order.' if more else 'Dense reaches 3.33; stop the R3 optimization sequence.'}
'''
p=r/'docs/STEP5_CAPACITY.md';old=p.read_text();assert '### R3c accepted (2026-10-14)' not in old;p.write_text(old+text)
p=r/'manifest/project.json';j=json.loads(p.read_text());j['step5_c4_r3c_status']='Passed as default-off candidate: normal %.5f, grid %.5f, dense %.5f vs legacy %.5f FPS; all arithmetic/state/frame/elapsed/exit/legacy/profile/DMA checks pass. Logic saving and 12k target outcome are recorded in the validation manifest.'%(rows['normal']['candidate']['fps'],rows['grid']['candidate']['fps'],rows['dense']['candidate']['fps'],rows['dense']['native']['fps']);j['step5_c4_r3c_validation']='tmp/dev/manifest/step5-c4-mul-r3c-validation.json';j['next_steps'][0]='Close dense-pack P01 with R3d; accepted through R3c. P02 remains closed. Preserve 200 ms, default-off and all matched workload/exact gates.' if more else 'R3 reached its dense target; audit C4-P01 and C4-P02 closure evidence.';p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'manifest/step5-c4-open-cases.json';j=json.loads(p.read_text());j['latest_accepted_performance_change']=dict(step='R3c',evidence='manifest/step5-c4-mul-r3c-validation.json')
for c in j['cases']:
 if c['id'] in ('C4-P01','C4-P02'):
  scene='dense' if c['id']=='C4-P01' else 'grid';c['latest']=dict(after='R3c',candidate_fps=rows[scene]['candidate']['fps'],matched_legacy_fps=rows[scene]['native']['fps'],status=('passed' if passed else 'open; next R3d') if scene=='dense' else 'still passed')
p.write_text(json.dumps(j,indent=2)+'\n')
(r/'tmp/step5/r3c-commit-message.txt').write_text('Inline three exact native multiply sites in the 200 ms path\n\n'+text.split('### R3c accepted (2026-10-14)\n',1)[1].strip()+'\n');print(table)
