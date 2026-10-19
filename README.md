# AgentScout

**Agentic market intelligence.** Give it a business idea or product, and it researches your competitors, pulls market trends, and returns a structured report, all in a few minutes.

AgentScout is a multi-step LangGraph pipeline that combines web search, scraping, and an LLM-as-judge quality gate to produce reports you can actually trust (or it retries until they're good enough).

## Features

- **Query rewriting**: turns a rough user input into focused search queries
- **Parallel competitor research**: researches up to 5 competitors per run using Tavily (search) and Scrapling (scraping)
- **Market trend research**: separate branch for industry news and trends
- **Synthesis**: merges everything into one structured report
- **LLM-as-judge quality gate**: scores the report with structured JSON evaluation and loops back to retry if quality is too low
- **Async job system**: submit a job, get a UUID, poll for the result
- **Full report in under 4 minutes** for a typical run

## Architecture

```
User request
     │
     ▼
 FastAPI ──► TaskIQ (Redis queue) ──► Worker
                                         │
                                         ▼
                                 LangGraph pipeline
        ┌────────────────────────────────────────────────────┐
        │  rewrite query                                     │
        │       │                                            │
        │       ├──► competitor research (Scrapling + Tavily)│
        │       └──► market trends research                  │
        │                    │                               │
        │                    ▼                               │
        │               synthesize                           │
        │                    │                               │
        │                    ▼                               │
        │          LLM-as-judge quality gate ──(fail)──┐     │
        │                    │                         │     │
        │                 (pass)                  retry loop │
        └────────────────────┼─────────────────────────┘─────┘
                             ▼
                  PostgreSQL (job state + checkpoints)
```

The graph uses conditional edges for the retry loop, and state is checkpointed in PostgreSQL via `AsyncPostgresSaver`, so runs are resumable and inspectable.

## Tech Stack

| Layer | Tools |
|---|---|
| Orchestration | LangGraph, LangChain |
| LLM | Gemma via Cloudflare Workers AI |
| Search & scraping | Tavily, Scrapling |
| API | FastAPI, SlowAPI (rate limiting) |
| Task queue | TaskIQ + Redis |
| Database | PostgreSQL, SQLAlchemy (async) |
| Observability | LangSmith |
| Deployment | Docker / Docker Compose |
| Frontend | See `frontend/` |

## Project Structure

```
AgentScout/
├── backend/     # FastAPI app, LangGraph pipeline, TaskIQ worker
├── frontend/    # Web UI
└── README.md
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- API keys for Tavily, Cloudflare Workers AI, and (optionally) LangSmith

### 1. Clone the repo

```bash
git clone https://github.com/seif-gaaloul123/AgentScout.git
cd AgentScout
```

### 2. Configure environment variables

Create a `.env` file in `backend/` (never commit it):

```env
# LLM
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_API_KEY=your_api_key

# Search
TAVILY_API_KEY=your_tavily_key

# Database & queue
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/agentscout
REDIS_URL=redis://redis:6379

# Observability (optional)
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_TRACING=true
```

> Adjust variable names to match your actual `.env` / config file.

### 3. Run with Docker

```bash
docker compose up --build
```

This starts the API, the TaskIQ worker, PostgreSQL, and Redis.

### 4. Try it

```bash
# Submit a job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"query": "AI-powered CRM for small businesses"}'

# Poll for the result
curl http://localhost:8000/jobs/<job-uuid>
```

> Adjust endpoints to match your actual routes. Interactive docs are available at `http://localhost:8000/docs`.

## Design Decisions

- **No RAG / vector store.** An earlier version used FAISS. It was removed because live search and scraping give fresher data and the retrieval layer added complexity without improving reports.
- **LLM-as-judge with retry loop.** Instead of trusting the first draft, a judge node scores the output and sends it back through the pipeline when it falls short.
- **Async job queue.** Research runs take minutes, so the API returns a job UUID immediately and a TaskIQ worker does the heavy lifting.
- **Checkpointed state.** PostgreSQL checkpointing keeps the graph state durable across retries and failures.

## Known Limitations

- Free/limited LLM tiers hit rate limits quickly; API key rotation is used to work around this.
- Scraping depends on target sites' structure and anti-bot protections, so results vary.
- Worker concurrency defaults to 2 concurrent jobs.

## Roadmap

- [ ] Multi-provider LLM fallback
- [ ] Export reports to PDF
- [ ] Caching of competitor data between runs

## Author

**Seif Gaaloul**
Industrial Computer Engineering student, ENET'Com Sfax
GitHub: [@seif-gaaloul123](https://github.com/seif-gaaloul123)


Add a license (e.g. MIT) if you want others to reuse the code.
