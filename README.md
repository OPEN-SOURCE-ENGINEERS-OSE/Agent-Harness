<p align="center">
  <img src="brand/prama-logo.svg" alt="Prama — Ask. Verify. Know." width="420" />
</p>

<p align="center"><strong>Ask. Verify. Know.</strong><br />Answers you can check.</p>

> Prama comes from Sanskrit *pramāṇa*: a valid source of knowledge, or evidence.
> A P whose bowl is a lens, with the source at its centre.

Prama is a local research assistant with web search, direct chat, follow-up threads, source previews, and inline citations. The Next.js app proxies HTTP events from FastAPI on the same origin. The LangGraph workflow fetches Tavily results, caches them in Upstash Redis, retrieves related excerpts from Pinecone using BGE embeddings, and ranks the combined candidates with a BGE cross-encoder before Groq streams the response.
of the bowl. Do not recolor the amber dot, outline the wordmark, or place the primary lockup on a busy image.

## Run locally

Use Node.js 22+ and Python 3.11 or 3.12. Open two PowerShell terminals from the repository.

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set DEMO_MODE=true for the sample stream.
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --hostname 127.0.0.1
```

Open <http://127.0.0.1:3000>. Demo mode streams a fixed, labeled sample response. API configuration stays in the backend. Next.js uses `BACKEND_URL` when FastAPI runs at a different address.

## Enable live providers

Set `DEMO_MODE=false` in `backend/.env`.


## License

MIT. The Montserrat font is licensed under the SIL Open Font License; see `frontend/public/fonts/OFL.txt`.
