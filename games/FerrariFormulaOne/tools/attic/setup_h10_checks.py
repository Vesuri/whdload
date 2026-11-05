from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/run_h9_checks.py').read_text().replace('h9','h10')
s=s.replace("pair('states','a1200-fast'","pair('states','040-40-bce'").replace("pair('frames','a1200-fast'","pair('frames','040-40-bce'").replace("('timing','a1200-fast'","('timing','040-40-bce'")
a=s.index("elif group=='fps':");z=s.index("elif group=='tracecontrol'",a)
s=s[:a]+'''elif group=='fps':
 pair('fps','040-40-bce','grid','render-h10-grid')
 pair('fps','040-40-bce','dense','render-h10-dense')
 cases.append(('fps','060-50-bce','grid-candidate','render-h10-grid'))
 cases.append(('fps','030-50-bce','grid-candidate','render-h10-grid'))
 pair('fps','a1200-fast','normal','render-h10')
'''+s[z:]
(r/'tools/run_h10_checks.py').write_text(s)
s=(r/'tools/analyze_h9_trace.py').read_text().replace('h9-trace-hash','h10-trace-hash');(r/'tools/analyze_h10_trace.py').write_text(s)
