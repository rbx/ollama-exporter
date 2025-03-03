# Ollama Prometheus Exporter

This is a **Prometheus Exporter** for **Ollama**, designed to monitor request statistics, response times, token usage, and model performance. It runs as a FastAPI service and is **Docker-ready**.

## Features
- **Tracks requests per model** (`ollama_requests_total`)
- **Measures response time** (`ollama_response_seconds`)
- **Monitors token usage** (`ollama_tokens_generated_total`)
- **Records evaluation steps** (`ollama_eval_total`)
- **Tracks model load times** (`ollama_load_time_seconds`)
- **Exposes `/api/tags` to list available models**

## Installation

### Running Locally

#### 1. Install Dependencies
```sh
pip install fastapi uvicorn prometheus_client httpx
```

#### 2. Run the Exporter
```sh
python ollama_exporter.py
```
By default, it connects to `http://localhost:11434` for Ollama.

### Running with Docker

#### 1. Build the Docker Image
```sh
docker build -t ollama-exporter .
```

#### 2. Run the Container
```sh
docker run -d --name ollama-exporter -p 8000:8000 \
  -e OLLAMA_HOST="http://192.168.1.100:11434" ollama-exporter
```

## Prometheus Integration

### Add to `prometheus.yml`
```yaml
scrape_configs:
  - job_name: 'ollama-metrics'
    static_configs:
      - targets: ['192.168.1.100:8000']
```
Restart Prometheus to apply changes:
```sh
docker restart <prometheus-container-name>
```

## Metrics
| Metric Name | Description |
|------------|-------------|
| `ollama_requests_total` | Total number of requests per model |
| `ollama_response_seconds` | Response time in seconds |
| `ollama_tokens_generated_total` | Number of tokens generated |
| `ollama_eval_total` | Number of evaluation steps |
| `ollama_load_time_seconds` | Time taken to load models |

## Grafana Integration
1. Open **Grafana**.
2. Go to **Explore**, select **Prometheus** as the data source.
3. Query example:
   ```
   ollama_requests_total
   ```
4. Create a new dashboard and add visualizations for these metrics.

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/metrics` | GET | Exposes Prometheus metrics |
| `/api/generate` | POST | Proxies requests to Ollama and logs metrics |
| `/api/tags` | GET | Lists available models |

## License
You don't need one.
