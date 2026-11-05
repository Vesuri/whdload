from pathlib import Path
import sys,json,subprocess,os
r=Path(__file__).resolve().parents[1];paths=[r/f'tmp/step5/c4-q03-render-profile-a1200-fast-h2-matched-{arm}' for arm in ['control','candidate']]
for p in paths:
 for script in ['analyze_render_profile.py','analyze_h2_blits.py']:subprocess.run([sys.executable,str(r/'tools'/script),str(p)],check=True,stdout=subprocess.DEVNULL)
a,b=[json.loads((p/'colour-analysis.json').read_text()) for p in paths];n=min(a['complete_draws'],b['complete_draws']);assert n>0
for i in range(n):
 x,y=a['draws'][i],b['draws'][i];assert x['planes']==y['planes'] and x['clip_shift']==y['clip_shift'],i
 assert x['cookie_blits']==y['cookie_blits']==len(x['planes']),i
 assert x['colour_blits']==len(x['planes']),i
 assert y['colour_blits']==sum(k not in [0,6] for k in y['planes']),i
stats=[json.loads((p/'render-analysis.json').read_text()) for p in paths];costs=[sum(j['draw_ms'][:n])/n for j in stats]
result=dict(status='passed',matched_draws=n,mean_draw_ms=dict(zip(['control','candidate'],costs)),colour_blits={arm:sum(x['colour_blits'] for x in j['draws'][:n]) for arm,j in zip(['control','candidate'],[a,b])},cookie_blits=sum(x['cookie_blits'] for x in a['draws'][:n]),exact_plane_and_clipping_sequences=True)
(r/'manifest/render-h2-matched-profile.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
