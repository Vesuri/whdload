from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];mp=r/'manifest/step5-c4-rotate-r3b-validation.json';m=json.loads(mp.read_text());assert m['status']=='passed'
rows=m['measurements'];fmt=lambda x:f'{x:.6f}'
table='\n'.join('| '+n+' | '+fmt(rows[k]['baseline-render']['fps'])+' | '+fmt(rows[k]['candidate']['fps'])+' | '+(fmt(rows[k]['native']['fps']) if 'native' in rows[k] else '—')+' |' for n,k in [('Normal demo','normal'),('Centered native grid','grid'),('Dense pack','dense')])
passed=m['p01_same_workload_passed'];more=m['r3c_required']
text=f'''
### R3b accepted (2026-10-14)

Rotation cosine products now use one signed multiply when the component fits
signed 16 bits. The measured common cosine=32767/sine=0 case uses the exact
identity floor(n*32767/32768)=n-ceil(n/32768); it preserves native Q15 shrinkage,
including negative fractions. Other coefficients and wide components retain the
existing algorithms. Three fixed branch operands select the equal-layout arms.
The compile flag absent build exactly reproduces accepted R3a.

| 300 presentations, warp off | R3b-disabled C4 | R3b | Legacy |
|---|---:|---:|---:|
{table}

8527 independent integer-model arithmetic/conversion cases pass, including
signed-word transitions, coefficient extremes, negative rounding and atomic
rollback. The independent rounding identity also passes all low words at nine
signed high-word boundaries (589824 cases). All 100 updates match the unchanged
27-block state inventory; all 30 full RGB frames, native exit restoration and
four-profile CUSTOM2=0 checks pass. The 60-second test has
{m['elapsed']['error_percent']:.7f}% elapsed error and {m['elapsed']['fps']:.6f} FPS.

Matched 100-field logic excluding presentation falls from
{m['logic_cycles_control']:.4f} to {m['logic_cycles_candidate']:.4f} cycles/update:
{m['logic_saved_cycles']:.4f} cycles ({m['logic_saved_ms']:.5f} ms). The planned
15000-cycle saving is NOT met. All three analyser totals, normalization and
Chip DMA gates pass; traces are verified compressed. Evidence:
`manifest/step5-c4-rotate-r3b-validation.json`. Default-off, 200 ms and no fallback
remain unchanged. P02 remains closed. P01 same-workload gate: {'passed' if passed else 'not passed'}.
{'Dense remains below 3.33; continue with R3c in histogram order.' if more else 'Dense reaches 3.33; stop the R3 optimization sequence.'}
'''
p=r/'docs/STEP5_CAPACITY.md';old=p.read_text();assert '### R3b accepted (2026-10-14)' not in old;p.write_text(old+text)
p=r/'manifest/project.json';j=json.loads(p.read_text());j['step5_c4_r3b_status']='Passed as default-off candidate: normal %.5f, grid %.5f, dense %.5f vs legacy %.5f FPS; all arithmetic/state/frame/elapsed/exit/legacy/profile/DMA checks pass. Logic saves 10054 cycles/update; 15k target unmet.'%(rows['normal']['candidate']['fps'],rows['grid']['candidate']['fps'],rows['dense']['candidate']['fps'],rows['dense']['native']['fps']);j['step5_c4_r3b_validation']='tmp/dev/manifest/step5-c4-rotate-r3b-validation.json';p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'manifest/step5-c4-open-cases.json';j=json.loads(p.read_text());j['latest_accepted_performance_change']=dict(step='R3b',evidence='manifest/step5-c4-rotate-r3b-validation.json')
for c in j['cases']:
 if c['id'] in ('C4-P01','C4-P02'):
  scene='dense' if c['id']=='C4-P01' else 'grid';c['latest']=dict(after='R3b',candidate_fps=rows[scene]['candidate']['fps'],matched_legacy_fps=rows[scene]['native']['fps'],status=('passed' if passed else 'open; next R3c') if scene=='dense' else 'still passed')
p.write_text(json.dumps(j,indent=2)+'\n')
(r/'tmp/step5/r3b-commit-message.txt').write_text('Reduce exact Q15 rotation cost in the 200 ms path\n\n'+text.split('### R3b accepted (2026-10-14)\n',1)[1].strip()+'\n');print(table)
