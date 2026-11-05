from pathlib import Path
import re,struct,subprocess,hashlib,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-fastcode-v2';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
regions=[(0x67120,10892,0x20),(0x6cd00,8732,0x2b00)];lines=(r/'tmp/step4/active.dis').read_text().splitlines();entries=set()
for line in lines:
 m=re.match(r'([0-9a-f]{6}):\s+[0-9a-f]+\s+(\S+)\s+(.*?) ;',line)
 if not m:continue
 pc=int(m[1],16);op=m[2];args=m[3];q=re.search(r'\$([0-9a-f]+)(?:\.l)?$',args)
 if any(a<=pc<a+z for a,z,_ in regions):assert 'pc)' not in args,line
 if not q:continue
 t=int(q[1],16)
 if op.startswith(('jsr','bsr')) and any(a<=t<a+z for a,z,_ in regions):entries.add(t)
 if op.startswith('b'):
  assert not any(a<=pc<a+z and not a<=t<a+z for a,z,_ in regions),line
memory=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
asm=(r/'tmp/build/step5-math-v6/logic.s').read_text().replace('modeval: dc.w 6','modeval: dc.w MODE').replace(' cmpi.w #6,d0\n bne.b keep_gauges',' cmpi.w #6,d0\n blo.b keep_gauges').replace('keep_gauges:\n','keep_gauges:\n bsr.w place_fast_code\n')
extra='''place_fast_code:
 movem.l d0-d7/a0-a6,-(sp)
 lea start(pc),a2
 suba.l #5440,a2
 move.l $20(a2),d0
 addi.l #$40000,d0
 lea fast_allocation(pc),a0
 move.l d0,(a0)
 cmpi.l #$200000,d0
 blo.w fast_bad
 cmpi.l #$5fb000,d0
 bhi.w fast_bad
 lea fast_range_checked(pc),a0
 move.l #1,(a0)
 addi.l #255,d0
 andi.l #$ffffff00,d0
 move.l d0,a4
'''
for a,z,offset in regions:
 extra+=f''' lea ${a:x},a0
 lea ${offset:x}(a4),a1
 move.w #{z//4-1},d2
copy_{a:x}:
 move.l (a0)+,(a1)+
 dbra d2,copy_{a:x}
'''
extra+=''' move.w modeval(pc),d0
 cmpi.w #7,d0
 bne.w fast_done
'''
for t in sorted(entries):
 signature=memory[t:t+6];extra+=f' cmpi.l #${signature[:4].hex()},${t:x}\n bne.w fast_bad\n cmpi.w #${signature[4:].hex()},${t+4:x}\n bne.w fast_bad\n'
for t in sorted(entries):
 a,z,offset=next(x for x in regions if x[0]<=t<x[0]+x[1]);extra+=f' lea ${offset+t-a:x}(a4),a0\n move.w #$4ef9,${t:x}\n move.l a0,${t+2:x}\n'
extra+=''' lea fast_installed(pc),a0
 move.l #1,(a0)
 bra.b fast_done
fast_bad:
 lea error(pc),a0
 move.l #4,(a0)
fast_done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
fast_allocation: dc.l 0
fast_range_checked: dc.l 0
fast_installed: dc.l 0
'''
asm+=extra;(o/'original_div.bin').write_bytes((r/'tmp/build/step5-math-v6/original_div.bin').read_bytes())
(o/'map.json').write_text(json.dumps({'regions':regions,'entries':[hex(t) for t in sorted(entries)],'scope':'SPS fixed-layout diagnostic only; code copy, data remains at original addresses; slave-owned expansion memory; extra ws_ExpMem request; fixed 4 MiB Fast profile address guard; production memory-profile gating unvalidated'},indent=2)+'\n')
for mode,name in ((6,'control'),(7,'fast')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 normal=bytearray(base[32:-4]);assert normal[0x20:0x24]==bytes.fromhex('00040000');normal[0x20:0x24]=struct.pack('>I',0x45000);size=len(normal);pos=normal.find(bytes.fromhex('d0ab001c2240'));pos=normal.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=(o/(name+'.bin')).read_bytes();normal+=b'\0'*((-len(normal))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(normal)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+normal+bytes.fromhex('000003f2'))
a=(o/'control.slave').read_bytes();b=(o/'fast.slave').read_bytes();assert len(a)==len(b) and sum(x!=y for x,y in zip(a,b))==1
print('Built equal-layout Fast code placement diagnostics;',len(entries),'entries')
