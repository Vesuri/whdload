SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: help check
help:
	@echo 'make check: verify archives; make slave: build the reconstructed loader in tmp/.'
check:
	shasum -a 256 -c manifest/SHA256SUMS

.PHONY: slave
slave:
	@/bin/bash whdload/build.sh
