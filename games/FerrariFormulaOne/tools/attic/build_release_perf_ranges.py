from pathlib import Path
import json,struct,hashlib
from step5_b7_addresses import Addresses
r=Path(__file__).resolve().parents[1];build=json.loads((r/'tmp/build/production/build.json').read_text());points=set();sources=[]
for kind,name,label in [('000','c4-q03-production-live-a500-candidate','takeover'),('fine','c4-q03-production-live-a1200-fast-candidate','takeover'),('020','c4-q03-production-state-production-a1200-candidate','anchor')]:
 p=r/'tmp/step5'/name;report=json.loads((p/'result.json').read_text());mem=(p/(label+'.bin')).read_bytes()
 slow=p/(label+'-slow.bin')
 if slow.exists():mem+=bytes(0xc00000-len(mem))+slow.read_bytes()
 addresses=Addresses(mem,int(report['table'],16));sy=(json.loads((r/'tmp/build/production-matched/build.json').read_text()) if kind=='020' else build)['payloads'][kind]['symbols'];probe=int(report['probe'],16);ctx=probe+sy['public_patch_context' if kind=='fine' else 'C1Ledger'];data,capacity,used=struct.unpack_from('>III',mem,ctx+8);assert 0<used<=capacity and used%6==0
 native=[]
 for off in range(0,used,6):
  actual=struct.unpack_from('>I',mem,data+off)[0];canonical=addresses.map(actual,True);assert canonical<0x80000,(kind,hex(actual),hex(canonical));native.append(canonical);points.add(canonical)
 sources.append(dict(engine=kind,evidence=name,label=label,ledger_words=len(set(native)),snapshot_sha256=hashlib.sha256(mem).hexdigest()))
ranges=[]
for address in sorted(points):
 if ranges and ranges[-1]['start']+ranges[-1]['bytes']==address:ranges[-1]['bytes']+=2
 else:ranges.append({'start':address,'bytes':2})
report={'scope':'Union of actual native patch-ledger words from all three accepted production engines; compare disabled runtime with legacy at these exact native ranges. Includes engine patches; loader/host gates require separate audit.','sources':sources,'PERF_RANGE':ranges,'words':len(points),'version':'SPS 0481'}
(r/'manifest/release-perf-ranges.json').write_text(json.dumps(report,indent=2)+'\n');print(len(points),'native words across',len(ranges),'ranges')
