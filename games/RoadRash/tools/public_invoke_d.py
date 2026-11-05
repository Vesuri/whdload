"""Virtual original-address view for existing read-only probes of relocated game RAM.
Only typed pointers used by the harness are normalized; positions and arbitrary
longwords are not guessed to be pointers. The actual memory is never changed.
"""
import runpy,sys,struct,re
import harness_a as h
import drive
orig_rd=drive.rd;orig_read=h.read_bytes;orig_cmd=drive.Session.cmd
LO=0x80000;SIZE=0x3c3ec

def base(s):
 if not hasattr(s,'public_main_base'):
  if orig_rd(s,LO,2)==0x4ef9:
   b=orig_rd(s,LO+2)
   if 0x200000<=b<0xa00000 or b>=0x1000000:
    try:valid=orig_rd(s,b)==0x21c80422
    except (ValueError,IndexError,RuntimeError):valid=False
    if valid:s.public_main_base=b
 return getattr(s,'public_main_base',None)
def address(s,a):
 b=base(s)
 return b+a-LO if b and LO<=a<LO+SIZE else a

def pointer(s,v):
 b=base(s)
 return v-b+LO if b and b<=v<b+SIZE else v

def rd(s,a,size=4):
 v=orig_rd(s,address(s,a),size)
 if size==4 and a in (0xa5916,0xa726e,0xa7266,0xa726a):v=pointer(s,v)
 return v

def read(s,a,n):
 b=bytearray(orig_read(s,address(s,a),n))
 start=None
 if a==0x909cc:start=0
 elif a in (0x90946,0x90988):start=2
 if start is not None:
  for i in range(start,n-3,4):struct.pack_into('>I',b,i,pointer(s,struct.unpack_from('>I',b,i)[0]))
 return bytes(b)

def cmd(s,text,timeout=600):
 if text.startswith(('break *','tbreak *')):
  text=re.sub(r'0x([0-9a-fA-F]+)',lambda m:hex(address(s,int(m[1],16))),text)
 return orig_cmd(s,text,timeout=timeout)
orig_provenance=h.provenance
def provenance(slave,s=None):
 r=orig_provenance(slave,s)
 if s:r['public_main_base']=hex(base(s)) if base(s) else None
 return r
drive.rd=h.rd=rd;h.read_bytes=read;drive.Session.cmd=cmd;h.provenance=provenance
script=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(script,run_name='__main__')
