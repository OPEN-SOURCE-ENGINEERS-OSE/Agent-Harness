<p align="center">
  <img src="brand/prama-logo.svg" alt="Prama — Ask. Verify. Know." width="420" />
</p>

<p align="center"><strong>Ask. Verify. Know.</strong><br />Answers you can check.</p>

> Prama comes from Sanskrit *pramāṇa*: a valid source of knowledge, or evidence.
> A P whose bowl is a lens, with the source at its centre.

Prama is a local research assistant with web search, direct chat, follow-up threads, source previews, and inline citations. The Next.js app proxies HTTP events from FastAPI on the same origin. The LangGraph workflow fetches Tavily results, caches them in Upstash Redis, retrieves related excerpts from Pinecone using BGE embeddings, and ranks the combined candidates with a BGE cross-encoder before Groq streams the response.

## Brand

| Token | Value | Use |
| --- | --- | --- |
| Cream | `#F4F1E7` | Page and lockup background |
| Paper | `#FBF8EF` | Cards, composer, panels |
| Ink | `#14151D` | Type, mark, app icon |
| Amber | `#F5A800` | The source dot and primary actions |

The wordmark is **Montserrat SemiBold**, self-hosted at `frontend/public/fonts/Montserrat-Variable.ttf` (SIL Open Font License). The mark is drawn from the same geometry as the app icon, so the dot always sits at the centre of the bowl.

Assets live in [`brand/`](brand):

| File | Use |
| --- | --- |
| `prama-logo.svg` | Primary lockup on cream |
| `prama-logo-reversed.svg` | Lockup on ink |
| `prama-mark.svg` / `prama-mark-light.svg` | Transparent mark for light / dark surfaces |
| `prama-app-icon.svg` | App icon |
| `prama-mark-amber.svg` | One-colour mark on amber |
| `prama-favicon-32.svg` / `prama-favicon-16.svg` | Favicons |

Keep clear space around the mark equal to the height of the bowl. Do not recolor the amber dot, outline the wordmark, or place the primary lockup on a busy image.

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

| Feature | Setup |
| --- | --- |
| Web and chat | Set `GROQ_API_KEY`. Web search also needs `TAVILY_API_KEY`. The default Groq model is `openai/gpt-oss-20b`. [Groq streaming docs](https://console.groq.com/docs/text-chat) |
| Search cache | Set `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`. Search results expire after 15 minutes. |
| Vector retrieval | Create a dense, 384-dimensional, cosine Pinecone index. Set `PINECONE_API_KEY` and `PINECONE_HOST` to the index's data-plane host. New web results populate the `prama-web` namespace as searches run. |
| Reranking | Enabled by default. The BGE models are downloaded on first use. Set `ENABLE_RERANKING=false` to skip the cross-encoder. |
| Saved history | Apply the SQL migration in `supabase/migrations`, then set `SUPABASE_URL` and the server-side `SUPABASE_SECRET_KEY`. The dashboard's publishable key has a different role. [Supabase key docs](https://supabase.com/docs/guides/getting-started/api-keys) |

To apply the migration with the Supabase CLI from the repository root:

```powershell
supabase login
supabase init
supabase link --project-ref gjqyfvpyotqyqjftlpzx
supabase db push
```

History is scoped to a randomly generated browser session. Completed turns are also available in local browser storage. Run the app on localhost for personal use. Public deployment requires account authentication and abuse controls for paid API calls.

## License

MIT. The Montserrat font is licensed under the SIL Open Font License; see `frontend/public/fonts/OFL.txt`.
