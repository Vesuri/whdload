from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_step5_c4_q02_writers.py').read_text().replace("kind=sys.argv[1] if len(sys.argv)>1 else 'position'","kind='velocity'")
s=s.replace("ns={};snippet=", "old=old.replace(\"('zero_both',0x6e95e,0x6f13c)]\",\"('zero_both',0x6e95e,0x6f13c),('speed_zero_a',0x6897e,0x2275a),('speed_zero_b',0x68b84,0x2275a)]\")\nold=old.replace('(0x68996,0x689a6,0x68b9e,0x68bb2,0x6e96e)', '(0x68996,0x689a6,0x68b9e,0x68bb2,0x6e96e,0x68984,0x68b8a)')\nns={};snippet=")
s=s.replace("endpoints=[0x68996,0x689a6,0x68b9e,0x68bb2,0x6e96e]", "endpoints=[0x68996,0x689a6,0x68b9e,0x68bb2,0x6e96e,0x68984,0x68b8a]")
s=s.replace("blocks=[('$6f13c',32),('velocity_shadow',96)]", "blocks=[('$6f13c',32),('velocity_shadow',96),('$2275a',16),('speed_shadow',48)]")
s=s.replace("'set_z200','zero_both')];record=132", "'set_z200','zero_both','speed_zero_a','speed_zero_b')];record=196")
pos=s.index("blocks=[(f'${p:x}'")
s=s[:pos]+'''a=a.replace('writer_seed:\\n','writer_seed:\\n lea speed_shadow(pc),a0\\n lea $2275a,a1\\n moveq #7,d0\\n.speedseed:\\n move.l #$00641234,(a0)+\\n move.w #2,(a0)+\\n move.w #100,(a1)+\\n dbra d0,.speedseed\\n')
a=a.replace(' move.l velocity_cold_writes(pc),(a4)+',' move.l velocity_cold_writes(pc),(a4)+\\n lea speed_shadow(pc),a0\\n moveq #11,d6\\n.speedshadow:\\n move.l (a0)+,(a4)+\\n dbra d6,.speedshadow\\n lea $2275a,a0\\n moveq #3,d6\\n.speednative:\\n move.l (a0)+,(a4)+\\n dbra d6,.speednative')
a=a.replace('writer_results: ds.b 5280','writer_results: ds.b 10976')
'''+s[pos:]
s=s.replace('q02-{kind}', 'q02-{kind}-v2').replace('q02_'+"{kind}", 'q02_'+"{kind}_v2")
# String-built include source needs the same versioned file name.
s=s.replace('"+kind+".s', '"+kind+"_v2.s')
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
