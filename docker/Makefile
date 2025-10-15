.PHONY: all build tag push clean prune help

# Image configuration
IMAGE_NAME := openpi-training

# Extract version from pyproject.toml
VERSION := $(shell grep '^version = ' ../pyproject.toml | sed 's/version = "\(.*\)"/\1/')

# Get git commit SHA (short)
GIT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Registry URL - can be overridden via environment variable or command line
# Example: make push REGISTRY_URL=cr.eu-north1.nebius.cloud/e00a0ahqzcp9x0xczz
REGISTRY_URL ?= cr.eu-north1.nebius.cloud/e00a0ahqzcp9x0xczz

# Image tags
TAG_LATEST := $(REGISTRY_URL)/$(IMAGE_NAME):latest
TAG_VERSION := $(REGISTRY_URL)/$(IMAGE_NAME):v$(VERSION)
TAG_SHA := $(REGISTRY_URL)/$(IMAGE_NAME):$(GIT_SHA)
LOCAL_TAG := $(IMAGE_NAME):local

help:
	@echo "OpenPI Training Container - Makefile"
	@echo ""
	@echo "Configuration:"
	@echo "  Image Name:     $(IMAGE_NAME)"
	@echo "  Version:        $(VERSION)"
	@echo "  Git SHA:        $(GIT_SHA)"
	@echo "  Registry URL:   $(REGISTRY_URL)"
	@echo ""
	@echo "Targets:"
	@echo "  make build      Build the training image with baked source code"
	@echo "  make tag        Tag the image (depends on build)"
	@echo "  make push       Push all tags to registry (depends on tag)"
	@echo "  make all        Build, tag, and push (alias for push)"
	@echo "  make clean      Remove local training images"
	@echo "  make prune      Remove dangling/unused Docker images"
	@echo "  make help       Show this help message"
	@echo ""
	@echo "To override registry URL:"
	@echo "  make push REGISTRY_URL=your-registry-url"

build:
	@echo "Building $(IMAGE_NAME) with source code baked in..."
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: Could not extract version from pyproject.toml"; \
		exit 1; \
	fi
	docker build -f Dockerfile.training.cloud -t $(LOCAL_TAG) ..

tag: build
	@echo "Tagging image with multiple tags..."
	@if [ -z "$(REGISTRY_URL)" ]; then \
		echo "Error: REGISTRY_URL is not set."; \
		echo "Please set it via: make push REGISTRY_URL=your-registry-url"; \
		exit 1; \
	fi
	docker tag $(LOCAL_TAG) $(TAG_LATEST)
	docker tag $(LOCAL_TAG) $(TAG_VERSION)
	docker tag $(LOCAL_TAG) $(TAG_SHA)
	@echo "Tagged with:"
	@echo "  - $(TAG_LATEST)"
	@echo "  - $(TAG_VERSION)"
	@echo "  - $(TAG_SHA)"

push: tag
	@echo "Pushing images to Container Registry..."
	docker push $(TAG_LATEST)
	docker push $(TAG_VERSION)
	docker push $(TAG_SHA)
	@echo ""
	@echo "Successfully pushed to Container Registry!"
	@echo "Pull with:"
	@echo "  docker pull $(TAG_LATEST)"

all: push

clean:
	@echo "Removing local training images..."
	-docker rmi $(LOCAL_TAG)
	-docker rmi $(TAG_LATEST)
	-docker rmi $(TAG_VERSION)
	-docker rmi $(TAG_SHA)
	@echo "Local images removed."

prune:
	@echo "Pruning dangling and unused Docker images..."
	docker image prune -f
	@echo "Prune complete."
