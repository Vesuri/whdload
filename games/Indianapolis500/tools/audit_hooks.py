#!/usr/bin/env python3
"""Audit optional hook instruction boundaries and direct incoming branches.
Uses local Disk.1 only; saves no game bytes. Indirect control flow needs trace review.
"""
import os,re,subprocess,tempfile
from pathlib import Path
from i500_report import DISK,game_hunks
from amigaxdev.env import tool
hooks={0x140:(6,['jsr']),0x2a8c0:(6,['jsr']),0x9c32:(6,['addq']),0x270:(6,['clr']),0x2da:(6,['jsr']),0xc29a:(8,['btst']),0xbb8e:(6,['move']),0xbc96:(6,['move']),0xbde4:(6,['move']),0xb8ca:(8,['move','move']),0xb574:(8,['btst']),0x7ee:(8,['move']),0xb57e:(8,['bset']),0x152:(8,['move','beq']),0x9c06:(6,['addq']),0x3af0:(6,['movem','rte']),0x26d4c:(8,['btst']),0xbbb4:(8,['move','move']),0xbcbc:(8,['move','move']),0xbe04:(8,['move','move']),0xb92c:(10,['asl','add','move']),0xc240:(6,['move'])}
disk=Path(DISK).read_bytes(); _,_,start,size,_=game_hunks(disk)[0]
with tempfile.TemporaryDirectory(prefix='i500-audit-') as temp:
    binary=Path(temp)/'hunk.bin';binary.write_bytes(disk[start:start+size])
    output=subprocess.check_output([tool('objdump'),'-D','-b','binary','-m','m68k:68000',str(binary)],text=True)
ins={};last=None
for line in output.splitlines():
    parts=line.split('\t')
    if len(parts)<2: continue
    try:address=int(parts[0].strip().rstrip(':'),16)
    except ValueError:continue
    n=len(parts[1].split())*2
    if len(parts)>2 and parts[2].strip():
        last=address;ins[last]=[n,' '.join(parts[2:])]
    elif last is not None:ins[last][0]+=n
for address,(size,expected) in hooks.items():
    at=address;actual=[]
    while at<address+size:
        length,text=ins[at];actual.append(text.split()[0].split('.')[0]);at+=length
    assert at==address+size,(hex(address),'partial instruction')
    assert actual==expected,(hex(address),actual,expected)
    incoming=[]
    for pc,(length,text) in ins.items():
        mnemonic=text.split()[0]
        if mnemonic.startswith(('b','db')) or mnemonic in ('jmp','jsr'):
            match=re.search(r'0x([0-9a-f]+)\s*$',text)
            if match and address<int(match[1],16)<address+size:incoming.append(pc)
    assert not incoming,(hex(address),'incoming interior branches',incoming)
    print(f'game:{address:05x}: {size} bytes, whole {"/".join(actual)}, no direct interior targets')
print('SOFT common epilogue saves/restores must also be confirmed from executed interrupt paths.')
