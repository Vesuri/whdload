#!/usr/bin/env python3
"""Identify file-backed code by independent non-relocation signature votes."""
from pathlib import Path
import json,collections,sys
from amitools.binfmt.hunk.HunkReader import HunkReader
root=Path(__file__).resolve().parents[1]
r=HunkReader();assert r.read_file(str(root/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'))==0
memory=Path(sys.argv[1]).read_bytes();items=[];current=None
for h in r.hunks:
 if h['type_name'] in ('HUNK_CODE','HUNK_DATA','HUNK_BSS'):
  current=dict(h); current['relocations']=[];items.append(current)
 elif 'RELOC32' in h['type_name'] and current is not None:
  current['relocations'] += [off for offsets in h['reloc'].values() for off in offsets]
result=[]
for ordinal,h in enumerate(items):
 if 'data' not in h or h['size']<16:continue
 b=h['data'];masked={i for off in h['relocations'] for i in range(off,off+4)}
 votes=collections.Counter()
 for off in range(0,len(b)-15,2):
  if any(i in masked for i in range(off,off+16)):continue
  part=b[off:off+16]
  if len(set(part))<5:continue
  start=memory.find(part)
  if start<0 or memory.find(part,start+1)>=0:continue
  votes[start-off]+=1
 if not votes:continue
 base,count=votes.most_common(1)[0]
 if base<0 or base+len(b)>len(memory) or count<2:continue
 valid=[i for i in range(len(b)) if i not in masked]
 matches=sum(memory[base+i]==b[i] for i in valid)
 if matches/len(valid)<0.98:continue
 result.append(dict(nonrelocation_matches=matches,nonrelocation_bytes=len(valid),ordinal=ordinal,file_offset=h['data_file_offset'],type=h['type_name'],size=len(b),base=base,votes=count,relocations=h['relocations']))
print(json.dumps(result,indent=2))
