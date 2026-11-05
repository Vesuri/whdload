from pathlib import Path
p=Path(__file__).with_name('capture_hi25_profile.py');s=p.read_text();old=" mode=os.environ.get('RENDER_CAPTURE'"
at=s.index(old)
s=s[:at]+'''
 hooks={}
 for native,label in [(0x6b0e4,'H10BenchBottom'),(0x6b138,'H10BenchTop')]:
  actual=addresses.map(native);raw=memory[actual:actual+6]
  expected=(b'\\x4e\\xb9'+struct.pack('>I',probe+sy[label])) if 'candidate' in variant else (bytes.fromhex('33c000dff058') if native==0x6b0e4 else bytes.fromhex('33fc045800df'))
  assert raw==expected,(hex(native),raw.hex(),expected.hex())
  hooks[hex(native)]=raw.hex()
 report['verified_hooks']=hooks
''' +s[at:];exec(compile(s,str(p),'exec'))
