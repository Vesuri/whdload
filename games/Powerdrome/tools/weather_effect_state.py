"""Read the installed experimental weather-effect record, never a stale loader copy."""
import struct

NAMES=('visible','visual_seed','drawing','saved_seed','cleanup_pending','reserved',
       'ticks','visual_events','attempts','selections','draws','clock','cleanups')
NATIVE=(('rng',0x62),('lifetime',0x4ce),('delay',0x4d2),('enabled',0x4cc),
        ('transition',0x4c6),('palette',0x4d0))


def locate(chip,code,game,base):
    if chip[game+0x112e6:game+0x112e8]!=bytes.fromhex('4ef9'):
        return None
    draw=struct.unpack_from('>I',chip,game+0x112e8)[0]-base
    assert 0<=draw<len(code) and code[draw:draw+2]==bytes.fromhex('48e7')
    tag=code.find(b'PDWEFX01',draw,draw+4096)
    assert tag>=0 and code.find(b'PDWEFX01',tag+1,draw+4096)<0
    assert tag+48<=len(code)
    return base+tag


def snapshot(root,final=False):
    prefix='final-' if final else ''
    chip=(root/(prefix+'chip.bin')).read_bytes()
    code=(root/(prefix+'code.bin')).read_bytes()
    game=int((root/'game-base.txt').read_text(),0)
    base=int((root/'dump-base.txt').read_text(),0)
    address=locate(chip,code,game,base)
    assert address is not None, 'Experimental effect hook is not installed'
    out=dict(zip(NAMES,struct.unpack_from('>6H7I',code,address-base+8)))
    out.update({name:struct.unpack_from('>H',chip,game+0xa6e+off)[0] for name,off in NATIVE})
    return out


def probe_command(address,game,off):
    values=[f'*(unsigned short*){address+i:#x}' for i in range(8,20,2)]
    values += [f'*(unsigned int*){address+i:#x}' for i in range(20,48,4)]
    values += [f'*(unsigned short*){game+0xa6e+i:#x}' for _,i in NATIVE]
    return ('printf "PDWEFX_EVENT %d '+hex(off)+' '+' '.join(['%u']*len(values))+
            '\\n", $pd_field, '+', '.join(values)+'\n')


def parse_values(text):
    values=list(map(int,text.split()))
    names=(*NAMES,*(name for name,_ in NATIVE))
    assert len(values)==len(names)
    return dict(zip(names,values))
