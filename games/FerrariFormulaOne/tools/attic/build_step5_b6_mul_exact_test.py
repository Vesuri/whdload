from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_step5_div_test.py').read_text().replace('step5-div-test','step5-b6-mul-exact-test').replace('0x293d0:0x29412','0x29500:0x29542').replace('move.w sr','move.w ccr').replace('lea FF1Divide020(pc),a2','lea FF1NativeMultiply(pc),a2')
s=s.replace("for mode in (0,1):", "asm+='\\nFF1NativeMultiply:'+(r.parent.parent/'Games/FerrariFormulaOne_NativeExact.s').read_text().split('FF1NativeMultiply:')[1].split('FF1MultiplySignature:')[0]\nfor mode in (1,):")
(r/'tools/build_step5_b6_mul_exact_generated.py').write_text(s)
s=(r/'tools/test_step5_div.py').read_text().replace('step5-div-test','step5-b6-mul-exact-test').replace("(('a500',0),('a1200',0),('a1200',1))","(('a1200',1),)").replace("'div-oracle-'","'b6-mul-exact-oracle-'")
(r/'tools/test_step5_b6_mul_exact.py').write_text(s)
