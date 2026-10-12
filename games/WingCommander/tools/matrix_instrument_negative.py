#!/usr/bin/env python3
"""Check that instrument acceptance rejects stale audits and keeps absent runs pending."""
import argparse
import copy
import json
from pathlib import Path
from cd32_runtime import ROOT
from matrix_instrument_accept import validate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('fresh tmp output required')
    cell=json.loads(a.manifest.read_text())[0]
    out.mkdir();results=[]
    for field,value in (('emulator_sha256','0'*64),('cacr',-1),('options','INVALID')):
        changed=copy.deepcopy(cell)
        audit=json.loads((ROOT/cell['dma_audit']).read_text());audit[field]=value
        file=out/(field+'.json');file.write_text(json.dumps(audit,indent=2)+'\n')
        changed['dma_audit']=str(file.relative_to(ROOT))
        try:validate(changed)
        except ValueError as error:results.append(dict(field=field,rejected=True,reason=str(error)))
        else:raise ValueError('stale audit accepted: '+field)
    changed=copy.deepcopy(cell);changed['beam']=str((out/'absent').relative_to(ROOT))
    result=validate(changed)
    if result.get('status')!='pending' or result.get('missing')!=['beam']:
        raise ValueError('missing beam run did not remain pending')
    results.append(dict(missing_run_pending=True))
    (out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
