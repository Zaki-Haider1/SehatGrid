FROM node:22-bookworm-slim AS web
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app/backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NODE_ENV=production
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY data/seed/ /app/data/seed/
RUN python scripts/preload_model.py
COPY --from=web /usr/local/bin/node /usr/local/bin/node
COPY --from=web /build/.next/standalone /app/frontend
COPY --from=web /build/.next/static /app/frontend/.next/static
COPY scripts/serve.py /app/serve.py
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 3000
CMD ["python", "/app/serve.py"]
