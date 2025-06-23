# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Ollama Prometheus Exporter - a FastAPI-based proxy service that sits between Ollama clients and the Ollama API server to collect and expose Prometheus metrics about model usage, performance, and token statistics.

## Architecture

**Core Components:**
- `ollama_exporter.py` - Main FastAPI application that acts as a transparent proxy
- `/api/chat` endpoint - Intercepts chat requests to extract metrics from responses
- `/metrics` endpoint - Exposes Prometheus metrics in standard format
- Catch-all proxy - Forwards all other requests directly to Ollama without modification

**Key Design Patterns:**
- Transparent proxy pattern - All non-chat requests pass through unchanged
- Streaming response handling - Preserves Ollama's streaming chat responses while extracting final metrics
- Prometheus metrics collection - Uses standard Counter and Histogram metrics with model labels
- Environment-based configuration - Ollama host configurable via OLLAMA_HOST env var

## Development Commands

**Running locally:**
```bash
# Install dependencies (no requirements.txt, install manually)
pip install fastapi uvicorn prometheus_client httpx

# Run the service
python ollama_exporter.py
# Or with uvicorn directly:
uvicorn ollama_exporter:app --host 0.0.0.0 --port 8000
```

**Docker:**
```bash
# Build container
docker build -t ollama-exporter .

# Run container with custom Ollama host
docker run -d --name ollama-exporter -p 8000:8000 \
  -e OLLAMA_HOST="http://your-ollama-host:11434" ollama-exporter
```

**Testing:**
```bash
# Verify Python syntax
python -m py_compile ollama_exporter.py

# Test endpoints (requires running service)
curl http://localhost:8000/metrics
curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"model":"llama2","messages":[{"role":"user","content":"test"}]}'
```

## Metrics Collected

The service extracts timing and token metrics from Ollama's response metadata:
- `ollama_requests_total` - Request counter by model
- `ollama_response_seconds` - Total response duration
- `ollama_load_duration_seconds` - Model loading time
- `ollama_prompt_eval_duration_seconds` - Prompt evaluation time
- `ollama_tokens_processed_total` - Input token count
- `ollama_eval_duration_seconds` - Response generation time
- `ollama_tokens_generated_total` - Output token count
- `ollama_tokens_per_second` - Generation throughput

## Configuration

- `OLLAMA_HOST` environment variable sets the upstream Ollama server (default: http://localhost:11434)
- Service runs on port 8000 by default
- All timeouts set to 900 seconds for long-running model operations

## File Structure

- `ollama_exporter.py` - Single-file application containing all logic
- `Dockerfile` - Container build configuration
- `dashboard.json` / `dashboard_custom.json` - Grafana dashboard templates
- `README.md` - Installation and usage documentation