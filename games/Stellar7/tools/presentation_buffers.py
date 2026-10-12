#!/usr/bin/env python3
"""Map actual bitplane fetches to native bitmaps in a retained raw trace.

Checks that every field fetches one complete 320x200 four-plane bitmap, with
no mixture of buffer addresses. Also compares fetched words across consecutive
fields using the same bitmap. Unchanged fetched words cannot rule out writes
that are overwritten again before scanout; changed words prove unstable content.
"""
import argparse
import collections
import json
import struct
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto


def inspect(folder, require_stable=False):
    folder=Path(folder);data=(folder/'state.bin').read_bytes()
    bitmaps=[]
    for index in range(3):
        off=0x71da+40*index
        width,height=struct.unpack_from('>2H',data,off);depth=data[off+5]
        assert (width,height,depth)==(40,200,5 if index==2 else 4)
        planes=struct.unpack_from('>8I',data,off+8)[:depth]
        bitmaps.append(planes)
    trace=barto.load(folder/'trace.bin');rows=[];kinds=collections.Counter();previous=None;changes=[]
    for field in trace.fields:
        assert field.dma_size==58 and len(field.dma)%58==0
        buffers=collections.Counter();planes=collections.Counter();offsets=collections.defaultdict(set);words={}
        for at in range(0,len(field.dma),58):
            kind=struct.unpack_from('<h',field.dma,at+29)[0];kinds[kind]+=1
            if kind!=6:continue
            reg,value,size,address=struct.unpack_from('<HQHI',field.dma,at)
            assert size==2 and reg in (0x110,0x112,0x114,0x116)
            matches=[(i,p,address-origin) for i,ptrs in enumerate(bitmaps) for p,origin in enumerate(ptrs) if origin<=address<origin+8000]
            assert len(matches)==1,('unknown/ambiguous bitplane address',address,matches)
            i,p,offset=matches[0];assert p==(reg-0x110)//2
            buffers[i]+=1;planes[p]+=1;offsets[p].add(offset);words[address]=value
        assert len(buffers)==1 and planes=={0:4000,1:4000,2:4000,3:4000},('incomplete/mixed field',field.index,buffers,planes)
        assert all(values==set(range(0,8000,2)) for values in offsets.values())
        buffer=next(iter(buffers))
        if previous is not None and previous[0]==buffer:
            assert words.keys()==previous[1].keys(), 'same bitmap has different fetch coverage'
            count=sum(value!=previous[1][address] for address,value in words.items())
            if count:changes.append(dict(field=field.index,buffer=buffer,changed_words=count))
        previous=(buffer,words)
        rows.append(dict(field=field.index,buffer=buffer,words=sum(buffers.values())))
    assert rows
    switches=[row['field'] for prev,row in zip(rows,rows[1:]) if row['buffer']!=prev['buffer']]
    if require_stable:assert not changes, ('displayed bitmap content changes',changes)
    return dict(fields=len(rows),scanout=rows,buffer_change_fields=switches,same_buffer_word_changes=changes,dma_kinds=dict(kinds),scope=__doc__.strip())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path)
    p.add_argument('--require-stable',action='store_true',help='reject changed fetched words in consecutive fields using the same bitmap')
    a=p.parse_args();print(json.dumps(inspect(a.capture,a.require_stable),indent=2))
