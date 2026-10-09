#!/usr/bin/env python3
"""Inspect Practice loop timing and bitmap traffic from an existing Barto capture.
Usage: python3 tools/analyze_pipeline.py CAPTURE_DIRECTORY > CAPTURE_DIRECTORY/pipeline.json
Registers are sampled at executed PCs; initial memory is used only for immutable opcode identification.
All output addresses are hunk-relative or bitmap-relative.
"""
import collections
import json
from pathlib import Path
import sys
import barto
from powerdrome_report import Memory

MARKS = {
    0xbc4e:'outer simulation/render call', 0xca3e:'update entry',
    0xccf2:'player movement multiply', 0xcdc4:'player position write',
    0xcf90:'speed smoothing', 0xcfd4:'boost speed smoothing',
    0xd56c:'opponent movement multiply', 0xcd60:'fall counter increment',
    0xcdb4:'impulse counter write', 0xcdb8:'impulse decay',
    0xcee8:'scene render call',
    0x10df2:'renderer entry', 0x117da:'renderer return',
    0xd8ea:'post-render update entry', 0xd94a:'resource decrement',
    0xbc7c:'outer display update call', 0x8056:'display update entry',
    0x7f8e:'raw delta', 0x7fa4:'clamped delta',
    0xbc86:'frame counter increment', 0x5684:'VBL entry',
    0x157a6:'background base', 0x1582c:'background store',
    0x1602a:'span row',
    0x112cc:'renderer sprite background', 0x112e0:'renderer conditional helper',
    0x112f0:'renderer transient effect', 0x117ce:'renderer effect cleanup',
}

def main():
    root=Path(sys.argv[1]); trace=barto.load(root/'trace.bin')
    game=int((root/'game-base.txt').read_text().strip(),0)
    mem=Memory(trace,(root/'code.bin').read_bytes(),int((root/'dump-base.txt').read_text().strip(),0))
    traffic=collections.Counter(); span_rows=collections.Counter(); written_rows=collections.Counter(); opcache={}
    events=[]; counts=collections.Counter(); dt=[]; raw_dt=None
    track=False; current=None; buffers=set(); clear_ranges=collections.defaultdict(lambda:[32000,0,0])
    cycles=0; in_renderer=False; outside_span_records=0; completed_traffic=None; completed_clear_bytes=0
    for f in trace.fields:
        for pc,cost,r in trace.instructions(f):
            off=pc-game if pc is not None else -1
            if off==0xca3e: track=True
            if track and off==0x10df2: in_renderer=True
            if track and 0x15b68 <= off < 0x15e68:
                if not in_renderer: outside_span_records+=1
                if pc not in opcache: opcache[pc]=mem.word(pc)
                w=opcache[pc]
                if w & 0xf1f8 in (0xc158,0x8158):
                    traffic['span destination read bytes']+=2
                    traffic['span destination write bytes']+=2
                    if current is not None: written_rows[(r[10]-current)//40]+=1
                elif w & 0xf1f8 == 0x30c0:
                    traffic['span destination write bytes']+=2
                    if current is not None: written_rows[(r[10]-current)//40]+=1
            if off in MARKS and track:
                name=MARKS[off]; counts[name]+=1
                if off==0x7f8e: raw_dt=r[6]
                if off==0x7fa4: dt.append({'field':f.index,'raw':raw_dt,'used':r[6]})
                if off==0x157a6:
                    current=r[13]; buffers.add(current)
                if off==0x1582c and current is not None:
                    # MOVEM will predecrement by 40 bytes.
                    rel=r[13]-40-current; bounds=clear_ranges[str(rel//8000)]
                    bounds[0]=min(bounds[0],rel%8000); bounds[1]=max(bounds[1],rel%8000+40); bounds[2]+=40
                if off==0x1602a and current is not None:
                    span_rows[(r[10]-current)//40]+=1
                if off not in (0x1582c,0x1602a):
                    item={'field':f.index,'cycles_before':cycles,'event':name}
                    if off==0xccf2: item['speed_signed']=((r[4]&65535)^32768)-32768
                    if off==0xd94a: item['decrement']=r[0]&65535
                    if off==0xcdc4: item['position_words']=[((r[i]&65535)^32768)-32768 for i in (5,6,7)]
                    if off in (0x7f8e,0x7fa4): item['d6']=r[6]
                    events.append(item)
            if track and off==0x117da:
                in_renderer=False
                completed_traffic=dict(traffic)
                completed_clear_bytes=counts['background store']*40
            cycles+=cost
    print(json.dumps({'span_records_outside_renderer':outside_span_records,'counts':counts,'delta_samples':dt,'draw_buffer_count':len(buffers),
                      'background_plane_byte_ranges_and_traffic':clear_ranges,
                      'span_destination_traffic':traffic,
                      'through_last_renderer_return':{'span_traffic':completed_traffic,'background_write_bytes':completed_clear_bytes},'span_row_histogram':span_rows,
                      'span_written_row_histogram':written_rows,'events':events},indent=2))

if __name__=='__main__': main()
