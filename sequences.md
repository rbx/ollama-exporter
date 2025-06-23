# Ollama Exporter Sequence Diagrams

This document contains sequence diagrams showing the common flows in the Ollama Prometheus Exporter.

## 1. Metrics Endpoint Flow

```mermaid
sequenceDiagram
    participant Client as Prometheus
    participant Exporter as Ollama Exporter
    participant Metrics as Prometheus Client

    Client->>Exporter: GET /metrics
    Exporter->>Metrics: generate_latest()
    Metrics-->>Exporter: Prometheus format metrics
    Exporter-->>Client: Response with metrics (text/plain)
```

## 2. Non-Streaming Chat Request Flow

```mermaid
sequenceDiagram
    participant Client as Chat Client
    participant Exporter as Ollama Exporter
    participant Ollama as Ollama API
    participant Metrics as Prometheus Metrics

    Client->>Exporter: POST /api/chat (stream: false)
    Exporter->>Exporter: Extract model from request
    Exporter->>Metrics: Increment request counter
    Exporter->>Exporter: Clean headers (remove host, content-length)
    Exporter->>Ollama: POST /api/chat
    Ollama-->>Exporter: JSON response with metrics data
    Exporter->>Exporter: extract_and_record_metrics()
    Exporter->>Metrics: Record duration histograms
    Exporter->>Metrics: Record token counters
    Exporter-->>Client: Forward Ollama response
```

## 3. Streaming Chat Request Flow

```mermaid
sequenceDiagram
    participant Client as Chat Client
    participant Exporter as Ollama Exporter
    participant Ollama as Ollama API
    participant Metrics as Prometheus Metrics

    Client->>Exporter: POST /api/chat (stream: true)
    Exporter->>Exporter: Extract model from request
    Exporter->>Metrics: Increment request counter
    Exporter->>Exporter: Clean headers
    Exporter->>Ollama: POST /api/chat (streaming)

    loop For each chunk
        Ollama-->>Exporter: Stream chunk
        Exporter-->>Client: Forward chunk immediately
        Exporter->>Exporter: Try to parse chunk for final data
        alt If chunk contains "done": true
            Exporter->>Exporter: Store final_chunk_data
        end
    end

    Exporter->>Exporter: extract_and_record_metrics(final_chunk_data)
    Exporter->>Metrics: Record duration histograms
    Exporter->>Metrics: Record token counters
```

## 4. Generic Proxy Flow (All Other Endpoints)

```mermaid
sequenceDiagram
    participant Client as API Client
    participant Exporter as Ollama Exporter
    participant Ollama as Ollama API

    Client->>Exporter: Any HTTP method to /{path}
    Note over Client,Exporter: e.g., GET /api/tags, POST /api/generate
    Exporter->>Exporter: Clean headers (remove host, content-length)
    Exporter->>Ollama: Forward request to /{path}
    Ollama-->>Exporter: Response
    Exporter-->>Client: Forward response unchanged
    Note over Exporter: No metrics collected for non-chat endpoints
```

## Key Flow Characteristics

- **Transparent Proxy**: All non-chat requests pass through unchanged
- **Metrics Collection**: Only `/api/chat` requests have metrics extracted
- **Streaming Preservation**: Streaming responses are forwarded in real-time while collecting final metrics
- **Error Handling**: JSON parsing errors are silently ignored to maintain proxy transparency
- **Header Cleaning**: Host and content-length headers are removed before forwarding to prevent conflicts