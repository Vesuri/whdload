"""Independent colour minterm and masked boundary-word equivalence model."""
from pathlib import Path
import json, random
r=Path(__file__).resolve().parents[1]
def bit(mt,a,b,c):return (mt>>((a<<2)|(b<<1)|c))&1
truth=0
for a in range(2):
 for p in range(2):
  for q in range(2):
   for c in range(2):
    assert bit(0xca,a,0,c)==bit(0x0a,a,q,c)
    assert bit(0xca,a,bit(0xf0,q,p,0),c)==bit(0xca,a,q,c)
    truth+=2
rng=random.Random(0xC402)
# The cookie-cut reads an extra source word at an unclipped right edge.
# Colour-copy and direct-Q have identical interior words. Their final guard
# word may differ: A's zero last-word mask makes those B bits unobservable,
# including shifter carry into the next row. Model both guards independently.
cases=0
for width in range(1,9):
 for height in (1,2,7):
  for left in range(width):
   for right in range(width-left):
    for shift in range(16):
     mask=[rng.getrandbits(16) for _ in range(width*height)]+[rng.getrandbits(16)]
     q=[rng.getrandbits(16) for _ in range(width*height)]
     old=q+[rng.getrandbits(16)];new=q+[rng.getrandbits(16)]
     prev_a=prev_old=prev_new=0
     count=width+1-left-right
     for row in range(height):
      for col in range(count):
       at=row*width+left+col
       aw=mask[at]
       if col==0 and left:aw=0
       if col==count-1:aw=0
       aa=((prev_a<<16)|aw)>>shift & 0xffff
       bo=((prev_old<<16)|old[at])>>shift & 0xffff
       bn=((prev_new<<16)|new[at])>>shift & 0xffff
       c=rng.getrandbits(16)
       assert ((aa&bo)|((~aa)&c))==((aa&bn)|((~aa)&c))
       prev_a,prev_old,prev_new=aw,old[at],new[at]
     cases+=1
out=dict(status='passed',boolean_cases=truth,shift_clip_row_cases=cases,scope='Independent Boolean and masked guard-word proof. Guest frame/state/DMA checks remain required; this does not replace hardware validation.')
(r/'manifest/step5-c4-colour-r2-model.json').write_text(json.dumps(out,indent=2)+'\n')
print(out)
