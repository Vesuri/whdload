"""Installed retired speed key: accepted commands, unchanged clock and speed data."""
from pathlib import Path
import json,re,struct,sys
root=Path(__file__).resolve().parents[1]
l=(root/'tmp/build/retired-speed.slave.lst').read_text(encoding='latin1')
sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
d=Path(sys.argv[1]);initial=(d/'active-epoch-arena.bin').read_bytes();fast=(d/'fast.bin').read_bytes()
def val(a,n,o=0,w=4):return int.from_bytes(a[sym(n)+o:sym(n)+o+w],'big')
h6=val(initial,'RT_HUNKS',24);original=fast[h6+0x1548-0x200000:h6+0x154c-0x200000]
epoch=val(initial,'RT_CLOCK')-val(initial,'RT_CLOCK',4);records={};rows=[]
for directory in sorted(d.glob('world-*'),key=lambda p:int(p.name.split('-')[1])):
 a=(directory/'arena.bin').read_bytes();h=(directory/'h6.bin').read_bytes();w=int(directory.name.split('-')[1])
 assert h[0x1548:0x154c]==original
 assert val(a,'RT_CLOCK',16)==val(initial,'RT_CLOCK',16)
 assert val(a,'RT_CLOCK')-val(a,'RT_CLOCK',4)==epoch
 assert val(a,'RT_CLOCK',4)==(w*50+2)//3
 assert val(a,'RT_CLOCK',24,2)==val(a,'RT_CAPTURE_OWNER',0,2)==1
 for name,off in [('RT_CLOCK',12),('RT_HISTORY',12),('RT_COMMANDS',16),('RT_COMMANDS',20)]:assert val(a,name,off)==0
 write=val(a,'RT_COMMANDS',0,2);assert write<128
 for index in range(write):
  seq,key,flags=struct.unpack_from('>IHH',a,sym('RT_COMMANDS')+24+index*8)
  if key==12:records[seq]=dict(key=key,flags=flags)
 rows.append(w)
assert len(rows)==21 and len(records)==3,(len(rows),records)
assert all(r['flags']==0 for r in records.values()),records
result=dict(status='passed',worlds=rows,accepted_speed_keys=len(records),lifecycle_markers=0,rebases_added=0,active_time_input_loss=0,native_speed_words=original.hex(),clock_epoch_preserved=True)
(d/'retired-speed-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
