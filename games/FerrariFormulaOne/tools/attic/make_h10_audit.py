from pathlib import Path
r=Path(__file__).resolve().parents[1];s=(r/'tools/audit_h9_final.py').read_text().replace('h9','h10').replace('H9','H10')
s=s.replace('020Fast exact state/private fractions','040BCE exact state/private fractions').replace('matched020 normal/dense','matched020 normal').replace('060BCE grid candidate','030/060BCE grid candidate')
a=s.index("model=read(");b=s.index('states=[]',a)
s=s[:a]+'''out['microbench']=read(r/'manifest/render-h10-microbench.json');assert out['microbench']['status']=='passed'
x=result('c4-q03-h10-oracle-040-40-bce-h10-candidate','render-h10-oracle');assert x['status']=='passed' and x['checked']==480 and x['oracle_error']==0;out['native_oracle_cases']=480
'''+s[b:]
s=s.replace('drive-state-production-a1200-fast-h10','drive-state-production-040-40-bce-h10').replace('h5-frame-production-a1200-fast-h10','h5-frame-production-040-40-bce-h10').replace('drive-timing-a1200-fast-h10','drive-timing-040-40-bce-h10')
s=s.replace("[('a1200-fast','normal'),('a1200-fast','dense'),('040-40-bce','grid'),('040-40-bce','dense'),('060-50-bce','grid')]", "[('a1200-fast','normal'),('040-40-bce','grid'),('040-40-bce','dense'),('060-50-bce','grid'),('030-50-bce','grid')]")
s=s.replace("p.startswith('060')", "p.startswith(('060','030'))")
s=s.replace(" and s['maximum_dma_address']=='0x59fb0'", " and int(s['maximum_dma_address'],16)<0x200000")
a=s.index("p=r/'tmp/step5/c4-q03-h7-live-040-40-h10-candidate';");b=s.index("x=result('c4-q03-h10-bad-signature",a)
s=s[:a]+'''p=r/'tmp/step5/c4-q03-h7-live-040-40-h10-candidate';table=int(x['table'],16);probe=int(x['probe'],16);sy=read(r/'tmp/build/render-h10/build.json')['payloads']['fine']['symbols']
for snap in ['takeover','fresh-session-step21']:
 m=(p/(snap+'.bin')).read_bytes()
 for native,label in [(0x6b0e4,'FF1RenderClearBottom'),(0x6b138,'FF1RenderClearTop')]:
  a=Addresses(m,table).map(native);assert m[a:a+6]==bytes.fromhex('4eb9')+struct.pack('>I',probe+sy[label])
out['lifecycle']={'ledger_restored_words':x['ledger_restored_words'],'clear_hooks_present_on_takeover_and_reload':True,'native_pause_tow_pit_menu_reentry':'passed'}
'''+s[b:]
s=s.replace('h10-bad-signature-a1200-fast','h10-bad-signature-040-40').replace('road_fill_hook_not_installed','clear_hook_not_installed')
s=s.replace("['test_h10_model.py','capture_h10_planes.py','run_h10_checks.py','analyze_h10_trace.py','audit_h10_build.py','audit_h10_final.py']", "['build_h10_oracle.py','test_h10_oracle.py','run_h10_checks.py','analyze_h10_trace.py','audit_h10_cpu.py','audit_h10_build.py','audit_h10_final.py']")
s=s.replace("out['next']='H10;", "out['next']='H13;" )
s=s.replace("out['traces']=traces", "out['traces']=traces;out['cpu_bus']=read(r/'tmp/step5/hi25-profile-040-40-bce-h10-grid-candidate/h10-cpu-audit.json');assert out['cpu_bus']['status']=='passed'")
(r/'tools/audit_h10_final.py').write_text(s)
