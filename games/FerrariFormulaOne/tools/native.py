from pathlib import Path
import struct
from amitools.binfmt.hunk.HunkReader import HunkReader
def catalog(game):
 r=HunkReader();assert r.read_file(str(game))==0
 raw=(game).read_bytes()
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
