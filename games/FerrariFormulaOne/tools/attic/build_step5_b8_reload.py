from pathlib import Path
import ast
r=Path(__file__).resolve().parents[1]
old=ast.parse((r/'tools/build_step5_b7_reload_v3.py').read_text())
patch=next(ast.literal_eval(n.value) for n in old.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='patch' for t in n.targets))
node=ast.parse(patch).body[0]
fixture=ast.literal_eval(node.value.args[1]).replace('FF1PresentationAfterTick:', 'B8ReloadFixture:',1)
rest='\n'.join(patch.splitlines()[patch.splitlines().index(' rts""")')+1:])
extra="s=s.replace(' bsr.l B8PoseTick', ' bsr.l B8ReloadFixture\\n bsr.l B8PoseTick',1)\ns+='\\n'+"+repr(fixture)+"\n"+rest
s=(r/'tools/build_step5_b8_source.py').read_text().replace('step5-b8-v3-source','step5-b8-v3-reload')
s=s.replace('exec(compile(s,',"s=s.replace(\"(o/'reset.bin').write_bytes\", "+repr(extra)+"+\"\\n(o/'reset.bin').write_bytes\",1)\nexec(compile(s,",1)
exec(compile(s,str(r/'tools/build_step5_b8_source.py'),'exec'))
