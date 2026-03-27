# Stage 1: Build the Next.js frontend
FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
RUN npm run build && ls -la .next/standalone/

# Stage 2: Python + Node runtime (in-memory Aerospike fallback)
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl supervisor nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY config.py ./
COPY agent/ ./agent/
COPY agents/ ./agents/
COPY server/ ./server/
COPY data/ ./data/
COPY docs/ ./docs/
COPY .overclaw/ ./.overclaw/

# Copy built frontend (standalone output)
COPY --from=frontend-build /app/frontend/.next/standalone ./frontend
COPY --from=frontend-build /app/frontend/.next/static ./frontend/.next/static
COPY --from=frontend-build /app/frontend/public ./frontend/public

# Copy supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/deepops.conf

# Frontend on 4000 (avoids potential port conflicts)
EXPOSE 4000

# Health check against the backend
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD curl -f http://127.0.0.1:8000/api/health || exit 1

ENV DEEPOPS_API_HOST=0.0.0.0
ENV DEEPOPS_API_PORT=8000
ENV DEEPOPS_ALLOW_IN_MEMORY_STORE=true

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/deepops.conf"]
