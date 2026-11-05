"""Cross-check a trace against an independent full-state and swap capture."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('trace');p.add_argument('baseline');a=p.parse_args();root=Path(__file__).resolve().parents[1]/'tmp/prof';tr=root/a.trace;bl=root/a.baseline
m=json.loads((tr/'metadata.json').read_text());bm=json.loads((bl/'metadata.json').read_text());r=json.loads((tr/'window-metrics.json').read_text());b=json.loads((bl/'baseline.json').read_text());first=m['trace_window']['first_full_race_field'];n=m['trace_window']['fields'];assert first>1
assert m['slave_sha256']==bm['slave_sha256'] and m['emulator_sha256']==bm['emulator_sha256'] and m['layout']==bm['layout']
expected=[sum(e['offset']==0xb4 and e['field']==f for e in b['events']) for f in range(first-1,first-1+n)];actual=[x['swaps'] for x in r['per_field']]
size=sum(x['size'] for x in m['layout']['regions'][1:]);proc=subprocess.Popen(['zstd','-qdc',str(bl/'states.bin.zst')],stdout=subprocess.PIPE);target=None
for i in range(b['fields']):
 raw=proc.stdout.read(size);assert len(raw)==size
 if i==first-2:target=raw
assert proc.wait()==0
banks=[(0,(tr/'before-chip.bin').read_bytes()),(0xc00000,(tr/'before-slow.bin').read_bytes())]
def read(addr,size):
 for base,raw in banks:
  if base<=addr and addr+size<=base+len(raw):return raw[addr-base:addr-base+size]
 raise ValueError(hex(addr))
current=b''.join(read(x['base'],x['size']) for x in m['layout']['regions'][1:]);result=dict(first_full_field=first,fields=n,swaps_expected=sum(expected),swaps_traced=sum(actual),per_field_match=expected==actual,mismatches=[i for i,(x,y) in enumerate(zip(expected,actual)) if x!=y],pre_trace_full_state_match=current==target,instruction_coverage=r['coverage'],pre_trace_field=first-1)
result['passed']=result['per_field_match'] and result['pre_trace_full_state_match'];(tr/'independent-window-check.json').write_text(json.dumps(result,indent=2)+'\n');print(result);assert result['passed']
