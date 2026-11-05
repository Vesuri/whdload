#!/usr/bin/env python3
"""Stage the combined installer in a fresh tmp directory; never include game data."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
from ocs_reconstruct import ROOT,new_output
from archives import verified


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
    installer=verified('installer')
    script=(ROOT/'release/Install').read_text(encoding='latin1');validate_script(script)
    readme=(ROOT/'release/ReadMe').read_bytes()
    assert readme==(ROOT/'release/ReadMe.OCS').read_bytes()
    assert b'Version 2.0b (19.10.2026)' in readme and b'Version 1.0 (11.01.2014)' in readme
    assert b'\n Wing Commander Enhanced 2.0b (19.10.2026)\n' in readme
    assert 'QuickDocED' not in script
    for variant,build,name in [('cd32',a.cd32,'WingCommanderCD32'),('ocs',a.ocs,'WingCommander')]:
        meta=json.loads((build/'build.json').read_text());slave=(build/(name+'.Slave')).read_bytes()
        assert meta['version']=='2.0b' and meta['release_date']=='19.10.2026'
        assert meta.get('release') if variant=='cd32' else meta.get('public_option')
        assert hashlib.sha256(slave).hexdigest()==meta['sha256']
        assert ('$VER: '+name+' 2.0b (19.10.2026)\0').encode() in slave
    out.mkdir(parents=True)
    # Extract the verified original afresh, retaining its exact member names.
    subprocess.run(['lha','xq',str(installer)],cwd=out,check=True)
    def hashes():
        return {str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted(out.rglob('*')) if f.is_file()}
    original=hashes()
    replacements={
        'WingCommanderHD/Install-WingCommander':ROOT/'release/Install',
        'WingCommanderHD/ReadMe':ROOT/'release/ReadMe',
        'WingCommanderHD/WingCommanderCD32.slave':a.cd32/'WingCommanderCD32.Slave',
        'WingCommanderHD/WingCommanderECS.slave':a.ocs/'WingCommander.Slave',
    }
    assert set(replacements)<=set(original)
    for name,source in replacements.items():shutil.copyfile(source,out/name)
    report=hashes()
    assert report.keys()==original.keys()
    assert {n for n in report if report[n]!=original[n]}==set(replacements)
    assert '(set #prefix-slave "WingCommanderECS")' in script
    assert '(source ("%s.slave" #icon_slave))' in script
    # Keep validation metadata outside the installer's original member list.
    out.with_name(out.name+'-package-check.json').write_text(json.dumps(dict(
        version='2.0b',date='19.10.2026',files=report,replacements=sorted(replacements),
        validation='exact original member list; four replacements; Amiga Installer not executed'),indent=2)+'\n')
    print('PASS: installer structure, version metadata, original assets and game-free staging')

if __name__=='__main__':main()
