#!/usr/bin/env python3
"""Overlay identities are executable file HEADER offsets plus local hunk numbers.
Decode the loader's actual hunk table, including BSS, instead of signature guesses.
Runtime table entries are validated against immutable CODE (relocations masked).
"""
from pathlib import Path
import struct,json,sys,hashlib
from amitools.binfmt.hunk.HunkReader import HunkReader
ROOT=Path(__file__).resolve().parents[1]
def catalog():
 r=HunkReader();assert r.read_file(str(ROOT/'tmp/game/FerrariFormulaOne/data/racemenu'))==0
 raw=(ROOT/'tmp/game/FerrariFormulaOne/data/racemenu').read_bytes()
 groups=[];current=None
 for h in r.hunks:
  typ=h['type_name']
  if typ=='HUNK_HEADER':
   group={'identity':f'file:{h["hunk_file_offset"]:05x}','header':h['hunk_file_offset'],'first':h['first_hunk'],'last':h['last_hunk'],'hunks':[]};groups.append(group)
  elif typ in ('HUNK_CODE','HUNK_DATA','HUNK_BSS'):
   current={'number':group['first']+len(group['hunks']),'type':typ,'size':h['size'],'data':h.get('data',b''),'reloc':{}};group['hunks'].append(current)
  elif 'RELOC32' in typ:
   # This executable repeats destination hunks within a relocation block.
   # HunkReader.parse_reloc overwrites earlier entries; preserve every group.
   at=h['hunk_file_offset']+4
   while True:
    count=struct.unpack_from('>I',raw,at)[0];at+=4
    if count==0:break
    target=struct.unpack_from('>I',raw,at)[0];at+=4
    offsets=list(struct.unpack_from('>'+str(count)+'I',raw,at));at+=count*4
    current['reloc'].setdefault(target,[]).extend(offsets)
 return groups

def decode(b):
 u=lambda a:struct.unpack_from('>I',b,a)[0]
 table=u(0x197b0)*4
 groups=catalog();out=[]
 # Settled demo: resolve active overlays from loader records, never stale slots.
 records=[]
 for i in range(u(0x19d98)+1):
  a=u(0x19d9c)+32*i
  records.append({"header":u(a),"segment_bptr":u(a+4),"first_hunk":u(a+20),"entry_hunk":u(a+24),"entry_offset":u(a+28)})
 active={0}|{v["header"] for v in records if v["segment_bptr"] & 0x80000000}
 for gr in groups:
  if gr['header'] not in active:continue
  hunks=[];good=bad=0
  for h in gr['hunks']:
   ptr=u(table+h['number']*4)*4;base=ptr+4;size=h['size'];matching=None
   if not 0<base<0x80000 or base+size>len(b):continue
   if h['type']=='HUNK_CODE' and size>=16:
    mask={i for offsets in h['reloc'].values() for off in offsets for i in range(off,off+4)}
    # Every source modification is explicitly recorded, not a fuzzy threshold.
    if gr['header']==0:patches={0:[(0x770,0x770+6),(0x7f6,0x7f8),(0x7fc,0x802),(0x2e6,0x2ec),(0x7aa,0x7b0),(0x864,0x86a)],3:[(0x1b9f2-base,0x1b9f8-base)]}.get(h['number'],[])
    else:patches=[]
    for lo,hi in patches:mask.update(range(lo,hi))
    # Overlay patches expressed relative to the first race hunk base.
    if gr['header']==0x22f30:
     for lo,hi in [(0x65518,0x6551e),(0x6a304,0x6a30a),(0x6b0ba,0x6b0bc)]:mask.update(range(max(0,lo-base),min(size,hi-base)))
    valid=[i for i in range(size) if i not in mask];matching=sum(b[base+i]==h['data'][i] for i in valid)
    good+=matching;bad+=len(valid)-matching
   hunks.append({'number':h['number'],'base':base,'size':size,'type':h['type'],'next_bptr':u(ptr),'allocation_size':u(ptr-4),'matched_code_bytes':matching})
  out.append({'identity':gr['identity'],'header':gr['header'],'first':gr['first'],'last':gr['last'],'matched_code_bytes':good,'different_code_bytes':bad,'hunks':hunks})
 return {'scope':'SPS/A500 settled demo; code differences include instrumentation and mutable CODE data, not an acceptance check','table':table,'overlay_records':records,'groups':out}
if __name__=='__main__':
 result=decode(Path(sys.argv[1]).read_bytes());print(json.dumps(result,indent=2))
