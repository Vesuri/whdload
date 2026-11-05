from pathlib import Path
import re,struct,subprocess,hashlib
r=Path(__file__).resolve().parents[1];games=r.parents[1]/'Games';o=r/'tmp/build/step5-b3-native-control-lean-v4';o.mkdir(parents=True,exist_ok=True)
s=(r/'tmp/build/step5-b3-v4/lean/fine.s').read_text();hooks=(games/'FerrariFormulaOne_UpdateHooks.s').read_text();op=(games/'FerrariFormulaOne_Opponents.s').read_text()
addresses=[int(m[2],16) for m in re.finditer(r'^(\w+)_([0-9a-f]{5}):\n IFD FF1_PLAN_B\n',hooks,re.M)]+[0x67a04,0x67a36,0x68292]
assert len(addresses)==93
# Runtime copies preserve native-equivalent math patches installed before the
# conversion hooks. Sixteen-byte windows may overlap; both snapshots are taken
# globally before/after installation, so restoration order cannot mix variants.
s=s.replace(' bsr.w install_velocity',' bsr.w B3SaveNative\n bsr.w install_velocity',1).replace(' bsr.w FF1InstallOpponents',' bsr.w FF1InstallOpponents\n bsr.w B3SavePatched',1)
op=op.replace('.native:\n jmp $671bc','.native:\n bsr.w B3NativeLoop\n jmp $671bc',1)
hooks=hooks.replace(' include "FerrariFormulaOne_Opponents.s"',op)
s=s.replace(' include "FerrariFormulaOne_UpdateHooks.s"',hooks)
extra='''
B3SaveNative:
 movem.l d0-d7/a0-a6,-(sp)
 lea B3NativeWords(pc),a1
 bra.b B3SaveWords
B3SavePatched:
 movem.l d0-d7/a0-a6,-(sp)
 lea B3PatchedWords(pc),a1
B3SaveWords:
 lea B3Addresses(pc),a0
 move.w #92,d7
.next:
 move.l (a0)+,a2
 move.l (a2)+,(a1)+
 move.l (a2)+,(a1)+
 move.l (a2)+,(a1)+
 move.l (a2)+,(a1)+
 dbra d7,.next
 movem.l (sp)+,d0-d7/a0-a6
 rts
B3NativeLoop:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 tst.w d0
 beq.b .player
 cmpi.w #7,d0
 bne.b .done
 lea B3NativeWords(pc),a1
 bra.b .restore
.player:
 lea B3PatchedWords(pc),a1
.restore:
 lea B3Addresses(pc),a0
 move.w #92,d7
.next:
 move.l (a0)+,a2
 move.l (a1)+,(a2)+
 move.l (a1)+,(a2)+
 move.l (a1)+,(a2)+
 move.l (a1)+,(a2)+
 dbra d7,.next
 move.l cache_api(pc),a2
 jsr $20(a2)
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts
B3Addresses:
'''+''.join(f' dc.l ${a:x}\n' for a in addresses)+f'B3NativeWords: ds.b {16*93}\nB3PatchedWords: ds.b {16*93}\n'
s=s.replace('\n FF1UpdateWorkspace',extra+'\n FF1UpdateWorkspace')
(o/'fine.s').write_text(s);(o/'original_div.bin').write_bytes((r/'tmp/build/step5-b3-v4/lean/original_div.bin').read_bytes())
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-I'+str(games),'-DFF1_PLAN_B=1','-DFF1_PRESENTATION_SPLIT=1','-DFF1_PRESENTATION_CALLBACK=1','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();code=bytearray(base[32:-4]);size=len(code);entry=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',(o/'fine.list').read_text(),re.M)[1],16);assert size+entry<32768
struct.pack_into('>H',code,24,size+entry);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4);h=bytearray(base[:32]);struct.pack_into('>I',h,20,len(code)//4);h[28:32]=h[20:24];(o/'fine.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
print(hashlib.sha256((o/'fine.slave').read_bytes()).hexdigest())
