from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];mp='manifest/step5-c4-divide-frame-r3g-validation.json';m=json.loads((r/mp).read_text());assert m['status']=='passed'
rows=m['measurements'];fmt=lambda x:f'{x:.6f}'
table='\n'.join('| '+n+' | '+fmt(rows[k]['baseline-render']['fps'])+' | '+fmt(rows[k]['candidate']['fps'])+' | '+(fmt(rows[k]['native']['fps']) if 'native' in rows[k] else '—')+' |' for n,k in [('Normal demo','normal'),('Centered native grid','grid'),('Dense pack','dense')])
passed=m['p01_same_workload_passed'];target=m['dense_target_reached'];exit_report=json.loads((r/m['exit']).read_text());oracle=json.loads((r/m['arithmetic_oracle']).read_text())
next_work='Dense reaches 3.33; stop the R3 optimization sequence and audit P01/P02 closure.' if target and passed else 'Dense remains below the stopping target; re-profile remaining cost before another change.'
text=f'''
### R3g accepted (2026-10-14)

The positive short-divisor path now checks quotient fit by swapping D0, without
saving D2. It unpacks the DIVU remainder and quotient directly into zero-extended
D1/D0. A word add clears X and a long test restores the exact native quotient
flags. A wide quotient restores D0 before entering the unchanged general path;
zero/negative operands and existing constant-divisor paths retain their logic.
The four-byte selector replaces the original save/move pair in the candidate;
the control executes those original instructions. The helper remains in the
existing public owner. Global labels expose the exact patch site; with the
feature absent, the complete slave is byte-identical to accepted R3f.

| 300 presentations, warp off | R3g-disabled C4 | R3g | Legacy |
|---|---:|---:|---:|
{table}

{oracle['expected']['comparisons']} comparisons against original native division pass at all 32 input CCR
values, checking quotient/remainder, D2-D5 and SP, including directed 16-bit
quotient overflow boundaries and full-width signed range misses. All 100 updates
match the unchanged 27-block inventory, all 30 full RGB frames match, and
CUSTOM2=0 remains release-exact on all four profiles. Exit restores all
{exit_report['ledger_restore_checked_words']} recorded patch words, including all 20 direct WaitBlit sites.
The 60-second test has {m['elapsed']['error_percent']:.7f}% elapsed error and
{m['elapsed']['fps']:.6f} FPS; both clocks advance by 600 tenths. The 200 ms
simulation interval, default-off mode and no-fallback decision remain unchanged.

Matched 100-field logic excluding presentation falls from
{m['logic_cycles_control']:.4f} to {m['logic_cycles_candidate']:.4f} cycles/update,
saving {m['logic_saved_cycles']:.4f} cycles ({m['logic_saved_ms']:.5f} ms).
All three analyser totals, normalization and actual Chip DMA checks pass, and
traces are verified compressed. Evidence: `{mp}`.
P02 remains closed. P01 same-workload gate: {'passed' if passed else 'not passed'}.
{next_work}

This closes performance work only if the final closure audit passes. C4-Q01,
C4-Q02, C4-Q03, C4-T01 and production/release acceptance remain separate; no
universal FPS floor or completion of those correctness cases is claimed.
'''
p=r/'docs/STEP5_CAPACITY.md';old=p.read_text();assert '### R3g accepted (2026-10-14)' not in old;p.write_text(old+text)
p=r/'manifest/project.json';j=json.loads(p.read_text());j['step5_c4_r3g_status']='Accepted default-off candidate: normal %.6f, grid %.6f, dense %.6f vs legacy %.6f FPS. Native arithmetic/state/frame/elapsed/exit/legacy/profile/DMA gates passed.'%(rows['normal']['candidate']['fps'],rows['grid']['candidate']['fps'],rows['dense']['candidate']['fps'],rows['dense']['native']['fps']);j['step5_c4_r3g_validation']='tmp/dev/'+mp;j['next_steps'][0]=next_work;p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'manifest/step5-c4-open-cases.json';j=json.loads(p.read_text());j['latest_accepted_performance_change']=dict(step='R3g',evidence=mp)
for c in j['cases']:
 if c['id'] in ('C4-P01','C4-P02'):
  scene='dense' if c['id']=='C4-P01' else 'grid';c['latest']=dict(after='R3g',candidate_fps=rows[scene]['candidate']['fps'],matched_legacy_fps=rows[scene]['native']['fps'],status=('passed; closure audit pending' if passed else 'open') if scene=='dense' else 'still passed')
p.write_text(json.dumps(j,indent=2)+'\n')
(r/'tmp/step5/r3g-commit-message.txt').write_text('Remove register frames from exact short division\n\n'+text.split('### R3g accepted (2026-10-14)\n',1)[1].strip()+'\n');print(table)
