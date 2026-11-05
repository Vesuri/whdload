#!/usr/bin/env python3
"""Read-only VBL-entry/swap counter with per-machine anchor calibration."""
import argparse,json,os,re,shutil
from pathlib import Path
from capture_demo import ROOT,command
from capture_session import Session
from machine_profiles import PROFILES

def count(session,fields):
 base=session.layout['code_base']
 reply=command(f'''gdb break *{base+0x44:#x}
break *{base+0xb4:#x}
set $hd_field=-1
while $hd_field < {fields}
continue
if $pc == {base+0x44:#x}
set $hd_field=$hd_field+1
else
printf "HDSWAP %d\\n", $hd_field
end
end
delete
''')
 (session.out/'swaps-gdb.txt').write_text(reply);counts=[0]*fields
 for f in map(int,re.findall(r'^HDSWAP (-?\d+)$',reply,re.M)):
  if 0<=f<fields:counts[f]+=1
 result=dict(fields=fields,swaps=sum(counts),per_field=counts,seconds=fields*142102/7093790)
 (session.out/'counter.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('out');p.add_argument('--profile',choices=PROFILES,default='a500');p.add_argument('--fields',type=int,default=1000);p.add_argument('--slave');p.add_argument('--compare-trace',type=Path);a=p.parse_args();os.chdir(ROOT)
 assert a.fields>0
 out=Path(a.out).resolve();rel=out.relative_to(ROOT/'tmp/prof');assert not any(c.isspace() for c in str(rel));out.mkdir(exist_ok=False,parents=True)
 slave=Path(a.slave).resolve() if a.slave else ROOT/'tmp/build/HardDrivin-verify.slave';shutil.copyfile(slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10844)
 try:
  print('Calibrating',a.profile,flush=True);print(s.boot(),flush=True);r=count(s,a.fields)
  if a.compare_trace:
   expected=[v['candidate_swaps'] for v in json.loads(a.compare_trace.read_text())['per_field']];assert r['per_field']==expected
  print({k:v for k,v in r.items() if k!='per_field'},flush=True)
 finally:s.close()
if __name__=='__main__':main()
