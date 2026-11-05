from pathlib import Path
import struct,subprocess,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b7-bindings-test';o.mkdir(parents=True,exist_ok=True);base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0]
cases=[]
for bp in (0x4000,0x17ffff,0x400000,0x3ffffffe):
 for add in (0,2,0x1000):
  value=bp*4+4+add;ok=value<=0xffffffff
  cases.append(dict(name=f'address-{bp:x}-{add:x}',bp=bp,add=add,slot=4,shift=0,offset=2,expected_word=0x2222,expect=[value>>16&65535,value&65535,0] if ok else [0x1111,0x2222,0xffffffff]))
for name,change in [('zero',{'bp':0}),('bptr-overflow',{'bp':0x40000000}),('header-overflow',{'bp':0x3fffffff}),('add-overflow',{'bp':0x3ffffffe,'add':8}),('slot-alignment',{'slot':5}),('slot-bound',{'slot':836}),('shift',{'shift':15}),('odd-write',{'offset':1}),('negative-write',{'offset':0x80000000}),('changed-word',{'expected_word':0x3333})]:
 c=dict(name=name,bp=0x50000,add=0,slot=4,shift=0,offset=2,expected_word=0x2222,expect=[0x1111,0x2222,0xffffffff]);c.update(change);cases.append(c)
s=prefix+' lea results(pc),a6\n'
for c in cases:
 s+=''' lea destination(pc),a0
 move.l #$11112222,(a0)
 lea records(pc),a1
 lea table(pc),a2
'''
 s+=f" move.l #${c['bp']:x},(a2)\n move.l #${c['bp']:x},4(a2)\n move.l #0,(a1)\n move.w #0,4(a1)\n move.w #16,6(a1)\n move.l #${c['add']:x},8(a1)\n move.w #$1111,12(a1)\n move.l #${c['offset']:x},16(a1)\n move.w #{c['slot']},20(a1)\n move.w #{c['shift']},22(a1)\n move.l #${c['add']:x},24(a1)\n move.w #${c['expected_word']:x},28(a1)\n bsr.w FF1ApplyBindings\n move.w (a0),(a6)+\n move.w 2(a0),(a6)+\n move.l d0,(a6)+\n"
 # Successful repeat must also pass after changing the live hunk base.
 if c['expect'][2]==0:
  s+=' bsr.w FF1ApplyBindings\n tst.l d0\n beq.b .repeat_'+str(cases.index(c))+'\n move.l #$deadbeef,-4(a6)\n.repeat_'+str(cases.index(c))+':\n'
s+=' rts\ninstalled: dc.l 0\ndestination: dc.l 0\nrecords: ds.b 32\n dc.l -1\ntable: ds.l 209\nresults: ds.b '+str(len(cases)*8)+'\n include "FerrariFormulaOne_Bindings.s"\n'
(o/'binding.s').write_text(s);(o/'expected.json').write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-DFF1_PUBLIC_BINDINGS=1','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-L','binding.list','-o','binding.bin','binding.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);size=len(code);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'binding.bin').read_bytes();code+=b'\0'*((-len(code))%4);h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'binding.slave').write_bytes(h+code+bytes.fromhex('000003f2'));print(len(cases),'transactional binding cases')
