# Host cross-build of the reconstructed Legends of Valour slave (CFou! v1.0 has no public
# source; LegendsOfValourHD.s is rebuilt from its disassembly).  Not byte-identical to the
# shipped slave: kick13.s is the vendored 2025 copy (whdload/), the original used 2005's.
#   make            LegendsOfValour.Slave
#   make developer  independent performance switches, no verification instruments
#   make verify     same with -DVERIFY=1 (verification instruments; never ship)
WHDLOAD ?= $(HOME)/.local/share/amiga/WHDLoad
NDK ?= $(HOME)/.local/opt/m68k-amiga-elf/sys-include
# Use the verified project-local native build when present; explicit VASM still wins.
# Older installations retain their shared toolchain fallback.
VASM ?= $(if $(wildcard ../tmp/vasm-native-src/vasm/vasmm68k_mot),../tmp/vasm-native-src/vasm/vasmm68k_mot,$(HOME)/.local/vasmm68k_mot)
VASMFLAGS ?=

.PHONY: all developer verify clean FORCE
OUT ?= ../tmp/build
SLAVE = $(OUT)/LegendsOfValour.Slave
empty :=
space := $(empty) $(empty)
# Escape spaces for make targets; shell arguments are quoted separately below.
SLAVE_TARGET = $(subst $(space),\ ,$(SLAVE))
all: $(SLAVE_TARGET)

# Always assemble: options must not leave a stale variant.
$(SLAVE_TARGET): LegendsOfValourHD.s FORCE
	mkdir -p "$(OUT)"
	"$(VASM)" -m68000 -pic -x -devpac -Fhunkexe -nosym -L "$(OUT)/LegendsOfValour.lst" $(VASMFLAGS) -I. -I"$(WHDLOAD)/Include" -I"$(NDK)" -o "$(SLAVE)" "$<"

developer:
	$(MAKE) all VASMFLAGS="$(VASMFLAGS) -DDEVELOPER=1"

verify:
	$(MAKE) all VASMFLAGS="$(VASMFLAGS) -DVERIFY=1"

clean:
	rm -f "$(SLAVE)" "$(OUT)/LegendsOfValour.lst"
