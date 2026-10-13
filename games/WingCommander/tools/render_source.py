"""Position-independent, immutable Kalms specialisations for CD32 surfaces."""
import hashlib
from pathlib import Path


def source(root):
    parts = [(root/'whdload/render.s').read_text()]
    for row in (root/'manifest/kalms-c2p.tsv').read_text().splitlines():
        if not row or row.startswith('#'): continue
        path,sha,upstream=row.split('\t')
        cpu=Path(path).stem.rsplit('_',1)[1]
        if cpu not in ('030','040'): raise ValueError('unexpected converter in manifest')
        name = 'c2p1x1_8_c5_'+cpu
        raw = (root/path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError('vendored Kalms source changed')
        body = raw.decode().split('\n'+name+'\n',1)[1]
        body = body.split('\n\tsection\tbss',1)[0] if cpu=='030' else body.split('\n'+name+'_data',1)[0]
        for height in (128,166,200):
            plane=40*height
            label=f'kalms_{cpu}_{height}'
            constants={'scroffs':0,'pixels':320*height, 'delta0':7*plane,
                       'delta4':7*plane+4, **{f'delta{i}':4*plane for i in (1,3,5,7)},
                       **{f'delta{i}':3*plane for i in (2,6,8)}}
            lines=[label+':']
            for line in body.splitlines():
                if line.startswith(name+'_smc'): continue
                if line.strip().lower().startswith(('section','xdef')): continue
                for key,value in constants.items():
                    line=line.replace(name+'_'+key+'(pc)', '#'+str(value))
                    line=line.replace(name+'_'+key, '#'+str(value))
                line=line.replace('BPLSIZE',str(plane))
                lines.append(line)
            parts.append('\n'.join(lines))
    parts.append('\tcnop 0,4')
    return '\n'.join(parts)


def flight_source(root, verify=False, control=False, comparison_control=False, experiment=None):
    wrapper=(root/'whdload/flight_render.s').read_text()
    # Keep the comparison region exactly 82 bytes, including the no-change
    # branch. The control reproduces the old instruction stream; the candidate
    # uses advancing scratch pointers and never executes the padding.
    old = '\n'.join(f'\tmove.l {i}(a3),d0\n\tcmp.l {i}(a5),d0\n\tbne.s .changed' for i in range(0,32,4))
    new = '\tmove.l a3,a0\n\tmove.l a5,a1\n' + '\n'.join(
        '\tcmpm.l (a0)+,(a1)+\n\tbne.s .changed' for _ in range(8))
    wrapper=wrapper.replace('FLIGHT_COMPARE_BLOCK\n        bra.s   .next',
        '.compare_start:\n'+(old if comparison_control else new)+
        '\n\tbra.s .next\n\tdcb.b 82-(*-.compare_start),0')
    wrapper=wrapper.replace('FLIGHT_COPY_BLOCK', '\n'.join(
        f'\tmove.l {i}(a3),d0\n\tmove.l d0,{i}(a5)' for i in range(0,32,4)))
    # Reuse the pinned immutable Kalms transform with one 32-pixel block,
    # retaining the full 320x200 plane stride. No derived game bytes here.
    full=source(root)
    block=full.split('kalms_030_200:',1)[1].split('kalms_040_128:',1)[0]
    if experiment:
        # Equal 720-byte slots keep every diagnostic arm's layout identical.
        # Default/release bytes remain untouched. 040 is also valid on 020 ISA.
        if experiment == 'block040':
            block=full.split('kalms_040_200:',1)[1].rsplit('\tcnop 0,4',1)[0]
        if experiment.startswith('full'):
            control=True
            if experiment != 'full-original':
                wrapper=wrapper.replace('movem.l a3/a5,-(sp)\n        bsr.w   slave+$1ac6',
                    'movem.l a3/a5,-(sp)\n        bsr.w   kalms_'+experiment[-3:]+'_200')
        block += '\n\tdcb.b 720-(*-flight_kalms_block),0\n'
    block=block.replace('#64000', '#32')
    return f'FLIGHT_VERIFY equ {int(verify)}\nFLIGHT_CONTROL equ {int(control)}\n'+wrapper+'\nflight_kalms_block:'+block+'\n\tcnop 0,4\n'
