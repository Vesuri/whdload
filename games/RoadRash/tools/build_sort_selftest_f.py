from pathlib import Path
import shutil,random
src=Path('tmp/f-sort-selftest-source');shutil.copytree('src',src)
rng=random.Random(1234)
cases=[[9]*12,list(range(62,-1,-1)),list(range(63)),[3,1,3,1,2,2],[1],[0x7fff0000,0x80000000,0,0xffff0000]]
cases += [[rng.randrange(0,8)*65536+rng.randrange(3) for i in range(n)] for n in [4,32,32,2,63,64,5,5]]
s='\nf_sort_test:\n movem.l d0-d7/a0-a6,-(a7)\n'
for j,keys in enumerate(cases):
 s+=f' lea f_test_in{j}(pc),a0\n lea f_test_out{j}(pc),a1\n lea f_test_ids{j}(pc),a2\n bsr f_sort\n'
s+=' movem.l (a7)+,d0-d7/a0-a6\n rts\n'
for j,keys in enumerate(cases):s+=f'f_test_in{j}: dc.l '+','.join('$%08x'%k for k in keys+[0xffffffff])+f'\nf_test_out{j}: ds.l {len(keys)+1}\nf_test_ids{j}: ds.w {len(keys)+1}\n even\n'
p=src/'cpu_work.s';p.write_text(p.read_text().replace(' bsr.w f_sort_init',' bsr.w f_sort_init\n bsr f_sort_test',1)+s)
import json
Path('tmp/f-sort-selftest-cases.json').write_text(json.dumps(cases))
