from pathlib import Path
import sys,struct,collections,json
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path('tmp/dev/tmp/step5/c4-q03-render-profile-a1200-fast-h3-matched-candidate');t=barto.load(p/'detail.bin')
def reads(f):
 out={}
 for at in range(0,len(f.dma),f.dma_size):
  if struct.unpack_from('<h',f.dma,at+29)[0]==6:
   addr=struct.unpack_from('<I',f.dma,at+12)[0];reg=struct.unpack_from('<H',f.dma,at)[0];data=struct.unpack_from('<Q',f.dma,at+2)[0]
   out[(reg,addr)]=data
 return out
x,y=reads(t.fields[0]),reads(t.fields[2]);diff=[(reg,addr,x[(reg,addr)],v) for (reg,addr),v in y.items() if x[(reg,addr)]!=v];print('diff words',len(diff));print(diff[:30]);print('address ranges',[(hex(reg),hex(min(a for rr,a,_,_ in diff if rr==reg)),hex(max(a for rr,a,_,_ in diff if rr==reg))) for reg in sorted({k[0] for k in diff})]);print('all refs',len(x),len(y))
z=reads(t.fields[3]);firsts=[102220,112540,122860];nexts=[338140,348460,358780]
print('Changed words matching next buffer',sum(y[(reg,a)]==z.get((reg,a-firsts[(reg-0x110)//2]+nexts[(reg-0x110)//2])) for reg,a,_,v in diff),'/',len(diff))
for i in [0,2,3]:
 im=__import__('PIL.Image',fromlist=['Image']).open(p/f'field-{i}.png');im.crop((450,50,680,120)).resize((920,280)).save(p/f'clock-{i}.png')
