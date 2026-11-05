"""Explicit emulated machines; profiling mode is a capability, not a speed claim."""
import os,shutil
PROFILES={
 'a500':('A500','68000',512,0,1536,0,'trace'),
 'a500-fast':('A500','68000',512,2048,0,0,'trace'),
 'a1200-020':('A1200','68EC020',2048,4096,0,0,'trace'),
 'a1200-030-50':('A1200','68030',2048,4096,0,50000000,'swaps'),
 'a4000-040-25':('A4000','68040-NOMMU',2048,8192,0,25000000,'swaps'),
 'a4000-040-40':('A4000','68040-NOMMU',2048,8192,0,40000000,'swaps'),
 'a4000-060-50':('A4000','68060-NOMMU',2048,8192,0,50000000,'swaps'),
}
def environment(name,slave,custom4=0):
 model,cpu,chip,fast,slow,hz,mode=PROFILES[name]
 e=dict(os.environ,AMIGA_MODEL=model,CPU=cpu,CHIP_KB=str(chip),FAST_KB=str(fast),SLOW_KB=str(slow),FSUAE=os.environ.get('PROFILE_FSUAE',shutil.which('fs-uae')),SLAVE=str(slave),WHD_ARGS=f'CUSTOM4={custom4}',JOY0='none',JOY1='none',DETERMINISTIC='1',WARP='1',WINDOW='none',WAIT_FOR_EXIT='0',SWAP_ONLY='1' if mode=='swaps' or os.environ.get('SWAP_ONLY')=='1' else '0',SERVE_WAIT=os.environ.get('SERVE_WAIT','600' if mode=='swaps' else '300'))
 for k in ['BOOT_BREAK','START_STOPPED','EXTRA_ARGS','JOY0_MODE','JOY1_MODE']:e.pop(k,None)
 if model!='A500':e['KICKSTART']=os.environ['KICKSTART_A1200']
 e['EXTRA_ARGS']='' if not hz else f'--uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency={hz} --uae_cpu_cycle_exact=true'
 # A4000's model default includes 8 MiB motherboard Fast RAM; retain it explicitly.
 e['MOTHERBOARD_KB']='8192' if model=='A4000' else '0'
 e['EXTRA_ARGS']+=' --uae_a3000mem_size='+('8' if model=='A4000' else '0')
 return e

def banks(e):
 return [(name,base,int(e[key])*1024) for name,base,key in [('chip',0,'CHIP_KB'),('fast',0x200000,'FAST_KB'),('slow',0xc00000,'SLOW_KB'),('motherboard',0x7800000,'MOTHERBOARD_KB')] if int(e[key])]
