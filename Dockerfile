# Stage 1: Build the Next.js frontend
FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
RUN npm run build

# Stage 2: Python + Node + Aerospike runtime
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl supervisor nodejs gnupg2 && \
    rm -rf /var/lib/apt/lists/*

# Install Aerospike Community Edition
RUN curl -fsSL https://artifacts.aerospike.com/aerospike-server-community/7.2.0.2/aerospike-server-community_7.2.0.2_tools-13.0.0_debian12_x86_64.tgz \
      -o /tmp/aerospike.tgz && \
    tar xzf /tmp/aerospike.tgz -C /tmp && \
    dpkg -i /tmp/aerospike-server-community_7.2.0.2_tools-13.0.0_debian12_x86_64/aerospike-server-community_*.deb || true && \
    apt-get -f install -y && \
    rm -rf /tmp/aerospike* && \
    mkdir -p /opt/aerospike/data

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy Aerospike config
COPY infra/aerospike/aerospike.conf /etc/aerospike/aerospike.conf

# Copy backend code
COPY config.py ./
COPY agent/ ./agent/
COPY agents/ ./agents/
COPY server/ ./server/
COPY data/ ./data/
COPY docs/ ./docs/
COPY .overclaw/ ./.overclaw/

# Copy built frontend (standalone output)
COPY --from=frontend-build /app/frontend/.next/standalone/frontend ./frontend
COPY --from=frontend-build /app/frontend/.next/static ./frontend/.next/static
COPY --from=frontend-build /app/frontend/public ./frontend/public

# Copy supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/deepops.conf

# Frontend on 4000 (avoids Aerospike port 3000 conflict)
EXPOSE 4000

# Health check against the backend
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD curl -f http://127.0.0.1:8000/api/health || exit 1

ENV DEEPOPS_API_HOST=0.0.0.0
ENV DEEPOPS_API_PORT=8000

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/deepops.conf"]
