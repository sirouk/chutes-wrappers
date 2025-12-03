# Chutes Wrappers

A toolkit for wrapping Docker images and deploying them on [Chutes.ai](https://chutes.ai).

## Overview

This repo provides:

- **`deploy.sh`** - Interactive CLI for building, testing, and deploying chutes
- **`tools/chute_wrappers.py`** - Helper functions for wrapping Docker images
- **`tools/discover_routes.py`** - Auto-discovers HTTP routes from running containers
- **`deploy_example.py`** - Template for creating new wrapped chutes

## Quick Start

### 1. Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install chutes httpx requests loguru

# Register with Chutes (creates ~/.chutes/config.ini)
chutes register
```

### 2. Create a Chute

Copy the template and customize:

```bash
cp deploy_example.py deploy_myservice.py
```

Edit `deploy_myservice.py`:

```python
# Basic identification
CHUTE_NAME = "myservice"
CHUTE_TAG = "v1.0.0"
CHUTE_BASE_IMAGE = "your-registry/your-image:latest"

# Environment variables for the container
CHUTE_ENV = {
    "MODEL_NAME": "your-model",
}

# Static routes (for services without OpenAPI)
CHUTE_STATIC_ROUTES = [
    {"path": "/predict", "method": "POST", "port": 8080, "target_path": "/predict"},
]

# Resource requirements
CHUTE_GPU_COUNT = 1
CHUTE_MIN_VRAM_GB_PER_GPU = 16
```

### 3. Discover Routes

If your service exposes an OpenAPI spec, auto-discover routes:

```bash
./deploy.sh --discover deploy_myservice
```

This will:
1. Start your Docker image
2. Probe for OpenAPI endpoints (`/openapi.json`, `/docs.json`, etc.)
3. Generate `deploy_myservice.routes.json`

### 4. Build & Deploy

```bash
# Interactive mode
./deploy.sh

# Or direct commands
./deploy.sh --build deploy_myservice --local    # Local build
./deploy.sh --deploy deploy_myservice           # Deploy to Chutes
```

## File Structure

```
chutes-wrappers/
├── deploy.sh                    # Main CLI script
├── deploy_example.py            # Template for new chutes
├── deploy_example_original.py   # Reference: SGLang-style chute
├── config.ini.example           # Chutes config template
├── tools/
│   ├── __init__.py
│   ├── chute_wrappers.py        # Image building & route registration
│   └── discover_routes.py       # Route auto-discovery
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CHUTES_USERNAME` | Override username | from config.ini |
| `CHUTE_GPU_COUNT` | Number of GPUs | 1 |
| `CHUTE_MIN_VRAM_GB_PER_GPU` | Minimum VRAM per GPU | 16 |
| `CHUTE_INCLUDE_GPU_TYPES` | Comma-separated GPU types | rtx4090,rtx3090,a100 |
| `CHUTE_PORTS` | Comma-separated service ports | 8080 |
| `CHUTE_CONCURRENCY` | Max concurrent requests | 1 |
| `CHUTE_SHUTDOWN_AFTER_SECONDS` | Idle shutdown timeout | 3600 |
| `CHUTE_BASE_IMAGE` | Override base image | from deploy script |
| `CHUTE_ENTRYPOINT` | Container entrypoint | /usr/local/bin/docker-entrypoint.sh |

### Chute Config Variables

In your `deploy_*.py`:

| Variable | Description |
|----------|-------------|
| `CHUTE_NAME` | Unique name for your chute |
| `CHUTE_TAG` | Version tag for the image |
| `CHUTE_BASE_IMAGE` | Docker image to wrap |
| `CHUTE_TAGLINE` | Short description |
| `CHUTE_DOC` | Markdown documentation |
| `CHUTE_ENV` | Environment variables dict |
| `CHUTE_STATIC_ROUTES` | Routes to always include |
| `SERVICE_PORTS` | Ports to wait for on startup |

## Route Discovery

### OpenAPI-based Discovery

For services with OpenAPI specs:

```bash
./deploy.sh --discover deploy_myservice
```

The tool probes these paths:
- `/openapi.json`
- `/swagger.json`
- `/docs/openapi.json`
- `/docs.json`

### Static Routes

For services without OpenAPI (e.g., whisper.cpp), define routes manually:

```python
CHUTE_STATIC_ROUTES = [
    {"path": "/inference", "method": "POST", "port": 8080, "target_path": "/inference"},
    {"path": "/health", "method": "GET", "port": 8080, "target_path": "/health"},
]
```

### Route Filtering

The following routes are automatically filtered out:
- Path parameters (`{param}`) - Chutes SDK limitation
- File extensions (`.txt`, `.ico`, etc.)
- Root path (`/`)
- Internal routes: `/static`, `/assets`, `/svelte`, `/login`, `/logout`, `/gradio_api`, `/theme`, `/__*`

## Deploy Script Commands

```bash
./deploy.sh --help                              # Show all options

# Listing
./deploy.sh --list-images                       # List built images
./deploy.sh --list-chutes                       # List deployed chutes
./deploy.sh --status myservice                  # Get chute status

# Building
./deploy.sh --discover deploy_myservice         # Discover routes
./deploy.sh --build deploy_myservice --local    # Local build
./deploy.sh --build deploy_myservice            # Remote build

# Running
./deploy.sh --run-docker deploy_myservice       # Run in Docker with GPU
./deploy.sh --run deploy_myservice              # Run on host (dev mode)

# Deploying
./deploy.sh --deploy deploy_myservice           # Deploy to Chutes
./deploy.sh --deploy deploy_myservice --public  # Public deployment

# Management
./deploy.sh --delete myservice                  # Delete a chute
```

## Examples

### Wrapping a TTS/STT Service

```python
CHUTE_NAME = "tts-whisper"
CHUTE_BASE_IMAGE = "your-registry/tts-whisper:latest"
SERVICE_PORTS = [8020, 8080]  # TTS on 8020, Whisper on 8080

CHUTE_ENV = {
    "WHISPER_MODEL": "large-v3-turbo",
}

# Whisper.cpp doesn't expose OpenAPI, so define routes manually
CHUTE_STATIC_ROUTES = [
    {"path": "/inference", "method": "POST", "port": 8080, "target_path": "/inference"},
    {"path": "/load", "method": "GET", "port": 8080, "target_path": "/load"},
    {"path": "/v1/audio/transcriptions", "method": "POST", "port": 8080, "target_path": "/inference"},
]
```

### Wrapping a Gradio App

```python
CHUTE_NAME = "gradio-app"
CHUTE_BASE_IMAGE = "your-registry/gradio-app:latest"
SERVICE_PORTS = [7860]

# Let discovery find the routes (Gradio exposes OpenAPI)
# Run: ./deploy.sh --discover deploy_gradio_app
```

## Troubleshooting

### Route Discovery Fails

1. **Container exits immediately**: Check `CHUTE_ENV` for required environment variables
2. **No routes found**: The service may not expose OpenAPI; use `CHUTE_STATIC_ROUTES`
3. **Timeout**: Increase `--startup-delay` and `--probe-timeout`

### Build Fails with InvalidPath

The Chutes SDK has path restrictions:
- No path parameters (`{param}`)
- No file extensions (`.txt`, `.js`, etc.)
- No root path (`/`)

These are automatically filtered, but if you see this error, check your `CHUTE_STATIC_ROUTES`.

### Remote Build Requires Balance

Remote builds require >= $50 USD account balance. Use `--local` for local builds.

## License

MIT

