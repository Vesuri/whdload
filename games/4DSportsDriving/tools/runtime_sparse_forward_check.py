#!/usr/bin/env python3
"""Check native reload/playback regeneration of a fully omitted checkpoint pair."""
import json,struct,zlib,hashlib
from pathlib import Path
src=Path('tmp/runtime-later-checkpoint');r=Path('tmp/runtime-sparse-forward-fixed');m=json.loads((r/'start/anchor.json').read_text());a=m['data_base']+0x7ffe-m['memory_base']
f=(r/'game/data/a4test.rpl').read_bytes();expected=bytearray((src/'a4test.rpl').read_bytes());expected[32984:34104]=bytes(1120);expected[54656:55048]=bytes(392);expected[-4:]=zlib.crc32(expected[:-4]).to_bytes(4,'big');assert f==expected
loaded=(r/'loaded.bin').read_bytes();ptr=struct.unpack_from('>I',loaded,a-0x16bc)[0]-m['memory_base'];h=loaded.index(b'4DHISTRY')+28;assert not any(loaded[ptr+1120:ptr+2240]+loaded[h+392:h+784])
def sem(root,name):
 b=(root/(name+'.bin')).read_bytes();q=json.loads((root/'start/anchor.json').read_text());aa=q['data_base']+0x7ffe-q['memory_base'];v=b[aa-0xa80:aa-0x620]+b[aa+0x228:aa+0x22e]
 for tag,n in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
  p=b.index(tag)+12;v+=b[p:p+n]
 assert len(v)==1510;return v
for t in (1500,1550,1600):assert sem(src,'live-'+str(t))==sem(r,'seek-'+str(t)),t
end=(r/'seek-result.bin').read_bytes();ptr=struct.unpack_from('>I',end,a-0x16bc)[0]-m['memory_base'];h=end.index(b'4DHISTRY')+28;orig=(src/'a4test.rpl').read_bytes()
assert end[ptr+1120:ptr+2240]==orig[32984:34104]
assert end[h+392:h+784]==orig[54656:55048]
s=json.loads((r/'seek-result.json').read_text());assert s['perf_failure']==s['sim_schedule_overflow']==0
assert 'TARGET 1651' in (r/'seek.log').read_text() and 'HISTORY_FAILURE 0 DONE 1' in (r/'seek.log').read_text()
assert s['consumer']==s['imported']==1651
report=dict(file_sha256=hashlib.sha256(f).hexdigest(),omitted_slot=1,loaded_slot_empty=True,rebuilt_native_bytes=1120,rebuilt_companion_bytes=392,exact_semantic_bytes=1510,equal_ticks=[1500,1550,1600],guest_memory_modified=False,scope='Current fixed runtime native file chooser accepts sparse checkpoint pair; direct forward seek targets1651 from loaded origin0 and reconstructs missing slot1 exactly. WARP correctness only; no guest writes.')
(r/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
