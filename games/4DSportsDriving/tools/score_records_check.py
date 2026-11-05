#!/usr/bin/env python3
"""Check the actual game's loaded/reset exact-score companion state."""
import argparse,json,re,struct
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path);p.add_argument('--status',type=int,required=True)
p.add_argument('--first',type=int,default=0xffffffffffffffff);p.add_argument('--reset',action='store_true')
p.add_argument('--expected-sidecar',type=Path)
a=p.parse_args();b=(a.capture/'memory.bin').read_bytes();meta=json.loads((a.capture/'anchor.json').read_text())
symbols={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',(a.capture/'slave.lst').read_text(encoding='latin1'),re.M)}
starts=[m.start() for m in re.finditer(b'4DSCRECS',b) if struct.unpack_from('>I',b,m.start()+16)[0]>0]
assert len(starts)==1,starts
at=starts[0];version,size,status,loads,resets=struct.unpack_from('>HHIII',b,at+8)
assert (version,size,status)==(1,56,a.status),(version,size,status)
expected_times=list(struct.unpack_from('>7Q',a.expected_sidecar.read_bytes(),384)) if a.expected_sidecar else [a.first]+[0xffffffffffffffff]*6
exact=list(struct.unpack_from('>7Q',b,at+24));assert exact==expected_times,exact
assert struct.unpack_from('>I',b,at+80)[0]==0x52454353
assert struct.unpack_from('>I',b,at+84+256)[0]==0x50415448
name=b[at+84:at+84+256].split(b'\0',1)[0].decode()
if status!=3:assert name.lower().endswith('default.hix'),name
base=at+12-symbols['sim_score_record_status']
q=base+symbols['sim_score_load_test_count'];assert struct.unpack_from('>II',b,q)==(1,1 if status==3 else 0)
if a.reset:
 assert resets==1,resets
 q=base+symbols['sim_score_reset_test_count'];assert struct.unpack_from('>II',b,q)==(1,0)
else:assert resets==0,resets
native_ptr=struct.unpack_from('>I',b,meta['data_base']+0x7ffe-0x1784-meta['memory_base'])[0]
native=b[native_ptr-meta['memory_base']:native_ptr-meta['memory_base']+364];assert len(native)==364
mirrors=[struct.unpack_from('>H',native,i*52+50)[0] for i in range(7)]
expected=[(v+4)//5 if v<=327670 else 65535 for v in exact]
if status!=3:assert mirrors==expected,(mirrors,expected)
result={'status':status,'loads':loads,'resets':resets,'filename':name,'exact_hundredths':exact,'native_mirrors':mirrors,'guards':'intact'}
(a.capture/'score-records-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
