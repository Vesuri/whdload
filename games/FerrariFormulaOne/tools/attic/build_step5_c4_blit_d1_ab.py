from pathlib import Path
import os,json
r=Path(__file__).resolve().parents[1]
os.environ['C1_ARCH']='000'
s=(r/'tools/build_step5_c1.py').read_text().replace('step5-c1','step5-c4-blit-d1-ab')
s=s.replace("'-m68'+arch,", "'-m68'+arch,'-DFF1_COARSE_NATIVE_000=1','-DFF1_NATIVE_000_STAGE=3','-DFF1_COARSE_200=1','-DFF1_COARSE_200_COMPLETE=1','-DFF1_PRODUCT_AB=1','-DFF1_DIV200_AB=1','-DFF1_NATIVEMUL200_AB=1','-DFF1_RESET200_AB=1','-DFF1_CROSS200_AB=1','-DFF1_ROOTLEAD_AB=1','-DFF1_SMALLROOT_AB=1','-DFF1_C4_BLIT_GUARD=1',")
# Explicit binding of the audited native signature/site table.
s=s.replace("('native',2,1)]", "('native',2,1),('baseline',0,0),('baseline-render',0,1)]")
s=s.replace("(o/(variant+'.slave')).write_bytes", "struct.pack_into('>H',b,size+symbols['C4Enabled'],1)\n struct.pack_into('>H',b,size+symbols['C4ResponseSkipEnabled'],1)\n struct.pack_into('>H',b,size+symbols['C4ReturnSkipEnabled'],1)\n struct.pack_into('>H',b,size+symbols['C4NativeHeading'],1)\n struct.pack_into('>H',b,size+symbols['FF1ProductControl'],0)\n struct.pack_into('>H',b,size+symbols['FF1Div200Control'],0)\n struct.pack_into('>H',b,size+symbols['FF1NativeMul200Control'],0)\n struct.pack_into('>H',b,size+symbols['FF1Reset200Control'],0)\n struct.pack_into('>H',b,size+symbols['FF1Cross200Control'],0)\n struct.pack_into('>H',b,size+symbols['FF1RootLeadControl'],0)\n struct.pack_into('>H',b,size+symbols['C4ProjectionSkipEnabled'],1)\n struct.pack_into('>H',b,size+symbols['FF1SmallRootControl'],0)\n struct.pack_into('>H',b,size+symbols['C4BlitEnabled'],0 if variant.startswith('baseline') else 1)\n struct.pack_into('>H',b,size+symbols['C3Enabled'],3)\n (o/(variant+'.slave')).write_bytes")
extra="data_candidates=[]\nfragment(symbols['FF1Track000Signature'],0x6977a,0x112,'lookahead signature')\nfragment(symbols['FF1Track000Signature']+0x112,0x67514,0x16,'lookahead caller signature')\nfragment(symbols['FF1Trig000Signature'],0x24fe0,64,'trig signature')\n"
t=(r/'tools/build_step5_b7_bindings.py').read_text()
displaced=t[t.index('# UpdateHooks deliberately'):t.index('# NativeExact')].replace("symbols['schedule_install']","symbols['FF1MultiplyU64_000']")
extra=displaced+extra
s=s.replace(repr('data_candidates=[]\n').replace("'", '"'),repr(extra))
s=s.replace('lea C1RecordBuffer(pc),a1',r'lea C1Record(pc),a1\n adda.w #((C1RecordBuffer-C1Record)/2),a1\n adda.w #((C1RecordBuffer-C1Record)-(C1RecordBuffer-C1Record)/2),a1')
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
