from pathlib import Path
import json,sys,struct,collections,gzip,shutil,hashlib,subprocess
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
r=Path(__file__).resolve().parents[1];out={}
for name,leaf in [('before','hi25-profile-040-40-bce-h11-v2-grid-candidate'),('after','hi25-profile-040-40-bce-b8pal-grid')]:
 p=r/'tmp/step5'/leaf;raw=p/'detail.bin';temporary=not raw.exists()
 if temporary:
  with gzip.open(str(raw)+'.gz','rb') as a,raw.open('wb') as b:shutil.copyfileobj(a,b)
 report=json.loads((p/'result.json').read_text());sy=report['symbols'];base=int(report['probe'],16);trace=barto.load(raw);counts=collections.Counter();palette=[];entries=[]
 for f in trace.fields[:6]:
  for pc,cost,regs in trace.instructions(f):
   if pc==base+sy['B8_65518']:entries.append((f.index,regs[1]&65535))
   if name=='before' and pc==base+sy['B8_6551e']-6:counts['pulse_instructions']+=1
  for at in range(0,len(f.dma),f.dma_size):
   reg=struct.unpack_from('<H',f.dma,at)[0];addr=struct.unpack_from('<I',f.dma,at+12)[0];data=struct.unpack_from('<Q',f.dma,at+2)[0];typ=struct.unpack_from('<h',f.dma,at+29)[0]
   if reg in (0x1101,0x1102,0x1104) and 0xdff180<=addr<=0xdff1be:counts['CPU_palette_bus_writes']+=1
   if reg!=65535 and 0x180<=reg<=0x1be:
    palette.append((f.index,at//f.dma_size,typ,reg,data))
 counts['palette_register_events']=len(palette);out[name]={'counts':dict(counts),'draw_entries':entries,'palette_events':palette,'fields':6}
 if temporary:raw.unlink()
assert out['before']['counts']['pulse_instructions']>0
assert out['after']['draw_entries'] and out['after']['counts'].get('CPU_palette_bus_writes',0)==0
# The removed direct CPU register events must be absent; copper events persist.
print(json.dumps(out,indent=2))
(r/'manifest/b8-pal-trace-audit.json').write_text(json.dumps(out,indent=2)+'\n')
p=r/'tmp/step5/hi25-profile-040-40-bce-b8pal-grid'
subprocess.run([sys.executable,str(r/'tools/audit_h7_trace.py'),str(p)],check=True)
