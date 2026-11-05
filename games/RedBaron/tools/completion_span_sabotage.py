import json,os,re,struct,subprocess,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,'tools')
from completion_machines import environment
for fault in (1,2):
 out=Path(f'tmp/prof/completion-e3-span-fault-{fault}')
 assert not out.exists()
 env=environment('040',0xf2ffa)
 env.update(WHD_ARGS='CUSTOM2=995322 CUSTOM5=65536',FILL_TRACE='1',TWIN_FAIL_SYMBOL='cpu_span_twin_fail',VERIFY_SPAN_TWIN_FAULT=str(fault))
 result=subprocess.run([sys.executable,'tools/reach_flight.py','--no-shot','--out',str(out)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (out/'driver.log').write_text(result.stdout)
 assert result.returncode != 0,result.stdout
 base=json.loads((out/'diagnostic-base.json').read_text())['base']
 listing=(out/'slave.lst').read_text(encoding='latin1')
 def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
 raw=r.command('gdb info registers pc d5 d6')
 (out/'stop.log').write_text(raw)
 def reg(n):return int(re.search(r'^'+n+r'\s+0x([0-9a-f]+)',raw,re.M)[1],16)
 assert reg('pc')==base+sym('cpu_span_twin_fail'),raw
 for name,size in [('cpu_span_header',20),('cpu_span_counts',8)]:
  at=base+sym(name);r.command(f'gdb dump binary memory {out}/{name}.bin {at:#x} {at+size:#x}')
 b=(out/'cpu_span_header.bin').read_bytes();assert b[:8]==b'RBSPAN01'
 version,planes,words=struct.unpack('>3I',b[8:]);cpu,fallback=struct.unpack('>2I',(out/'cpu_span_counts.bin').read_bytes())
 area=(reg('d5')&65535)*(reg('d6')&65535)
 assert version==1 and planes==0 and cpu==1 and fallback==0
 assert words==(0 if fault==1 else area-1),(fault,words,area)
 evidence=dict(fault=fault,detected=True,words_before_detection=words,rectangle_words=area)
 (out/'result.json').write_text(json.dumps(evidence,indent=2)+'\n');print(evidence,flush=True)
 print(r.command('quit'),flush=True)
print('BOTH CHECKER SABOTAGES PASS',flush=True)
