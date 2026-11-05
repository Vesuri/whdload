"""List and extract the TMS34010 sections the 68010 uploads through a host port.
Each image is a section count followed by (bit address, bit length, 32-bit
words) records; FUN_1c0ea writes each word low half first.
Usage: msp_sections.py MAINCPU.BIN POINTER_ADDR OUTDIR"""
import struct,sys
from pathlib import Path
d=open(sys.argv[1],'rb').read();ptr=int(sys.argv[2],16);out=Path(sys.argv[3]);out.mkdir(exist_ok=True)
p=struct.unpack_from('>I',d,ptr)[0];n=struct.unpack_from('>I',d,p)[0];q=p+4
print('image at %06x, %d sections'%(p,n))
for i in range(n):
 addr,bits=struct.unpack_from('>II',d,q);q+=8;words=(bits+31)//32
 raw=d[q:q+4*words];q+=4*words
 # TMS34010 memory is little-endian 16-bit words; the 68010 long holds hi:lo,
 # and the low half goes to the lower address.
 le=b''.join(raw[j+2:j+4][::-1]+raw[j:j+2][::-1] for j in range(0,len(raw),4))
 (out/('sec%02d_%08x.bin'%(i,addr))).write_bytes(le)
 print('  %2d bitaddr %08x (byte %07x) bits %7d bytes %6d  rom %06x-%06x'%(i,addr,addr>>3,bits,bits//8,q-4*words,q))
print('end %06x'%q)
