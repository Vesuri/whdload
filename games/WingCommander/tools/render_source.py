"""Position-independent, immutable Kalms specialisations for CD32 surfaces."""
import hashlib
from pathlib import Path

HASHES = {'030':'31bf210db133f206a262f54443d5470c6454be5dcc80806064fe04a1c89e4bf5',
          '040':'9fb2c00184c0a69edb41b9d234648ea8f0f1d478b02c745e6f377d36984df716'}


def source(root):
    parts = [(root/'whdload/render.s').read_text()]
    for cpu, sha in HASHES.items():
        name = 'c2p1x1_8_c5_'+cpu
        raw = (root/'whdload/kalms'/f'{name}.s').read_bytes()
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
