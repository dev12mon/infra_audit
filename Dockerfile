# ==========================================
# STAGE 1: Builder
# Compiles dependencies and generates wheels
# ==========================================
FROM python:3.11-slim as builder

# Install build dependencies (gcc, etc.) needed for compiling Python C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Copy only requirements to cache this layer
COPY requirements.txt .

# Build wheels for all dependencies to avoid installing build tools in final image
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r requirements.txt

# ==========================================
# STAGE 2: Runtime
# Minimal final image optimized for space and security
# ==========================================
FROM python:3.11-slim

# Set strict Python runtime configurations
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Create a non-root system user and group for security
RUN addgroup --system appgroup && \
    adduser --system --group appuser

WORKDIR /app

# Copy compiled wheels from the builder stage
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .

# Install the pre-compiled wheels (no build tools needed here)
RUN pip install --no-cache /wheels/*

# Copy application source code and set ownership to the non-root user
COPY --chown=appuser:appgroup . .

# Switch to the restricted user
USER appuser

# Execute the application
CMD ["python", "main.py"]