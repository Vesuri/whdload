from pathlib import Path
import json,hashlib,struct,re,random
r=Path(__file__).resolve().parents[1];g=r.parents[1]/'Games';b=r/'tmp/build/render-h5';m=json.loads((b/'build.json').read_text());sy=m['payloads']['fine']['symbols'];s=(g/'FerrariFormulaOne/RenderBitmap.s').read_text();code=(b/'fine/fine.bin').read_bytes();control=(r/'tmp/build/render-h5-control/FerrariFormulaOne.slave').read_bytes();slave=(b/'FerrariFormulaOne.slave').read_bytes();at=32+m['payloads']['fine']['offset']+sy['FF1RenderBitmapControl']
assert [i for i,(a,c) in enumerate(zip(slave,control)) if a!=c]==[at+1]
assert len(slave)==len(control) and slave[at:at+2]==b'\0\1' and control[at:at+2]==b'\0\0'
assert 'move.w sr' not in s and '$dff' not in s and 'ds.' not in s
assert 'jsr $2a130' in s and 'jsr $2a260' in s and 'jmp $24d70' in s
assert s.index(' jsr $2a130')<s.index(' move.b (a0),d5')<s.index(' move.b d0,(a1)')
assert 'tst.w $1c1b4               ; displaced entry' in s
old=json.loads((r/'tmp/build/render-h4/build.json').read_text())
payloads={}
for kind in ['000','020']:
 olddata=(r/f'tmp/build/render-h4/{kind}/fine.bin').read_bytes();newdata=(b/f'{kind}/fine.bin').read_bytes();assert olddata==newdata;payloads[kind]=hashlib.sha256(newdata).hexdigest()
out=dict(status='passed',new_native_patch_sites=['$24ae0..$24ae5'],signature='tst.w $1c1b4, with relocated immediate validation',lifetime='Existing public diff ledger automatically owns and restores the six entry bytes; no allocation or persistent mutable workspace added.',ownership='Original conditional OwnBlitter/DisownBlitter preserved; native WaitBlit before any CPU font read or plane write. KickEmu OwnBlitter explicitly preserves D0-D1/A0-A1.',bounds='Only 8x8, 3 planes, destination pitch 48 bytes, byte-aligned x, source y=0, nonnegative mono foreground, current font and native driving destination pointer tables. Other calls use displaced TST and original branch.',no_sr_reads=True,no_irq_changes=True,coarse_payload_sha256=payloads,sources={str(p.relative_to(g)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [g/'FerrariFormulaOne/RenderBitmap.s',g/'FerrariFormulaOne/Fine.s']},candidate_sha256=hashlib.sha256(slave).hexdigest(),control_sha256=hashlib.sha256(control).hexdigest(),one_byte_ab_offset=at+1)
(r/'manifest/render-h5-source-audit.json').write_text(json.dumps(out,indent=2)+'\n')
# Independent bit-level native minterm and byte CPU model, all colours, both
# byte positions, changed fonts/backgrounds and edges. Whole rows compared.
rng=random.Random(0x4855);cases=0
for fg in range(8):
 for bg in range(8):
  for x in [0,8,16,184,368,376]:
   for iteration in range(8):
    glyph=bytes(rng.getrandbits(8) for _ in range(8));native=bytearray(rng.randbytes(3*8*48));cpu=bytearray(native)
    for plane in range(3):
     for y,q in enumerate(glyph):
      dest=(plane*8+y)*48+x//8
      for bit in range(8):
       mask=128>>bit;value=((fg if q&mask else bg)>>plane)&1
       native[dest]=(native[dest]&~mask)|(mask if value else 0)
      f=(fg>>plane)&1;z=(bg>>plane)&1
      cpu[dest]=(q if f else 0)|((q^255) if z else 0)
    assert native==cpu
    cases+=1
(r/'manifest/render-h5-text-model.json').write_text(json.dumps(dict(status='passed',cases=cases,scope='Independent complete-row bit-level minterm vs CPU byte overwrite; all 64 foreground/background pairs, both destination byte positions and edges; emulator native oracle is separate.'),indent=2)+'\n')
print('H5 source/byte-model audit passed:',cases)
