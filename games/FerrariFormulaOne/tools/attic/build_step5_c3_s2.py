from pathlib import Path
import os
r=Path(__file__).resolve().parents[1]
os.environ['C1_ARCH']='000'
s=(r/'tools/build_step5_c1.py').read_text().replace('step5-c1','step5-c3-s2')
s=s.replace("'-m68'+arch,", "'-m68'+arch,'-DFF1_COARSE_NATIVE_000=1','-DFF1_NATIVE_000_STAGE=2',")
# Explicit binding of the audited native signature/site table.
s=s.replace("('native',2,1)]", "('native',2,1),('baseline',0,0),('baseline-render',0,1)]")
s=s.replace("(o/(variant+'.slave')).write_bytes", "struct.pack_into('>H',b,size+symbols['C3Enabled'],1 if variant.startswith('baseline') else 2)\n (o/(variant+'.slave')).write_bytes")
s=s.replace(repr('data_candidates=[]\n').replace("'", '"'),'"data_candidates=[]\\nfragment(symbols[\'FF1Track000Signature\'],0x6977a,0x112,\'lookahead signature\')\\nfragment(symbols[\'FF1Track000Signature\']+0x112,0x67514,0x16,\'lookahead caller signature\')\\n"')
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
