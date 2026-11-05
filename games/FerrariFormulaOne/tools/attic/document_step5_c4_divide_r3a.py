from pathlib import Path
import json
r=Path(__file__).resolve().parents[1]
p=r/'manifest/step5-c4-divide-r3a-validation.json';m=json.loads(p.read_text());assert m['status']=='passed'
rows=m['measurements']; fmt=lambda x:f'{x:.6f}'
table='\n'.join('| '+n+' | '+fmt(rows[k]['baseline-render']['fps'])+' | '+fmt(rows[k]['candidate']['fps'])+' | '+(fmt(rows[k]['native']['fps']) if 'native' in rows[k] else '—')+' |' for n,k in [('Normal demo','normal'),('Centered native grid','grid'),('Dense pack','dense')])
text=f'''
### R3a accepted (2026-10-14); P01 requires R3b

The positive division path uses native DIVU when its quotient fits, an exact
2 KiB public-memory table for positive /10 inputs <=1023, a bounded reciprocal
for /56 inputs <=1048575, and an exact fold guarded on both operands of the
repeated 0x3fc000/700000 pair. Other inputs retain the general signed helper.
The fixed branch selector gives equal-layout A/B without a per-call memory test.
The disabled build exactly reproduces accepted R2. Default-off remains unchanged.

| 300 presentations, warp off | R3a-disabled C4 | R3a | Legacy |
|---|---:|---:|---:|
{table}

145536 native comparisons cover quotient, remainder, all 32 CCR inputs and
preserved registers. The /56 model was exhausted over all 1048576 bounded inputs;
the guest oracle includes every table entry. All 100 updates match the unchanged
27-block state gate; 30 full RGB frames, native exit restoration and four-profile
CUSTOM2=0 checks pass. Elapsed error is {m['elapsed']['error_percent']:.7f}%, with
{m['elapsed']['fps']:.6f} FPS and both clocks advancing 600 tenths.

Matched 100-field profiles reduce logic excluding presentation from
558903.5556 to 544464.2222 cycles/update: 14439.3333 cycles (2.03549 ms).
Division helpers save 16148 cycles; the planned 20000-cycle target is NOT met.
All three analyser totals, normalization and actual Chip DMA gates pass. Traces
are verified compressed. Evidence: `manifest/step5-c4-divide-r3a-validation.json`.

An initial diagnostic flagged a stale line-mode A pointer after the blitter had
finished. BUSY was clear, and the next setup instruction replaced it with a Chip
pointer before BLTSIZE. No actual non-Chip DMA occurred. The audit now distinguishes
inactive register contents from active DMA; every recorded DMA address remains
strictly checked. Original failure and proof are retained in
`manifest/step5-c4-r3a-idle-pointer.json`; this changes no game code or exact gate.

P02 remains closed; P01 still fails same-workload no-regression and dense <3.33.
Proceed to R3b in plan order, retaining the 200 ms path with no fallback. Rotation
histogram: only 169/666 general cosine products fit signed 16 bits, while
cosine=32767/sine=0 appears 126 times. An exact Q15 shortcut for that observed
case is independently modelled; implementation and all acceptance gates remain
pending. Do not assume zero sine means identity: Q15 rounding must be preserved.
'''
doc=r/'docs/STEP5_CAPACITY.md';old=doc.read_text();assert '### R3a accepted (2026-10-14)' not in old;doc.write_text(old+text)
p=r/'manifest/project.json';j=json.loads(p.read_text());j['step5_c4_r3a_status']='Passed as default-off candidate: normal %.5f, grid %.5f, dense %.5f vs legacy %.5f FPS. 145536 native arithmetic cases, 100 exact updates, 30 full RGB frames, elapsed, exit, four-profile legacy and full-loop/DMA pass. Logic saves 14439 cycles/update; 20k target unmet. P01 open, next R3b.'%(rows['normal']['candidate']['fps'],rows['grid']['candidate']['fps'],rows['dense']['candidate']['fps'],rows['dense']['native']['fps']);j['step5_c4_r3a_validation']='tmp/dev/manifest/step5-c4-divide-r3a-validation.json';p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'manifest/step5-c4-open-cases.json';j=json.loads(p.read_text());j['latest_accepted_performance_change']=dict(step='R3a',evidence='manifest/step5-c4-divide-r3a-validation.json');j['closing_plan'].pop('gate_decision_pending',None)
for c in j['cases']:
 if c['id'] in ('C4-P01','C4-P02'):
  scene='dense' if c['id']=='C4-P01' else 'grid';c['latest']=dict(after='R3a',candidate_fps=rows[scene]['candidate']['fps'],matched_legacy_fps=rows[scene]['native']['fps'],status='open; next R3b' if scene=='dense' else 'still passed')
p.write_text(json.dumps(j,indent=2)+'\n')
(r/'tmp/step5/r3a-commit-message.txt').write_text('Accelerate exact positive division in the 200 ms path\n\n'+text.split('### R3a accepted (2026-10-14); P01 requires R3b\n',1)[1].strip()+'\n')
print(table)
