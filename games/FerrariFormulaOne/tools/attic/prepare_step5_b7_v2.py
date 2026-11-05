from pathlib import Path
p=Path(__file__).parent
s=(p/'build_step5_b7.py').read_text().replace('step5-b7-v1','step5-b7-v2').replace('step5-b7-loader/','step5-b7-loader-v2/')
injection="host_listing=(r/'tmp/build/step5-b7-loader-v2/build.list').read_text(errors='replace')\nstack_owner=int(re.search(r'^FF1PublicStackOwner\\s+00:([0-9A-F]+)',host_listing,re.M)[1],16)\n"
changes=[
 (' bsr.l public_bind\n',' bsr.l public_bind\n cmpi.l #2,selection_path(pc)\n bne.b public_early_done\n bsr.l public_install_lifetime\n bsr.l public_begin_early\npublic_early_done:\n'),
 ('done:\n move.w (sp)+,ccr','done:\n bsr.l public_seal\n move.w (sp)+,ccr'),
 (' cmpi.l #126,(a0)\n bne.w finish',' cmpi.l #126,(a0)\n bne.w finish\n bsr.l public_begin\n cmpi.l #2,selection_path(pc)\n bne.w finish'),
 ('finish:\n bsr.w schedule_begin',' bsr.l public_seal\nfinish:\n bsr.w schedule_begin')]
for a,b in changes:injection+='s=s.replace('+repr(a)+','+repr(b)+',1)\n'
injection+="s+='\\n'+(r/'tools/step5_b7_lifecycle.s').read_text().replace('HOSTSIZE',str(size))\n"
s=s.replace("s+='''",injection+"s+='''",1)
s=s.replace(' include "FerrariFormulaOne_Bindings.s"',' include "FerrariFormulaOne_Bindings.s"\n include "FerrariFormulaOne_PublicMemory.s"')
old=' ; Qualify every CPU hunk.'
new=' lea start(pc),a0\n suba.l #HOSTSIZE,a0\n move.l STACKOWNER(a0),d2\n move.l STACKOWNER+4(a0),d3\n moveq #1,d0\n moveq #2,d1\n bsr.l FF1SelectProfile\n cmpi.l #2,d0\n bne.w .coarse\n ; Qualify every CPU hunk.'
injection='s=s.replace('+repr(old)+', '+repr(new)+".replace('HOSTSIZE',str(size)).replace('STACKOWNER',str(stack_owner)))\n(o/'reset.bin').write_bytes(struct.pack('>I',0xffffffff))\n"
s=s.replace("(o/'fine.s').write_text(s);",injection+"(o/'fine.s').write_text(s);")
s=s.replace("'-DFF1_PUBLIC_BINDINGS=1'", "'-DFF1_PUBLIC_BINDINGS=1','-DFF1_PUBLIC_PATCHES=1','-DFF1_PUBLIC_MEMORY=1'")
needle="subprocess.run([os.sys.executable,str(r/'tools/build_step5_b7_bindings.py'),str(o)],check=True)"
s=s.replace(needle,needle+"\nsubprocess.run([os.sys.executable,str(r/'tools/build_step5_b7_reset.py'),str(o)],check=True)")
(p/'build_step5_b7_v2.py').write_text(s)
