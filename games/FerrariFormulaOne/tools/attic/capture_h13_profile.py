from pathlib import Path
p=Path(__file__).with_name('capture_hi25_profile.py');s=p.read_text();at=s.index(" mode=os.environ.get('RENDER_CAPTURE'")
s=s[:at]+'''
 actual=addresses.map(0x6bbe6)
 expected=b'\\x4e\\xb9'+struct.pack('>I',probe+sy['H13Blit']) if 'candidate' in variant else bytes.fromhex('33c000dff058')
 assert memory[actual:actual+6]==expected,(hex(actual),memory[actual:actual+6].hex(),expected.hex())
 report['verified_hook']=expected.hex()
'''+s[at:];exec(compile(s,str(p),'exec'))
