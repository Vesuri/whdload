#!/usr/bin/env python3
"""OCS control-flow closure and explicit indirect-transfer ownership."""
import argparse, json, capstone
from ocs_reconstruct import ROOT, new_output, require, sha
from cd32_static import HunkReader
from variants import ocs
from timing_inventory import inventory

BASES=(0x100000,0x140000,0x150000,0x160000)
PROFILE=dict(base=0,sizes=tuple(x[2] for x in ocs.HUNKS),prefix='O',data_prefix='OD',
    action=0x13ad6,action_data=0x38c,byte_switch=0x30664,
    extra_tables={0x2bae6:(0x2baf0,0x2baf0,14)},
    helpers={0x26830:(0x268ce,0x26974),0x311c2:(0x33b76,0x33b60),0x312ea:(0x33b76,0x33b60),0x31e20:(0x33b76,0x33b60),
        **dict.fromkeys((0x30866,0x3088c,0x30896,0x308a0,0x308aa,0x308bc,0x308c6,0x308d0,0x308da),(0x30a76,)),
        **dict.fromkeys((0x30972,0x3097c,0x309a4,0x309ae),(0x30aba,))},
    boundaries={**dict.fromkeys((0x27ab0,0x27ac0),'resource byte-copy run length'),
        **dict.fromkeys((0x2e60e,0x2e61c,0x2ef86,0x2f6b4,0x2f6c2,0x2f7a2,0x2f7ac,0x2bf8e,0x2fc72,0x2fc80,0x2fc92,0x2fcaa,0x2fcb2,0x2fd56,0x2fd72,0x2fd7c,0x2fd8e,0x2fd9e,0x2fe50,0x2fe56,0x2fe5c,0x2ff16,0x2ff20,0x2ff26,0x30b18,0x30b64,0x315d6,0x31f68,0x31f86,0x32328,0x323a6),'image copy/fill kernel'),
        **dict.fromkeys((0x34ce2,0x2c9d8,0x2ca0e,0x2cb54,0x2cbea),'formatted text callback'),
        **dict.fromkeys((0x34930,0x34a96,0x357ca,0x357e0),'C runtime callback')})

def load():
    path=ROOT/ocs.GAME
    require(sha(path.read_bytes())==ocs.GAME_SHA,'unsupported OCS executable')
    r=HunkReader();require(r.read_file(str(path))==0,r.error_string)
    memory=bytearray(0x200000);index=-1
    for rec in r.hunks:
        if rec['type_name'] in ('HUNK_CODE','HUNK_DATA','HUNK_BSS'):
            index+=1
            if 'data' in rec:memory[BASES[index]:BASES[index]+len(rec['data'])]=rec['data']
        for target,offsets in rec.get('reloc',{}).items():
            for offset in offsets:
                at=BASES[index]+offset
                memory[at:at+4]=((int.from_bytes(memory[at:at+4],'big')+BASES[target])&0xffffffff).to_bytes(4,'big')
    return memory,dict(hunks=BASES,slave=0x180000)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    out=new_output(a.output);out.mkdir(parents=True)
    memory,layout=load();report,seen=inventory(memory,layout,[0x2be,0x512,0x18d14,0x640,0x1eeb2],PROFILE)
    report['game_sha256']=ocs.GAME_SHA
    report['decoder_version']=capstone.__version__
    (out/'inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'reachable.dis').write_text('\n'.join(f'{at-BASES[0]:05x} {i.mnemonic} {i.op_str}' for at,i in sorted(seen.items()))+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('edges','tables','boundaries')},indent=2))
    print('tables',len(report['tables']),'entries',sum(len(t['entries']) for t in report['tables']))
    require(not report['unresolved'],'unclassified indirect transfers')
    require(not report['external'],'unclassified external transfers')

if __name__=='__main__':main()
