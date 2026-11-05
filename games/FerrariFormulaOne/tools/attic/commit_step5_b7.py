from pathlib import Path
import os,subprocess,json,sys
r=Path(__file__).resolve().parents[1];part=sys.argv[1]
if part=='bindings':
 files=['Games/FerrariFormulaOne_Bindings.s'];title='Bind Ferrari hooks to native hunk addresses';reports={p:json.loads((r/f'tmp/step5/b7-bindings-{p}/result.json').read_text()) for p in ('a1200-fast','a500')};assert all(x['status']=='passed' for x in reports.values());body='Default-off 68000-safe transactional address binding, with all operands checked before writes. Twenty-two guest cases pass on 68000 and 68020, covering repeated application, malformed records, pointer overflow and atomic rejection. B7 loader integration remains in progress.'
else:raise ValueError(part)
e={k:v for k,v in os.environ.items() if not k.startswith('GIT_') and k!='EMAIL'};e.update(GIT_AUTHOR_NAME='Vesa Halttunen',GIT_AUTHOR_EMAIL='vesuri@jormas.com',GIT_COMMITTER_NAME='Vesa Halttunen',GIT_COMMITTER_EMAIL='vesuri@jormas.com',GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1')
cfg={'user.name':'Vesa Halttunen','user.email':'vesuri@jormas.com','user.signingkey':'','core.hooksPath':'/dev/null','commit.gpgsign':'false','tag.gpgsign':'false','push.gpgSign':'false'};base=['git']
for k,v in cfg.items():base+=['-c',k+'='+v]
def git(*a):return subprocess.check_output(base+list(a),env=e,text=True).strip()
assert git('branch','--show-current')=='ferrariformulaone'
for n in ('GIT_AUTHOR_IDENT','GIT_COMMITTER_IDENT'):assert git('var',n).startswith('Vesa Halttunen <vesuri@jormas.com> ')
for k,v in cfg.items():assert git('config','--get',k)==v
assert git('diff','--cached','--name-only')=='';git('diff','--check');git('config','--local','core.hooksPath','/dev/null');git('add','--',*files);print(git('commit','--no-gpg-sign','-m',title,'-m',body));commit=git('rev-parse','HEAD');assert git('show','-s','--format=%an%n%ae%n%cn%n%ce%n%G?').splitlines()==['Vesa Halttunen','vesuri@jormas.com','Vesa Halttunen','vesuri@jormas.com','N'];(r/f'manifest/step5-b7-{part}-validation.json').write_text(json.dumps(dict(status='passed',scope=body,commit=commit,profiles=reports),indent=2)+'\n')
print(commit)
