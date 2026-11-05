#!/usr/bin/env python3
"""Synthetic exact signed-depth fixtures, with overflow fallback cases."""
from pathlib import Path
from geometry_model import s16,s32
rows=['; Synthetic arithmetic cases: n.w, sum.l, translation.w, expected depth.w.','book_depth_cases:']
for n in [1,2,3,4,5,6,7,8,16,127,128,255]:
 for i,total in enumerate([0,-1,2147483647,-2147483648]):
  trans=[-32768,-1,0,32767][i]
  if n in (1,2,4,8):q=total>>{1:0,2:1,4:2,8:3}[n]
  else:
   divisor=n if n<128 else n-256
   q=abs(total)//abs(divisor)
   if (total<0)!=(divisor<0):q=-q
  rows+=[' dc.w '+str(n),' dc.l '+str(total),' dc.w '+str(trans)+','+str(s16(q+trans))]
rows+=['book_depth_cases_end:']
root=Path(__file__).resolve().parents[1]
(root/'src/bookkeeping_cases.i').write_text('\n'.join(rows)+'\n')
