from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];mp=r/'manifest/step5-c4-native-frame-r3e-validation.json';m=json.loads(mp.read_text());assert m['status']=='passed'
rows=m['measurements'];fmt=lambda x:f'{x:.6f}'
table='\n'.join('| '+n+' | '+fmt(rows[k]['baseline-render']['fps'])+' | '+fmt(rows[k]['candidate']['fps'])+' | '+(fmt(rows[k]['native']['fps']) if 'native' in rows[k] else '—')+' |' for n,k in [('Normal demo','normal'),('Centered native grid','grid'),('Dense pack','dense')])
passed=m['p01_same_workload_passed'];more=m['r3f_required']
text=f'''
### R3e accepted (2026-10-14)

Guarded unsigned-word and signed-word native products now avoid register-save
frames. Equal-input, zero-input and mixed-sign paths preserve the original
low-32 product and unusual XNZVC, including zero-input X and equal-input Z.
An exact eight-times-positive-long fold avoids the measured wide multiply.
Other inputs use the accepted general helper. D1-D7/A0-A6 stay unchanged.
One fixed branch selects equal-layout arms; the disabled build reproduces R3d.
All code remains in the existing public owner and the mode remains default-off.

| 300 presentations, warp off | R3e-disabled C4 | R3e | Legacy |
|---|---:|---:|---:|
{table}

227712 native comparisons pass, including all 32 input CCR values, full-width
range misses, preserved D1-D5 and SP. The independent mathematical model passes
1248576 cases. All 100 updates match the unchanged 27-block state inventory;
all 30 full RGB frames and four-profile CUSTOM2=0 checks pass. Native exit
restores all {json.loads((r/m['exit']).read_text())['ledger_restore_checked_words']} recorded patch words, including the three R3c inlined call sites. The 60-second test has
{m['elapsed']['error_percent']:.7f}% elapsed error and {m['elapsed']['fps']:.6f} FPS.

Matched 100-field logic excluding presentation falls from
{m['logic_cycles_control']:.4f} to {m['logic_cycles_candidate']:.4f} cycles/update:
{m['logic_saved_cycles']:.4f} cycles ({m['logic_saved_ms']:.5f} ms). All three analyser totals, normalization and
Chip DMA gates pass; traces are verified compressed. Evidence:
`manifest/step5-c4-native-frame-r3e-validation.json`. Default-off, 200 ms and no fallback
remain unchanged. P02 remains closed. P01 same-workload gate: {'passed' if passed else 'not passed'}.
{'Dense remains below 3.33; continue with the measured direct-WaitBlit follow-up R3f.' if more else 'Dense reaches 3.33; stop the R3 optimization sequence.'}
'''
text+='\nThe first VERIFY control could not initialize the diagnostic marker: its\nws_GameLoader offset grew to 0x8020, outside the positive signed-word range.\nA near entry trampoline (0x19da in that fixture) restores startup, preserves\nthe original entry ABI and adds a build-time range assertion. The failed slave\nand memory/log evidence are retained in `manifest/step5-c4-r3e-entry-range.json`.\nBoth repaired arms pass all exact gates; compiling the feature out still\nreproduces R3d. The generic lesson is committed in AmigaXDev as 5f9353e.\n'
p=r/'docs/STEP5_CAPACITY.md';old=p.read_text();assert '### R3e accepted (2026-10-14)' not in old;p.write_text(old+text)
p=r/'manifest/project.json';j=json.loads(p.read_text());j['step5_c4_r3e_status']='Passed as default-off candidate: normal %.5f, grid %.5f, dense %.5f vs legacy %.5f FPS; all arithmetic/state/frame/elapsed/exit/legacy/profile/DMA checks pass. Measured logic saving is recorded in the validation manifest.'%(rows['normal']['candidate']['fps'],rows['grid']['candidate']['fps'],rows['dense']['candidate']['fps'],rows['dense']['native']['fps']);j['step5_c4_r3e_validation']='tmp/dev/manifest/step5-c4-native-frame-r3e-validation.json';j['next_steps'][0]='R3e accepted; test the measured direct-WaitBlit follow-up R3f while dense remains below 3.33. P02 remains closed. Preserve 200 ms, default-off and all matched workload/exact gates.' if more else 'R3 reached its dense target; audit C4-P01 and C4-P02 closure evidence.';p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'manifest/step5-c4-open-cases.json';j=json.loads(p.read_text());j['latest_accepted_performance_change']=dict(step='R3e',evidence='manifest/step5-c4-native-frame-r3e-validation.json')
for c in j['cases']:
 if c['id'] in ('C4-P01','C4-P02'):
  scene='dense' if c['id']=='C4-P01' else 'grid';c['latest']=dict(after='R3e',candidate_fps=rows[scene]['candidate']['fps'],matched_legacy_fps=rows[scene]['native']['fps'],status=('passed' if passed else 'open; next R3f') if scene=='dense' else 'still passed')
p.write_text(json.dumps(j,indent=2)+'\n')
(r/'tmp/step5/r3e-commit-message.txt').write_text('Remove native multiply frames while preserving exact flags\n\n'+text.split('### R3e accepted (2026-10-14)\n',1)[1].strip()+'\n');print(table)
