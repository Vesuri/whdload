# Host cross-build of the reconstructed Legends of Valour slave (CFou! v1.0 has no public
# source; LegendsOfValourHD.s is rebuilt from its disassembly).  Not byte-identical to the
# shipped slave: kick13.s is the vendored 2025 copy (whdload/), the original used 2005's.
#   make            LegendsOfValour.Slave
#   make verify     same with -DVERIFY=1 (verification instruments; never ship)
WHDLOAD ?= $(HOME)/.local/share/amiga/WHDLoad
NDK ?= $(HOME)/.local/opt/m68k-amiga-elf/sys-include
VASM ?= $(HOME)/.local/vasmm68k_mot
VASMFLAGS ?=

.PHONY: all verify clean FORCE
OUT ?= ../tmp/build
SLAVE = $(OUT)/LegendsOfValour.Slave
all: $(SLAVE)

# Always assemble: options must not leave a stale variant.
$(SLAVE): LegendsOfValourHD.s FORCE
	mkdir -p "$(OUT)"
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym -L $(@:.Slave=.lst) $(VASMFLAGS) -I. -I"$(WHDLOAD)/Include" -I"$(NDK)" -o $@ $<

verify:
	$(MAKE) all VASMFLAGS="$(VASMFLAGS) -DVERIFY=1"

clean:
	rm -f "$(SLAVE)" "$(OUT)/LegendsOfValour.lst"
