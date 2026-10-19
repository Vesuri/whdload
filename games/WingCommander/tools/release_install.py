#!/usr/bin/env python3
"""Stage the combined installer in a fresh tmp directory; never include game data."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
from ocs_reconstruct import ROOT,new_output


def validate_script(text):
    # Installer expressions, comments and escaped strings; no execution on host.
    depth=0;quoted=False;comment=False;escape=False
    for c in text:
        if comment:
            if c=='\n':comment=False
        elif quoted:
            if escape:escape=False
            elif c=='\\':escape=True
            elif c=='"':quoted=False
        elif c==';':comment=True
        elif c=='"':quoted=True
        elif c=='(':depth+=1
        elif c==')':
            depth-=1
            if depth<0:raise ValueError('unbalanced Install expression')
    if depth or quoted:raise ValueError('unterminated Install expression/string')
    definitions=set(re.findall(r'\(procedure\s+(\w+)',text))
    calls=set(re.findall(r'\((P_\w+|PDI_\w+)\b',text))
    if calls-definitions:raise ValueError('undefined installer procedures: '+str(calls-definitions))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cd32',type=Path,required=True);p.add_argument('--ocs',type=Path,required=True)
    p.add_argument('--output',required=True);a=p.parse_args();out=new_output(a.output)
    subprocess.run(['/bin/bash',str(ROOT/'tools/inputs.sh'),'verify'],cwd=ROOT,check=True)
    script=(ROOT/'release/Install').read_text(encoding='latin1');validate_script(script)
    readme=(ROOT/'release/ReadMe').read_bytes()
    assert readme==(ROOT/'release/ReadMe.OCS').read_bytes()
    assert b'Version 2.0b (19.10.2026)' in readme and b'Version 1.0 (11.01.2014)' in readme
    assert 'QuickDocED' not in script
    for variant,build,name in [('cd32',a.cd32,'WingCommanderCD32'),('ocs',a.ocs,'WingCommander')]:
        meta=json.loads((build/'build.json').read_text());slave=(build/(name+'.Slave')).read_bytes()
        assert meta['version']=='2.0b' and meta['release_date']=='19.10.2026'
        assert meta.get('release') if variant=='cd32' else meta.get('public_option')
        assert hashlib.sha256(slave).hexdigest()==meta['sha256']
        assert ('$VER: '+name+' 2.0b (19.10.2026)\0').encode() in slave
    out.mkdir(parents=True)
    original=ROOT/'tmp/originals/installer/WingCommanderHD'
    # Original installer assets are preserved byte-for-byte, staged only in tmp/.
    names=['ReadMe.info','Manual','Manual.info']
    names += [n+suffix for n in ('QuickDocEN','QuickDocDE','QuickDocFR','QuickDocIT') for suffix in ('','.info')]
    names += ['WingCommander.'+suffix for suffix in ('inf','newfrank','colfrank','colzarkov','colbox')]
    for name in names:shutil.copyfile(original/name,out/name)
    shutil.copyfile(original/'Install-WingCommander.info',out/'Install.info')
    for name in ('Install','ReadMe'):shutil.copyfile(ROOT/'release'/name,out/name)
    for build,name in ((a.cd32,'WingCommanderCD32.Slave'),(a.ocs,'WingCommander.Slave')):
        shutil.copyfile(build/name,out/name)
    report={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.iterdir())}
    (out/'package-check.json').write_text(json.dumps(dict(version='2.0b',date='19.10.2026',files=report,
        validation='static script structure and package/version checks; Amiga Installer not executed'),indent=2)+'\n')
    print('PASS: installer structure, version metadata, original assets and game-free staging')

if __name__=='__main__':main()
