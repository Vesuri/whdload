"""Read the experimental fade scheduler through its installed outer-loop hook."""
import struct

FIELDS=(('expected',8,2),('active',10,2),('deadline',12,4),
        ('published',16,2),('pending',18,2),('ticks',20,4),
        ('positive',24,4),('negative',28,4),('gears',32,4),('draws',36,4),
        ('start',40,4),('last',44,4))
NATIVE=(('transition',0x4c6),('gear',0x450),('forecast',0x4c0),('track',0x118))


def locate(chip,code,game,base):
    if chip[game+0xbd1a:game+0xbd1c]!=bytes.fromhex('4ef9'):
        return None
    entry=struct.unpack_from('>I',chip,game+0xbd1c)[0]-base
    assert 0<=entry<len(code) and code[entry:entry+2]==bytes.fromhex('48e7')
    tag=code.find(b'PDWFAD01',entry,entry+4096)
    assert tag>=0 and code.find(b'PDWFAD01',tag+1,entry+4096)<0
    assert tag+48<=len(code)
    return base+tag


def snapshot(root,final=False):
    prefix='final-' if final else ''
    chip=(root/(prefix+'chip.bin')).read_bytes()
    code=(root/(prefix+'code.bin')).read_bytes()
    game=int((root/'game-base.txt').read_text(),0)
    base=int((root/'dump-base.txt').read_text(),0)
    address=locate(chip,code,game,base)
    assert address is not None
    values={name:struct.unpack_from('>H' if size==2 else '>I',code,address-base+off)[0]
            for name,off,size in FIELDS}
    values.update({name:struct.unpack_from('>H',chip,game+0xa6e+off)[0] for name,off in NATIVE})
    return values


def probe_command(address,game,off):
    values=[f'*(unsigned {"short" if size==2 else "int"}*){address+i:#x}' for _,i,size in FIELDS]
    values += [f'*(unsigned short*){game+0xa6e+i:#x}' for _,i in NATIVE]
    return ('printf "PDWFADE_EVENT %d '+hex(off)+' '+' '.join(['%u']*len(values))+
            '\\n", $pd_field, '+', '.join(values)+'\n')


def parse_values(text):
    values=list(map(int,text.split()))
    names=[name for name,_,_ in FIELDS]+[name for name,_ in NATIVE]
    assert len(values)==len(names)
    return dict(zip(names,values))
