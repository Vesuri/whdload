#!/usr/bin/env python3
"""Build equal-size VERIFY-only c2p delay fixtures; never a release slave."""
import argparse, hashlib, json, os, struct, subprocess
from pathlib import Path
from reconstruct import ROOT, SLAVE_SHA


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True)
    p.add_argument('--iterations',type=int,required=True,choices=(0,100000))
    a=p.parse_args(); out=(ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('new output below tmp/ required')
    original=(ROOT/'tmp/originals/cd32/WingCommanderCD32/WingCommanderCD32.Slave').read_bytes()
    if hashlib.sha256(original).hexdigest()!=SLAVE_SHA: raise ValueError('changed original')
    code=original[32:-4]; assert len(code)==0x1e0c and code[0x178e:0x1792]==bytes.fromhex('203a0674')
    out.mkdir(parents=True)
    # Wrapper already saved all registers. D0 is overwritten by the displaced
    # instruction before returning, including its CCR result. Interrupts stay on.
    source=f'''\torg $1e0c
\tmove.l #{a.iterations},d0
\tbeq.s done
loop:
\tsubq.l #1,d0
\tbne.s loop
done:
\tmove.l $1e04(pc),d0
\trts
\tcnop 0,4
'''
    (out/'delay.s').write_text(source)
    subprocess.run([os.environ['VASM'],'-m68020','-spaces','-no-opt','-Fbin','-o',str(out/'delay.bin'),str(out/'delay.s')],check=True)
    tail=(out/'delay.bin').read_bytes(); assert len(tail)==20
    payload=bytearray(code+tail)
    payload[0x178e:0x1792]=struct.pack('>Hh',0x6100,len(code)-0x1790)
    assert payload[:0x178e]==code[:0x178e] and payload[0x1792:len(code)]==code[0x1792:]
    result=struct.pack('>8I',0x3f3,0,1,0,0,len(payload)//4,0x3e9,len(payload)//4)+payload+struct.pack('>I',0x3f2)
    (out/'WingCommanderCD32.Slave').write_bytes(result)
    (out/'build.json').write_text(json.dumps(dict(verify_only=True,iterations=a.iterations,hook=0x178e,tail=0x1e0c,bytes=len(result),sha256=hashlib.sha256(result).hexdigest()),indent=2)+'\n')

if __name__=='__main__': main()
