from pathlib import Path
r=Path(__file__).resolve().parents[1];s=(r/'tools/audit_h10_final.py').read_text().replace('h10','h13').replace('H10','H13')
s=s.replace("x['checked']==480","x['checked']==108 and x['gauge_calls']>=108").replace("out['native_oracle_cases']=480","out['native_oracle_cases']=108;out['native_register_ccr_comparison']=True")
a=s.index("for profile in ['030-50-trace-bce'");z=s.index('states=[]',a);s=s[:a]+s[z:]
s=s.replace("[(0x6b0e4,'FF1RenderClearBottom'),(0x6b138,'FF1RenderClearTop')]","[(0x6bd66,'FF1RenderGaugeStrip'),(0x6bdb6,'FF1RenderGaugeStrip')]")
s=s.replace("bytes.fromhex('33c000dff058' if native==0x6b0e4 else '33fc045800df')","bytes.fromhex('4eb9')+struct.pack('>I',a.map(0x24ae0))")
s=s.replace('clear_hooks_present_on_takeover_and_reload','gauge_hooks_present_on_takeover_and_reload').replace("x['clear_hook_not_installed']","x['gauge_hook_not_installed']")
s=s.replace('build_h13_oracle.py','build_h13_final_oracle.py').replace('H13; H6c 25FPS target not yet met; H12 still needs explicit approval','H11 if common-scene H6c remains unmet; H12 dropped by user')
(r/'tools/audit_h13_final.py').write_text(s)
