#!/usr/bin/env python3
"""Analyze a cockpit_probe.py run: opaque panel mask, call order, ScanFillDown overdraw.

  cockpit_probe_analyze.py PROBE_DIR [OUT.json]

Buffer layout: 8 planes x 8,000 bytes, 40 bytes per row, 200 rows.
"""
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);d=json.loads((p/'probe.json').read_text());ev=d['events']
W,H=320,200
def s16(x):return x-65536 if x&32768 else x
def bits(buf):
 # Per pixel, an 8-bit tuple of plane bits as an integer mask over planes.
 out=[[0]*W for _ in range(H)]
 for pl in range(8):
  b=buf[pl*8000:(pl+1)*8000]
  for y in range(H):
   row=out[y];o=y*40
   for x in range(W):
    if b[o+(x>>3)]&(0x80>>(x&7)):row[x]|=1<<pl
 return out
report=dict(probe=d['probe'])
post1=p/'frame1-post.bin';post2=p/'frame2-post.bin'
if post1.exists() and post2.exists():
 a=bits(post1.read_bytes());b=bits(post2.read_bytes())
 # Plane bits that do not depend on the $00/$ff background are panel-written.
 opaque=[[a[y][x]==b[y][x] for x in range(W)] for y in range(H)]
 partial=[[(~(a[y][x]^b[y][x]))&255 for x in range(W)] for y in range(H)]
 report['opaque_pixels']=sum(map(sum,opaque))
 report['partially_written_pixels']=sum(1 for y in range(H) for x in range(W) if 0<partial[y][x]<255)
 rows_full=[y for y in range(H) if all(opaque[y])]
 report['fully_opaque_rows']=[rows_full[0],rows_full[-1],len(rows_full)] if rows_full else []
 report['opaque_per_row']=[sum(opaque[y]) for y in range(H)]
 # Opaque runs per row (x ranges) in 32-pixel longword columns.
 report['opaque_longword_columns_per_row']=[sum(all(opaque[y][c*32:(c+1)*32]) for c in range(10)) for y in range(H)]
 (p/'opaque-mask.json').write_text(json.dumps([[int(v) for v in r] for r in opaque]))
else:opaque=None
frames={}
for e in ev:
 f=e['frame']
 if f<1:continue
 fr=frames.setdefault(f,dict(order=[],spans=0,lines=0,pixels=0,hidden=0,hidden_lines=0,lines_fully_hidden=0,calls_fully_hidden=0,after_panel=0,rows=[0]*H))
 if e['event']=='swap':continue
 if not fr['order'] or fr['order'][-1][0]!=e['event']:fr['order'].append([e['event'],1])
 else:fr['order'][-1][1]+=1
 if e['event']=='panel_call':fr['panel']=True
 if e['event']!='ScanFillDown':continue
 if fr.get('panel'):fr['after_panel']+=1
 r=e['regs'];y0=s16(r['a6']&65535);n=s16(r['d7']&65535);xl=r['a2'];xr=r['a3'];dl=r['a4'];dr=r['a5']
 fr['spans']+=1;callhidden=True
 for i in range(max(n,0)):
  l=s16(((xl+i*dl)&0xffffffff)>>16);rr=s16(((xr+i*dr)&0xffffffff)>>16);y=y0+i
  if rr<l:continue
  fr['lines']+=1;fr['pixels']+=rr-l+1
  if 0<=y<H:fr['rows'][y]+=rr-l+1
  if opaque and 0<=y<H:
   h=sum(opaque[y][x] for x in range(max(l,0),min(rr,W-1)+1));fr['hidden']+=h
   if h==rr-l+1:fr['lines_fully_hidden']+=1
   else:callhidden=False
  else:callhidden=False
 if callhidden and n>0:fr['calls_fully_hidden']+=1
for f,fr in frames.items():
 fr.pop('panel',None);fr['hidden_pct']=round(100*fr['hidden']/fr['pixels'],2) if fr['pixels'] else 0
 rows=fr.pop('rows');fr['span_pixels_by_band']={f'{y}-{y+19}':sum(rows[y:y+20]) for y in range(0,H,20)}
report['frames']=frames
out=Path(sys.argv[2]) if len(sys.argv)>2 else p/'analysis.json'
out.write_text(json.dumps(report,indent=1));print(json.dumps({k:v for k,v in report.items() if k not in('opaque_per_row','opaque_longword_columns_per_row')},indent=1))
