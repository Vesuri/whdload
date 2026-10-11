"""Versioned experimental weather generation/visual deadlines."""
import struct
from weather_effect_state import locate as effect_locate

FIELDS=(('initialized',8,2),('pending',10,2),('next_generation',12,4),
        ('visual_deadline',16,4),('generation_clock',20,4),('visual_clock',24,4),
        ('generations',28,4),('publications',32,4),('period',36,2),
        ('generation_seed',38,2),('visual_after_seed',40,2),('reserved',42,2))


def locate(chip,code,game,base):
    address=effect_locate(chip,code,game,base)
    if address is None or code[address-base:address-base+8]==b'PDWEFX01':return None
    assert code[address-base+48:address-base+56]==b'PDWECLK1'
    return address+48


def snapshot(root,final=False):
    prefix='final-' if final else ''
    chip=(root/(prefix+'chip.bin')).read_bytes();code=(root/(prefix+'code.bin')).read_bytes()
    game=int((root/'game-base.txt').read_text(),0);base=int((root/'dump-base.txt').read_text(),0)
    address=locate(chip,code,game,base)
    assert address is not None
    return {name:struct.unpack_from('>H' if size==2 else '>I',code,address-base+off)[0]
            for name,off,size in FIELDS}


def probe_command(address,off):
    values=[f'*(unsigned {"short" if size==2 else "int"}*){address+i:#x}' for _,i,size in FIELDS]
    return ('printf "PDWECLK_EVENT %d '+hex(off)+' '+' '.join(['%u']*len(values))+
            '\\n", $pd_field, '+', '.join(values)+'\n')


def parse_values(text):
    values=list(map(int,text.split()))
    assert len(values)==len(FIELDS)
    return dict(zip((name for name,_,_ in FIELDS),values))
