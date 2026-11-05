"""Isolate extra native-ranking reads from the old distance probe."""
import inspect
import harness_a
src=inspect.getsource(harness_a.snapshot)
a=src.index('    def inactive(');b=src.index('    return dict(',a)
src=src[:a]+src[b:]
src=src.replace("                native_ranking=ranking,rank_displayed=ranking['displayed'],\n",'')
exec(src,harness_a.__dict__)
import check_a
check_a.main()
