from pathlib import Path
p=Path(__file__).with_name('capture_hi25_profile.py');s=p.read_text();at=s.index(" mode=os.environ.get('RENDER_CAPTURE'")
s=s[:at]+'''
 hooks={}
 for site in (0x6bd66,0x6bdb6):
  actual=addresses.map(site)
  expected=b'\\x4e\\xb9'+struct.pack('>I',probe+sy['H13Gauge'] if 'candidate' in variant else addresses.map(0x24ae0))
  assert memory[actual:actual+6]==expected,(hex(site),memory[actual:actual+6].hex(),expected.hex())
  hooks[hex(site)]=expected.hex()
 report['verified_hooks']=hooks
'''+s[at:];exec(compile(s,str(p),'exec'))
