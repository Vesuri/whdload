#!/usr/bin/env python3
from pathlib import Path
import sys,json,collections,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from overlay_map import decode
root=Path(__file__).resolve().parents[1]
def run(name):
 p=root/'tmp/step3'/name;b=(p/'anchor.bin').read_bytes();a=json.loads((p/'analysis.json').read_text());mapping=decode(b)
 hunks=[(h['base'],h['base']+h['size'],g['identity']+':h'+str(h['number']),h['type']) for g in mapping['groups'] for h in g['hunks']]
 groups=collections.Counter();categories=collections.Counter();total=sum(int(k)*n for k,n in a['cycle_values'].items())*min(500,a['fields'])/a['fields']
 for key,(cycles,hits) in a['all_pcs_first500'].items():
  pc=int(key,16)
  if pc in (0x7fffffff,0xfffffffe):categories['trace overhead / stopped CPU']+=cycles;groups['trace overhead / stopped CPU']+=cycles;continue
  irq=bool(pc&0x1000000);pc &= 0xffffff
  owner=next((n for lo,hi,n,typ in hunks if lo<=pc<hi),'outside active game hunks')
  groups[('IRQ: ' if irq else '')+owner]+=cycles
  if irq:cat='interrupt stack'
  elif pc==0x2ae58:cat='idle task spin'
  elif 0x65728<=pc<0x65734:cat='explicit beam wait'
  elif 0x293d0<=pc<=0x29410:cat='software signed 32-bit division'
  elif 0x67120<=pc<0x6872e:cat='eight-car simulation body (self)'
  elif 0x64a68<=pc<0x6ef20:cat='other race code (self)'
  elif owner!='outside active game hunks':cat='resident game/runtime (self)'
  else:cat='KickEmu/OS/other code (self)'
  categories[cat]+=cycles
 result={'scope':'first 500 fields or whole shorter capture; exclusive PC cost, not inclusive routine time','accounting_fraction':sum(categories.values())/total,'categories':[{'name':k,'cycles':v,'percent':100*v/total} for k,v in categories.most_common()],'hunks':[{'name':k,'cycles':v,'percent':100*v/total} for k,v in groups.most_common()]}
 (p/'costs.json').write_text(json.dumps(result,indent=2)+'\n');(p/'overlays.json').write_text(json.dumps(mapping,indent=2)+'\n');print(name,result['categories'])
if __name__=='__main__':
 for name in sys.argv[1:]:run(name)
