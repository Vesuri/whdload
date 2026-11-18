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
from mouse_model import BUTTON_SEQUENCE, BUTTON_KEYS, buttons_expected, APERTURE, KEY, Pointer, cockpit, FIRE_SEQUENCE, fire_poll, fire_expected, fire_native_holds


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
        if c.get(c.reg(2),4)==CHIP:c.write(CHIP,word(c.reg(9)&0xffff)+word(c.reg(10)&0xffff))    # control words: x, y
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
    # A new screen places the pointer without a room exit: the mouse continues from there.
    c.write(a4+412,struct.pack('>hh',120,70))
    require(event(4,0)==[(119,68)] and room()==(122,70),'mouse kept its old position')
    c.write(a4+412,struct.pack('>hh',150,90))
    require(room()==(150,90) and event(2,2)==[(148,89)] and room()==(151,91),'room routine kept the old mouse position')
    c.write(STACK-8,long(STOP));segment(0x26478,0x26486,STACK-8)
    require(moves[-1]==(997,998) and var('mouse_active')==0 and event(-9,-9)==[],'mouse room exit')
    fire={}
    for pra in (0xff,0xbf,0x7f,0x3f):
        c.write(0xbfe001,bytes([pra]));segment(0x33f88,0x33f94);fire[pra]=c.reg(9)&255
    require(fire=={0xff:0,0xbf:1,0x7f:1,0x3f:1},'left button is not port-1 fire')
    # Left button in flight: the sample and native decode (O:33fa4) field by
    # field, then the flight poll's fire and modifier; without a flight the
    # native scheme (a hold alone is the modifier) is the control.
    record=DATA+0x77c8;require(c.get(record+12,2)==15 and c.get(record+14,2)==10,'click thresholds')
    rows={}
    for flight in (False,True):
        c.write(record,bytes(12));polled=[]
        for down in FIRE_SEQUENCE:
            fields=c.get(slave+sy['mouse_fields'],2)
            c.write(slave+sy['stick_field'],word(fields if flight else (fields-100)&0xffff))
            c.write(0xbfe001,bytes([0xbf if down else 0xff]));segment(0x33f82,0x33f96)
            polled.append(fire_poll(c.read(record,9)));c.write(record+6,bytes(2))
        rows[flight]=polled
    require(fire_native_holds(FIRE_SEQUENCE,rows[False])>0,'control: a hold alone fired')
    require(rows[True]==fire_expected(),'left button flight fire')
    c.write(record,bytes(10)+word(0));c.write(0xbfe001,bytes([0x3f]))
    c.write(slave+sy['stick_field'],word(c.get(slave+sy['mouse_fields'],2)));segment(0x33f82,0x33f96)
    require(c.read(record,9)[8]==0,'stick fire took the mouse path')
    c.write(record,bytes(12))
    guard={}
    for pra in (0xff,0xbf,0x7f):
        c.write(0xbfe001,bytes([pra]));c.write(a4-2114,b'\x5a'*24)
        c.run(0x33f02);guard[pra]=c.read(a4-2114,24)
    require(all(g[:10]==bytes(10) and g[10:12]==word(-1) and g[12:22]==bytes(10) for g in guard.values()),'record reset')
    require([g[22:] for g in guard.values()]==[word(0),word(-1),word(-1)],'click release guard')
    steer_scenario(c,slave,sy,moves)
    buttons_scenario(c,slave,sy)
    for r,v in saved.items():c.reg(r,v)


def buttons_scenario(c,slave,sy):
    """Mouse buttons in flight: mouse_vbl's button read and the native flight
    poll O:182ce with the slave's epilogue hook, field by field through
    BUTTON_SEQUENCE; its flags and the keys queued in the game's key FIFO
    (read/write A4-2038/-2036, buffer O:34568). Without a flight and with lines
    that never read up, the poll is native; the pointer holds while the right
    button is down."""
    a4=DATA+0x7ffe;record=DATA+0x77c8
    require(c.read(CODE+0x183dc,6)==bytes.fromhex('4eb9')+long(slave+sy['mouse_poll_ocs']),'flight poll epilogue not hooked')
    execbase=c.get(4,4)
    for off in (-132,-138):c.write(execbase+off,word(0x4e75))       # Forbid, Permit
    fields=lambda:c.get(slave+sy['mouse_fields'],2)
    def event(dx,dy):
        c.write(EVENT,struct.pack('>IBBHHhh',0,2,0,0xff,0x8000,dx,dy))
        c.run(slave-CODE+sy['mouse_event'],registers={4:EVENT})
    def reset():
        c.write(slave+sy['btn'],word(7)+bytes(42))
        c.write(a4-2036,word(c.get(a4-2038,2)))
    def run(sequence,flight=True,lines=True):
        rows=[]
        stamp=lambda:word(fields() if flight else (fields()-100)&0xffff)
        for left,right,middle,dx,dy in sequence:
            if dx or dy:event(dx,dy)
            c.write(slave+sy['stick_field'],stamp())
            c.write(0xbfe001,bytes([0xbf if left else 0xff]))
            c.write(0xdff016,word((0xffff&~(right<<10|middle<<8)) if lines else 0))
            c.run(slave-CODE+sy['mouse_vbl'])
            c.write(slave+sy['stick_field'],stamp())
            c.write(record,bytes(12));c.write(record+8,bytes([left]))
            c.run(0x182ce)
            flags=tuple(bool(x) for x in c.read(a4+16084,6))
            rd,wr=c.get(a4-2038,2),c.get(a4-2036,2)
            keys=bytes(c.read(CODE+0x34568+(i%64),1)[0] for i in range(rd,rd+(wr-rd)%64))
            c.write(a4-2038,word(wr));rows.append((flags,keys))
        return rows
    reset();got=run(BUTTON_SEQUENCE);want=buttons_expected()
    bad=[i for i,(g,w) in enumerate(zip(got,want)) if g!=w]
    require(not bad,f'mouse buttons at fields {bad[:8]}: {[(got[i],want[i]) for i in bad[:4]]}')
    require(b''.join(k for _,k in got)==BUTTON_KEYS,'mouse button keys')
    for flight,lines in ((False,True),(True,False)):
        reset();got=run(BUTTON_SEQUENCE,flight,lines)
        require(got==buttons_expected(flight=flight,lines=lines) and
                all(f==(False,)*5+(bool(s[0]),) and k==b'' for (f,k),s in zip(got,BUTTON_SEQUENCE)),'mouse buttons control')
    reset()
    def steer(right,dx):
        c.write(0xdff016,word(0xffff&~(right<<10)));c.run(slave-CODE+sy['mouse_vbl']);event(dx,0)
        c.write(a4+16084,bytes([0,0,0,0,right]));c.write(a4-18318,word(0));c.run(0x183e4)
        return struct.unpack('>hh',c.read(slave+sy['stick_ptr'],4))
    c.write(0xdff016,word(0xffff));c.run(slave-CODE+sy['mouse_vbl'])
    base=steer(0,0)
    require(steer(0,20)==(base[0]+20,base[1]) and steer(1,40)==(base[0]+20,base[1]) and
            steer(0,6)==(base[0]+26,base[1]),'pointer moved with the right button held')
    # The right button's roll: the native ramp (A4 3724) with four times its
    # steps, cap and decay, until it settles after the release.
    def roll(right,flag):
        c.write(0xdff016,word(0xffff&~(right<<10)));c.run(slave-CODE+sy['mouse_vbl'])
        c.write(a4+16084,bytes([flag<0,flag>0,0,0,1]));c.write(a4-18318,word(0));c.run(0x183e4)
        return struct.unpack('>h',c.read(a4+3724,2))[0]
    roll(0,0);roll(0,0);roll(0,0);roll(0,0);roll(0,0)
    got=[roll(0,1) for _ in range(11)]+[roll(0,0) for _ in range(5)]
    require(got==[1,2,3,4,5,6,7,8,9,9,9,7,5,3,1,0],f'native roll {got}')
    got=[roll(1,-1) for _ in range(10)]+[roll(1,1) for _ in range(2)]+[roll(1,0) for _ in range(2)]
    require(got==[-4,-8,-12,-16,-20,-24,-28,-32,-36,-36,4,8,0,0],f'mouse roll {got}')
    got=[roll(1,1) for _ in range(9)]+[roll(0,0) for _ in range(6)]+[roll(0,1) for _ in range(2)]
    require(got==[4,8,12,16,20,24,28,32,36,28,20,12,4,0,0,1,2],f'released roll {got}')
    # The right button as Esc in the cutscene waits (key reads O:180ce in the
    # key-or-fire wait O:180c4, O:1814c in the timed wait): the whole wait
    # returns 'continue' and sets the abort flag (A4-28796) for a recent
    # press, once; native for none, held, stale, a flight press, low lines.
    for site in (0x180ce,0x1814c):
        require(c.read(CODE+site,6)==bytes.fromhex('4eb9')+long(slave+sy['mouse_esc']),f'cutscene key read O:{site:x} not hooked')
    require(c.get(slave+sy['mouse_keyread'],4)==CODE+0x345a8,'native key read')
    def vbl(right,n=1,lines=True):
        for _ in range(n):
            c.write(slave+sy['stick_field'],word((fields()-100)&0xffff));c.write(0xbfe001,b'\xff')
            c.write(0xdff016,word((0xffff&~(right<<10)) if lines else 0));c.run(slave-CODE+sy['mouse_vbl'])
    def wait():
        c.write(a4-28796,word(0));c.run(0x180c4)
        return c.reg(9)&0xffff,c.get(a4-28796,2)
    got={}
    reset();vbl(0,2);got['none']=wait()
    vbl(1);got['press']=wait();got['held']=wait()
    vbl(1,3);got['still_held']=wait()
    vbl(0);vbl(1);vbl(1,60);got['stale']=wait()
    vbl(0);vbl(1);c.write(slave+sy['stick_field'],word(fields()));c.run(slave-CODE+sy['mouse_poll']);got['flight']=wait()
    vbl(0);vbl(1,2);got['again']=wait()
    reset();vbl(0,2,False);vbl(1,2,False);got['lines_low']=wait()
    require(got==dict(none=(0,0),press=(1,1),held=(0,0),still_held=(0,0),stale=(0,0),flight=(0,0),again=(1,1),lines_low=(0,0)),f'cutscene Esc {got}')
    c.write(0xdff016,word(0))


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
    for off in (-120,-126):c.write(c.get(4,4)+off,word(0x4e75))       # Disable, Enable
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
    # The VBL (stick_commit, mouse_vbl's first call) copies the staging to the
    # Chip image: the control words and lines change together.
    commit=lambda:c.run(slave-CODE+sy['stick_commit'])
    chip=lambda:c.read(CHIP,40)
    def image():commit();return [struct.unpack('>HH',c.read(CHIP+4+4*r,4)) for r in range(9)]
    control=lambda:struct.unpack('>hh',c.read(CHIP,4))
    def shown():commit();return c.read(CHIP,4)!=bytes(4)
    tick(100)
    require(steer((5,-3))==((3,-1),[]),'native ramp decay')
    ev(160,0);tick();require(steer((0,0))==want()==((0,5),[(234,58)]),'mouse right: yaw right')
    require(sprites==[(ANY,7)] and changes==[(ANY,CHIP)] and c.get(ANY+4,2)==9,'pointer sprite not bound')
    require(chip()==bytes(40),'pointer image written before the VBL')
    require(image()==img() and control()==ptr.sprite(),'pointer image')
    ev(0,52);tick();before=chip()
    require(ptr.at()==(239,88) and steer()==want() and want()[0]==(2,5),'mouse down: pitch down, as the PC')
    require(chip()==before,'pointer moved or masked before the VBL')
    require(image()==img() and control()==ptr.sprite() and chip()!=before,'pointer image and position not together')
    tick();require(steer()==(want()[0],[]),'held pointer position')
    c.write(slave+sy['mouse_dive'],word(0x00ff))
    tick();require(steer()[0]==Pointer(dive=True).move(160,52).ramps()==(-2,5),'mouse_dive: pitch up')
    c.write(slave+sy['mouse_dive'],word(0))
    ev(-150,-44);tick();require(ptr.at()==(164,66) and steer()==want() and want()[0]==(0,0),'PC dead zone')
    ev(1000,1000);tick();require(steer()==want()==((9,9),[(319-5,199-4)]) and image()==[(0,0)]*9,'full deflection, hidden')
    ev(-2000,-2000);tick();require(steer()==want()==((-9,-9),[(0-5,0-4)]) and image()==[(0,0)]*9,'full deflection up left')
    ev(0,28);tick();require(ptr.at()==(0,14) and steer()==want() and image()==img()!=[(0,0)]*9,'aperture edge: full, shown')
    ev(10,2);tick();require(steer()==want() and want()[0]==(-5,-5),'off the edge: PC steps')
    ev(308,94);tick();require(steer()[1]==[ptr.sprite()] and ptr.at()==(159,62) and image()==img(),'pointer behind the cockpit')
    tick();require(steer((0,-9),(0,1,0,0,0))==((0,1),[]) and not shown(),'stick steering re-centres');ptr.centre()
    tick();require(steer((0,0))==((0,0),[]),'not re-centred')
    ev(80,80);tick();require(steer(flags=(1,0,0,0,1))==want() and want()[0]==(5,2),'modifier: the mouse steers')
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
    require(payload[info:].startswith(b'2.0b (18.11.2026)\n'), 'public release information missing')
    require(b'$VER: WingCommander 2.0b (18.11.2026)\0' in payload, 'public version missing')
    config=int.from_bytes(payload[0x32:0x34],'big')
    require(payload[config:].split(b'\0',1)[0].endswith(b'C5:X:Enhanced framerate:0;C5:M:World speed (68020+Fast RAM):1.0x,1.2x,1.5x,2.0x,CPU-dependent:1-3;C5:M:Mouse speed:1.0x,Off,0.5x,0.75x,1.5x,2.0x,3.0x,4.0x:4-6;C5:X:Mouse forward dives:7;'),'public config missing')
    if mutation:
        start,end=sy['ocs_option_gate'],sy['ocs_option_tags']
        segment=payload[start:end]
        old,new={'option':(bytes.fromhex('0c8000000009'),bytes.fromhex('0c8000000001')),
                 'cpu':(bytes.fromhex('0240008e'),bytes.fromhex('0240008f')),
                 'slow':(bytes.fromhex('0c8100a00000'),bytes.fromhex('0c8100e00000'))}[mutation]
        require(segment.count(old)==1,'mutation site missing')
        payload=payload[:start]+segment.replace(old,new)+payload[end:]
    results=[]
    from ocs_memory_build import ALWAYS
    exact=[h for h in meta['hooks'] if h[1] in ALWAYS]
    require(len(exact)==len(ALWAYS),'always-on hooks missing from build')
    from ocs_memory_build import WORDS, MOUSE
    MOUSE_LABELS={label for _,label,_ in MOUSE}
    mouse_off=[]
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
            for option in (0,1,3,6,8,9,10,0xffffffff,0x13,0x10,0x11,0x19,0x73,0x2b,0x81,0xa3):
                # CUSTOM5 bits 4-6 the mouse: 0 normal, 1 off, 2-7 0.5x-4x; bit 7 mouse forward dives.
                mouse=(option>>4)&7;opt=option&~0xf0;dive=0xff if option&0x80 else 0
                if opt<=9:opt=(opt+2)%10     # the list: 1.0x-2.0x, then CPU-dependent (internal 0)
                speed=(4,0,2,3,6,8,12,16)[mouse]
                if option>>4 and option!=0xffffffff and (flags not in (0,2) or bank not in ('z2-fast','chip')):continue
                for revision in (0x1302,0x12bc,0x1348):
                    enabled=2<=opt<=9 and bool(flags&0x8e) and bank in ('z2-fast','high-fast','chip-slave-fast') and revision==0x1302
                    # A damaged enhancement-only site must only be examined
                    # when enabled. A damaged exact site makes original mode
                    # fall back to the untouched game instead of aborting.
                    # A damaged word-fix site skips only that fix.
                    for corrupt in ((False,) if option>>4 and option!=0xffffffff else (False,'enhanced','exact','word')):
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
                                    if speed==0 and label in MOUSE_LABELS:
                                        require(c.read(CODE+at,6)==before[at:at+6],'mouse off kept a mouse hook')
                                    else:require(c.get(CODE+at,2)==opcode and c.get(CODE+at+2,4)==slave+sy[label],'missing enhanced hook')
                                require(c.get(slave+sy['mouse_speed'],2)==speed and c.get(slave+sy['mouse_dive'],2)==dive,'mouse option not decoded')
                                for at,guard,value in words:
                                    require(c.read(CODE+at,2)==(before[at:at+2] if corrupt=='word' else bytes.fromhex(value)),'word fix state')
                                rate=struct.unpack('>I',c.read(slave+sy['timing_flight_rate'],4))[0]
                                framerate=struct.unpack('>H',c.read(slave+sy['timing_high_framerate'],2))[0]
                                require(rate==(10,12,15,20)[(opt>>1)-1] and framerate==opt&1,'world speed/framerate option not decoded')
                                if 'enhanced' not in mouse_runs and not corrupt and speed==4:
                                    mouse_scenario(c,slave,sy);mouse_runs.add('enhanced')
                            elif revision==0x1302 and corrupt!='exact':
                                # Original mode: only the E1 shortcuts, waypoint marker order and mouse.
                                after=bytearray(c.read(CODE,0x358c8))
                                for at,label,opcode in exact:
                                    if speed==0 and label in MOUSE_LABELS:continue   # put back: compared below
                                    require(after[at:at+6]==word(opcode)+long(slave+sy[label]),'missing exact hook')
                                    after[at:at+6]=before[at:at+6]
                                require(c.get(slave+sy['mouse_speed'],2)==speed and c.get(slave+sy['mouse_dive'],2)==dive,'mouse option not decoded')
                                for at,guard,value in words:
                                    require(after[at:at+2]==(before[at:at+2] if corrupt=='word' else bytes.fromhex(value)),'word fix state')
                                    after[at:at+2]=before[at:at+2]
                                require(bytes(after)==before and c.read(STARTUP,0x1d94)==opening_before,'original mode modified game')
                                require(events[-1]=='flush' and 'abort' not in events,'original mode enhanced')
                                for pos in meta['fixups']:
                                    value=int.from_bytes(payload[pos:pos+4],'big')
                                    require(c.read(slave+pos,4)==long((value&0x0fffffff)+CODE),'exact native operand unresolved')
                                if 'original' not in mouse_runs and not corrupt and speed==4:
                                    mouse_scenario(c,slave,sy);mouse_runs.add('original')
                            else:
                                require(c.read(CODE,0x358c8)==before and c.read(STARTUP,0x1d94)==opening_before,'original mode modified game')
                                require('flush' not in events and 'abort' not in events,'original mode enhanced')
                                for pos in meta['fixups']:
                                    require(c.read(slave+pos,4)==payload[pos:pos+4],'original mode relocated payload')
                            if not (enabled and fatal):
                                expected=dict(regs);expected.update({1:regs[4],2:regs[16]})
                                require(all(c.reg(r)==v for r,v in expected.items()),'startup register ABI changed')
                            if speed==0 and revision==0x1302:mouse_off.append('enhanced' if enabled else 'original')
                            results.append(dict(bank=bank,flags=flags,option=option,mouse=speed,revision=revision,corrupt=corrupt,enhanced=enabled,events=events))
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
    require(set(mouse_off)=={'enhanced','original'},'mouse off not checked on both install paths')
    return dict(passed=True,sha256=meta['sha256'],cases=results,icon_rejections=rejected)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build');p.add_argument('--output',required=True)
    a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    r=check(Path(a.build))
    rejected=[]
    for mutation in ('option','cpu','slow'):
        try:check(Path(a.build),mutation)
        except ValueError as error:
            require(str(error) in ('original mode modified game','original mode enhanced','missing enhancement flush','missing enhanced hook'),'unexpected mutation failure: '+str(error))
            rejected.append(mutation)
        else:raise ValueError('undetected gate mutation: '+mutation)
    r['negative_controls']=rejected
    (out/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(len(r['cases']),'public option/hardware cases passed; icon checks passed')

if __name__=='__main__':main()
