SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: help check
help:
	@echo 'F1GP setup only. make check verifies the original downloaded archives.'
check:
	shasum -a 256 -c manifest/SHA256SUMS
