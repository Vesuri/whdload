from pathlib import Path
src=Path('src');out=Path('tmp/build').resolve()
p=(src/'timing-runtime-present.i').read_text();old=' movea.l RT_DRAW_ENTRY(a0),a1\n movea.l RT_HUNKS+24(a0),a4\n jsr (a1)';assert p.count(old)==1
p=p.replace(old,' movea.l RT_HUNKS+8(a0),a1\n move.l $1c(a1),d0\n.wait_field:\n cmp.l $1c(a1),d0\n beq .wait_field')
(out/'no-draw-present.i').write_text(p)
c=(src/'timing-core.i').read_text().replace('"timing-runtime-present.i"',f'"{out}/no-draw-present.i"');(out/'no-draw-core.i').write_text(c)
s=(src/'GunshipHD.s').read_text().replace('"timing-core.i"',f'"{out}/no-draw-core.i"');(out/'no-draw.s').write_text(s)
