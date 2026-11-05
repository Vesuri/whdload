from pathlib import Path
import random,json,re,hashlib,struct,sys
r=Path(__file__).resolve().parents[1];rng=random.Random(481);s=b'hit a key to end demo';src=Path('Games/FerrariFormulaOne/RenderText.s').read_text();cols=[int(v) for v in re.search(r'FF1RenderDemoColumns:\n dc.b (.*)',src)[1].split(',')];assert len(cols)==len(s)==21
cases=0
for stride in [26,28,32,64]:
 for iteration in range(100):
  font=rng.randbytes(stride*8)
  packed=bytearray()
  for row in range(8):
   packed.extend(0 if col<0 else font[row*stride+col] for col in cols);packed.extend(b'\0'*3)
  assert len(packed)==192
  for fg,bg in [(0,1)]:
   native=[bytearray(rng.randbytes(48*40)) for _ in range(3)];batched=[bytearray(x) for x in native]
   for j,ch in enumerate(s):
    for row in range(8):
     for bit in range(8):
      on=0 if ch==32 else (font[row*stride+(ch-97)]>>(7-bit))&1
      color=bg if ch==32 or not on else fg
      x=38+8*j+bit;y=20+row
      for p in range(3):
       mask=128>>(x&7);off=y*48+x//8
       native[p][off]=(native[p][off]&~mask)|(mask if color>>p&1 else 0)
   for row in range(8):
    for xoff in range(168):
     on=packed[row*24+xoff//8]>>(7-xoff%8)&1;color=fg if on else bg;x=38+xoff;y=20+row
     for p in range(3):
      mask=128>>(x&7);off=y*48+x//8
      batched[p][off]=(batched[p][off]&~mask)|(mask if color>>p&1 else 0)
   assert native==batched
   cases+=1
# Native scratch allocation in its original overlay is passed h5+$5eba.
# Its live canonical value is 1020 bytes; the scratch-reader audit was redone for H2.
m=(r/'tmp/step5/c4-q03-render-profile-a1200-fast-h3-candidate/canonical.bin').read_bytes()
size=struct.unpack_from('>I',m,0x22352)[0];assert size==1020 and size>=192
out=dict(status='passed',random_live_font_cases=cases,source_strides_bytes=[26,28,32,64],whole_destinations_exact=True,source_refresh='Every draw, so changed font bytes/pointer and race lifetime cannot leave a stale cached glyph.',scratch_allocation=size,borrowed_bytes=192,prior_reader_audit='manifest/render-h2-scratch.json',native_fallback='Non-driving view, changed label/position/style/font dimensions or absent scratch',scope='Independent pixel model; native blitter shift/mask correctness also requires full emulator RGB and DMA comparisons.')
(r/'manifest/render-h5-text-model.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
