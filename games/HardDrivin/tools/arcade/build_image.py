"""Interleave the Hard Drivin' rev 7 68010 program ROMs into a flat 1 MB image.
Usage: build_image.py ROMDIR OUT"""
import sys
from pathlib import Path
roms=Path(sys.argv[1])
pairs=[(0x000000,'136052-7105.200r','136052-7113.210r'),(0x020000,'136052-2106.200s','136052-2114.210s'),
 (0x0a0000,'136052-1110.200w','136052-1118.210w'),(0x0c0000,'136052-1111.200x','136052-1119.210x')]
img=bytearray(b'\xff'*0x100000)
for base,even,odd in pairs:
 e=(roms/even).read_bytes();o=(roms/odd).read_bytes()
 for i in range(len(e)):img[base+2*i]=e[i];img[base+2*i+1]=o[i]
Path(sys.argv[2]).write_bytes(img)
