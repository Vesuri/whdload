# A stopped DMA field can precede its delayed SOFT handler. Finish exactly the
# missing game tick at its existing post-increment instruction, without writes.
import runpy,sys
import harness_a as h
old=h.advance
def advance(s,target):
 while h.field(s)<target:
  current=h.field(s);gap=target-current
  if gap==1:
   s.cmd('tbreak *0x86fe6');s.cmd('continue',timeout=60)
   assert h.field(s)==target,(current,target,h.field(s))
  else:
   s.cmd(f'monitor fields {min(gap,6000)-1}',timeout=120)
   assert current<h.field(s)<=target,(current,target,h.field(s))
h.advance=advance
script=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(script,run_name='__main__')
