async function forward(request: Request) {
  const backend = process.env.BACKEND_URL || "http://127.0.0.1:8000";
  try {
    const response = await fetch(backend + "/search" + new URL(request.url).search, {
      method: request.method,
      headers: { "content-type": "application/json", "x-session-id": request.headers.get("x-session-id") || "" },
      body: request.method === "POST" ? await request.text() : undefined,
      signal: request.signal,
      cache: "no-store",
    });
    return new Response(response.body, { status: response.status, headers: {
      "content-type": response.headers.get("content-type") || "application/json",
      "cache-control": "no-store, no-transform",
      "x-accel-buffering": "no",
    } });
  } catch {
    return Response.json({ detail: "The research backend is unavailable. Start FastAPI and try again." }, { status: 503 });
  }
}
export { forward as GET, forward as POST };