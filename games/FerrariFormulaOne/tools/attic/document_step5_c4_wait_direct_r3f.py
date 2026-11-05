from pathlib import Path
import json
r=Path(__file__).resolve().parents[1]
mp='manifest/step5-c4-wait-direct-r3f-validation.json'
m=json.loads((r/mp).read_text());assert m['status']=='passed'
rows=m['measurements'];fmt=lambda x:f'{x:.6f}'
table='\n'.join('| '+n+' | '+fmt(rows[k]['baseline-render']['fps'])+' | '+fmt(rows[k]['candidate']['fps'])+' | '+(fmt(rows[k]['native']['fps']) if 'native' in rows[k] else '—')+' |' for n,k in [('Normal demo','normal'),('Centered native grid','grid'),('Dense pack','dense')])
passed=m['p01_same_workload_passed'];target=m['dense_target_reached'];exit_report=json.loads((r/m['exit']).read_text())
next_work='Dense reaches 3.33; stop the R3 optimization sequence and audit P01/P02 closure.' if target and passed else 'Dense remains below the stopping target; re-profile remaining cost before another change.'
text=f'''
### R3f accepted (2026-10-14)

Twenty histogram-selected absolute JSR destinations now call the existing R1
WaitBlit helper directly, removing the intermediate native JMP. Every original
opcode and relocated destination is checked before any operand is changed.
The return address, registers, settling reads, final status flags and busy path
are unchanged. Tail JMP and private host callers retain the existing route.
All writes belong to the hunk ledger; both A/B arms validate the same sites.
One installation word selects equal-layout arms. Without FF1_C4_WAIT_DIRECT,
the build reproduces accepted R3e exactly. Arithmetic sources are unchanged.

| 300 presentations, warp off | R3f-disabled C4 | R3f | Legacy |
|---|---:|---:|---:|
{table}

All 100 updates match the unchanged 27-block state inventory, all 30 full RGB
frames match, and CUSTOM2=0 matches the release on all four profiles. The exit
fixture confirms active direct routing and native restoration at all 20 sites,
and checks all {exit_report['ledger_restore_checked_words']} recorded patch words.
The 60-second test has {m['elapsed']['error_percent']:.7f}% elapsed error and
{m['elapsed']['fps']:.6f} FPS. The 200 ms simulation interval, default-off mode
and no-fallback decision remain unchanged.

The matched 100-field traces pass all three analyser totals, instruction-cost
normalization and actual Chip DMA checks, and are verified compressed. Logic
excluding presentation measures {m['logic_cycles_control']:.4f} to
{m['logic_cycles_candidate']:.4f} cycles/update (difference
{m['logic_saved_cycles']:.4f}); this is a rendering-call optimization and the
untraced workload timings above are the acceptance evidence.
Evidence: `{mp}`. P02 remains closed. P01 same-workload gate:
{'passed' if passed else 'not passed'}. {next_work}
'''
if not target:
 text+='\nFresh R3f trace: the short-divisor path executes 662 times over 100 fields.\nR3g will test guarding DIVU by swapping D0 instead of saving D2, then unpack\nquotient/remainder directly without register-save frames. Preserve all native\nflags and the full-domain fallback; validate against native division before\nmatched integration tests. The largest remaining arithmetic label is division\n(35599 cycles/update in classification). Evidence: division-histogram.json in\n`tmp/step5/c4-wait-direct-r3f-v1-fullloop-a500-candidate`. Stop at 3.33 and retain\nthe same-workload and exact gates. No interval or fallback change.\n'
p=r/'docs/STEP5_CAPACITY.md';old=p.read_text();assert '### R3f accepted (2026-10-14)' not in old;p.write_text(old+text)
p=r/'manifest/project.json';j=json.loads(p.read_text());j['step5_c4_r3f_status']='Accepted default-off candidate; normal %.6f, grid %.6f, dense %.6f versus legacy %.6f FPS. Exact-state/frame/elapsed/exit/legacy/profile/DMA gates passed.'%(rows['normal']['candidate']['fps'],rows['grid']['candidate']['fps'],rows['dense']['candidate']['fps'],rows['dense']['native']['fps']);j['step5_c4_r3f_validation']='tmp/dev/'+mp;j['next_steps'][0]=next_work;p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'manifest/step5-c4-open-cases.json';j=json.loads(p.read_text());j['latest_accepted_performance_change']=dict(step='R3f',evidence=mp)
for c in j['cases']:
 if c['id'] in ('C4-P01','C4-P02'):
  scene='dense' if c['id']=='C4-P01' else 'grid';c['latest']=dict(after='R3f',candidate_fps=rows[scene]['candidate']['fps'],matched_legacy_fps=rows[scene]['native']['fps'],status=('passed; closure audit pending' if passed else 'open') if scene=='dense' else 'still passed')
p.write_text(json.dumps(j,indent=2)+'\n')
(r/'tmp/step5/r3f-commit-message.txt').write_text('Route measured WaitBlit calls directly to the idle helper\n\n'+text.split('### R3f accepted (2026-10-14)\n',1)[1].strip()+'\n');print(table)
