from pathlib import Path
import struct,re
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-c4-source-default-control';o.mkdir(exist_ok=True)
stub=(r/'tmp/build/rng-control/control.bin').read_bytes()
normal=(r/'tmp/build/step5-c4-source-ab/000/candidate.slave').read_bytes();host=(r/'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave').read_bytes();listing=(r/'tmp/build/step5-b7-loader-v3/build.list').read_text(errors='replace')
slot=int(re.search(r'^FF1PublicPoolOpen\s+00:([0-9A-F]+)',listing,re.M)[1],16)
assert slot+len(stub)<len(host)-36
for arm,raw in [('c4-source',normal),('release',(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes())]:
 code=bytearray(raw[32:-4]);site=code.index(bytes.fromhex('e34048c02840'));dest=slot if arm=='c4-source' else len(code)
 assert dest<32768 and abs(dest-site-2)<32768
 for cpu in ('000','020'):
  data=bytearray(code);fixture=bytearray(stub)
  if cpu=='020':
   assert fixture[4:6].hex()=='40e7';fixture[4:6]=bytes.fromhex('42e7')
  if arm=='release':data+=fixture
  else:data[dest:dest+len(fixture)]=fixture
  data[site:site+6]=bytes.fromhex('6100')+struct.pack('>h',dest-site-2)+bytes.fromhex('4e71')
  data+=bytes(len(normal)-36-len(data));hdr=bytearray(normal[:32]);hdr[20:24]=struct.pack('>I',len(data)//4);hdr[28:32]=hdr[20:24]
  data[24:26]=raw[56:58]
  # Expansion reservation is inside the slave header, not the outer hunk header.
  data[32:36]=normal[64:68]
  (o/f'{arm}-{cpu}.slave').write_bytes(hdr+data+bytes.fromhex('000003f2'))
print('Built controlled default-off arms; CUSTOM1=0 required for RNG fixture')
