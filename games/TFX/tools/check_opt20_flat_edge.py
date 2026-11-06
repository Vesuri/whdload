import struct,json,sys
from pathlib import Path
p=Path(sys.argv[1]);data=(p/'results.bin').read_bytes()
def check(data):
 assert len(data)==65536*44
 state=0xfedcba98
 for i in range(65536):
  x=data[i*44:i*44+22];y=data[i*44+22:i*44+44];assert x==y
  a,b,c,d,e,ccr=struct.unpack('>5IH',x)
  assert a==((state&0xffff0000)|(65535-i)) and b==((state&65535)<<16)|i
  assert c==a&31 and d==32-(a&31) and e==(b&31)+1 and ccr==0
  state=(((state<<7)|(state>>25))+0x1234567)&0xffffffff
check(data)
for offsets in [[8],[8,30],[20,42],[0,22]]:
 corrupt=bytearray(data)
 for o in offsets:corrupt[o]^=1
 try:check(corrupt)
 except AssertionError:pass
 else:raise AssertionError('Corruption accepted')
report=dict(cases=65536,complete_input_domain=True,registers_and_ccr_equal=True,independent_oracle=True,negative_controls=4)
(p/'oracle.json').write_text(json.dumps(report,indent=2));print(report)
