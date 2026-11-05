#!/usr/bin/env python3
"""Check public original-mode captures against relocated original hook bytes.
The bit-exact E1 sites must instead hold their always-on hooks."""
import argparse
import json
from pathlib import Path
from cd32_static import HunkReader
from ocs_reconstruct import ROOT, require, guard_game
from ocs_clock_source import NOPS, MODALS
from ocs_prediction_source import NOPS as PREDICTION_NOPS
from ocs_memory_build import ALWAYS


def check(build, run, corrupt=False):
    b=json.loads((build/'build.json').read_text())
    r=json.loads((run/'result.json').read_text())
    require(b.get('public_option') and b['sha256']==r['slave_sha256'],'wrong public build')
    require(r['whd_args']=='CUSTOM5=0' or (r['whd_args']=='CUSTOM5=1' and r['machine'].startswith('68000-')),'not an original-mode run')
    reader=HunkReader();game=ROOT/'tmp/game/WingCommander/data/Wing.english'
    guard_game(game.read_bytes())
    require(reader.read_file(str(game))==0,'cannot read original hunks')
    expected=None
    for record in reader.hunks:
        if record['type_name'] in ('HUNK_CODE','HUNK_DATA','HUNK_BSS'):
            if expected is not None:break
            expected=bytearray(record['data'])
        if 'reloc' in record and expected is not None:
            for target, offsets in record['reloc'].items():
                for offset in offsets:
                    value=int.from_bytes(expected[offset:offset+4],'big')+r['hunks'][target]
                    expected[offset:offset+4]=(value & 0xffffffff).to_bytes(4,'big')
    # E1 shortcuts and the waypoint marker order are installed in every mode;
    # all else stays original.
    exact={off:(op,label) for off,label,op in b['hooks'] if label in ALWAYS}
    require(len(exact)==len(ALWAYS),'always-on hooks missing from build')
    for off,(op,label) in exact.items():
        expected[off:off+6]=op.to_bytes(2,'big')+(r['slave']+b['symbols'][label]).to_bytes(4,'big')
    windows=[(off,6) for off,_,_ in b['hooks']]
    windows += [(off,2) for off in (*NOPS,*PREDICTION_NOPS)]
    windows += [(off,width) for off,width,_,_ in MODALS]
    checks=0
    for label in ('origin','title','credits','menu'):
        code=bytearray((run/(label+'-h0.bin')).read_bytes())
        if corrupt and label=='origin':code[windows[0][0]] ^= 1
        for off,size in windows:
            require(code[off:off+size]==expected[off:off+size],f'enhancement changed O:{off:x} at {label}')
            checks+=1
        memory=(run/(label+'-fast.bin')).read_bytes()
        start=r['slave']-0x200000
        for name in ('game_base','ocs_requested_backend','ocs_clock_completed'):
            off=start+b['symbols'][name]
            require(memory[off:off+4]==bytes(4),'enhancement state active: '+name)
    return dict(passed=True,checks=checks,slave_sha256=b['sha256'],machine=r['machine'],whd_args=r['whd_args'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build');p.add_argument('run');p.add_argument('--output',required=True)
    a=p.parse_args();out=(ROOT/a.output).resolve()
    require((ROOT/'tmp').resolve() in out.parents and not out.exists(),'choose new output below tmp')
    result=check(ROOT/a.build,ROOT/a.run)
    try:check(ROOT/a.build,ROOT/a.run,corrupt=True)
    except ValueError as error:
        require(str(error).startswith('enhancement changed'),'unexpected negative-control failure')
    else:raise ValueError('hook-byte corruption undetected')
    result['negative_controls']=['changed original hook']
    out.write_text(json.dumps(result,indent=2)+'\n');print(result)

if __name__=='__main__':main()
