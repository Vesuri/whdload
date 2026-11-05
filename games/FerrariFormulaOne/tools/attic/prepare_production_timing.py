from pathlib import Path
r=Path(__file__).resolve().parents[1];s=(r/'tools/test_production_smoke.py').read_text().replace("kind='production-smoke'","kind='production-timing'")
s=s.replace("sy['schedule_end' if kind=='fine' else 'C1Checkpoint']","sy['FF1PresentationAfterTick' if kind=='fine' else 'C1Checkpoint']")
a=s.index(" report['context_before']");z=s.index('\nfinally:',a)
s=s[:a]+''' cmd('monitor warp 0');cmd('ignore $bpnum 9');assert 'Breakpoint' in cmd('continue')
 def context():return [val(f'*(unsigned int*){ctx+i*4}') for i in range(14)]
 report['elapsed_start']=context();report['warp_start']=cmd('monitor warp-status');updates=300 if kind=='000' else 600 if kind=='020' else 3000
 cmd('ignore $bpnum '+str(updates-1));assert 'Breakpoint' in cmd('continue')
 report['elapsed_end']=context();report['warp_end']=cmd('monitor warp-status');x=report['elapsed_start'];y=report['elapsed_end']
 elapsed=(y[0]-x[0])*71051/3546895;simulated=(y[6]-x[6])*((y[7]&65535)/1000)
 report.update(elapsed_seconds=elapsed,simulated_seconds=simulated,error_percent=abs(simulated/elapsed-1)*100)
 assert report['error_percent']<=1 and simulated==60 and report['warp_start']==report['warp_end']=='warp=0',report
 listing=(b.parent/kind/'fine.list').read_text()
 import re
 pubs=[int(m[1],16)+6 for m in re.finditer(r'^00:([0-9A-F]{8}) 4EB90002A270\\s+\\d+:\\s+jsr \\$2a270',listing,re.M)]
 assert len(pubs)==1,pubs
 publication=probe+pubs[0];cmd('delete');cmd(f'break *{publication}');assert 'Breakpoint' in cmd('continue')
 report['fps_start']=context();cmd('ignore $bpnum 299');assert 'Breakpoint' in cmd('continue');report['fps_end']=context()
 fields=report['fps_end'][0]-report['fps_start'][0];report['fps']=300/(fields*71051/3546895);report['fps_fields']=fields
 report['error']=val(f'*(unsigned int*){probe+sy["error"]}');report['status']='passed' if report['error']==0 and report['fps']>=(3.494 if kind=='000' else 5.54) else 'failed'
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\\n');print(report,flush=True);assert report['status']=='passed'
'''+s[z:];(r/'tools/test_production_timing.py').write_text(s)
