# Makefile (project root)
SANDBOX_TAG ?= code-sandbox:py311

.PHONY: build-sandbox
build-sandbox:
	docker build -t $(SANDBOX_TAG) ./sandbox