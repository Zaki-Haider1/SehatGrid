# Deployment setup

Frontend configuration is Vercel (`frontend/` root, Node 22, `npm ci`, `npm run build`). Set private build variable `API_PROXY_TARGET` to the backend HTTPS origin so Next.js proxies `/api/v1`; do not expose backend secrets through `NEXT_PUBLIC_*`.

Backend configuration is a Docker Space on Hugging Face (`hank47/Hermes`). Build from the repository root using `backend/Dockerfile` because its context needs `data/seed/`. Configure the Space for port 7860 and set `PORT=7860`; the Dockerfile otherwise defaults to port 8000. The pinned embedding model is downloaded at image build.

Set Space variables/secrets: `JWT_SECRET` (32+ random characters), `DEMO_PASSWORD`, `DEMO_MODE=true`, `SEED_ON_START=true`, `DATABASE_URL`, `CORS_ORIGINS`, `APP_TIMEZONE=Asia/Karachi`, and `PORT=7860`. For AI, add `AI_API_KEY` as a secret and `AI_MODEL=qwen/qwen3.8-27b` as a variable. The API key stays in the backend.

SQLite on ephemeral Space storage may lose data after restart/rebuild; use persistent storage or PostgreSQL when records must survive. Free Space hardware can sleep. This document describes configuration only.

For local development use the [README](../../README.md). The root Dockerfile and `docker compose up --build` provide a combined local container with PostgreSQL.
