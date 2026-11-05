from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/test_step5_c4_q03_live.py').read_text();s=s[:s.index('\n import re\n')]
s=s.replace("kind='modal-final'","kind='production-smoke'").replace("b=r/'tmp/build/step5-c4-divide-frame-r3g-v1-ab'/('000' if profile.startswith('a500') else '020')/(variant+'.slave')","b=r/'tmp/build/production/FerrariFormulaOne.slave'")
s += '''
 build=json.loads((b.parent/'build.json').read_text());hs=build['host_symbols'];kind='000' if profile.startswith('a500') else '020' if profile=='a1200' else 'fine';module=build['payloads'][kind];sy=module['symbols'];host=marker-hs['FF1PublicMarker'];probe=host+module['offset']
 report.update(host=hex(host),probe=hex(probe),kind=kind,selection=val(f'*(unsigned int*){host+hs["FF1ProfileMode"]}'))
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\\n')
 cmd('delete')
 faults=['FF1WrongVersion']
 for n in faults:cmd(f'break *{host+hs[n]}')
 for n in (['C1Fault','velocity_stop'] if kind=='000' else ['C1Fault'] if kind=='020' else ['velocity_fault','schedule_bad']):
  if n in sy:cmd(f'break *{probe+sy[n]}')
 checkpoint=probe+sy['schedule_end' if kind=='fine' else 'C1Checkpoint'];cmd(f'break *{checkpoint}')
 assert 'Breakpoint' in cmd('continue')
 report['stop_pc']=hex(val('$pc'));report['error']=val(f'*(unsigned int*){probe+sy["error"]}')
 if val('$pc')!=checkpoint:
  report['regs']=cmd('info registers');dump('fault');(out/'result.json').write_text(json.dumps(report,indent=2)+'\\n');raise AssertionError(report)
 ctx=probe+sy['schedule_context' if kind=='fine' else 'C1Context'];report['context_address']=hex(ctx)
 report['context_before']=[val(f'*(unsigned int*){ctx+i*4}') for i in range(14)]
 cmd('delete');cmd(f'break *{checkpoint}');cmd('ignore $bpnum 19');assert 'Breakpoint' in cmd('continue')
 report['context_after']=[val(f'*(unsigned int*){ctx+i*4}') for i in range(14)];report['error']=val(f'*(unsigned int*){probe+sy["error"]}')
 report['status']='passed' if report['error']==0 else 'failed'
 dump('final');(out/'result.json').write_text(json.dumps(report,indent=2)+'\\n');print(report,flush=True)
finally:
 (out/'capture.log').write_text('\\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
'''
(r/'tools/test_production_smoke.py').write_text(s)
