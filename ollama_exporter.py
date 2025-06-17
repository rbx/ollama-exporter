import os
import httpx
import json
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

import uvicorn
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Configurable Ollama host (via env variable or defaults to localhost)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

app = FastAPI()

OLLAMA_CHAT_REQUEST_COUNT = Counter("ollama_requests_total", "Total chat requests", ["model"])

OLLAMA_TOTAL_DURATION = Histogram("ollama_response_seconds", "Total time spent for the response", ["model"])
OLLAMA_LOAD_DURATION = Histogram("ollama_load_duration_seconds", "Time spent loading the model", ["model"])
OLLAMA_PROMPT_EVAL_DURATION = Histogram("ollama_prompt_eval_duration_seconds", "Time spent evaluating prompt", ["model"])
OLLAMA_PROMPT_EVAL_COUNT = Counter("ollama_tokens_processed_total", "Number of tokens in the prompt", ["model"])
OLLAMA_EVAL_DURATION = Histogram("ollama_eval_duration_seconds", "Time spent generating the response", ["model"])
OLLAMA_EVAL_COUNT = Counter("ollama_tokens_generated_total", "Number of tokens in the response", ["model"])
OLLAMA_TOKENS_PER_SECOND = Histogram("ollama_tokens_per_second", "Tokens generated per second", ["model"])

def extract_and_record_metrics(response_data, model):
    """Extract and record metrics from Ollama response data."""
    if not isinstance(response_data, dict):
        return

    # https://github.com/ollama/ollama/blob/main/docs/api.md#response
    total_duration = response_data.get("total_duration", 0) # total time spent in nanoseconds generating the response
    load_duration = response_data.get("load_duration", 0) # time spent in nanoseconds loading the model
    prompt_eval_duration = response_data.get("prompt_eval_duration", 0) # time spent in nanoseconds evaluating the prompt
    prompt_eval_count = response_data.get("prompt_eval_count", 0) # number of tokens in the prompt
    eval_duration = response_data.get("eval_duration", 0) # time spent in nanoseconds generating the response
    eval_count = response_data.get("eval_count", 0) # number of tokens in the response

    if total_duration > 0:
        total_duration_seconds = total_duration / 1_000_000_000
        OLLAMA_TOTAL_DURATION.labels(model=model).observe(total_duration_seconds)
    if load_duration > 0:
        load_duration_seconds = load_duration / 1_000_000_000
        OLLAMA_LOAD_DURATION.labels(model=model).observe(load_duration_seconds)
    if prompt_eval_duration > 0:
        prompt_eval_time_seconds = prompt_eval_duration / 1_000_000_000
        OLLAMA_PROMPT_EVAL_DURATION.labels(model=model).observe(prompt_eval_time_seconds)
    if prompt_eval_count > 0:
        OLLAMA_PROMPT_EVAL_COUNT.labels(model=model).inc(prompt_eval_count)
    if eval_duration > 0:
        eval_duration_seconds = eval_duration / 1_000_000_000
        OLLAMA_EVAL_DURATION.labels(model=model).observe(eval_duration_seconds)
    if eval_count > 0:
        OLLAMA_EVAL_COUNT.labels(model=model).inc(eval_count)
    if eval_duration > 0 and eval_count > 0:
        tps = eval_count / eval_duration * 1_000_000_000
        OLLAMA_TOKENS_PER_SECOND.labels(model=model).observe(tps)

@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/api/chat")
async def chat_with_metrics(request: Request):
    """Handle chat requests with streaming support and metrics extraction."""
    body = await request.json()
    model = body.get("model", "unknown")
    is_streaming = body.get("stream", False)

    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    headers.pop("content-type", None)

    OLLAMA_CHAT_REQUEST_COUNT.labels(model=model).inc()

    if is_streaming:
        async def generate_stream():
            async with httpx.AsyncClient(timeout=httpx.Timeout(900.0, read=900.0)) as client:
                async with client.stream("POST", f"{OLLAMA_HOST}/api/chat", headers=headers, json=body, params=request.query_params) as response:

                    final_chunk_data = None

                    async for chunk in response.aiter_bytes():
                        # Forward the chunk immediately to the client
                        yield chunk

                        # Try to parse the chunk to look for metrics
                        if chunk:
                            try:
                                chunk_text = chunk.decode('utf-8')
                                lines = chunk_text.strip().split('\n')

                                for line in lines:
                                    if line.strip():
                                        try:
                                            chunk_json = json.loads(line)
                                            # Check if this is the final chunk (contains "done": true)
                                            if chunk_json.get("done", False):
                                                final_chunk_data = chunk_json
                                        except json.JSONDecodeError:
                                            continue

                            except UnicodeDecodeError:
                                pass

                    # Extract metrics from the final chunk if available
                    if final_chunk_data:
                        extract_and_record_metrics(final_chunk_data, model)

        return StreamingResponse(generate_stream(), media_type="application/json")
    else:
        async with httpx.AsyncClient(timeout=httpx.Timeout(900.0, read=900.0)) as client:
            response = await client.post(f"{OLLAMA_HOST}/api/chat", headers=headers, json=body, params=request.query_params)

            if response.status_code == 200:
                try:
                    response_data = response.json()
                    extract_and_record_metrics(response_data, model)
                except (json.JSONDecodeError, TypeError):
                    pass

            return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def simple_proxy(request: Request, path: str):
    """Simple pass-through proxy for all other endpoints."""
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    async with httpx.AsyncClient(timeout=httpx.Timeout(900.0, read=900.0)) as client:
        response = await client.request(method=request.method, url=f"{OLLAMA_HOST}/{path}", headers=headers, content=await request.body(), params=request.query_params)

    return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
