"""Read Barto captures with explicit one-field gaps at joins without duplicating their large binary data."""
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
class Series:
    def __init__(self, paths):
        self.traces=[barto.load(p) for p in paths]
        self.chip=self.traces[0].chip
        self.fields=[];self.owner={};self.gap_fields=set()
        self.gap_size=1
        for t in self.traces:
            if self.fields:self.gap_fields.add(len(self.fields))
            for f in t.fields:
                f.index=len(self.fields);self.fields.append(f);self.owner[id(f)]=t
    def instructions(self,f):return self.owner[id(f)].instructions(f)
