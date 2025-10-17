# Edison

Edison is a prompt experimentation studio that helps teams rapidly design, evaluate, and refine LLM prompts with AI assistance and human-in-the-loop controls.

## Monorepo structure

- `backend/` — FastAPI service exposing the experimentation API and an async worker that processes queued jobs.
- `frontend/` — Next.js + Tailwind UI for building, executing, and reviewing experiments.
- `docker-compose.yml` — Local development stack with Postgres, API, worker, and web app containers.

## Getting started

### Requirements

- Python 3.11+
- Node.js 20+
- Docker (optional but recommended for full stack)

### Backend setup

```bash
cd backend
poetry install
cp .env.example .env
poetry run uvicorn app.main:app --reload
```

### Frontend setup

```bash
cd frontend
npm install
npm run dev
```

### Docker Compose

```bash
docker-compose up --build
```

The API is available at `http://localhost:8080/api/v1` and the UI at `http://localhost:3000`.

## Testing

```bash
cd backend
poetry run pytest
```

## License

MIT
