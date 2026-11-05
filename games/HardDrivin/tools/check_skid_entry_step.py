"""Check skid entry cadence and entry-step spin hold in live motion captures.

Native steering tests skid entry once per eight-field engine step, and the
native step that creates the spin also decays it, so the undecayed spin never
rotates the car. For every captured skid entry this checks that the entry pass
contains an engine-step start, that the published spin phase counts from that
start, that no spin rotation happens before the first decay boundary, and it
reports the spin part of the heading change over the skid next to the native
sum. Spin rotation is the INPUT-row heading delta: B386 rotates by spin before
steering, whose half-rate turn the INTEGRATED row adds.
Usage: check_skid_entry_step.py RUN [RUN...]   (run names below tmp/prof)
"""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'tmp/prof'
def decay(v):
 p=(v*9+32768)%65536-32768
 return abs(p)//10*(-1 if p<0 else 1)
def wrap(d):
 return (d+720)%1440-720
report=[]
for name in sys.argv[1:]:
 rows=[r for r in json.loads((root/name/'motion.json').read_text())['rows'] if r['kind'] in('INPUT','INTEGRATED')]
 passes=[];cur=None
 for r in rows:
  if r['kind']=='INPUT':cur=r
  elif cur is not None:passes.append((cur,r));cur=None
 entries=[]
 for i,(a,b) in enumerate(passes):
  if a['skid'] or not b['skid']:continue
  T=b['interval'];first=(8-a['phase'])%8
  assert first<T,(name,'entry pass without an engine-step start',a['field'],a['phase'],T)
  since=T-first
  assert b['spin_carry']==since%8,(name,a['field'],b['spin_carry'],since)
  # Native rotation starts with the spin after the entry step's own decay.
  x=decay(b['spin']) if since<8 else b['spin'];native=0
  while x:native+=x;x=decay(x)
  held=max(0,8-since);fields=0;spin=0;j=i+1
  while j<len(passes) and passes[j][0]['skid']:
   d=wrap(passes[j][0]['heading']-passes[j-1][1]['heading']);n=passes[j][1]['interval']
   if fields+n<=held:assert d==0,(name,'spin rotated during entry hold',passes[j][0]['field'],d)
   spin+=d;fields+=n;j+=1
  entries.append(dict(field=a['field'],interval=T,engine_phase=a['phase'],fields_since_step=since,
   published_spin=b['spin'],native_spin_sum=native,spin_rotation=spin,skid_fields_after_entry=fields))
 assert entries,(name,'no skid entries')
 report.append(dict(run=name,entries=entries))
print(json.dumps(report,indent=1))
