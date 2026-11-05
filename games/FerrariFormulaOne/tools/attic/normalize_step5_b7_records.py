from pathlib import Path
import struct,json,sys
from step5_b7_addresses import Addresses
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'/sys.argv[1];report=json.loads((p/'result.json').read_text());assert report['status']=='complete';table=int(report['table'],16);ad=Addresses((p/'loop225-raw.bin').read_bytes(),table)
for name,offsets in [('speed_records',(0,)),('wear_records',(0,4)),('fuel_records',(0,4))]:
 f=p/(name+'.bin')
 if not f.exists():continue
 raw=p/(name+'-raw.bin')
 if not raw.exists():raw.write_bytes(f.read_bytes())
 b=bytearray(raw.read_bytes());assert len(b)%32==0
 for at in range(0,len(b),32):
  for off in offsets:
   value=struct.unpack_from('>I',b,at+off)[0];struct.pack_into('>I',b,at+off,ad.map(value,True))
 f.write_bytes(b)
report['record_normalization']='Explicit native-pointer columns only: speed[0], wear[0,4], fuel[0,4], 32-byte records. Raw records retained. All numeric fields unchanged.'
(p/'result.json').write_text(json.dumps(report,indent=2)+'\n')
