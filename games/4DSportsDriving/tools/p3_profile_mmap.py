"""Use the shared profile decoder without reading multi-GB traces into RAM."""
import inspect,mmap,os,runpy,sys
import _amigaxdev
from amigaxdev import barto
src=inspect.getsource(barto.load).replace("memoryview(open(path, 'rb').read())", "memoryview(_mmap_trace(path))")
def mapped(path):
 with open(path,'rb') as f:return mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
barto.__dict__['_mmap_trace']=mapped
exec(src,barto.__dict__)
kind=sys.argv.pop(1);sys.argv[0]='tools/profile_'+kind+'.py';runpy.run_path(sys.argv[0],run_name='__main__')
