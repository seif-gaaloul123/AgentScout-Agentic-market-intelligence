# AgentScout

**Agentic market intelligence.** Describe a business idea or product, and AgentScout researches your competitors, pulls market trends, and returns a structured report in under 4 minutes.

## What it does

Give it a rough idea like *"AI-powered CRM for small businesses"*. AgentScout:

1. Rewrites the input into focused search queries
2. Researches up to **5 competitors in parallel** (Tavily for search, Scrapling for scraping)
3. Runs a separate branch for **market trends and industry news**
4. Synthesizes everything into one structured report
5. Scores the report with an **LLM-as-judge** and automatically retries if quality is too low

The whole thing runs as an async job: you submit a request, get a job ID back immediately, and poll for the result.

## How it works

```mermaid
flowchart TD
    U[User request] --> API[FastAPI]
    API -->|enqueue job| Q[(Redis / TaskIQ)]
    Q --> W[TaskIQ worker]
    W --> R[Rewrite query]
    R --> C[Competitor research<br/>Tavily + Scrapling]
    R --> T[Market trends research]
    C --> S[Synthesize report]
    T --> S
    S --> J{LLM-as-judge<br/>quality gate}
    J -->|fail| R
    J -->|pass| DB[(PostgreSQL<br/>job state + checkpoints)]
```

The pipeline is a LangGraph state graph with conditional edges for the retry loop. State is checkpointed in PostgreSQL with `AsyncPostgresSaver`, so runs are resumable and inspectable after a failure.

## Design decisions

- **LLM-as-judge instead of trusting the first draft.** A judge node returns structured JSON scores. If the report falls below the threshold, the graph loops back and tries again.
- **No RAG or vector store.** An earlier version used FAISS. I removed it: live search and scraping give fresher data, and the retrieval layer added complexity without improving the reports.
- **Async job queue.** Runs take minutes, so the API returns a job UUID right away and a TaskIQ worker does the heavy lifting.
- **Checkpointed state.** PostgreSQL checkpointing keeps graph state durable across retries and crashes.
- **Observability from the start.** Runs are traced with LangSmith, which made debugging node-level failures much easier.

## Tech stack

| Layer | Tools |
| --- | --- |
| Orchestration | LangGraph, LangChain |
| LLM | Gemma via Cloudflare Workers AI |
| Search and scraping | Tavily, Scrapling |
| API | FastAPI, SlowAPI (rate limiting) |
| Task queue | TaskIQ + Redis |
| Database | PostgreSQL, SQLAlchemy (async) |
| Observability | LangSmith |
| Deployment | Docker, Docker Compose |

## Getting started

**Prerequisites:** Docker and Docker Compose, plus API keys for Tavily, your LLM provider, and (optionally) LangSmith.

```bash
git clone https://github.com/seif-gaaloul123/AgentScout-Agentic-market-intelligence.git
cd AgentScout-Agentic-market-intelligence
```

Create `backend/.env` (never commit it):

```env
# LLM
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_API_KEY=your_api_key

# Search
TAVILY_API_KEY=your_tavily_key

# Database and queue
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/agentscout
REDIS_URL=redis://redis:6379

# Observability (optional)
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_TRACING=true
```

Start everything (API, worker, PostgreSQL, Redis):

```bash
docker compose up --build
```

## Usage

```bash
# Submit a job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"query": "AI-powered CRM for small businesses"}'

# Poll for the result
curl http://localhost:8000/jobs/<job-uuid>
```

Interactive API docs are available at `http://localhost:8000/docs`.

## Project structure

```
.
├── backend/     # FastAPI app, LangGraph pipeline, TaskIQ worker
├── frontend/    # Web UI
└── README.md
```

## Known limitations

- Free-tier LLM plans hit rate limits quickly, so the project rotates API keys to work around them.
- Scraping depends on each target site's structure and anti-bot protection, so results vary between runs.
- Worker concurrency defaults to 2 concurrent jobs.

## Roadmap

- [ ] Multi-provider LLM fallback
- [ ] Report export to PDF
- [ ] Caching of competitor data between runs

## Author

**Seif Gaaloul**, Industrial Computer Engineering student at ENET'Com Sfax.
[GitHub](https://github.com/seif-gaaloul123) · [LinkedIn](https://linkedin.com/in/seif-gaaloul)

## License

MIT. See [LICENSE](LICENSE).

