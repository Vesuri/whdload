"""Ordinary C/D/T camera transitions with whole-frame twins and primitive census."""
import json,re,subprocess,sys
from pathlib import Path
from profile_window import command
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());g=m['game_base'];a=m['data_base']+0x7ffe
script=['delete']
for name,off in [('circle',0x286fe),('wheel',0x28c08),('dot',0x333b2)]:
 script += [f'set $camera_{name}=0',f'break *{g+off:#x}','commands','silent',f'set $camera_{name}=$camera_{name}+1','continue','end']
command('gdb '+'\n'.join(script));rows=[]
for key in (None,0x33,0x33,0x33,0x22,0x14,0x33):
 if key is not None:
  command(f'gdb monitor key {key:x} 1\nmonitor fields 3\nmonitor key {key:x} 0')
 command(f'gdb tbreak *{g+0x7500:#x}\nignore $bpnum 19\ncontinue')
 text=command('gdb '+'\n'.join([f'p /u *(unsigned char*){a+off:#x}' for off in (-0x770d,0x37,0x45)]+[f'p /u $camera_{name}' for name in ('circle','wheel','dot')]))
 vals=[int(x) for x in re.findall(r'^\$\d+ = (\d+)',text,re.M)];assert len(vals)==6,text
 rows.append(dict(key=key,camera=vals[0],view=vals[1],mode=vals[2],circle=vals[3],wheel=vals[4],dot=vals[5]));print(rows[-1],flush=True)
(p/'camera-primitive-check.json').write_text(json.dumps(rows,indent=2)+'\n')
command('gdb delete')
subprocess.run([sys.executable,str(Path(__file__).with_name('p3_background_check.py')),str(p)],check=True)
assert len({r['camera'] for r in rows})>=3,rows
assert rows[-1]['wheel']>0,rows
