from pathlib import Path
import json,struct,re
r=Path(__file__).resolve().parents[1];out={}
for profile in ['a1200-fast','030-50','040-40','060-50']:
 p=r/f'tmp/step5/c4-q03-h7-live-{profile}-h7-baseline';d=json.loads((p/'result.json').read_text());assert d['status']=='passed'
 m=(p/'demo-entry.bin').read_bytes();u=lambda a:struct.unpack_from('>I',m,a)[0];e=u(4);g,h,node=struct.unpack_from('>III',m,e+84+6*12);timer=u(g+96+18);cia=u(g+42);name=u(cia+10)
 assert m[name:name+13]==b'ciab.resource'
 assert u(g+96+14)==g
 assert m[timer:timer+38]==bytes.fromhex('2c69002a2f0970044eaeffee225f4aa9003a661033fc804000dff09a33fc804000dff09c4e75')
 writes=[dict(zip(['pc','value','old','new','a1','a6','d0'],[int(x,16) for x in z])) for z in re.findall(r'pc=([0-9a-f]+) value=([0-9a-f]+) old=([0-9a-f]+) new=([0-9a-f]+) a1=([0-9a-f]+) a6=([0-9a-f]+) d0=([0-9a-f]+)',(p/'irq-native.log').read_text())]
 resets=[i for i,w in enumerate(writes) if w['value']==0x7fff and w['a1']==0xa1a1a1a1];assert len(resets)==1
 guest=writes[resets[0]+1:];assert len(guest)==(0 if profile=='a1200-fast' else 1)
 for w in guest:assert w['value']==0x8040 and timer<=w['pc']<timer+0x26 and w['a1']==g and w['a6']==cia
 assert node==g+118 and h==u(node+18)
 snapshots={k:hex(v['intena']) for k,v in d.items() if isinstance(v,dict) and 'intena' in v}
 assert set(snapshots.values())==({'0x67ac'} if profile=='a1200-fast' else {'0x67ec'})
 racing={k:d[k]['gfx_queue_heads'] for k in ['demo-entry','takeover','resumed-update','fresh-session-update','fresh-session-step21']};assert all(x==['0x0','0x0'] for x in racing.values())
 assert all(v['blit_server']==d['demo-entry']['blit_server'] for v in d.values() if isinstance(v,dict) and 'blit_server' in v)
 out[profile]={'timer_callback':hex(timer),'blit_server':hex(h),'graphics_base':hex(g),'enabling_writes':guest,'all_bit6_writes':writes,'snapshots':snapshots,'racing_queues':racing,'server_unchanged_through_lifecycle':True,'result':str((p/'result.json').relative_to(r))}
report={'status':'passed','profiles':out,'finding':'After the guest Kick reset, only030/040/060 execute graphics gb_timsrv: AbleICR(ciab.resource,4) disables ALRM, then an empty gb_blthd causes INTENA8040 and INTREQ8040.020 does not execute that startup callback in these runs. No further native bit6 writes through pause/tow/pit/menu/unload/re-entry. This is observed startup alarm delivery, not a fine-path CPU-selector policy.','logger_sha256':'42c8deb0b765a95ea99fe8d8e98cb3cc73e7252ac535880d0c8de95660865853','static_native_queue_audit':'manifest/step5-c4-blit-d1-queue-audit.json','scope':'Complete bit6-write logging from emulator boot through native lifecycle and fresh race, plus memory snapshots; not a universal claim about all future workloads.'}
(r/'manifest/render-h7-enabler.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS all four enabler/lifecycle audits')
