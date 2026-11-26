import asyncio
import json
import logging
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from research import Query, Source, build_graph, generate, settings

log = logging.getLogger(__name__)
PERSISTENCE = bool(settings.supabase_url and settings.supabase_secret_key)


@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(timeout=httpx.Timeout(45, connect=10)) as client:
        app.state.client = client
        app.state.graph = None
        yield


app = FastAPI(title="Fieldwork", lifespan=lifespan)


def event(kind, payload):
    return f"event: {kind}\ndata: {json.dumps(payload)}\n\n"


async def database(method, **kwargs):
    response = await app.state.client.request(
        method, settings.supabase_url.rstrip("/") + "/rest/v1/research_turns",
        headers={"apikey": settings.supabase_secret_key}, **kwargs,
    )
    response.raise_for_status()
    return response


@app.get("/health")
async def health():
    return {"status": "ok", "demo": settings.demo_mode, "persistence": PERSISTENCE}


@app.get("/search")
async def history(thread: UUID | None = None, x_session_id: UUID = Header()):
    if not PERSISTENCE:
        return []
    params = {"session_id": f"eq.{x_session_id}", "order": "created_at.desc", "limit": 100,
              "select": "id,thread_id,question,answer,sources,created_at"}
    if thread:
        params["thread_id"] = f"eq.{thread}"
    try:
        return (await database("GET", params=params)).json()
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Saved history is unavailable.") from exc


@app.post("/search")
async def search(query: Query, thread: UUID, x_session_id: UUID = Header()):
    query.question = query.question.strip()
    if not query.question:
        raise HTTPException(422, "Enter a question.")
    if not settings.demo_mode and (not settings.groq_api_key or (query.mode == "web" and not settings.tavily_api_key)):
        raise HTTPException(503, "Configure the Groq and web search credentials, or enable demo mode.")

    async def stream():
        yield event("status", {"message": "Finding relevant sources" if query.mode == "web" else "Preparing answer"})
        try:
            sources = []
            if settings.demo_mode:
                if query.mode == "web":
                    sources = [Source(url="https://docs.tavily.com/documentation/api-reference/endpoint/search",
                                      title="Tavily search API", content="Returns relevant web search results."),
                               Source(url="https://console.groq.com/docs/text-chat", title="Groq text generation",
                                      content="Supports streaming model completions.")]
            elif query.mode == "web":
                if app.state.graph is None:
                    app.state.graph = build_graph(app.state.client)
                context = query.history[-1].question[:160] + " " if query.history else ""
                result = await app.state.graph.ainvoke({"query": (context + query.question)[:400]})
                sources = result["sources"]
            public = [source.model_dump(mode="json") for source in sources]
            yield event("sources", public)
            yield event("status", {"message": "Writing answer"})
            answer = ""
            if settings.demo_mode:
                answer = ("**Demo mode**\n\nThis sample shows how Fieldwork streams an answer."
                          " Live responses require provider credentials.")
                if sources:
                    answer += "\n\nTavily supplies web results [1], and Groq streams the answer [2]."
                for word in answer.split(" "):
                    yield event("token", {"text": word + " "})
                    await asyncio.sleep(0.022)
            else:
                async for token in generate(app.state.client, query, sources):
                    answer += token
                    yield event("token", {"text": token})
                if not answer.strip():
                    raise RuntimeError("The model did not return an answer")
            saved = False
            if PERSISTENCE and not settings.demo_mode:
                try:
                    await database("POST", json={"id": str(uuid4()), "session_id": str(x_session_id),
                                                  "thread_id": str(thread), "question": query.question,
                                                  "answer": answer, "sources": public})
                    saved = True
                except httpx.HTTPError:
                    yield event("status", {"message": "Supabase could not save this answer. It is available in this browser."})
            yield event("done", {"persisted": saved})
        except Exception as exc:
            log.error("Research pipeline failed: %s", type(exc).__name__)
            yield event("error", {"message": "The answer could not finish. Try again in a moment."})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})
