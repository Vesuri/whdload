# Try any installed WHDLoad archive without a games/<Game> directory: download it here (or
# pass ARCHIVE=<file>) and `make run SETUP=a1200-040`. Options: common/try.sh, common/run.sh.
SHELL := /bin/bash
COMMON := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))../common)
# Paths given on the command line (ARCHIVE=, SLAVE=) are relative to where make started.
CALLER_DIR ?= $(CURDIR)
export CALLER_DIR

.DEFAULT_GOAL := help
.PHONY: help run stop unpack list serve server clean

help:
	@echo 'make run [ARCHIVE=file] [VARIANT=name] SETUP=name WHD_ARGS=... DEBUG=1 ...   newest archive here by default'
	@echo 'make list | unpack | stop | clean'
	@echo "make serve [...]; make server CMD='shot tmp/x.png' | CMD='wait 5' | CMD=quit   the gdb-stub server"
run stop unpack list:
	@"$(COMMON)/try.sh" $@
serve:
	@"$(COMMON)/try.sh" server serve
server:
	@[ -n "$(CMD)" ] || { echo "make server CMD='<command>'" >&2; exit 1; }
	@"$(COMMON)/try.sh" server $(CMD)
clean:
	rm -rf tmp
