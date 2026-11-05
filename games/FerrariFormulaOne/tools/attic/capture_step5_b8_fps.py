from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/capture_step5_b7_profile_v3.py').read_text().replace('a1200-fast-b7-v3-profile','a1200-fast-b8-v3-fps').replace('step5-b7-v3/lean','step5-b8-v3/lean')
a=s.index(" cmd('delete');cmd(f'monitor profile");z=s.index('\nfinally:',a)
s=s[:a]+'''
 import re
 listing=b.with_name('fine.list').read_text()
 def sym(n):return int(re.search(r'^'+n+r'\\s+00:([0-9A-F]+)',listing,re.M)[1],16)
 probe=struct.unpack_from('>I',memory,addresses.map(0x654e8))[0]-sym('barrier')
 def counts():return {n:val(f'*(unsigned int*){probe+sym(n)}') for n in ('B8Frames','schedule_completed','error')}|{'fields':val(f'*(unsigned int*){probe+sym("schedule_context")}')}
 # Identical endpoints immediately after native buffer publication. No CPU
 # trace and no intervening debugger stops in the 100-presentation window.
 cmd('delete');cmd(f'break *{probe+sym("B8_654fc")}');assert 'Breakpoint' in cmd('continue')
 report['start']=counts();report['warp_start']=cmd('monitor warp-status');cmd('ignore $bpnum 99');assert 'Breakpoint' in cmd('continue')
 report['end']=counts();report['warp_end']=cmd('monitor warp-status')
 delta=report['end']['B8Frames']-report['start']['B8Frames'];fields=report['end']['fields']-report['start']['fields']
 report.update(presentations=delta,elapsed_fields=fields,elapsed_seconds=fields*71051/3546895,presented_fps=delta*3546895/71051/fields,untraced=True,gate_fps=5.54)
 assert delta==100 and report['end']['error']==0 and report['warp_start']==report['warp_end']=='warp=0'
 cmd('dump binary memory tmp/step5/a1200-fast-b8-v3-fps/end-raw.bin 0 0x600000')
 (out/'end.bin').write_bytes(addresses.canonical_memory((out/'end-raw.bin').read_bytes()))
 cmd('delete');cmd(f'monitor profile 1 "" "{out}/screenshot.bin"')
 from amigaxdev import barto
 kind,pixels=barto.last_screenshot(out/'screenshot.bin');(out/'frame.png').write_bytes(pixels)
 report['status']='passed' if report['presented_fps']>=5.54 else 'failed';report['slave']=str(b)
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\\n');print(report,flush=True)
''' + s[z:]
exec(compile(s,str(r/'tools/capture_step5_b7_profile_v3.py'),'exec'))
