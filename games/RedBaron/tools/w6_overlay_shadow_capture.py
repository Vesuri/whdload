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
 r.command(f'gdb delete\nbreak *{at("overlay_mask_observed"):#x}\ncontinue')
 raw=r.command(f'gdb printf "MASK %u %u %u %u\\n", *(unsigned long*){at("overlay_mask_result"):#x}, *(unsigned long*){at("overlay_mask_result")+4:#x}, *(unsigned long*){at("overlay_mask_result")+8:#x}, *(unsigned long*){at("overlay_mask_result")+12:#x}')
 match=re.search(r'MASK (\d+) (\d+) (\d+) (\d+)',raw);assert match,raw
 ptr,supported,program,count=map(int,match.groups());assert supported==1 and count==i+1,raw
 mask_file=f'mask-{i}.bin'
 r.command(f'gdb dump binary memory {p/mask_file} {ptr:#x} {ptr+8032:#x}')

 r.command(f'gdb delete\nbreak *{at("overlay_probe_before"):#x}\ncondition $bpnum *(unsigned short*){at("overlay_probe_header"):#x}==3 || *(unsigned short*){at("overlay_probe_header"):#x}==4\ncontinue')
 before=snapshot(f'program-{i}-before');assert before['pc']==at('overlay_probe_before')
 r.command(f'gdb delete\nbreak *{at("overlay_pack_observed"):#x}\ncontinue')
 pack_file=f'pack-{i}.bin';header_file=f'pack-{i}-header.bin'
 raw=r.command(f'gdb printf "PACK %u\\n", *(unsigned long*){at("overlay_pack_result"):#x}')
 match=re.search(r'PACK (\d+)',raw);assert match,raw
 pack_ptr=int(match[1]);assert pack_ptr
 r.command(f'gdb dump binary memory {p/pack_file} {pack_ptr:#x} {pack_ptr+5240:#x}')
 r.command(f'gdb dump binary memory {p/header_file} {at("overlay_pack_result"):#x} {at("overlay_pack_result")+28:#x}')
 r.command(f'gdb delete\nbreak *{at("overlay_shadow_observed"):#x}\ncontinue')
 shadow_header=f'shadow-{i}-header.bin';shadow_target=f'shadow-{i}-target.bin';shadow_cache=f'shadow-{i}-cache.bin'
 r.command(f'gdb dump binary memory {p/shadow_header} {at("overlay_shadow_result"):#x} {at("overlay_shadow_result")+72:#x}')
 import struct
 shadow=struct.unpack('>10I12H2I',(p/shadow_header).read_bytes())
 target_ptr=shadow[2];cache_ptr=shadow[-2];assert target_ptr and cache_ptr,shadow
 r.command(f'gdb dump binary memory {p/shadow_target} {target_ptr:#x} {target_ptr+40032:#x}')
 r.command(f'gdb dump binary memory {p/shadow_cache} {cache_ptr:#x} {cache_ptr+5240:#x}')
 r.command(f'gdb delete\nbreak *{at("overlay_probe_after"):#x}\ncontinue')
 after=snapshot(f'program-{i}-after');assert after['pc']==at('overlay_probe_after');assert (before['program'],before['count'])==(after['program'],after['count'])
 raw=r.command(f'gdb printf "RETURN %u\\n", *(unsigned long*){before["sp"]:#x}')
 match=re.search(r'RETURN (\d+)',raw);assert match,raw
 target=int(match[1])
 r.command(f'gdb delete\nbreak *{target:#x}\ncontinue')
 returned=registers();assert returned['values']['pc']==target
 assert before['program']==program
 frames.append(dict(index=i,before=before,after=after,returned=returned,mask=dict(file=mask_file,pointer=ptr,supported=supported,program=program,count=count),pack=dict(file=pack_file,header=header_file),shadow=dict(header=shadow_header,target=shadow_target,cache=shadow_cache))); (p/'overlay-capture.json').write_text(json.dumps(dict(h3=m['entry']['h3'] if 'h3' in m['entry'] else json.loads((p/'entry-steps.json').read_text())['h3'],sha256=m['slave_sha256'],frames=frames),indent=2)+'\n');print(i,before['program'],before['count'],flush=True)
