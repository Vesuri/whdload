from pathlib import Path
import os
r=Path(__file__).resolve().parents[1]
os.environ['C1_ARCH']='020'
s=(r/'tools/build_step5_c1.py').read_text().replace('step5-c1','step5-c2')
s=s.replace("'-m68'+arch,", "'-m68'+arch,'-DFF1_COARSE_NATIVE_EXACT=1','-DFF1_NATIVE_EXACT=1',")
# Explicit binding of the audited native signature/site table.
extra="""data_candidates=[]
p=symbols['FF1NativeSites']
while True:
 start=struct.unpack_from('>I',code,p)[0]
 if not start:break
 size,kind=struct.unpack_from('>HH',code,p+4)
 addlong(p,start,'native site address');fragment(p+8,start,size,'native site signature');p+=8+size
"""
s=s.replace(repr('data_candidates=[]\n').replace("'", '"'),repr(extra))
s=s.replace("('native',2,1)]", "('native',2,1),('baseline',0,0),('baseline-render',0,1)]")
s=s.replace("(o/(variant+'.slave')).write_bytes", "struct.pack_into('>H',b,size+symbols['C2Enabled'],int(not variant.startswith('baseline')))\n (o/(variant+'.slave')).write_bytes")
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
