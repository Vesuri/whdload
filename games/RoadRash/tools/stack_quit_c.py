import sys,json,os
from harness_a import *
from stack_probe_c import stack_probe
s=Session(sys.argv[1])
try:
 route(s)
 result=dict(stack=stack_probe(s),stats=counters(s,stats_address(s)),provenance=provenance(os.environ['SLAVE'],s))
 if os.environ.get('RR_MMU_TEST'):assert result['stats']['mmu_tc']&0x8000,result
 s.cmd('monitor key 5f 1');s.cmd('monitor fields 99');s.cmd('monitor key 5f 0');s.cmd('monitor fields 99')
 result['after_help_registers']=s.cmd('info registers pc sp')
 (s.out/'quit.json').write_text(json.dumps(result,indent=2)+'\n')
 s.shot('after-help.png');print(result)
finally:s.quit()
