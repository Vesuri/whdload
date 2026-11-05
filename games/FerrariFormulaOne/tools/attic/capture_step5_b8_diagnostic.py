from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/capture_step5_b7_profile_v3.py').read_text().replace('a1200-fast-b7-v3-profile','a1200-fast-b8-v1-diagnostic').replace('step5-b7-v3/lean','step5-b8-v1/lean')
a=s.index(" cmd('delete');cmd(f'monitor profile")
z=s.index('\nfinally:',a)
s=s[:a]+'''
 import re
 listing=b.with_name('fine.list').read_text()
 def sym(n):return int(re.search(r'^'+n+r'\\s+00:([0-9A-F]+)',listing,re.M)[1],16)
 # Runtime hook pointer identifies the public-bound candidate base.
 probe=struct.unpack_from('>I',memory,addresses.actual(0x654e8))[0]-sym('barrier')
 def counts():return {n:val(f'*(unsigned int*){probe+sym(n)}') for n in ('B8Frames','schedule_completed','error') }|{'fields':val(f'*(unsigned int*){probe+sym("schedule_context")}')}
 report['start']=counts();cmd('delete');cmd(f'monitor profile 12 "" "{out}/detail.bin"')
 report['end']=counts();report['registers']=cmd('info registers')

 cmd('dump binary memory tmp/step5/a1200-fast-b8-v1-diagnostic/end-raw.bin 0 0x600000')
 (out/'end.bin').write_bytes(addresses.canonical_memory((out/'end-raw.bin').read_bytes()))
 report['status']='diagnostic';(out/'result.json').write_text(json.dumps(report,indent=2)+'\\n');print(report,flush=True)
''' + s[z:]
s=s.replace('addresses.actual(0x654e8)','addresses.map(0x654e8)')
exec(compile(s,str(r/'tools/capture_step5_b7_profile_v3.py'),'exec'))
