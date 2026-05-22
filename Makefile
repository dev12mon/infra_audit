# Makefile
# Standardizes build and execution commands

IMAGE_NAME = infra-audit
TAG = latest

.PHONY: build run clean

build:
	@echo "Building Docker image: $(IMAGE_NAME):$(TAG)"
	docker build -t $(IMAGE_NAME):$(TAG) .

run:
	@echo "Running Docker container..."
	# --rm removes the container after it exits to keep the host clean
	docker run --rm $(IMAGE_NAME):$(TAG)

clean:
	@echo "Pruning unused Docker artifacts..."
	docker system prune -f