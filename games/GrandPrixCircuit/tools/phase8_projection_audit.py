"""Independent checks of actual projection hook inputs and outputs in CPU traces."""
import os,re,sys,json,struct,collections
from functools import cache
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from gpc_report import regions
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());raw=(p/'before.bin').read_bytes();base=m['base'];os.environ['SLAVE']=str(p/'slave.slave');rr={n:lo for lo,hi,n,o in regions(raw,base)};sb=rr['slave'];a4=rr['gpc-data']+32766;h=rr['gpc'];listing=(p/'slave.slave.lst').read_text(encoding='latin1')
@cache
def sym(n):return sb+int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)$',listing,re.M)[1],16)
def word(addr):return struct.unpack_from('>H',raw,addr-base)[0]
def signed(x):return (x+32768)%65536-32768
value=sym('render_project_value');end=value+raw[value-base:value-base+60].index(bytes.fromhex('4e75'))
main=[word(sym('render_main_y')+i*2) for i in range(41)];mirror=[word(sym('render_mirror_y')+i*2) for i in range(21)]
active=None;pending=None;calls=collections.Counter();fractions=set();draw=None
heading=sym('render_heading_fraction');heading_end=heading+raw[heading-base:heading-base+80].index(bytes.fromhex('4e75'));heading_expected=None;heading_values=[]
t=barto.load(p/'trace.bin')
for f in t.fields:
 for pc,c,r in t.instructions(f):
  if pc in (sym('render_main_projection'),sym('render_mirror_projection')):
   kind='main' if pc==sym('render_main_projection') else 'mirror';i=(r[3]&65535)//2;y=main if kind=='main' else mirror
   j=i if i==1 or i>=len(y)-1 else i+(-1 if kind=='main' else 1)
   rows=(y[i]*2,y[j]*2) if i<len(y) else (r[5]&65535,)*2
   active=dict(kind=kind,rows=rows,results=[],unused=i>=len(y))
  if pc==heading+8:
   yaw=signed(r[1]&65535);steer=signed(r[0]&65535);fraction=r[7]&65535
   if signed(abs(yaw))>=8192 and (yaw<0)==(steer<0):steer=0
   heading_expected=(steer//2)*fraction//256
  if pc==heading_end and heading_expected is not None:
   assert signed(r[0]&65535)==heading_expected
   heading_values.append(heading_expected);heading_expected=None
  if active is None:continue
  if pc==value:
   assert (r[1]&65535,r[2]&65535)==active['rows'],(active,r)
   fraction=r[7]&65535
   assert 0<=fraction<=255
   i,j=active['rows'];lo,hi=word(r[8]+i),word(r[8]+j)
   pending=(lo+(hi-lo)*fraction//256)&65535
   pending_info=dict(field=f.index,rows=(i,j),base=hex(r[8]-a4),lo=lo,hi=hi,fraction=fraction,active=active.copy())
   assert min(lo,hi)<=pending<=max(lo,hi)
   fractions.add(fraction);calls[active['kind']]+=1
  # The original shared mirror list also visits unused far entries whose
  # native row can alias changing road-length scratch. Check the actual load
  # and unchanged row selection there, not a stale before-frame RAM value.
  if pc==value+4 and active['unused']:
   pending=r[0]&65535
  if pc==value+8 and active['unused']:
   assert r[4]&65535==pending
  if pc==end:
   assert pending is not None and r[0]&65535==pending,(pc,r[0],pending,pending_info)
   active['results'].append(pending);pending=None
  if pc in (h+0x9b24,h+0x9232):
   assert len(active['results'])==3
   assert r[0]&65535==active['results'][0]
  if pc in (h+0x9b3c,h+0x924a):assert r[6]&65535==active['results'][1]
  if pc in (h+0x9b48,h+0x9256):before_left=r[4]&65535
  if pc in (h+0x9b50,h+0x925e):assert r[4]&65535==(before_left-active['results'][2])&65535
  if pc in (h+0x9b64,h+0x9272):before_right=r[0]&65535
  if pc in (h+0x9b6c,h+0x927a):assert r[0]&65535==(before_right+active['results'][2])&65535
assert calls['main'] and calls['mirror'],calls
result=dict(coefficient_calls=dict(calls),fractions=sorted(fractions),neighbours_and_results='exact',width_and_margin_outputs='exact',heading_samples=len(heading_values),heading_nonzero=sum(x!=0 for x in heading_values),heading_corrections=sorted(set(heading_values)))
(p/'projection-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
