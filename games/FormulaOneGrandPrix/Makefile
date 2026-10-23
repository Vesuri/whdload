SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: help check
help:
	@echo 'make check; make slave / slave-developer / slave-verify; make check-disabled CAPTURE=tmp/...; make slave-clean OUT=tmp/...'
check:
	shasum -a 256 -c manifest/SHA256SUMS

.PHONY: slave
slave:
	@BUILD=release OUT="$(or $(OUT),tmp/build)" /bin/bash whdload/build.sh

.PHONY: slave-developer slave-verify check-disabled
slave-developer:
	@BUILD=developer OUT="$(or $(OUT),tmp/build-developer)" /bin/bash whdload/build.sh
slave-verify:
	@BUILD=verify OUT="$(or $(OUT),tmp/build-verify)" /bin/bash whdload/build.sh
check-disabled:
	@python3 tools/check_disabled.py "$(CAPTURE)"

.PHONY: slave-clean test-disabled
slave-clean:
	@CLEAN=1 OUT="$(or $(OUT),tmp/build)" /bin/bash whdload/build.sh
test-disabled:
	@python3 tools/test_disabled.py
