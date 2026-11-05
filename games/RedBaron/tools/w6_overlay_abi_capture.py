"""Capture quiescent native programs through VERIFY CUSTOM2 bit 14."""
import json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from presentation_state import symbol
p=Path(sys.argv[1]);m=json.loads((p/'entry.json').read_text());lines=(p/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda n:base+symbol(lines,n)
regions=r.memory_regions();frames=[]
def registers():
 raw=r.command('gdb info registers')
 values={name:int(value,16) for name,value in re.findall(r'^(d[0-7]|a[0-6]|sp|pc|ps|sr)\s+0x([0-9a-fA-F]+)',raw,re.M)}
 assert len(values)>=18,raw
 return dict(values=values,raw=raw)

def snapshot(label):
 raw=r.command(f'gdb printf "PROBE %u %u %u %u %u\\n", $pc, $sp, *(unsigned short*){at("overlay_probe_header"):#x}, *(unsigned long*){at("overlay_probe_header")+4:#x}, *(unsigned short*)0xdff002')
 match=re.search(r'PROBE (\d+) (\d+) (\d+) (\d+) (\d+)',raw);assert match,raw
 pc,sp,program,count,dmacon=map(int,match.groups());assert not dmacon&0x4000,'Blitter is still busy'
 banks=[]
 for lo,hi in regions:
  name=f'{label}-{lo:x}.bin';r.command(f'gdb dump binary memory {p/name} {lo:#x} {hi:#x}');banks.append(dict(base=lo,size=hi-lo,file=name))
 return dict(pc=pc,sp=sp,program=program,count=count,dmacon=dmacon,banks=banks,registers=registers())
for i in range(4):
 r.command(f'gdb delete\nbreak *{at("overlay_probe_before"):#x}\ncondition $bpnum *(unsigned short*){at("overlay_probe_header"):#x}==3 || *(unsigned short*){at("overlay_probe_header"):#x}==4\ncontinue')
 before=snapshot(f'program-{i}-before');assert before['pc']==at('overlay_probe_before')
 r.command(f'gdb delete\nbreak *{at("overlay_probe_after"):#x}\ncontinue')
 after=snapshot(f'program-{i}-after');assert after['pc']==at('overlay_probe_after');assert (before['program'],before['count'])==(after['program'],after['count'])
 raw=r.command(f'gdb printf "RETURN %u\\n", *(unsigned long*){before["sp"]:#x}')
 match=re.search(r'RETURN (\d+)',raw);assert match,raw
 target=int(match[1])
 r.command(f'gdb delete\nbreak *{target:#x}\ncontinue')
 returned=registers();assert returned['values']['pc']==target
 frames.append(dict(index=i,before=before,after=after,returned=returned));(p/'overlay-capture.json').write_text(json.dumps(dict(h3=m['entry']['h3'] if 'h3' in m['entry'] else json.loads((p/'entry-steps.json').read_text())['h3'],sha256=m['slave_sha256'],frames=frames),indent=2)+'\n');print(i,before['program'],before['count'],flush=True)
