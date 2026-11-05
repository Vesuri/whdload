# Included by every games/<Game>/Makefile. The game is the directory the Makefile is in.
# A game's Makefile may add its own targets after the include line.
COMMON := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))..)
GAME := $(notdir $(CURDIR))
export GAME
# Paths given on the command line (SLAVE=, ARCHIVES=) are relative to where make started.
CALLER_DIR ?= $(CURDIR)
export CALLER_DIR

.DEFAULT_GOAL := help
.PHONY: help slave verify developer build run stop unpack dist check record clean

help:
	@echo "$(GAME): make slave | verify | developer | build BUILD=name | run | stop | unpack ARCHIVES=dir | dist | check | record | clean"
	@echo "run: SETUP=name VARIANT=name BUILD=name SLAVE=original|path WHD_ARGS='...' DEBUG=1 INSTANCE=name (see common/run.sh)"

slave:
	@"$(COMMON)/build.sh" release
verify:
	@"$(COMMON)/build.sh" verify
developer:
	@"$(COMMON)/build.sh" developer
build:
	@"$(COMMON)/build.sh" "$(or $(BUILD),release)"
run:
	@"$(COMMON)/run.sh" run
stop:
	@"$(COMMON)/run.sh" stop
unpack:
	@"$(COMMON)/unpack.sh"
dist:
	@"$(COMMON)/dist.sh"
check:
	@"$(COMMON)/check.sh" game
record:
	@"$(COMMON)/check.sh" record
clean:
	@"$(COMMON)/build.sh" clean
