from pathlib import Path
import struct,subprocess,hashlib,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-position-fine';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
asm=(r/'tmp/build/step5-math-v6/logic.s').read_text().replace('modeval: dc.w 6','modeval: dc.w MODE').replace(' cmpi.w #6,d0\n bne.b keep_gauges',' cmpi.w #6,d0\n blo.b keep_gauges')
asm=asm.replace('keep_gauges:\n','keep_gauges:\n bsr.w install_position_bridge\n bsr.w install_fine_position\n')
hooks=[(0x6720e,6,'load'),(0x68546,6,'store'),(0x67b52,6,'rotate'),(0x67a12,6,'sync_x'),(0x67a26,6,'sync_z'),(0x67a30,6,'reset_z'),(0x68306,6,'reset_x'),(0x68352,6,'reset_x'),(0x68376,8,'reset_x'),(0x683b8,6,'reset_z'),(0x694c8,6,'reset_z'),(0x6956a,6,'reset_x'),(0x691c4,6,'contact_first'),(0x692ae,6,'contact_second'),(0x6886e,6,'array_x'),(0x688e2,6,'array_z'),(0x68918,8,'array_x'),(0x68ab8,8,'array_x'),(0x68b26,6,'array_z'),(0x663f4,6,'snapshot'),(0x68c12,6,'restore')]
extra='''install_position_bridge:
 movem.l d0-d2/a0-a1,-(sp)
 cmpi.w #7,d0
 blo.w bridge_install_done
'''
for addr,size,action in hooks:
 for i in range(0,size,2):extra+=f' cmpi.w #${m[addr+i:addr+i+2].hex()},${addr+i:x}\n bne.w bridge_install_bad\n'
for addr,size,action in hooks:
 extra+=f' lea bridge_{addr:x}(pc),a1\n move.w #$4ef9,${addr:x}\n move.l a1,${addr+2:x}\n'
 if size==8:extra+=f' move.w #$4e71,${addr+6:x}\n'
extra+=''' lea bridge_installed(pc),a0
 move.l #1,(a0)
 bra.b bridge_install_done
bridge_install_bad:
 lea error(pc),a0
 move.l #6,(a0)
bridge_install_done:
 movem.l (sp)+,d0-d2/a0-a1
 rts
'''
for addr,size,action in hooks:
 # Original instruction executes first; callback preserves its exact CCR/registers.
 extra+=f'bridge_{addr:x}:\n dc.w '+','.join('$'+m[addr+i:addr+i+2].hex() for i in range(0,2 if addr==0x6886e else size,2))+'\n'
 extra+=' movem.l d0-d7/a0-a6,-(sp)\n move.w sr,-(sp)\n'
 if not action.startswith(('contact_','array_')) and action not in ('snapshot','restore'):
  extra+=' bsr.w bridge_context\n tst.l d0\n bmi.b .done\n'
 extra+=f' bsr.w bridge_{action}\n.done:\n move.w (sp)+,ccr\n movem.l (sp)+,d0-d7/a0-a6\n jmp ${0x6895e if addr==0x6886e else addr+size:x}\n'
extra+='''bridge_context:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.l #7,d0
 bhi.b .bad
 mulu.w #12,d0
 lea position_shadow(pc),a0
 adda.l d0,a0
 moveq #0,d0
 rts
.bad:
 lea error(pc),a0
 move.l #7,(a0)
 moveq #-1,d0
 rts
bridge_load:
 lea fine_cross_pending(pc),a1
 clr.w (a1)
 lea fine_car_crosses(pc),a1
 clr.w (a1)
 lea bridge_loads(pc),a1
 addq.l #1,(a1)
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 rts
bridge_store:
 lea bridge_stores(pc),a1
 addq.l #1,(a1)
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 rts
bridge_sync_x:
 move.w $32fc2,(a0)
 rts
bridge_sync_z:
 move.w $32fc4,6(a0)
 rts
bridge_reset_x:
 lea bridge_resets(pc),a1
 addq.l #1,(a1)
 move.w $32fc2,d0
 bra.w FF1PositionReset
bridge_reset_z:
 lea bridge_resets(pc),a1
 addq.l #1,(a1)
 move.w $32fc4,d0
 addq.l #6,a0
 bra.w FF1PositionReset
bridge_rotate:
 lea bridge_rotations(pc),a1
 addq.l #1,(a1)
 move.w -16(a6),d4
 andi.l #1023,d4
 add.l d4,d4
 lea $2180c,a1
 move.w (a1,d4.l),d1
 lea $21a0c,a1
 move.w (a1,d4.l),d0
 move.w $32fc2,d2
 move.w $32fc4,d3
 bsr.w FF1PositionRotate20
 tst.l d1
 bne.b .bad
 move.w (a0),$32fc2
 move.w 6(a0),$32fc4
 rts
.bad:
 lea error(pc),a1
 move.l #8,(a1)
 rts
bridge_contact_first:
 move.w -8(a6),d2
 bra.b bridge_contact
bridge_contact_second:
 move.w -6(a6),d2
bridge_contact:
 move.w (a0),d4
 move.l a0,d1
 subi.l #$6a62a,d1
 cmpi.l #14,d1
 bhi.b .bad
 btst #0,d1
 bne.b .bad
 andi.l #$ffff,d2
 cmpi.l #7,d2
 bhi.b .bad
 mulu.w #6,d1
 mulu.w #12,d2
 lea position_shadow+6(pc),a0
 lea position_shadow+6(pc),a1
 adda.l d1,a0
 adda.l d2,a1
 move.w d4,d0
 bsr.w FF1PositionAssign
 lea bridge_contacts(pc),a1
 addq.l #1,(a1)
 rts
.bad:
 lea error(pc),a1
 move.l #9,(a1)
 rts
; Pointer-based cold writers do not depend on main-loop car index.
bridge_array_x:
 moveq #0,d2
 move.l #$6a61a,d1
 bra.b bridge_array_reset
bridge_array_z:
 moveq #6,d2
 move.l #$6a62a,d1
bridge_array_reset:
 move.w (a0),d0
 move.l a0,d3
 sub.l d1,d3
 cmpi.l #14,d3
 bhi.w bridge_pointer_bad
 btst #0,d3
 bne.w bridge_pointer_bad
 mulu.w #6,d3
 lea position_shadow(pc),a0
 adda.l d3,a0
 adda.l d2,a0
 bsr.w FF1PositionReset
 lea bridge_array_resets(pc),a1
 addq.l #1,(a1)
 rts
bridge_snapshot:
 move.w (a0),d0
 move.l a0,d3
 subi.l #$227ca,d3
 cmpi.l #14,d3
 bhi.w bridge_pointer_bad
 btst #0,d3
 bne.w bridge_pointer_bad
 move.l d3,d2
 mulu.w #3,d3
 mulu.w #6,d2
 lea saved_position(pc),a0
 adda.l d3,a0
 lea position_shadow+6(pc),a1
 adda.l d2,a1
 bsr.w FF1PositionAssign
 lea bridge_snapshots(pc),a1
 addq.l #1,(a1)
 rts
bridge_restore:
 move.w (a0),d0
 move.l a0,d3
 subi.l #$6a62a,d3
 cmpi.l #14,d3
 bhi.w bridge_pointer_bad
 btst #0,d3
 bne.w bridge_pointer_bad
 move.l d3,d2
 mulu.w #6,d3
 mulu.w #3,d2
 lea position_shadow+6(pc),a0
 adda.l d3,a0
 lea saved_position(pc),a1
 adda.l d2,a1
 bsr.w FF1PositionAssign
 lea bridge_restores(pc),a1
 addq.l #1,(a1)
 rts
bridge_pointer_bad:
 lea error(pc),a1
 move.l #10,(a1)
 rts
bridge_array_resets: dc.l 0
bridge_snapshots: dc.l 0
bridge_restores: dc.l 0
saved_position: ds.b 48
bridge_contacts: dc.l 0
bridge_installed: dc.l 0
bridge_loads: dc.l 0
bridge_stores: dc.l 0
bridge_rotations: dc.l 0
bridge_resets: dc.l 0
position_shadow: ds.b 96
'''
for module in ('Step','Position'):extra+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+module+'.s'))+'"\n'
asm+=extra+(r/'tools/step5_fine_position.s').read_text()
(o/'original_div.bin').write_bytes((r/'tmp/build/step5-math-v6/original_div.bin').read_bytes())
(o/'hooks.json').write_text(json.dumps(hooks,indent=2)+'\n')
for mode,name in ((6,'control'),(7,'bridge'),(8,'fine')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
a=(o/'control.slave').read_bytes();b=(o/'bridge.slave').read_bytes();assert len(a)==len(b) and sum(x!=y for x,y in zip(a,b))==1
print('Built native-step per-car bridge with',len(hooks),'qualified sites')
