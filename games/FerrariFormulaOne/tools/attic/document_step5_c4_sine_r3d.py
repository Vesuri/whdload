from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];mp=r/'manifest/step5-c4-sine-r3d-validation.json';m=json.loads(mp.read_text());assert m['status']=='passed'
rows=m['measurements'];fmt=lambda x:f'{x:.6f}'
table='\n'.join('| '+n+' | '+fmt(rows[k]['baseline-render']['fps'])+' | '+fmt(rows[k]['candidate']['fps'])+' | '+(fmt(rows[k]['native']['fps']) if 'native' in rows[k] else '—')+' |' for n,k in [('Normal demo','normal'),('Centered native grid','grid'),('Dense pack','dense')])
passed=m['p01_same_workload_passed'];more=m['further_work_required']
text=f'''
### R3d accepted (2026-10-14)

The two measured rotation sine products now use the enclosing routine's
already-saved D6/D7 scratch registers, removing nested save/restore frames and
subroutine entry/return. Zero and integer-Q16 shortcuts and the exact two-part
signed product are unchanged. Other shared-helper callers keep their D2/D3
preservation; a fixed selector skips the old per-call diagnostic memory test.
Three fixed branch operands select the equal-layout arms. CPU code remains in
the existing public owner. The compile flag absent build reproduces accepted
R3c exactly. Larger diagnostic hosts use range-safe installer references.

| 300 presentations, warp off | R3d-disabled C4 | R3d | Legacy |
|---|---:|---:|---:|
{table}

8527 independent integer-model cases pass for the twelve 200 ms conversion
primitives, including full signed inputs, coefficient extremes, negative rounding,
atomic error rollback and register/stack preservation. All 100 updates match the
unchanged 27-block state inventory; all 30 full RGB frames, native exit restoration
and four-profile CUSTOM2=0 checks pass. The 60-second test has
{m['elapsed']['error_percent']:.7f}% elapsed error and {m['elapsed']['fps']:.6f} FPS.

Matched 100-field logic excluding presentation falls from
{m['logic_cycles_control']:.4f} to {m['logic_cycles_candidate']:.4f} cycles/update:
{m['logic_saved_cycles']:.4f} cycles ({m['logic_saved_ms']:.5f} ms). The planned
13000-cycle saving is {'met' if m['plan_target_met'] else 'NOT met'}. All three analyser totals, normalization and
Chip DMA gates pass; traces are verified compressed. Evidence:
`manifest/step5-c4-sine-r3d-validation.json`. Default-off, 200 ms and no fallback
remain unchanged. P02 remains closed. P01 same-workload gate: {'passed' if passed else 'not passed'}.
{'Dense remains below 3.33; re-profile the remaining cost before further changes.' if more else 'Dense reaches 3.33; stop the R3 optimization sequence.'}
'''
if more:
 text+='\n#### Measured follow-up after the original R3a-R3d sequence\n\nThe planned cycle savings were estimates; the accepted steps have not yet\nclosed P01. Preserve the user-selected same-workload gate and 3.33 working\nstop target, with no cadence change, fallback or gate relaxation.\n\nThe fresh 100-field R3d trace contains 700 unsigned-word native products,\n179 signed-word products, 220 zero cases and 83 positive word/long cases.\nR3e will test guarded native products without register-save frames, preserving\nD1-D7/A0-A6 and native XNZVC. The isolated mathematical model passes 1248576\ncomparisons; native guest execution and all integration gates remain required.\n\nIf R3e still misses the target, test direct calls to the existing idle WaitBlit\nhelper. The native stub accounts for 58168 instruction cycles across 4137 calls\nin this entire trace (not a measured saving per update). The original and current\nabsolute JSR instructions match at all eligible observed native call sites;\nonly their destination operands would change. Retain the existing busy path,\nsettling reads, final status flags and ledger restoration. Tail JMP and host\ncallers are outside that initial candidate. Stop once the target and all exact\nand same-workload gates pass.\n\nPlanning evidence: `manifest/step5-c4-native-frame-next-model.json`,\n`manifest/step5-c4-wait-direct-planning.json`, and the native-multiply-groups\nand wait-call-histogram files under the R3d candidate full-loop trace.\n'
p=r/'docs/STEP5_CAPACITY.md';old=p.read_text();assert '### R3d accepted (2026-10-14)' not in old;p.write_text(old+text)
p=r/'manifest/project.json';j=json.loads(p.read_text());j['step5_c4_r3d_status']='Passed as default-off candidate: normal %.5f, grid %.5f, dense %.5f vs legacy %.5f FPS; all arithmetic/state/frame/elapsed/exit/legacy/profile/DMA checks pass. Logic saving and 13k target outcome are recorded in the validation manifest.'%(rows['normal']['candidate']['fps'],rows['grid']['candidate']['fps'],rows['dense']['candidate']['fps'],rows['dense']['native']['fps']);j['step5_c4_r3d_validation']='tmp/dev/manifest/step5-c4-sine-r3d-validation.json';j['next_steps'][0]='P01 remains open after the planned R3a-R3d stages; re-profile the remaining cost and continue toward the same-workload gate and 3.33 target. P02 remains closed. Preserve 200 ms, default-off and all matched workload/exact gates.' if more else 'R3 reached its dense target; audit C4-P01 and C4-P02 closure evidence.';p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'manifest/step5-c4-open-cases.json';j=json.loads(p.read_text());j['latest_accepted_performance_change']=dict(step='R3d',evidence='manifest/step5-c4-sine-r3d-validation.json')
for c in j['cases']:
 if c['id'] in ('C4-P01','C4-P02'):
  scene='dense' if c['id']=='C4-P01' else 'grid';c['latest']=dict(after='R3d',candidate_fps=rows[scene]['candidate']['fps'],matched_legacy_fps=rows[scene]['native']['fps'],status=('passed' if passed else 'open; re-profile remaining cost') if scene=='dense' else 'still passed')
p.write_text(json.dumps(j,indent=2)+'\n')
(r/'tmp/step5/r3d-commit-message.txt').write_text('Remove repeated product frames in the 200 ms rotation\n\n'+text.split('### R3d accepted (2026-10-14)\n',1)[1].strip()+'\n');print(table)
