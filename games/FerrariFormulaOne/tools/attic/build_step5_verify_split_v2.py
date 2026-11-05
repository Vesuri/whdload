from pathlib import Path
import re,struct,subprocess,hashlib,json
r=Path(__file__).resolve().parents[1];root=r/'tmp/build/step5-verify-split-v2';root.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();source=(r/'tmp/build/step5-selection-elapsed/fine.s').read_text();changes=[]
def alternate(name,lean):
 global source
 pattern=r'(?m)^'+name+r':\n(.*?)(?=^[A-Za-z_][A-Za-z_0-9]*:)'
 m=re.search(pattern,source,re.S|re.M);assert m,name
 original=m[1]
 source=source[:m.start()]+name+':\n IFD VERIFY\n'+original+' ELSE\n'+lean+' ENDC\n'+source[m.end():]
 changes.append(name)
pulse=''' moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.w events_pulse(pc),d0
.done:
 rts
'''
for prefix in ('events','clocks','counters','boost'):
 alternate(prefix+'_before',pulse)
 alternate(prefix+'_after',' rts\n')
for name in ('events_snapshot','recovery_contact_before','recovery_contact_after','recovery_snapshot'):
 alternate(name,' rts\n')
alternate('recovery_tick',''' cmpi.w #7,modeval(pc)
 blo.b .done
 cmpi.w #8,modeval(pc)
 bne.b .run
 tst.w events_pulse(pc)
 beq.b .done
.run:
 lea $2268e,a0
 moveq #1,d0
 bsr.w FF1AdvanceRecovery
 tst.w $1c21e
 bne.b .done
 lea recovery_simulation(pc),a0
 move.w #1,(a0)
 jsr $6c5c6
 lea recovery_simulation(pc),a0
 clr.w (a0)
.done:
 rts
''')
for kind in ('wear','fuel'):
 alternate(kind+'_sample',f''' cmpi.w #8,modeval(pc)
 bne.b .done
 bsr.w {kind}_context
 move.l d4,d0
 bsr.w FF1Wear20Delta
 tst.l d1
 bne.w velocity_fault
 move.l d0,(sp,d7.l)
.done:
 rts
''')
alternate('velocity_speed_rate',''' lea (speed_work.l,pc),a0
 bsr.w FF1SpeedRate20
 tst.l d1
 bne.w velocity_fault
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 rts
''')
exec((r/'tools/verify_split_remaining.py').read_text())
# This is the first audited S2 slice. Velocity records remain live arithmetic
# workspace; wholesale removal would corrupt the converted physics.
for variant in ('verify','lean'):
 o=root/variant;o.mkdir(parents=True,exist_ok=True);(o/'fine.s').write_text(source);(o/'original_div.bin').write_bytes((r/'tmp/build/step5-selection-elapsed/original_div.bin').read_bytes())
 args=[str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L','fine.list','-o','fine.bin']
 if variant=='verify':args+=['-DVERIFY=1']
 subprocess.run(args+['fine.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);size=len(code);listing=(o/'fine.list').read_text();boot=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',listing,re.M)[1],16);struct.pack_into('>H',code,24,size+boot)
 pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);struct.pack_into('>I',header,20,len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
verify=(root/'verify/fine.slave').read_bytes();assert verify==(r/'tmp/build/step5-selection-elapsed/fine.slave').read_bytes(),'VERIFY changed baseline bytes'
(root/'audit.json').write_text(json.dumps({'scope':'S2 candidate, pending exact-state and cycle gates','verify_byte_identical_to':'step5-selection-elapsed/fine.slave','verify_sha256':hashlib.sha256(verify).hexdigest(),'conditional_functions':changes,'stat_sites':stat_sites,'fault_sites':fault_sites,'remaining':'Velocity arithmetic workspace versus trace split; position/heading/steering records; remaining statistics and guards; lean exact-state and cycle gates'},indent=2)+'\n')
print('Built first VERIFY split; VERIFY binary is byte-identical to accepted S0 elapsed benchmark')
