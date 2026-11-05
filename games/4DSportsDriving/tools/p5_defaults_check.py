import json,os,struct,sys
from pathlib import Path
cap=Path(sys.argv[1]);m=json.loads((cap/'anchor.json').read_text());b=(cap/'memory.bin').read_bytes();a=m['data_base']+0x7ffe-m['memory_base'];i=b.index(b'4DPREFS!');status,loads,saves,loaded=struct.unpack_from('>IIIH',b,i+12)
expected=int(os.environ['P5_EXPECT_RATE']);expected_status=int(os.environ.get('P5_EXPECT_STATUS','0'))
assert (status,loads,saves,loaded)==(expected_status,1,0,expected),(status,loads,saves,loaded)
rates=[struct.unpack_from('>H',b,a-0xbc)[0],struct.unpack_from('>H',b,a-0x15fa)[0],b[a-0x173a]]
assert rates==[expected]*3,rates
assert b[i+26:i+30]==b'PREF' and b[i+48:i+52]==b'END!'
r=dict(status=status,loads=loads,saves=saves,rate=expected,selected_active_recorded=rates,guards=True)
(cap/'defaults-check.json').write_text(json.dumps(r,indent=2));print(r)
