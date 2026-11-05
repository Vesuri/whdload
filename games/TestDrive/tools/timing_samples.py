"""Read data and saved main-race frame at every pre-increment VBL boundary."""
import json,re
from harness import ROOT,command,server
from timing_map import decode

def capture(count,out,rr,frame):
 out.mkdir(parents=True,exist_ok=False);db=rr['td-data'];vbl=rr['td']+0x18ba
 server.request('until '+hex(vbl));rel=out.relative_to(ROOT)
 lines=['cd '+str(ROOT),f'break *{vbl:#x}','set $td_n = 0',f'while $td_n < {count}',f'eval "dump binary memory {rel}/%04d.bin {db:#x} {db+0x32a4:#x}", $td_n',f'eval "dump binary memory {rel}/frame-%04d.bin {frame-52:#x} {frame+10:#x}", $td_n','set $td_n = $td_n + 1',f'if $td_n < {count}','continue','end','end','delete']
 (out/'gdb.txt').write_text(command('\n'.join(lines)))
 samples=[]
 for i in range(count):
  s=decode((out/f'{i:04d}.bin').read_bytes());b=(out/f'frame-{i:04d}.bin').read_bytes()
  for n,off in [('sum_speed',-44),('samples',-36),('epoch',-20),('period',-16),('deadline',-12)]:s[n]=int.from_bytes(b[52+off:56+off],'big',signed=True)
  samples.append(s)
 assert all(b['vbl']==a['vbl']+1 for a,b in zip(samples,samples[1:])), 'missed VBL'
 (out/'samples.json').write_text(json.dumps(samples,indent=2)+'\n')
 (out/'metadata.json').write_text(json.dumps(dict(fields=count,anchor='root:18ba pre-increment',race_frame=frame,regions=rr),indent=2)+'\n')
