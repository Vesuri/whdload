import sys,re,struct,json,collections
from harness_a import *
from drive import barto
s=Session(sys.argv[1]);first,last=0xa5d60,0xa6ee0
try:
 route(s)
 original=bytearray(0x40000);operands={}
 for line in (ROOT/'tmp/ana/game.dis').read_text().splitlines():
  m=re.match(r'\s*([0-9a-fA-F]{6,8})\s+([0-9a-f]+)\s+(.*)',line)
  if not m:continue
  a=int(m[1],16);data=bytes.fromhex(m[2]);original[a-0x80000:a-0x80000+len(data)]=data
  for off in range(2,len(data)-3,2):
   value=int.from_bytes(data[off:off+4],'big')
   if first<=value<last:operands[a+off]=dict(value=value,instruction=line.strip())
 # Recover three real operands hidden by linear disassembly of preceding data.
 for a,pc in [(0x898e6,0x898e4),(0x8af7c,0x8af7a),(0x8b48a,0x8b486)]:
  value=int.from_bytes(original[a-0x80000:a-0x80000+4],'big');assert first<=value<last
  operands[a]=dict(value=value,instruction='entry '+hex(pc)+' requires aligned decoding')
 data_sites={0x9017c}|set(range(0x90948,0x9096c,4))|set(range(0x909cc,0x909e4,4))|set(range(0x94192,0x941d2,4))|{0x941d6,0x941da,0x941e2}|set(range(0x941ea,0x9422a,4))
 raw={0x80000+i:int.from_bytes(original[i:i+4],'big') for i in range(0,len(original)-3,2) if first<=int.from_bytes(original[i:i+4],'big')<last}
 assert len(operands)==202 and len(data_sites)==51 and data_sites<=raw.keys()
 false_sites=sorted(raw.keys()-operands.keys()-data_sites);assert len(false_sites)==40
 live=read_bytes(s,0x80000,0x40000);(s.out/'main-field100.bin').write_bytes(live)
 for a,row in operands.items():row['live_value']=int.from_bytes(live[a-0x80000:a-0x80000+4],'big')
 s.input('JOY2_UP',1);advance(s,300);start=field(s);p=s.out/'actor-dma.bin';s.cmd(f'monitor profile 19 "" "{p}"',timeout=120);end=field(s);trace=barto.load(str(p));assert len(trace.fields)==19 and end==start+20
 overall=collections.Counter();actor=collections.Counter();addresses=set()
 for f in trace.fields:
  assert f.dma_size==58,f.dma_size
  for i in range(0,len(f.dma),f.dma_size):
   addr=struct.unpack_from('<I',f.dma,i+12)[0];kind=struct.unpack_from('<h',f.dma,i+29)[0]
   overall[kind]+=1
   if first<=addr<last:actor[kind]+=1;addresses.add(addr)
 result=dict(provenance=provenance(os.environ['SLAVE'],s),actor_range=[hex(first),hex(last)],instruction_operands={hex(a):r for a,r in sorted(operands.items())},snapshot_pointer_sites=[hex(a) for a in sorted(data_sites)],raw_scan_false_positives=[hex(a) for a in false_sites],changed_operands={hex(a):r for a,r in operands.items() if r['value']!=r['live_value']},dma=dict(start=start,end=end,recorded_fields=len(trace.fields),all_types=dict(overall),actor_types=dict(actor),distinct_actor_bus_addresses=len(addresses)))
 (s.out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print('operands',len(operands),'pointer sites',len(data_sites),'false positives',len(false_sites),'changed',list(result['changed_operands']),'actor bus types',dict(actor),flush=True)
finally:s.quit()
