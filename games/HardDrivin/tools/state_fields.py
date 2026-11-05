#!/usr/bin/env python3
"""Read complete allocated game globals at VBL entry and every physics return.
Field 0 is the first VBL entry after the native race-loop anchor. Capture includes
both boundary samples of N fields; physics records retain the preceding boundary.
No guest writes. Pointer normalization is a separate explicit comparison option.
"""
import argparse,json,os,re,shutil,struct
from pathlib import Path
from capture_demo import ROOT,command
from capture_session import Session
from machine_profiles import PROFILES
# Raw bytes are authoritative; these fields make important state easy to inspect.
FIELDS={'pose':(-0x6710,12),'angles':(-0x66bc,12),'velocity':(-0x66d8,4),'speed':(-0x66d4,2),'gear':(-0x66ca,2),'throttle':(-0x66e4,1),'mouse':(-0x6a06,4),'buttons':(-0x6a0a,1),'clocks':(-0x6870,12),'replay_pointer':(-0x16e2,4),'replay':(-0x5229,1),'crash':(-0x69fa,1),'rng':(-0x6fc4,4)}
def capture(s,fields):
 base=s.layout['code_base'];regions=s.layout['regions'][1:]
 for mode in ['vbl','physics']:(s.out/mode).mkdir()
 def dump(mode,var):
  lines=[]
  for i,r in enumerate(regions):
   verb='dump' if i==0 else 'append'
   lines.append(f'eval "{verb} binary memory {s.rel}/{mode}/%06d.bin {r["base"]:#x} {r["base"]+r["size"]:#x}", {var}')
  return '\n'.join(lines)
 reply=command(f'''gdb break *{base+0x44:#x}
break *{base+0xcdb0:#x}
set $hd_field=-1
set $hd_step=0
while $hd_field < {fields}
continue
if $pc == {base+0x44:#x}
set $hd_field=$hd_field+1
{dump('vbl','$hd_field')}
else
if $hd_field >= 0
{dump('physics','$hd_step')}
printf "HDSTEP %d %d\\n", $hd_step, $hd_field
set $hd_step=$hd_step+1
end
end
end
delete
''')
 (s.out/'state-gdb.txt').write_text(reply)
 steps=[dict(index=int(i),field=int(f)) for i,f in re.findall(r'^HDSTEP (\d+) (\d+)$',reply,re.M)]
 meta=dict(s.metadata,fields=fields,snapshot_regions=regions,snapshot_size=sum(r['size'] for r in regions),vbl_hook='0x44 entry',physics_hook='0xcdb0 before RTS',physics_steps=steps,semantic_fields=FIELDS)
 (s.out/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
 assert len(list((s.out/'vbl').glob('*.bin')))==fields+1
 assert len(list((s.out/'physics').glob('*.bin')))==len(steps)>0
 for mode in ['vbl','physics']:
  rows=[]
  for path in sorted((s.out/mode).glob('*.bin')):
   b=path.read_bytes();assert len(b)==meta['snapshot_size']
   rows.append(dict(index=int(path.stem),**{name:b[0x7ffe+off:0x7ffe+off+size].hex() for name,(off,size) in FIELDS.items()}))
  (s.out/(mode+'-state.json')).write_text(json.dumps(rows,indent=2)+'\n')
 print(f'{fields+1} VBL boundaries, {len(steps)} physics returns',flush=True)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('out');p.add_argument('--profile',choices=PROFILES,default='a500');p.add_argument('--fields',type=int,default=1250);p.add_argument('--slave',type=Path);p.add_argument('--custom4',type=int,default=0);a=p.parse_args();os.chdir(ROOT)
 assert a.fields>0 and 0<=a.custom4<=255
 out=Path(a.out).resolve();rel=out.relative_to(ROOT/'tmp/prof');assert not any(c.isspace() for c in str(rel));out.mkdir(parents=True,exist_ok=False)
 slave=a.slave.resolve() if a.slave else ROOT/'tmp/build/HardDrivin-drive.slave';shutil.copyfile(slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4,a.custom4)
 try:s.boot();capture(s,a.fields)
 finally:s.close()
if __name__=='__main__':main()
