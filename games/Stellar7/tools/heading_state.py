#!/usr/bin/env python3
"""Read the isolated all-register native heading comparison fixture."""
import argparse
import json
import re
import struct
from pathlib import Path
from sim60_state import decode_version


def read(folder):
    folder=Path(folder)
    meta={k:int(v,0) for k,v in re.findall(r'^(code|base)=(\S+)',(folder/'anchor.txt').read_text(),re.M)}
    memory=(folder/'code.bin').read_bytes()
    code=meta['code']-meta['base']
    assert memory[code+0x2af6:code+0x2af8]==bytes.fromhex('4ef9')
    entry=struct.unpack_from('>I',memory,code+0x2af8)[0]-meta['base']
    assert memory[entry+4:entry+8]==b'S760'
    assert decode_version(struct.unpack_from('>H', memory, entry+50)[0])[0]>=26
    offset=struct.unpack_from('>H',memory,entry+126)[0]
    assert offset,'HEADING_TEST absent'
    at=entry+offset
    signature=memory[at:at+4].decode('ascii')
    expected={'H760':121,'H761':4217}[signature]
    cases,errors=struct.unpack_from('>HH',memory,at+4)
    return dict(signature=signature,expected=expected,cases=cases,errors=errors)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures',nargs='+')
    args=p.parse_args()
    ok=True
    for folder in args.captures:
        result=read(folder)
        print(folder,json.dumps(result,sort_keys=True))
        ok &= result['cases']==result['expected'] and result['errors']==0
    raise SystemExit(0 if ok else 1)
