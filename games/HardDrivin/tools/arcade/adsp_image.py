"""Extract the ADSP-2100 program the 68010 uploads (FUN_17516 format):
records of 0, addr16, count16, then count 24-bit words; a nonzero lead byte ends.
Writes 24-bit big-endian words padded to 32 bits per instruction.
Usage: adsp_image.py MAINCPU.BIN OUT.BIN"""
import struct,sys
d=open(sys.argv[1],'rb').read();p=struct.unpack_from('>I',d,0xcb300)[0];mem={}
while d[p]==0:
 addr=d[p+1]<<8|d[p+2];n=d[p+3]<<8|d[p+4];p+=5
 print('ADSP pgm %04x count %5d rom %06x'%(addr,n,p))
 for i in range(n):mem[addr+i]=d[p]<<16|d[p+1]<<8|d[p+2];p+=3
print('end %06x, %d words, top %04x'%(p,len(mem),max(mem)))
open(sys.argv[2],'wb').write(b''.join(struct.pack('>I',mem.get(i,0)) for i in range(max(mem)+1)))
