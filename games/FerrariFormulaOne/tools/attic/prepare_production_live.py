from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/test_step5_c4_q03_live.py').read_text()
s=s.replace("kind='modal-final'","kind='production-live'").replace("b=r/'tmp/build/step5-c4-divide-frame-r3g-v1-ab'/('000' if profile.startswith('a500') else '020')/(variant+'.slave')","b=r/'tmp/build/production/FerrariFormulaOne.slave'")
a=s.index(' import re\n');z=s.index(" cmd('delete')\n for failure",a)
s=s[:a]+''' import re
 build=json.loads((b.parent/'build.json').read_text());hs=build['host_symbols'];kind='000' if profile.startswith('a500') else '020' if profile=='a1200' else 'fine';module=build['payloads'][kind];sy=module['symbols'];host=marker-hs['FF1PublicMarker'];probe=host+module['offset']
 fine=kind=='fine'
 aliases={'C1Checkpoint':'schedule_end','C1Context':'schedule_context','C1Pause':'FF1FinePause','C1Resume':'FF1FineResume','C1Vbl':'schedule_vbl','C1Ledger':'public_patch_context','C1Completed':'schedule_completed'} if fine else {}
 def sym(text,n):return sy[aliases.get(n,n)]
 fine_listing='';host_listing=''
 report['probe']=hex(probe);report['kind']=kind
'''+s[z:]
s=s.replace("for failure in ('C1Fault','velocity_stop'):","for failure in (('velocity_stop','schedule_bad') if fine else ('C1Fault',)):")
s=s.replace("irq=probe-len((r/'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave').read_bytes()[32:-4])+sym(host_listing,'keyboard_start')","irq=host+hs['keyboard_start']")
s=s.replace("struct.unpack_from('>I',m,probe+sym(fine_listing,'C1Completed'))[0]","struct.unpack_from('>I',m,probe+sym(fine_listing,'C1Context')+24)[0]")
s=s.replace("struct.unpack_from('>H',m,probe+sym(fine_listing,'C4BlitOwned'))[0]","(struct.unpack_from('>H',m,probe+sy['C4BlitOwned'])[0] if kind=='000' else 0)")
s=s.replace("and paused['intena']&64","and (fine or kind=='020' or paused['intena']&64)")
s=s.replace("assert v[11:]==[0,0,0] and resume['owned']==64 and resume['completed']==paused['completed'] and not resume['intena']&64","assert v[11:]==[0,0,0] and resume['completed']==paused['completed']\n if kind=='000':assert resume['owned']==64 and not resume['intena']&64")
s=s.replace("until(probe+sym(fine_listing,'C1Exit'))\n until(native(0x65f48))","if fine:\n  until(probe+sy['public_loop_entry'],f'*(unsigned short*){native(0x66be0)} == 1')\n  until(native(0x6517a))\n else:\n  until(probe+sym(fine_listing,'C1Exit'))\n  until(native(0x65f48))")
s=s.replace("assert ex['owned']==0 and ex['intena']&64","assert ex['owned']==0\n if kind=='000':assert ex['intena']&64")
(r/'tools/test_production_live.py').write_text(s)
