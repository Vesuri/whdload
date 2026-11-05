import struct,os
from harness_a import read_bytes,rd

def stack_probe(s):
 target=rd(s,0xa876e);data=read_bytes(s,target,1024);off=data.find(b'RRCSTK01');assert off>=0
 size,count,bottom,top=struct.unpack_from('>4I',data,off+8)
 assert count>0 and top-bottom==size and bottom>=0x200000,(size,count,bottom,top)
 pattern=b'\xa5\x5a\xa5\x5a'
 assert read_bytes(s,bottom-16,16)==pattern*4,'low stack guard overwritten'
 assert read_bytes(s,top,16)==pattern*4,'high stack guard overwritten'
 stack=read_bytes(s,bottom,size)
 untouched=0
 while untouched<size and stack[untouched:untouched+4]==pattern:untouched+=4
 if os.environ.get('RR_LUT_TEST'):
  table=struct.unpack('>8193H',read_bytes(s,bottom-16+0x5000,8193*2))
  assert table==tuple([0]+[0x1c00//n for n in range(1,8193)]),'incorrect width quotient table'
  expected=bytes.fromhex('377063b0')+struct.pack('>I',bottom-16+0x5000)+bytes.fromhex('00644e71')
  assert read_bytes(s,0x8984e,12)==expected,'incorrect inline indexed lookup'
 return dict(size=size,initializations=count,bottom=hex(bottom),top=hex(top),high_water_bytes=size-untouched,guards_intact=True)
