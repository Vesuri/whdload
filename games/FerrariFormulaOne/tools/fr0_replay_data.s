; FR0g replay data (appended after public_bindings).
 cnop 0,4
FR0ReplayFrames: dc.l 0
FR0UnsupportedCount: dc.l 0
FR0GenericCount: dc.l 0
FR0W: dc.w 0
FR0AM: dc.w 0
FR0BM: dc.w 0
FR0CM: dc.w 0
FR0DM: dc.w 0
 cnop 0,4
FR0G: ds.b 32
FR0Mask: ds.w 64
FR0ConstA: ds.w 64
FR0ConstC: ds.w 64
 cnop 0,16
FR0FillTab: incbin "FR0FillTab.bin"
 cnop 0,4
FR0BlitTab: incbin "FR0BlitTab.bin"
FR0BlitTabEnd:
 cnop 0,16
FR0Blob: incbin "FR0Blob.bin"
 cnop 0,16
FR0BlobInit: incbin "FR0Blob.bin"
FR0BlobInitEnd:
