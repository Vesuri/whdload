#!/usr/bin/env python3
"""Assemble reviewed TFX identities, full-span evidence and patch-site coverage."""
import map_symbols as m,json,re,csv,hashlib,bisect
P=m.OUT;src=m.ROOT/'src/TFXHD.s';text=src.read_text();target=m.load(m.GAME/'tfx.020')[0]['data'];beta=m.load(m.GAME/'TFX.040')
exact=json.loads((P/'exact-symbol-spans.json').read_text());byoff={x['target']:x for x in exact};maps=json.loads((P/'block-maps.json').read_text())
# Manual identities are semantic matches, not byte-equivalence or patch-ABI claims.
review={
0x38236:("@UseLevel",0,0x37992,"Entry aligned inside 1134-instruction block; level setup/teardown calls and globals match; relocation and branch operands differ."),
0x30b04:("@flight_computer",0,0x3027c,"Entry aligned inside 13274-instruction block, same control-flow and FPU operation sequence; global operands differ."),
0x4e53a:('MaskSprite_CPU_merge',0,0x4c116,'Internal CPU merge loop in _MaskSprite; aligned block at +2 and AND/OR mask loop. Local label; not a beta export.'),
0x3b93a:('_xSuperShapeView',0,0x3aac0,'Same shape handle decode (9-bit field), table lookup, globals $25ea/$25f0 and call to EmmGetAddress. Register allocation and length changed.'),
0x77c8:('aircraft_list_update_077c8',0,0x6f5c,'Whole aligned block, ending at @alien_move; beta has no entry symbol. Local name.'),
0x4bdca:('@SquareRoot',0,0x49a72,'Restoring integer sqrt: seed $40000000; subtract/test, OR result, shift by two; same result D0. Changed saved registers.'),
0x249a:('@AltFadeColsMiss',0,0x203e,'RGB triples; skips magenta ff/00/ff; blends each component with factor/50; sets palette-dirty flag $8020. Changed loop/register allocation.'),
0x4b774:('@MatrixAngleZ',0,0x4958e,'Matrix offsets 0,4,6,12,16; determinant term shifted 15 bits; same atan helper and negated result. Not MatrixAngleX/Y.'),
0x3f51e:('@EmmGetAddress',0,0x3e19e,'Handle indexed address lookup, same callers including _xSuperShapeView; inspected complete short routine.'),
0x3bc56:('@SuperShapeCall',0,0x3ad9a,'Same shape/global dispatch and parameter flow; changed register allocation.'),
0x3d032:('SuperShape_part_3d032',None,None,'Local function: object array at A4+$25ec, record size30 plus header16; shape table $25f0; part flags and indirect renderer calls. No recovered original entry name.'),
0x39cac:('viewport_scale_39cac',None,None,'Local function: viewport globals $2574/$2576/$2584/$2586; multiply/divide scale and horizon coordinates $ccfe/$cd06. No recovered original entry name.'),
0x7d54:('aircraft_iterator_07d54',0,0x74e8,'Whole aligned block; list head A4-9424; no beta entry symbol. Local label.'),
0x7d90:('aircraft_iterator_07d90',0,0x7524,'Whole aligned block; second list head A4-9224; no beta entry symbol. Local label.'),
}
# Exact spans recover Polygon and MakeScanTable even where linear decode swallowed entry.
rows=list(csv.DictReader((m.ROOT/'tmp/step5/strict1/routine-costs.csv').open()));hot=[]
for r in rows:
 if float(r['percent'])<.5:continue
 entry=r['start'];x=dict(profile_start=entry,profile_end=r['end'],profile_percent=float(r['percent']))
 if not entry.startswith('0x'):
  x.update(name=r['name'],evidence='External code: source listing for slave; captured asset code and call at $3816 for loaded image.',space='slave' if entry.startswith('slave') else 'loaded asset');hot.append(x);continue
 o=int(entry,16);x.update(space='game hunk 0',target=o)
 if o in review:
  name,h,bo,note=review[o];x.update(name=name,beta_hunk=h,beta_offset=bo,evidence=note,confidence='local descriptive label' if 'Local' in note or 'local' in note or h is None else 'reviewed semantic identity')
 elif o in byoff:x.update(byoff[o],confidence='exact relocation-masked symbol span')
 else:
  matches=[s for s in exact if s['target']<=o<s['target']+s['size']]
  assert matches,(entry,'missing hot mapping')
  s=min(matches,key=lambda s:s['size']);x.update(name=s['name']+'+'+hex(o-s['target']),beta_hunk=s['beta_hunk'],beta_offset=s['beta_offset']+o-s['target'],evidence='Inside exact relocation-masked symbol span',confidence='exact interior label')
 # Profile intervals may include multiple functions/data; never pretend whole interval is this name.
 x['symbols_inside_profile_region']=[{'offset':hex(s['target']),'name':s['name'],'span':s['size']} for s in exact if o<=s['target']<int(r['end'],16)]
 hot.append(x)

def patches(label):
 part=text.split('\n'+label+'\n')[1].split('PL_END\n')[0];out=[]
 for line in part.splitlines():
  line=line.split(';')[0].strip();mt=re.match(r'PL_(\w+)\s+\$([0-9a-fA-F]+),(.+)',line)
  if mt:
   op,o,tail=mt.groups();out.append(dict(op=op,source=int(o,16),tail=tail.strip()))
 return out
newpatch=patches('pl_fpu_new');oldpatch=patches('pl_020');audit=[]
# Missing 020 ports: function identity / logical counterpart only; preserve ABI warnings.
manual={
0x6b0ee:(0x6c4f2,"ScanFillDown","Exact beta symbol span and plain normalized block; plain normal_fill replacement absent."),
0x6b8e0:(0x4f840,'GouraudFill','ABI DIFFERENT: plain LINK a6 args y@10/table@12; target stack stream at SP+4 and y in A5. Port wrapper required.'),
0x4d6f0:(0x4f9f8,'_TextureFill','Changed C implementation; wrapper TextureFill at $4f9e4 calls this entry. Inspect scan record and stack args before port.'),
0x5ba1c:(0x55bec,'_texture_ptr','Geometry hunk6:$80 merged at $55b6c; data pointer cell; verify references, not instruction decode.'),
0x282b6:(0x1abfe,'frame_limit','SEMANTIC counterpart: MOVEQ #2,D0 then CMP D0,D1 at $1ac00; not an immediate word inside CMPI. Delta time moved from A4+500 to A4-$ba4.'),
0x16e8:(0x1830,'PlayLevel_update_1','Same site but delta-time global/ABI must be adapted; do not copy A4+500 from integer build.'),
0x1708:(0x1850,'PlayLevel_update_2','Same site but delta-time global/ABI must be adapted; do not copy A4+500 from integer build.'),
0x2dbf2:(0x1fec4,'@InsideZoomOut_divisor','Same DIVSL immediate30; clamp quotient guard is absent.'),
0x2caa2:(0x1ec38,'model_update_gate','Changed instructions/global: MOVE.B A4-$ba6,D0; SUBQ.B #1. Epilogue/register set differs; not drop-in skip_model.'),
0x594d6:(0x5efbe,'_DrawObjects_sort','Same instruction sequence; 32-byte replaced region through $5efde.'),
0x59556:(0x5f03e,'AddObject_sort_full','Same instruction sequence; 14-byte replaced region through $5f04c.'),
0x5642e:(0x5bf16,'_depth','Data: obcount=$5bf10, last index=$5bf12, depth=$5bf16, indices=$5c1ce (stride696). 348 slots.'),
0x4c4d8:(0x4e080,'ReadMouse_double_fire','Same MOVE.B keyboard-state synthesis site; replacement BRA +$24 lands at $4e0a6 and skips duplicate joystick synthesis.'),
}
for r in oldpatch:
 o=r['source'];x=dict(r)
 if o in manual:
  t,name,note=manual[o];x.update(target=t,name=name,evidence=note,status='missing port')
 else:
  candidates=[v for v in newpatch if v['op']==r['op'] and v['tail']==r['tail']]
  # find_click_box hook changed from PSS to PS and specialized helper.
  if o==0x42bbe:candidates=[dict(source=0x4385c)];note='Existing impatient-mode branch to $4391c; same fast_quit path.'
  elif o==0x46586:candidates=[dict(source=0x47d48)];note='Existing specialized find_click_box_020 hook; calling convention changed.'
  else:note='Existing pl_fpu_new counterpart; checked authoritative patch-list operation/helper.'
  assert candidates,('uncovered patch',r)
  targets=set(v['source'] for v in candidates)
  if len(targets)>1:
   anchor=maps['plain-0'].get(str(o),{}).get('target');assert anchor in targets,(r,targets);targets={anchor}
  assert len(targets)==1,(r,targets)
  x.update(target=targets.pop(),name=r['tail'].split(',')[0],evidence=note,status='already present')
 x['original_target_bytes']=target[x['target']:x['target']+12].hex();audit.append(x)
# CPU arithmetic list is a separate path and has repeated helper names: positional audit.
for a,b in zip(patches('pl_020_060'),patches('pl_fpu_new_060'),strict=True):
 assert a['op']==b['op'] and a['tail']==b['tail']
 audit.append(dict(a,target=b['source'],name=a['tail'].split(',')[0],status='already present / 060-specific',evidence='Authoritative paired 060 arithmetic patch lists; unchanged.',original_target_bytes=target[b['source']:b['source']+12].hex()))
(P/'hot-map.json').write_text(json.dumps(hot,indent=2));(P/'patch-map.json').write_text(json.dumps(audit,indent=2))
# CSV for Ghidra labels: reviewed hot labels and exact spans (symbols may be data, not all functions).
labels={s['target']:s['name'] for s in exact}
for x in hot:
 if x.get('space')=='game hunk 0':labels[x['target']]=x['name']
for x in audit:labels.setdefault(x['target'],x['name'].replace('$','value_'))
with (P/'symbols.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['offset','name'])
 for o,n in sorted(labels.items()):w.writerow([hex(o),n])
(P/'coverage.json').write_text(json.dumps(dict(hot_regions=len(hot),patch_rows=len(audit),unique_plain_sites=len(set(x['source'] for x in audit)),exact_symbol_spans=len(exact),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest()),indent=2))
print((P/'coverage.json').read_text())

extra=[0x4f840,0x4f9f8,0x5efba,0x5efe8,0x1abe6,0x62742,0x60002,0x6a438,0x4e018]
(P/'entries.txt').write_text(''.join(hex(o)+'\n' for o in sorted({x['target'] for x in hot if 'target' in x}|set(extra))))
fpu=[]
for o in [0x50f82,0x5169e,0x516b6,0x517a4,0x517f2,0x5183c]:
 match=[s for s in exact if s['target']<=o<s['target']+s['size']];assert len(match)==1
 fpu.append(dict(site=o,**match[0]))
(P/'fpu-map.json').write_text(json.dumps(fpu,indent=2))
