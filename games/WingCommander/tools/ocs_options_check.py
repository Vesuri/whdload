#!/usr/bin/env python3
"""Execute public OCS startup: option/hardware gates, hooks, ABI and icon checks.
Exec memory headers are fixtures; WHDLoad Control/PatchSeg/FlushCache are stubs.
This proves startup selection, not hardware speed or full gameplay.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
from ocs_display_check import Native, CODE, STARTUP, STOP, ck, u, word, long
from ocs_reconstruct import ROOT, new_output, require
from ocs_icon import enhanced_icon, tooltypes


def check(build, mutation=None):
    meta=json.loads((build/'build.json').read_text());sy=meta['symbols']
    blob=(build/'WingCommander.Slave').read_bytes();payload=blob[32:-4]
    require(meta.get('public_option'), 'public build required')
    original=(ROOT/'tmp/originals/ocs/WingCommander/WingCommander.Slave').read_bytes()[32:-4]
    require(payload[0x20:0x24] == long(0x100000), 'missing expansion headroom')
    require(payload[0x1fc:0x202] == bytes.fromhex('d9fc000c0000'),
            'expansion reservation/pool mismatch')
    for i,(old,new) in enumerate(zip(original,payload)):
        require(old==new or 0x20<=i<0x24 or 0x1fe<=i<0x202 or
                0x32<=i<0x34 or 0x11c6<=i<0x11ce,
                'unexpected change to original slave, including cache/wait paths')
    require(hashlib.sha256(blob).hexdigest()==meta['sha256'],'stale build metadata')
    config=int.from_bytes(payload[0x32:0x34],'big')
    require(payload[config:].split(b'\0',1)[0].endswith(b'C5:B:Enhanced framerate (68020+Fast RAM);'),'public config missing')
    if mutation:
        start,end=sy['ocs_option_gate'],sy['ocs_option_tags']
        segment=payload[start:end]
        old,new={'option':(bytes.fromhex('0c9000000001'),bytes.fromhex('0c9000000000')),
                 'cpu':(bytes.fromhex('0240008e'),bytes.fromhex('0240008f')),
                 'slow':(bytes.fromhex('0c8100a00000'),bytes.fromhex('0c8100e00000'))}[mutation]
        require(segment.count(old)==1,'mutation site missing')
        payload=payload[:start]+segment.replace(old,new)+payload[end:]
    results=[]
    banks=((0x500000,4,'z2-fast'),(0x1000000,4,'high-fast'),
           (0xc00000,4,'slow-labelled-fast'),(0x80000,2,'chip'),
           (0x500000,0,'unmapped'),(0x500000,6,'chip-and-fast'),
           (0x500000,1,'public-only'),(0x80000,4,'chip-slave-fast'),
           (0x500000,4,'empty'),(0x500000,4,'invalid-bounds'))
    for slave,kind,bank in banks:
        for flags in (0,1,2,3,4,8,128):
            for option in (0,1,2,0xffffffff):
                for revision in (0x1302,0x12bc,0x1348):
                    enabled=option==1 and bool(flags&0x8e) and bank in ('z2-fast','high-fast','chip-slave-fast') and revision==0x1302
                    # A damaged English enhancement site must only be examined
                    # when enabled: original mode must not acquire new guards.
                    for corrupt in (False,True):
                        c=Native(ROOT/'tmp/originals/ocs/WingCommander/data/Wing.english')
                        events=[]
                        try:
                            if slave>=0x1000000:ck(u.uc_mem_map(c.h,slave,0x100000,7))
                            c.write(slave,payload);c.write(4,long(0x8000));c.write(0x8000+296,word(flags))
                            c.write(slave+0xf24,long(0x190000))
                            # Traverse a Chip header before the candidate Fast bank.
                            c.write(0x8000+322,long(0x81c0 if bank!='empty' else 0x8000+326))
                            c.write(0x81c0,long(0x8200));c.write(0x81c0+14,word(2))
                            c.write(0x8200,long(0x8000+326));c.write(0x8000+326,long(0))
                            c.write(0x8200+14,word(kind));c.write(0x8200+20,long(0x500000 if bank=='chip-slave-fast' else slave));c.write(0x8200+24,long(0x600000 if bank=='chip-slave-fast' else slave if bank=='invalid-bounds' else slave+len(payload)))
                            def control():
                                a=c.reg(1)
                                require(c.get(a,4)==0x8800000b and c.get(a+8,4)==0,'incorrect CUSTOM5 tag')
                                c.write(a+4,long(option));events.append('control');c.return_call()
                            def patch():events.append('patch');c.return_call()
                            def flush():events.append('flush');c.return_call()
                            def abort():
                                events.append('abort');c.reg(18,STOP);ck(u.uc_emu_stop(c.h))
                            c.intercept(0x190034,control)
                            c.intercept(0x190074,patch);c.intercept(0x190020,flush);c.intercept(0x190000,abort)
                            off=meta['hooks'][0][0]
                            if corrupt:c.write(CODE+off,bytes([c.get(CODE+off,1)^1]))
                            before=c.read(CODE,0x358c8)
                            opening_before=c.read(STARTUP,0x1d94)
                            regs={r:0x12340000+r for r in list(range(1,8))+list(range(9,17))}
                            regs.update({3:0x190000,4:slave+revision,16:(CODE-4)//4})
                            c.run(slave-CODE+sy['install'],registers=regs)
                            require(events[0]=='patch','original PatchSeg omitted')
                            if enabled and corrupt:
                                require(events[-1]=='abort' and 'flush' not in events,'damaged enhanced site accepted')
                                require(c.read(CODE,0x358c8)==before,'partial installation before rejection')
                            elif enabled:
                                require(events[-1]=='flush','missing enhancement flush')
                                for at,label,opcode in meta['hooks']:
                                    require(c.get(CODE+at,2)==opcode and c.get(CODE+at+2,4)==slave+sy[label],'missing enhanced hook')
                            else:
                                require(c.read(CODE,0x358c8)==before and c.read(STARTUP,0x1d94)==opening_before,'original mode modified game')
                                require('flush' not in events and 'abort' not in events,'original mode enhanced')
                                for pos in meta['fixups']:
                                    require(c.read(slave+pos,4)==payload[pos:pos+4],'original mode relocated payload')
                            if not (enabled and corrupt):
                                expected=dict(regs);expected.update({1:regs[4],2:regs[16]})
                                require(all(c.reg(r)==v for r,v in expected.items()),'startup register ABI changed')
                            results.append(dict(bank=bank,flags=flags,option=option,revision=revision,corrupt=corrupt,enhanced=enabled,events=events))
                        finally:c.close()
    original=(ROOT/'tmp/originals/ocs/WingCommander/WingCommander.info').read_bytes()
    icon=(build/'WingCommander.info').read_bytes()
    require(icon==enhanced_icon(original),'generated icon mismatch')
    require(tooltypes(icon)[2][:2]==[b'CUSTOM5=1\0',b'DCACHE\0'],'icon defaults disabled')
    rejected=0
    for bad in (icon,b'bad icon',original[:80]):
        try:enhanced_icon(bad)
        except (ValueError,IndexError):rejected+=1
    require(rejected==3,'unsafe icon accepted')
    return dict(passed=True,sha256=meta['sha256'],cases=results,icon_rejections=rejected)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build');p.add_argument('--output',required=True)
    a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    r=check(Path(a.build))
    rejected=[]
    for mutation in ('option','cpu','slow'):
        try:check(Path(a.build),mutation)
        except ValueError as error:
            require(str(error) in ('original mode modified game','original mode enhanced','missing enhancement flush'),'unexpected mutation failure: '+str(error))
            rejected.append(mutation)
        else:raise ValueError('undetected gate mutation: '+mutation)
    r['negative_controls']=rejected
    (out/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(len(r['cases']),'public option/hardware cases passed; icon checks passed')

if __name__=='__main__':main()
