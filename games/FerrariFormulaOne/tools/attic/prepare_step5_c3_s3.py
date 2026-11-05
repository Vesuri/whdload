from pathlib import Path
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
p=repo/'Games/FerrariFormulaOne_Native000.s';s=p.read_text()
check=""" IFGT FF1_NATIVE_000_STAGE-2
 move.w C3Enabled(pc),d0
 cmpi.w #3,d0
 blo.b .trig_checked
 lea FF1Trig000Signature(pc),a0
 lea $24fe0,a1
 moveq #31,d1
.trig_check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.w .bad
 dbra d1,.trig_check
.trig_checked:
 ENDC
"""
s=s.replace(' lea FF1Divide000(pc),a0',check+' lea FF1Divide000(pc),a0',1)
patch=""" IFGT FF1_NATIVE_000_STAGE-2
 move.w C3Enabled(pc),d0
 cmpi.w #3,d0
 blo.b .done
 lea FF1Sine000(pc),a0
 lea $24fe0,a1
 moveq #15,d1
.trig_copy:
 move.l (a0)+,(a1)+
 dbra d1,.trig_copy
 ENDC
"""
s=s.replace(' bra.b .done',patch+' bra.b .done',1)
trig=(r/'tmp/build/step5-c3-trig-test/trig.s').read_text().split('FF1NativeSine:')[1].split('installed: dc.l')[0]
trig=('FF1Sine000:'+trig).replace('FF1NativeSine','FF1Sine000').replace('FF1NativeCosine','FF1Cosine000')
s+='\n IFGT FF1_NATIVE_000_STAGE-2\n; D0, A0 and all CCR bits equal native. Keep both final logical shifts.\n'+trig
sig=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()[0x24fe0:0x25020]
s+='FF1Trig000Signature:\n dc.b '+','.join('$%02x'%v for v in sig)+'\n ENDC\n';p.write_text(s)
b=(r/'tools/build_step5_c3_s2.py').read_text().replace('step5-c3-s2','step5-c3-s3').replace('-DFF1_NATIVE_000_STAGE=2','-DFF1_NATIVE_000_STAGE=3').replace("1 if variant.startswith('baseline') else 2","2 if variant.startswith('baseline') else 3")
b='\n'.join(line for line in b.splitlines() if not line.startswith('s=s.replace(repr('))+'\n'
extra="data_candidates=[]\nfragment(symbols['FF1Track000Signature'],0x6977a,0x112,'lookahead signature')\nfragment(symbols['FF1Track000Signature']+0x112,0x67514,0x16,'lookahead caller signature')\nfragment(symbols['FF1Trig000Signature'],0x24fe0,64,'trig signature')\n"
inject="extra="+repr(extra)+"\ns=s.replace(repr('data_candidates=[]\\n').replace(\"'\", '\"'),repr(extra))\n"
b=b.replace('exec(compile(s,',inject+'exec(compile(s,',1)
(r/'tools/build_step5_c3_s3.py').write_text(b)
for kind in ('profile','states','elapsed'):
 (r/f'tools/capture_step5_c3_s3_{kind}.py').write_text((r/f'tools/capture_step5_c3_s2_{kind}.py').read_text().replace('c3-s2','c3-s3'))
for kind in ('states','clocks'):
 (r/f'tools/analyze_step5_c3_s3_{kind}.py').write_text((r/f'tools/analyze_step5_c3_s2_{kind}.py').read_text().replace('c3-s2','c3-s3').replace('n==100','n==600'))
