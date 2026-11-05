from pathlib import Path
import sys,json,struct,hashlib,collections,bisect,statistics
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path('tmp/dev/tmp/step5');p=r/'c4-q03-render-profile-a1200-fast-rc2-trace';q=r/'c4-q03-render-profile-a1200-fast-rc2-census';a=json.loads((p/'result.json').read_text());b=json.loads((q/'result.json').read_text());t=barto.load(p/'detail.bin');lines=[json.loads(x) for x in (q/'window.jsonl').read_text().splitlines()];meta=lines[0];cs=lines[1:];assert len(t.fields)==len(cs)==48
rows=[]
for f,c in zip(t.fields,cs):
 counts=[0]*32;planes=[0]*3
 for y in range(313):
  for x in range(227):
   at=(y*227+x)*f.dma_size;typ=struct.unpack_from('<h',f.dma,at+29)[0];reg=struct.unpack_from('<H',f.dma,at)[0];addr=struct.unpack_from('<I',f.dma,at+12)[0]
   if 0<=typ<32:counts[typ]+=1
   if typ==6 and 0x110<=reg<=0x114 and reg%2==0 and not planes[(reg-0x110)//2]:planes[(reg-0x110)//2]=addr
 rows.append({'cycles_exact':f.cycles==c['cycles'],'dma_exact':counts==c['dma'],'planes_exact':planes==c['planes']})
from analyze_step3 import analyze
fps=analyze(q)
j=json.loads((p/'render-analysis.json').read_text());total=sum(x['header'] for x in j['field_accounting']);recorded=sum(x['sum'] for x in j['field_accounting'])
out={'status':'passed' if all(all(x.values()) for x in rows) and a['start_context']==b['start_context'] and a['end_context']==b['end_context'] else 'failed','fields':48,'start_context_exact':a['start_context']==b['start_context'],'end_context_exact':a['end_context']==b['end_context'],'start_snapshots_exact':all((p/f).read_bytes()==(q/f).read_bytes() for f in ['start.bin','start-fast.bin']),'end_snapshots_exact':all((p/f).read_bytes()==(q/f).read_bytes() for f in ['end.bin','end-fast.bin']),'all_dma_counts_and_bitplane_addresses_exact':all(x['dma_exact'] and x['planes_exact'] for x in rows),'field_cycles_exact':all(x['cycles_exact'] for x in rows),'trace_header_cycles':total,'recorded_cycles':recorded,'unrecorded_boundary_cycles':total-recorded,'coverage_percent':100*recorded/total,'census_fps_complete_intervals':fps['complete_interval_fps'],'census_presentations':len(fps['bank_changes']),'interval_fields':fps['interval_fields'],'metadata':meta}
(p/'audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));assert out['status']=='passed'
