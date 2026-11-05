#!/usr/bin/env python3
"""Check actual native score insertion, row permutation and both persisted files."""
import argparse,json,re,struct,zlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--case',type=int,choices=(1,2,3),required=True);p.add_argument('--saved-dir',type=Path,required=True);a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes();meta=json.loads((a.capture/'anchor.json').read_text())
symbols={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',(a.capture/'slave.lst').read_text(encoding='latin1'),re.M)}
starts=[m.start() for m in re.finditer(b'4DSCINS!',b) if struct.unpack_from('>I',b,m.start()+12)[0]==1];assert len(starts)==1
at=starts[0];assert struct.unpack_from('>HH4I',b,at+8)==(1,a.case,1,1,0,1)
base=at+12-symbols['sim_score_insert_test_count']
assert struct.unpack_from('>HHI',b,base+symbols['sim_score_rank_passed']-4)==(1,12,12)
empty=0xffffffffffffffff
mode=meta['active_simulation_word']
assert struct.unpack_from('>I',b,base+symbols['sim_score_insert_test_mode'])[0]==mode
initial=[1000,2000,3000,4000,5000,6000,7000] if a.case==1 and mode==50 else [150002]+[empty]*6
candidate={1:3502,2:131072,3:393216000}[a.case] if mode==50 else 1751*(100//mode)
if mode!=50:assert a.case==1
expected_physical=initial[:6]+[candidate]
expected_map={1:[0,1,2,6,3,4,5],2:[6,0,1,2,3,4,5],3:[0,6,1,2,3,4,5]}[a.case] if mode==50 else [6,0,1,2,3,4,5]
expected_sorted=[expected_physical[i] for i in expected_map]
assert list(struct.unpack_from('>7Q',b,base+symbols['sim_score_records']))==expected_physical
assert struct.unpack_from('>Q',b,base+symbols['sim_score_candidate'])[0]==candidate
assert list(struct.unpack_from('>7Q',b,base+symbols['sim_score_sorted']))==expected_sorted
assert struct.unpack_from('>I',b,base+symbols['sim_score_record_status'])[0]==1
assert struct.unpack_from('>I',b,base+symbols['sim_score_sorted_guard'])[0]==0x534f5254
state=meta['data_base']+0x7ffe-meta['memory_base'];order=list(struct.unpack_from('>7H',b,state-0x160a));assert order==expected_map,order
ptr=struct.unpack_from('>I',b,state-0x1784)[0]-meta['memory_base'];physical=b[ptr:ptr+364];assert len(physical)==364
native=(a.saved_dir/'Default.Hig').read_bytes();side=(a.saved_dir/'Default.hix').read_bytes()
assert native==b''.join(physical[i*52:(i+1)*52] for i in expected_map)
assert len(side)==440 and struct.unpack_from('>8sHHI',side)==(b'4DHIG100',1,7,364)
assert side[20:384]==native and struct.unpack_from('>I',side,16)[0]==zlib.crc32(side[20:])
assert list(struct.unpack_from('>7Q',side,384))==expected_sorted
mirrors=[struct.unpack_from('>H',native,i*52+50)[0] for i in range(7)]
assert mirrors==[(x+4)//5 if x<=327670 else 65535 for x in expected_sorted]
(a.capture/'saved-native.hig').write_bytes(native);(a.capture/'saved-sidecar.hix').write_bytes(side)
result={'case':a.case,'mode':mode,'eligibility':True,'candidate_hundredths':candidate,'repeat_rejected':True,'physical_times':expected_physical,'row_order':order,'saved_exact_times':expected_sorted,'native_mirrors':mirrors,'crc32':hex(zlib.crc32(side[20:])),'native_saved_bytes':len(native),'sidecar_saved_bytes':len(side)}
(a.capture/'score-insert-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
