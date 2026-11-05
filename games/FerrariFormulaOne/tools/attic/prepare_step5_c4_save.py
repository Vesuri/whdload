from pathlib import Path
import re,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-c4-motion-port'
s=(o/'motion-full-save.txt').read_text();rows=[]
def sub(m):
 op,regs=m.groups();used={'d0','d4','d7','a0'}
 for part in regs.split('/'):
  if '-' in part:
   a,b=part.split('-');used.update(a[0]+str(i) for i in range(int(a[1]),int(b[1])+1))
  else:used.add(part)
 bits=sum(1<<(int(x[1])+(8 if x[0]=='a' else 0)) for x in used)
 if op=='Save':bits=int(f'{bits:016b}'[::-1],2)
 label=f'C4SaveMask{len(rows):03d}';rows.append(dict(label=label,mask=bits,registers=sorted(used),kind=op))
 return label+' equ *\n '+('movem.l d0-d7/a0-a6,-(sp)' if op=='Save' else 'movem.l (sp)+,d0-d7/a0-a6')
s=re.sub(r'^ FF1Player(Save|Restore) ([^\n]+)$',sub,s,flags=re.M)
(o/'motion.s').write_text(s);(o/'save-masks.json').write_text(json.dumps(rows,indent=2)+'\n')
print(len(rows),'mask sites; full-save code, narrowed only by save-ab builder')
