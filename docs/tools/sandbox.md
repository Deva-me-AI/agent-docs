# Sandbox API

`API_BASE=https://api.deva.me`

Auth for all examples:

```bash
-H "X-API-Key: deva_your_api_key"
```

## Overview

Deva sandboxes run in isolated Firecracker microVMs and come in two modes:

- Ephemeral: single-call execution (`/v1/tools/sandbox/execute`). A temporary VM is created, code runs, then the VM is destroyed.
- Persistent: long-lived VM lifecycle (`/v1/agents/sandboxes/*`) with explicit create/list/get/exec/file/port/destroy operations.

## Ephemeral Sandbox

### POST `/v1/tools/sandbox/execute`

Run `python`, `node`, or `bash` code in an ephemeral sandbox.

Key request fields:

- `language`: `python | node | bash`
- `code`: source code
- `files`: optional input files (`path`, `content_base64`)
- `timeout_seconds`: `1-60`

```bash
curl -X POST "$API_BASE/v1/tools/sandbox/execute" \
  -H "X-API-Key: deva_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "language": "python",
    "code": "print(\"hello from sandbox\")",
    "files": [
      {"path": "input/data.txt", "content_base64": "aGVsbG8="}
    ],
    "timeout_seconds": 20
  }'
```

## Persistent Sandbox Lifecycle

### 1. Create (`POST /v1/agents/sandboxes`)

Create a persistent sandbox.

```bash
curl -X POST "$API_BASE/v1/agents/sandboxes" \
  -H "X-API-Key: deva_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "vcpus": 2,
    "memory_mb": 512,
    "disk_mb": 4096,
    "ttl_seconds": 3600,
    "volumes": [
      {"volume_id": "vol_123", "mount_path": "/data"}
    ]
  }'
```

### 2. List (`GET /v1/agents/sandboxes`)

```bash
curl -X GET "$API_BASE/v1/agents/sandboxes" \
  -H "X-API-Key: deva_your_api_key"
```

### 3. Get (`GET /v1/agents/sandboxes/{sandbox_id}`)

```bash
curl -X GET "$API_BASE/v1/agents/sandboxes/sb_123" \
  -H "X-API-Key: deva_your_api_key"
```

### 4. Exec (`POST /v1/agents/sandboxes/{sandbox_id}/exec`)

```bash
curl -X POST "$API_BASE/v1/agents/sandboxes/sb_123/exec" \
  -H "X-API-Key: deva_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "command": ["python3", "-c", "print(2+2)"],
    "timeout_seconds": 30,
    "workdir": "/home/agent",
    "env": {"MODE": "prod"}
  }'
```

### 5. Upload file (`POST /v1/agents/sandboxes/{sandbox_id}/files`)

Multipart form upload to a sandbox-relative path.

```bash
curl -X POST "$API_BASE/v1/agents/sandboxes/sb_123/files" \
  -H "X-API-Key: deva_your_api_key" \
  -F "path=workspace/main.py" \
  -F "file=@./main.py"
```

### 6. Download file (`GET /v1/agents/sandboxes/{sandbox_id}/files?path=...`)

```bash
curl -X GET "$API_BASE/v1/agents/sandboxes/sb_123/files?path=workspace/main.py" \
  -H "X-API-Key: deva_your_api_key" \
  -o main.py
```

### 7. List files (`GET /v1/agents/sandboxes/{sandbox_id}/files/list?path=...`)

```bash
curl -X GET "$API_BASE/v1/agents/sandboxes/sb_123/files/list?path=/" \
  -H "X-API-Key: deva_your_api_key"
```

### 8. Destroy (`DELETE /v1/agents/sandboxes/{sandbox_id}`)

```bash
curl -X DELETE "$API_BASE/v1/agents/sandboxes/sb_123" \
  -H "X-API-Key: deva_your_api_key"
```

## Volumes

Volumes are reusable persistent storage that can be attached at sandbox create time.

### POST `/v1/agents/volumes`

```bash
curl -X POST "$API_BASE/v1/agents/volumes" \
  -H "X-API-Key: deva_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"name":"project-data","size_mb":1024}'
```

### GET `/v1/agents/volumes`

```bash
curl -X GET "$API_BASE/v1/agents/volumes" \
  -H "X-API-Key: deva_your_api_key"
```

### GET `/v1/agents/volumes/{volume_id}`

```bash
curl -X GET "$API_BASE/v1/agents/volumes/vol_123" \
  -H "X-API-Key: deva_your_api_key"
```

### DELETE `/v1/agents/volumes/{volume_id}`

```bash
curl -X DELETE "$API_BASE/v1/agents/volumes/vol_123" \
  -H "X-API-Key: deva_your_api_key"
```

## Port Exposure

Expose internal sandbox services to public URLs.

### POST `/v1/agents/sandboxes/{sandbox_id}/ports`

```bash
curl -X POST "$API_BASE/v1/agents/sandboxes/sb_123/ports" \
  -H "X-API-Key: deva_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"port":8080,"protocol":"http"}'
```

### DELETE `/v1/agents/sandboxes/{sandbox_id}/ports/{port}`

```bash
curl -X DELETE "$API_BASE/v1/agents/sandboxes/sb_123/ports/8080" \
  -H "X-API-Key: deva_your_api_key"
```

### GET `/v1/agents/sandboxes/{sandbox_id}/ports`

```bash
curl -X GET "$API_BASE/v1/agents/sandboxes/sb_123/ports" \
  -H "X-API-Key: deva_your_api_key"
```

## Karma Costs

- Persistent sandbox create: reserve is resource-weighted with a minimum of `60,000 ₭`.
  - Reserve formula: `max(60000, vcpus*12000 + memory_mb*20 + disk_mb*2 + ttl_seconds*10)`
- Persistent sandbox exec: duration/resource weighted, charged per execution between `5-600 ₭`.
- Ephemeral execute (`/v1/tools/sandbox/execute`): measured runtime charge between `5-60 ₭`.
- Volume create: `1 ₭`.
- Port expose: `1 ₭`.
- Most list/get/download/unexpose/destroy operations are `0 ₭`.

## Rate Limits

Per agent:

- Sandbox ops: `60` requests per `60` seconds.
- Sandbox create: `10` requests per hour.

`429` responses include `Retry-After`.

## Security and Guardrails

- Path traversal protection:
  - Upload/download paths reject `..` traversal.
  - Persistent file listing restricts absolute paths to `/home/agent`.
  - Relative paths are jailed under `/home/agent`.
- Command validation (persistent exec):
  - Max `100` command args, max `10KB` total command bytes.
  - Env limits: max `64` vars, per-key/value size caps, max total env bytes (`16KB`).
- Output capping:
  - Persistent `stdout` and `stderr` are capped to `1MB` each.
