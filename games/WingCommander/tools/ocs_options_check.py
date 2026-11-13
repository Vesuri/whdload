#!/usr/bin/env python3
"""Execute public OCS startup: option/hardware gates, hooks, ABI and icon checks.
Exec memory headers are fixtures; WHDLoad Control/PatchSeg/FlushCache are stubs.
This proves startup selection, not hardware speed or full gameplay.
"""
from runtime_buffers import load as load_slave
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
from ocs_display_check import Native, CODE, DATA, STARTUP, STACK, STOP, ck, u, word, long
from ocs_reconstruct import ROOT, new_output, require
from ocs_icon import enhanced_icon, tooltypes
from mouse_model import APERTURE, KEY, Pointer, cockpit


GFX,RECT,IMAGE,EVENT,CHIP,ANY,SURFACE=0x1a0000,0x1a1000,0x1a1100,0x1a2000,0x1a3000,0x1a4000,0x1b0000


def mouse_scenario(c,slave,sy):
    """The installed mouse hooks on the native room routine, its exit, the
    RAWMOUSE callback and the VBL fire sample (68000)."""
    a4=DATA+0x7ffe;moves=[];saved={r:c.reg(r) for r in range(1,19)}
    var=lambda name:struct.unpack('>h',c.read(slave+sy[name],2))[0]
    require(c.get(slave+sy['mouse_params'],4)==slave+sy['ocs_mouse_params'] and
            c.get(slave+sy['mouse_move'],4)==CODE+0x31d22,'mouse not initialised')
    c.write(CODE+0x33518,long(GFX));c.write(GFX-426,word(0x4e75))
    def move():
        moves.append((struct.unpack('>h',word(c.reg(9)))[0],struct.unpack('>h',word(c.reg(10)))[0]))
        if c.get(c.reg(2),4)==CHIP:c.write(CHIP,long(0x6a7e7101))    # control words, as MoveSprite
    c.intercept(GFX-426,move)
    c.write(RECT+24,struct.pack('>4h',40,30,280,180));c.write(IMAGE+4,struct.pack('>hh',-3,-2))
    c.write(a4+444,long(RECT));c.write(a4-2158,long(IMAGE));c.write(a4-2154,word(0))
    c.write(a4+412,struct.pack('>hh',160,100));c.write(a4-13522,long(0))
    def segment(start,stop,sp=STACK):
        c.reg(17,0x2700);c.reg(5,a4);c.reg(8,sp)
        ck(u.uc_emu_start(c.h,CODE+start,CODE+stop,0,100000))
        if c.error:raise c.error
        require(c.reg(18)==CODE+stop,f'mouse segment stopped at O:{c.reg(18)-CODE:x}')
    def room(stick=(0,0,0,0)):
        c.write(a4+16084,bytes(stick));segment(0x2649a,0x26536)
        return struct.unpack('>hh',c.read(a4+412,4))
    def event(dx,dy,qualifier=0x8000):
        c.write(EVENT,struct.pack('>IBBHHhh',0,2,0,0xff,qualifier,dx,dy));n=len(moves)
        c.run(slave-CODE+sy['mouse_event'],registers={4:EVENT})
        return moves[n:]
    require(event(8,8)==[],'mouse callback active before the room routine')
    require(room()==(160,100) and var('mouse_active')==1 and c.get(a4-2028,4)==slave+sy['mouse_event'],'mouse room entry')
    require(event(10,-6)==[(162,95)] and event(1,1)==[(162,95)] and event(1,1)==[(163,96)],'mouse motion')
    require(room()==(166,98) and room((1,0,0,0))==(161,98),'room routine mouse/stick position')
    for _ in range(4):last=event(127,127)
    require(last==[(277,178)] and room()==(280,180),'mouse rectangle clamp')
    require(event(5,5,0)==[] and event(0,0)==[],'mouse non-relative event accepted')
    c.write(a4-2154,word(0x4000));require(event(-9,-9)==[],'hidden pointer moved');c.write(a4-2154,word(0))
    c.write(STACK-8,long(STOP));segment(0x26478,0x26486,STACK-8)
    require(moves[-1]==(997,998) and var('mouse_active')==0 and event(-9,-9)==[],'mouse room exit')
    fire={}
    for pra in (0xff,0xbf,0x7f,0x3f):
        c.write(0xbfe001,bytes([pra]));segment(0x33f88,0x33f94);fire[pra]=c.reg(9)&255
    require(fire=={0xff:0,0xbf:1,0x7f:1,0x3f:1},'left button is not port-1 fire')
    guard={}
    for pra in (0xff,0xbf,0x7f):
        c.write(0xbfe001,bytes([pra]));c.write(a4-2114,b'\x5a'*24)
        c.run(0x33f02);guard[pra]=c.read(a4-2114,24)
    require(all(g[:10]==bytes(10) and g[10:12]==word(-1) and g[12:22]==bytes(10) for g in guard.values()),'record reset')
    require([g[22:] for g in guard.values()]==[word(0),word(-1),word(-1)],'click release guard')
    steer_scenario(c,slave,sy,moves)
    for r,v in saved.items():c.reg(r,v)


def steer_scenario(c,slave,sy,moves):
    """Mouse flight: the native flight controller O:183e4 with the slave's ramp
    store hook; mouse_init's allocations; the aperture scan hook's mask; the
    pointer on sprite 7 (no colour bank on OCS); the VBL field count and hide."""
    a4=DATA+0x7ffe;changes=[];sprites=[]
    for site in (0x16ffc,0x1aff8):
        require(c.read(CODE+site,6)==bytes.fromhex('4eb9')+long(slave+sy['mouse_scan']),f'scan call O:{site:x} not hooked')
    require(c.get(slave+sy['stick_image'],4)==CHIP and c.get(slave+sy['stick_ss'],4)==ANY and c.get(slave+sy['stick_gfx'],4)==GFX,'pointer not allocated')
    require(c.get(slave+sy['mouse_scan_native'],4)==CODE+0x2bc9a,'native aperture scan')
    require(c.read(CHIP,44)==bytes(44),'pointer image not blank')
    for off in (-408,-420):c.write(GFX+off,word(0x4e75))
    def change():changes.append((c.reg(2),c.reg(3)));c.write(c.reg(2),long(c.reg(3)))
    def sprite():sprites.append((c.reg(1),c.reg(9)&0xffff));c.write(c.reg(1)+10,word(c.reg(9)&0xffff))
    c.intercept(GFX-420,change);c.intercept(GFX-408,sprite)
    # The native scan sets the aperture block; here it returns at once.
    c.write(CODE+0x2bc9a,word(0x4e75));c.write(a4-4188,struct.pack('>6h',*APERTURE))
    c.write(SURFACE,long(SURFACE+0x100));c.write(SURFACE+24,struct.pack('>4h',0,0,319,199))
    for y in range(200):
        c.write(SURFACE+0x100+4*y,long(SURFACE+0x1000+320*y));c.write(SURFACE+0x1000+320*y,bytes(cockpit(x,y) for x in range(320)))
    c.run(slave-CODE+sy['mouse_scan'],struct.pack('>IIBB',SURFACE,SURFACE+0x800,KEY,0))
    require((c.get(slave+sy['mask_top'],2),c.get(slave+sy['mask_rows'],2))==(10,105),'mask rows')
    def tick(n=1):
        for _ in range(n):c.run(slave-CODE+sy['mouse_vbl'])
    def event(dx,dy):
        c.write(EVENT,struct.pack('>IBBHHhh',0,2,0,0xff,0x8000,dx,dy))
        c.run(slave-CODE+sy['mouse_event'],registers={4:EVENT})
    def steer(ramps=None,flags=(0,0,0,0,0),view=0):
        if ramps is not None:c.write(a4+3720,struct.pack('>hh',*ramps))
        c.write(a4+16084,bytes(flags));c.write(a4-18318,word(view));n=len(moves)
        c.run(0x183e4)
        return struct.unpack('>hh',c.read(a4+3720,4)),moves[n:]
    ptr=Pointer()
    def ev(dx,dy):event(dx,dy);ptr.move(dx,dy)
    want=lambda:(ptr.ramps(),[ptr.sprite()])
    img=lambda:[(x,x) for x in ptr.lines()]
    image=lambda:[struct.unpack('>HH',c.read(CHIP+4+4*r,4)) for r in range(9)]
    shown=lambda:c.read(CHIP,4)!=bytes(4)
    tick(100)
    require(steer((5,-3))==((3,-1),[]),'native ramp decay')
    ev(160,0);tick();require(steer((0,0))==want()==((0,5),[(234,58)]),'mouse right: yaw right')
    require(sprites==[(ANY,7)] and changes==[(ANY,CHIP)] and c.get(ANY+4,2)==9,'pointer sprite not bound')
    require(image()==img(),'pointer image')
    ev(0,52);tick();require(ptr.at()==(239,88) and steer()==want() and want()[0]==(-2,5),'mouse down: pitch up')
    tick();require(steer()==(want()[0],[]),'held pointer position')
    ev(-150,-44);tick();require(ptr.at()==(164,66) and steer()==want() and want()[0]==(0,0),'PC dead zone')
    ev(1000,1000);tick();require(steer()==want()==((-9,9),[(319-5,199-4)]) and image()==[(0,0)]*9,'full deflection, hidden')
    ev(-2000,-2000);tick();require(steer()==want()==((9,-9),[(0-5,0-4)]) and image()==[(0,0)]*9,'full deflection up left')
    ev(0,28);tick();require(ptr.at()==(0,14) and steer()==want() and image()==img()!=[(0,0)]*9,'aperture edge: full, shown')
    ev(10,2);tick();require(steer()==want() and want()[0]==(5,-5),'off the edge: PC steps')
    ev(308,94);tick();require(steer()[1]==[ptr.sprite()] and ptr.at()==(159,62) and image()==img(),'pointer behind the cockpit')
    tick();require(steer((0,-9),(0,1,0,0,0))==((0,1),[]) and not shown(),'stick steering re-centres');ptr.centre()
    tick();require(steer((0,0))==((0,0),[]),'not re-centred')
    ev(80,80);tick();require(steer(flags=(1,0,0,0,1))==want() and want()[0]==(-5,2),'modifier: the mouse steers')
    tick();require(steer((3,3),view=8)==((1,1),[]),'external view');ptr.centre()
    ev(160,0);tick();steer()
    for _ in range(500):tick();require(steer()==((0,5),[]),'idle steering')
    require(shown(),'idle pointer hidden early');tick();require(not shown(),'idle pointer not hidden')
    tick();require(steer()==((0,5),[]) and not shown(),'idle pointer shown again')
    ev(1,0);tick();require(steer()==want(),'pointer not shown on motion')
    ev(16,0);tick();steer()
    tick(25);require(shown(),'hidden early');tick();require(not shown(),'pointer not hidden')
    tick(30);event(16,0);tick();require(steer((0,0))[0]==(0,0),'new flight not re-centred')
    require(len(sprites)==1 and len(changes)==1,'sprite taken or bound again')


def check(build, mutation=None):
    meta=json.loads((build/'build.json').read_text());sy=meta['symbols']
    blob=(build/'WingCommander.Slave').read_bytes();payload=load_slave(blob)
    require(meta.get('public_option'), 'public build required')
    original=(ROOT/'tmp/game/WingCommander/WingCommander.Slave').read_bytes()[32:-4]
    require(payload[0x20:0x24] == long(0x100000), 'missing expansion headroom')
    require(payload[0x1fc:0x202] == bytes.fromhex('d9fc000c0000'),
            'expansion reservation/pool mismatch')
    for i,(old,new) in enumerate(zip(original,payload)):
        require(old==new or 0x20<=i<0x24 or 0x1fe<=i<0x202 or
                0x18<=i<0x1a or 0x28<=i<0x2a or 0x32<=i<0x34 or 0x11c6<=i<0x11ce,
                'unexpected change to original slave, including cache/wait paths')
    require(hashlib.sha256(blob).hexdigest()==meta['sha256'],'stale build metadata')
    info=int.from_bytes(payload[0x28:0x2a],'big')
    require(payload[info:].startswith(b'2.0b (13.11.2026)\n'), 'public release information missing')
    require(b'$VER: WingCommander 2.0b (13.11.2026)\0' in payload, 'public version missing')
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
    from ocs_memory_build import ALWAYS
    exact=[h for h in meta['hooks'] if h[1] in ALWAYS]
    require(len(exact)==len(ALWAYS),'always-on hooks missing from build')
    from ocs_memory_build import WORDS
    words=[(at,guard,value) for at,guard,value in meta['word_fixes']]
    require(words==[list(w) for w in WORDS] or words==[tuple(w) for w in WORDS],'word fixes missing from build')
    game=(ROOT/'tmp/game/WingCommander/data/Wing.english').read_bytes()
    for at,guard,value in words:require(game[44+at:50+at]==bytes.fromhex(guard),'word fix guard does not match the pinned game')
    banks=((0x500000,4,'z2-fast'),(0x1000000,4,'high-fast'),
           (0xc00000,4,'slow-labelled-fast'),(0x80000,2,'chip'),
           (0x500000,0,'unmapped'),(0x500000,6,'chip-and-fast'),
           (0x500000,1,'public-only'),(0x80000,4,'chip-slave-fast'),
           (0x500000,4,'empty'),(0x500000,4,'invalid-bounds'))
    mouse_runs=set()
    for slave,kind,bank in banks:
        for flags in (0,1,2,3,4,8,128):
            for option in (0,1,2,0xffffffff):
                for revision in (0x1302,0x12bc,0x1348):
                    enabled=option==1 and bool(flags&0x8e) and bank in ('z2-fast','high-fast','chip-slave-fast') and revision==0x1302
                    # A damaged enhancement-only site must only be examined
                    # when enabled. A damaged exact site makes original mode
                    # fall back to the untouched game instead of aborting.
                    # A damaged word-fix site skips only that fix.
                    for corrupt in (False,'enhanced','exact','word'):
                        c=Native(ROOT/'tmp/game/WingCommander/data/Wing.english')
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
                            c.intercept(0x8000-552,lambda:c.return_call(GFX))      # OpenLibrary
                            c.intercept(0x8000-198,lambda:c.return_call(CHIP if c.reg(10)&2 else ANY))     # AllocMem
                            c.intercept(0x190034,control)
                            c.intercept(0x190074,patch);c.intercept(0x190020,flush);c.intercept(0x190000,abort)
                            off={'exact':exact[0][0],'word':words[0][0]+2}.get(corrupt,meta['hooks'][0][0])
                            if corrupt:c.write(CODE+off,bytes([c.get(CODE+off,1)^1]))
                            fatal=corrupt in ('enhanced','exact')
                            before=c.read(CODE,0x358c8)
                            opening_before=c.read(STARTUP,0x1d94)
                            regs={r:0x12340000+r for r in list(range(1,8))+list(range(9,17))}
                            regs.update({3:0x190000,4:slave+revision,16:(CODE-4)//4})
                            c.run(slave-CODE+sy['install'],registers=regs)
                            require(events[0]=='patch','original PatchSeg omitted')
                            if enabled and fatal:
                                require(events[-1]=='abort' and 'flush' not in events,'damaged enhanced site accepted')
                                require(c.read(CODE,0x358c8)==before,'partial installation before rejection')
                            elif enabled:
                                require(events[-1]=='flush','missing enhancement flush')
                                for at,label,opcode in meta['hooks']:
                                    require(c.get(CODE+at,2)==opcode and c.get(CODE+at+2,4)==slave+sy[label],'missing enhanced hook')
                                for at,guard,value in words:
                                    require(c.read(CODE+at,2)==(before[at:at+2] if corrupt=='word' else bytes.fromhex(value)),'word fix state')
                                if 'enhanced' not in mouse_runs and not corrupt:
                                    mouse_scenario(c,slave,sy);mouse_runs.add('enhanced')
                            elif revision==0x1302 and corrupt!='exact':
                                # Original mode: only the E1 shortcuts, waypoint marker order and mouse.
                                after=bytearray(c.read(CODE,0x358c8))
                                for at,label,opcode in exact:
                                    require(after[at:at+6]==word(opcode)+long(slave+sy[label]),'missing exact hook')
                                    after[at:at+6]=before[at:at+6]
                                for at,guard,value in words:
                                    require(after[at:at+2]==(before[at:at+2] if corrupt=='word' else bytes.fromhex(value)),'word fix state')
                                    after[at:at+2]=before[at:at+2]
                                require(bytes(after)==before and c.read(STARTUP,0x1d94)==opening_before,'original mode modified game')
                                require(events[-1]=='flush' and 'abort' not in events,'original mode enhanced')
                                for pos in meta['fixups']:
                                    value=int.from_bytes(payload[pos:pos+4],'big')
                                    require(c.read(slave+pos,4)==long((value&0x0fffffff)+CODE),'exact native operand unresolved')
                                if 'original' not in mouse_runs and not corrupt:
                                    mouse_scenario(c,slave,sy);mouse_runs.add('original')
                            else:
                                require(c.read(CODE,0x358c8)==before and c.read(STARTUP,0x1d94)==opening_before,'original mode modified game')
                                require('flush' not in events and 'abort' not in events,'original mode enhanced')
                                for pos in meta['fixups']:
                                    require(c.read(slave+pos,4)==payload[pos:pos+4],'original mode relocated payload')
                            if not (enabled and fatal):
                                expected=dict(regs);expected.update({1:regs[4],2:regs[16]})
                                require(all(c.reg(r)==v for r,v in expected.items()),'startup register ABI changed')
                            results.append(dict(bank=bank,flags=flags,option=option,revision=revision,corrupt=corrupt,enhanced=enabled,events=events))
                        finally:c.close()
    original=(ROOT/'tmp/game/WingCommander/WingCommander.info').read_bytes()
    icon=(build/'WingCommander.info').read_bytes()
    require(icon==enhanced_icon(original),'generated icon mismatch')
    require(tooltypes(icon)[2][:2]==[b'CUSTOM5=1\0',b'DCACHE\0'],'icon defaults disabled')
    rejected=0
    for bad in (icon,b'bad icon',original[:80]):
        try:enhanced_icon(bad)
        except (ValueError,IndexError):rejected+=1
    require(rejected==3,'unsafe icon accepted')
    require(mouse_runs=={'enhanced','original'},'mouse scenario not run on both install paths')
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
