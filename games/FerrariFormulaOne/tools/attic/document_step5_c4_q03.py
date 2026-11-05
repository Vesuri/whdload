from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
u=lambda c,i:(c[i]<<32)|c[i+1]
def tenths(h):
 b=bytes.fromhex(h);return ((b[3]*10+b[4])*3600+(b[5]*10+b[6])*60+b[7]*10+b[8])*10+b[9]
report={'status':'passed','scope':'C4-Q03 actual emulated keyboard IRQ and mouse register delivery through native pause, tow/results, pit, paddock, standings, session/time changes and fresh driving entry','candidate_sha256':'9a00159b7a852c4ab42099697c9d3c6e2a36814f80cd4f9e235dbacbfe5c296f','profiles':{},'runtime_changes':False,'limitations':['Explicit emulator device events, not physical host keyboard/mouse or a human real-hardware play-test.','Selected Rio-to-Jerez qualifying route, not every track, session, save/load or full-season combination.','Normal release integration remains separate; the performance candidate stays default-off with CUSTOM2=0 legacy-exact.']}
for profile in ('a500','a500-fast'):
 p=r/f'tmp/step5/c4-q03-modal-final-{profile}-candidate';j=json.loads((p/'result.json').read_text());assert j['status']=='complete' and j['error']==0 and j['slave_sha256']==report['candidate_sha256']
 assert [x['actual'] for x in j['key_reads'] if x['actual']==x['expected']]==[64,69,69,39]
 assert all(j[k] for k in ('pause_exact_debt_preserved','pit_native_clock_without_driving_debt','session_change_without_driving_debt','scripted_session_clock_without_driving_debt','fresh_epoch_after_actual_session_change'))
 pause=j['pause-start'];held=j['pause-held'];resume=j['resume-boundary'];ex=j['native-exit-restored'];pc=pause['context'];rc=resume['context'];duration=u(rc,1)-u(pc,12)
 assert held['completed']==pause['completed']==resume['completed'] and held['calendar']==pause['calendar']==resume['calendar'] and held['session']==pause['session']==resume['session']
 assert u(pc,12)-u(pc,3)==u(rc,1)-u(rc,3) and u(rc,3)==u(pc,3)+duration and u(rc,9)==u(pc,9)+duration and rc[8]==pc[8]+1 and rc[11:]==[0,0,0]
 assert duration==j['excluded_pause_units'] and pc[11]==1 and held['context'][0]>pc[0]
 for name,owned,blit in [('takeover',64,0),('pause-start',0,64),('pause-held',0,64),('resume-boundary',64,0),('native-exit-restored',0,64)]:assert j[name]['owned']==owned and j[name]['intena']&64==blit
 assert j['ledger_entries']==j['ledger_restored_words']==504
 for name in ('after-exit','pit-long-click','pit-clock-before','pit-clock-after','paddock','session-applied','qualifying-paddock-ready'):
  assert j[name]['context']==ex['context'] and j[name]['completed']==0 and j[name]['owned']==0
 assert tenths(j['pit-clock-after']['calendar'])>tenths(j['pit-clock-before']['calendar'])
 assert bytes.fromhex(j['session-applied']['calendar'])[:7]==bytes([86,4,11,1,1,3,2])
 q=j['qualifying-paddock-ready'];assert bytes.fromhex(q['calendar'])[:7]==bytes([86,4,11,1,3,3,2])
 assert abs(tenths(q['calendar'])-13*36000-tenths(q['session']))<=1
 fresh=j['fresh-session-update'];f=fresh['context'];assert fresh['completed']==f[6]==1 and f[7]==200 and f[8:]==[0]*6 and u(f,3)==f[5] and fresh['owned']==64 and not fresh['intena']&64
 assert j['fresh-session-step21']['completed']==j['fresh-session-step21']['context'][6]==21
 images=['after-exit','pit-long-click','paddock','control-panel','race-settings','session-selected','session-applied','qualifying-clock-set','qualifying-paddock-ready','fresh-session-driving']
 report['profiles'][profile]={'result':str((p/'result.json').relative_to(r)),'result_sha256':sha(p/'result.json'),'paused_fields':duration//710510,'preserved_pending_units':u(pc,12)-u(pc,3),'restored_patch_words':504,'pit_clock_advance_tenths':tenths(j['pit-clock-after']['calendar'])-tenths(j['pit-clock-before']['calendar']),'fresh_race':j['fresh_race'],'old_race':j['race'],'fresh_updates':21,'images':{name:sha(p/(name+'.png')) for name in images}}
report['input_diagnosis']={'first_key':'A pending OS keyboard.device request precedes the game request and consumes the first key. Captured queue pointers and real IRQ trace establish this; the next Space press reaches the game.','release':'The debugger normally ignores the host release that opened it. Explicit monitor input must clear this ignore flag so injected releases reach the normal keyboard/CIA path. The test-only emulator does this and exposes a side-effect-free INTENA query. No guest input consumer, modal wait or game flags are stubbed.','fixture_correction':'Early retry logic duplicated ESC while a prior event was queued and could pause again after resume. Final runs retry only the first Space, record native caller provenance and observe release codes.','evidence':['tmp/step5/c4-q03-input-irq-a500-candidate/result.json','tmp/step5/c4-q03-input-diag-a500-candidate/emulator-cia.log']}
report['emulator_sha256']=sha(r/'tmp/step3/fs-uae-q03-final')
report['harness_sha256']={name:sha(r/'tools'/name) for name in ['test_step5_c4_q03_live.py','control_step5_c4_q03.py','step5-c4-q03-modal-replay.json']}
p=repo/'Games/FerrariFormulaOne_Coarse.s';s=p.read_text();s=s.replace('; SPS 0481 native 100 ms candidate. Default-off: the host must select coarse,\n; bind game operands, validate/install patches, flush caches and own their lifetime.\n; No player/opponent rate conversion or fractional state is installed.', '; SPS 0481 coarse candidate: native 100 ms, or converted 200 ms with\n; FF1_COARSE_200_COMPLETE. Default-off: the host selects the profile, binds game\n; operands, validates/installs patches, flushes caches and owns their lifetime.')
old='; Reversible native pause preserves active debt. Called at native pause edges.'
new='''; Reversible native pause preserves active debt. Called at native pause edges.
; Q03 actual device-input checks on A500/A500+Fast preserve the exact pending
; units across native pause, restore BLIT ownership and all 504 patch words at
; tow/exit, leave menu/session clock jumps outside this context, and start a
; fresh epoch on driving re-entry. No native input or modal wait was stubbed.
; Evidence: tmp/dev/manifest/step5-c4-q03-validation.json. Physical host input
; and real-hardware play-testing remain separate release qualification.'''
assert old in s and 'Q03 actual device-input' not in s;p.write_text(s.replace(old,new));report['source_sha256']={p.name:sha(p)}
(r/'manifest/step5-c4-q03-validation.json').write_text(json.dumps(report,indent=2)+'\n')
p=r/'manifest/step5-c4-open-cases.json';j=json.loads(p.read_text());q=next(x for x in j['cases'] if x['id']=='C4-Q03');q['status']='closed';q['resolution']={'evidence':'manifest/step5-c4-q03-validation.json','scope':report['scope'],'physical_host_or_real_hardware':'Not tested; remains release qualification, not claimed by emulated device IRQ evidence.'};j['status']='performance-and-correctness-cases-closed; production-acceptance-open';p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'manifest/project.json';j=json.loads(p.read_text());j['step5_c4_q03_validation']='tmp/dev/manifest/step5-c4-q03-validation.json';j['step5_c4_q03_status']='Closed in emulator scope on A500/A500+Fast: real device input, exact pause debt, all 504 patch words restored, native pit/session clocks outside driving debt, fresh epoch and 21 updates after re-entry. Physical host/hardware play-test remains release work.'
j['step5_status']='S0-S3/B3-B8/C1-C4 candidate work passed in documented scope. C4-P01/P02 and Q01/Q02/Q03 closed; C4-T01 remains a documented unmet optimization target. Full Step 5 production integration and release qualification remain open. Default-off; CUSTOM2=0 legacy-exact; 200 ms 68000 retained without performance fallback.'
j['validation']='Steps 1-4 complete within documented SPS 0481 scope. R3g performance and C4 correctness Q01-Q03 pass as default-off candidates on documented profiles. Ordinary release unchanged; production integration, wider version/gameplay acceptance and human hardware play-testing remain. 030/040/060 analysis deferred.'
j['performance_design']['validation']='R3g performance and C4 Q01-Q03 correctness pass within documented emulator scope; full production/release acceptance remains open. Default-off, no performance-triggered fallback.'
j['next_steps']=['Integrate and accept the production performance mode on supported 68000, chip-only 68020 and 68020+Fast profiles, retaining disabled-path exactness and explicit CUSTOM1/CUSTOM2 interactions.','Complete wider release qualification: version gates, gameplay/track/save-load coverage and human play-tests. Physical host input and real hardware are not established by emulator device-event tests.','Keep C4-T01 optimization target shortfalls explicit. Defer 030/040/060, Irek and NTSC acceptance until scope and inputs permit.']
j['step5_c4_q01_status']=j['step5_c4_q01_status'].replace('Q02/Q03 remain open.','Q02/Q03 subsequently closed in their documented scopes.')
j['step5_c4_q02_status']=j['step5_c4_q02_status'].replace('Q03 remains open.','Q03 subsequently closed in documented emulator scope.')
j['step5_c4_final_acceptance']['correctness_closure']={'status':'passed in documented emulator scope','cases':['C4-Q01','C4-Q02','C4-Q03'],'evidence':[f'tmp/dev/manifest/step5-c4-{q}-validation.json' for q in ['q01','q02','q03']]}
j['step5_c4_final_acceptance']['lifecycle']='Final directed lifecycle gates and actual emulated keyboard/mouse pause, tow/exit, pit/menu/session changes and fresh driving epoch pass on A500/A500+Fast. All 504 owned patch words restore. Physical host input/hardware and wider release qualification remain.'
p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'docs/open-work.md';s=p.read_text();a=s.index('C4-Q03 is in progress:');z=s.index('\nAfter correctness closure',a);s=s[:a]+'''C4-Q03 is closed in emulator scope: real keyboard IRQ and mouse-register input,
exact paused clocks/debt, blitter ownership, all 504 patch words restored at
actual tow/exit, native pit/menu/session time excluded from driving debt, and
21 error-free updates from a fresh epoch after re-entry. No guest consumer or
modal wait is stubbed. Physical host input and real hardware remain untested.
'''+s[z:];s=s.replace('After correctness closure, Step 5','Step 5');p.write_text(s)
p=r/'docs/STEP5_CAPACITY.md';s=p.read_text();assert '### C4-Q03 actual input and modal closure' not in s
s+='''\n### C4-Q03 actual input and modal closure (2026-10-14)

Q03 is closed in emulator scope on A500 and A500+Fast, using the unchanged
final R3g candidate. Keyboard events pass through the emulated CIA and actual
KickEmu keyboard interrupt, keyboard.device queue, native raw consumer and
race/pause callers. Mouse motion and buttons enter the emulated hardware and
native VBL/polling paths. No game flags, native input consumer or pause wait
are replaced. This is device IRQ evidence, not a physical host or real-hardware
human play-test.

The actual route covers demo takeover, ESC pause/resume, K tow, race results,
Accept into the pit, pit clock advancement, paddock and standings panels,
Jerez qualifying-session selection, explicit calendar adjustment to 13:32,
native scripted session-clock catch-up, pit/cockpit entry and fresh driving.
Screenshots and control/readback logs identify the observed transitions.

Both profiles preserve exact active debt through a 50-field pause. Calendar,
session and completed-step counters remain fixed while paused; resume excludes
only the measured paused units. BLIT enable is checked directly through a
side-effect-free emulator query as well as the owner flag. Actual tow/exit
restores all 504 recorded patch words and releases the owner. Native pit time
continues while all 56 driving-clock bytes remain unchanged. Session/date jumps
and the native fast-forward to the selected session likewise do not add driving
debt. Qualifying calendar and session times agree to the native one-tenth call
boundary. Driving re-entry clears old pause exclusions and consumed time,
starts a fresh 200 ms epoch, and completes 21 updates with error zero.
'''
for profile,v in report['profiles'].items():s+=f"\n- {profile}: preserved {v['preserved_pending_units']} pending clock units; {v['paused_fields']} paused fields; pit clock advanced {v['pit_clock_advance_tenths']} tenths over the 120-field observation; 504 words restored; fresh 21 updates passed.\n"
s+='''
Input investigation resolved test-harness assumptions, not a game defect. A
pending OS keyboard request consumes the first key before the game request;
the second Space reaches the native consumer. The debugger's host-release
suppression must not discard explicit monitor releases. The final diagnostic
emulator clears that flag only for explicit monitor input and adds a read-only
INTENA query; its hash is recorded. Early retries could duplicate ESC and pause
again after resume; final runs retry only the first Space. Release events and
native caller provenance are retained. Diagnostic failures remain separate.

Evidence: `manifest/step5-c4-q03-validation.json`; full results and screenshots
under `tmp/step5/c4-q03-modal-final-{a500,a500-fast}-candidate/`. The saved replay
is `tools/step5-c4-q03-modal-replay.json`. Findings-only game-source comments
leave executable bytes unchanged; existing R3g exact-state/frame/elapsed and
four-profile CUSTOM2=0 gates remain applicable. Q01/Q02/Q03 are now closed.
C4-T01 remains a documented target shortfall; production integration, wider
version/track/save-load coverage and human hardware acceptance remain separate.
The 200 ms design, default-off policy and no-fallback decision are unchanged.
''';p.write_text(s)
(r/'tmp/step5/q03-commit-message.txt').write_text('Document C4 device-input and modal correctness closure\n\nVerify exact pause debt, native pit/session clock boundaries, 504-word\nrestoration and fresh driving re-entry on A500 and A500+Fast. Keep physical\nhost input and wider release qualification outside the emulator claim.\nExecutable game instructions remain unchanged.\n')
print(json.dumps(report['profiles'],indent=2))
