# ===============================
# Dockerfile for Chainlit + LangGraph demo
# ===============================
# 0. Remove previous images if any: 
#    docker rmi ifc-graph-builder_v0.1
# 1. docker build --platform linux/amd64 -t ifc-graph-builder_v0.1 .
# 2. docker images
# 3. docker save ifc-graph-builder_v0.1 | gzip > ifc-graph-builder_v0.1.tar.gz
# 4. Send to the client

FROM python:3.12-slim

WORKDIR /app

# 1. System dependencies (cmake, gcc, openssl headers, etc.)
RUN apt-get update && apt-get install -y \
    git curl cmake build-essential libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Install uv
RUN pip install --no-cache-dir uv

# 3. Copy your project
COPY . .

# 4. Install dependencies via uv (or pip fallback)
# If you have pyproject.toml and uv.lock, this is enough
RUN uv sync --frozen || uv pip install .

# 5. Expose Chainlit port
EXPOSE 8000

# 6. Run the app
CMD ["uv", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]