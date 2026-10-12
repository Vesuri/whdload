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
