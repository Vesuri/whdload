"""Accept only hash-checked, task-owned rendering builds."""
import hashlib, json
from cd32_runtime import ROOT


def load(path):
    target=(ROOT/path).resolve()
    if (ROOT/'tmp').resolve() not in target.parents: raise ValueError('render fixture must be in tmp/')
    meta=json.loads((target.parent/'build.json').read_text())
    data=target.read_bytes()
    if not (meta.get('render') or meta.get('render_control')): raise ValueError('render build required')
    if hashlib.sha256(data).hexdigest()!=meta['sha256'] or len(data)!=meta['bytes']:
        raise ValueError('render fixture changed')
    return target,meta
