# Chutes Wrappers

A toolkit for wrapping Docker images and deploying them on [Chutes.ai](https://chutes.ai).

For full Chutes SDK documentation, see the [Image API Reference](https://chutes.ai/docs/sdk-reference/image).

## Overview

This repo provides:

- **`deploy.sh`** - Interactive CLI for building, testing, and deploying chutes
- **`tools/chute_wrappers.py`** - Helper functions for wrapping Docker images
- **`tools/discover_routes.py`** - Auto-discovers HTTP routes from running containers
- **`deploy_example.py`** - Template for creating new wrapped chutes

## Quick Start

### 1. Setup

```bash
# Run the setup script
./setup.sh

# Activate the environment
source .venv/bin/activate

# Register with Chutes (if not already)
chutes register
```

Or manually:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
chutes register
```

### 2. Create a Chute

Copy the template and customize:

```bash
cp deploy_example.py deploy_myservice.py
```

Edit `deploy_myservice.py`:

```python
from chutes.chute import Chute, NodeSelector
from tools.chute_wrappers import (
    build_wrapper_image,
    load_route_manifest,
    register_passthrough_routes,
    wait_for_services,
    probe_services,
)

# Basic identification
CHUTE_NAME = "myservice"
CHUTE_TAG = "v1.0.0"
CHUTE_BASE_IMAGE = "your-registry/your-image:latest"
SERVICE_PORTS = [8080]  # Ports your service exposes

# Environment variables for the container
CHUTE_ENV = {
    "MODEL_NAME": "your-model",
}

# Static routes (for services without OpenAPI)
CHUTE_STATIC_ROUTES = [
    {"path": "/predict", "method": "POST", "port": 8080, "target_path": "/predict"},
]

# Build image
image = build_wrapper_image(USERNAME, CHUTE_NAME, CHUTE_TAG, CHUTE_BASE_IMAGE)

# Create chute
chute = Chute(
    username=USERNAME,
    name=CHUTE_NAME,
    image=image,
    node_selector=NodeSelector(gpu_count=1, min_vram_gb_per_gpu=16),
)

# Register routes from manifest + static routes
register_passthrough_routes(chute, load_route_manifest(static_routes=CHUTE_STATIC_ROUTES), SERVICE_PORTS[0])

@chute.on_startup()
async def boot(self):
    await wait_for_services(SERVICE_PORTS)
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
├── setup.sh                     # Quick setup script
├── deploy.sh                    # Main CLI script
├── requirements.txt             # Python dependencies
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
| `CHUTE_ENV` | Environment variables dict (used by route discovery) |
| `CHUTE_STATIC_ROUTES` | Routes to always include (merged with discovered routes) |
| `SERVICE_PORTS` | Ports to wait for on startup |

### Helper Functions (from `tools/chute_wrappers.py`)

| Function | Description |
|----------|-------------|
| `build_wrapper_image()` | Create a Chutes-compatible image from a base Docker image |
| `load_route_manifest()` | Load routes from `.routes.json` and merge with static routes |
| `register_passthrough_routes()` | Register all routes as passthrough cords on the chute |
| `wait_for_services()` | Block until all service ports are accepting connections |
| `probe_services()` | Check service health, returns list of errors |
| `parse_service_ports()` | Parse comma-separated port string to list of ints |

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

### Wrapping a TTS/STT Service (XTTS + Whisper)

```python
from chutes.chute import Chute, NodeSelector
from tools.chute_wrappers import (
    build_wrapper_image, load_route_manifest, register_passthrough_routes,
    wait_for_services, probe_services,
)

CHUTE_NAME = "xtts-whisper"
CHUTE_TAG = "tts-stt-v0.1.0"
CHUTE_BASE_IMAGE = "elbios/xtts-whisper:latest"
SERVICE_PORTS = [8020, 8080]  # XTTS on 8020, Whisper on 8080

CHUTE_ENV = {
    "WHISPER_MODEL": "large-v3-turbo",
    "XTTS_MODEL_ID": "tts_models/multilingual/multi-dataset/xtts_v2",
}

# Whisper.cpp doesn't expose OpenAPI, so define routes manually
CHUTE_STATIC_ROUTES = [
    {"path": "/inference", "method": "POST", "port": 8080, "target_path": "/inference"},
    {"path": "/load", "method": "GET", "port": 8080, "target_path": "/load"},
    {"path": "/v1/audio/transcriptions", "method": "POST", "port": 8080, "target_path": "/inference"},
]

image = build_wrapper_image(USERNAME, CHUTE_NAME, CHUTE_TAG, CHUTE_BASE_IMAGE)

chute = Chute(
    username=USERNAME,
    name=CHUTE_NAME,
    tagline="XTTS + Whisper.cpp for TTS/STT",
    image=image,
    node_selector=NodeSelector(gpu_count=1, min_vram_gb_per_gpu=16),
    concurrency=4,
)

register_passthrough_routes(chute, load_route_manifest(static_routes=CHUTE_STATIC_ROUTES), SERVICE_PORTS[0])

@chute.on_startup()
async def boot(self):
    await wait_for_services(SERVICE_PORTS, timeout=600)

@chute.cord(public_api_path="/health", public_api_method="GET", method="GET")
async def health_check(self) -> dict:
    errors = await probe_services(SERVICE_PORTS, timeout=5)
    return {"status": "unhealthy", "errors": errors} if errors else {"status": "healthy"}
```

### Wrapping a Gradio App

```python
CHUTE_NAME = "gradio-app"
CHUTE_BASE_IMAGE = "your-registry/gradio-app:latest"
SERVICE_PORTS = [7860]
CHUTE_ENV = {}  # Add any required env vars

# Gradio exposes OpenAPI - use route discovery:
# ./deploy.sh --discover deploy_gradio_app

image = build_wrapper_image(USERNAME, CHUTE_NAME, CHUTE_TAG, CHUTE_BASE_IMAGE)
chute = Chute(username=USERNAME, name=CHUTE_NAME, image=image, ...)

# Routes loaded from deploy_gradio_app.routes.json (auto-discovered)
register_passthrough_routes(chute, load_route_manifest(), SERVICE_PORTS[0])
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

## How It Works

### Image Wrapping

`build_wrapper_image()` creates a Chutes-compatible image by:

1. Starting from your base Docker image
2. Installing Python 3.12 and system dependencies (cmake, git, curl, etc.)
3. Setting up a non-root `chutes` user with proper permissions
4. Configuring Python paths and uv package manager
5. Setting environment variables for Chutes runtime

The resulting image can be built locally or remotely via Chutes' build infrastructure.

### Route Registration

Routes are registered as "cords" on your chute. Each cord:
- Maps a public API path to an internal service port
- Supports GET, POST, and other HTTP methods
- Can be a passthrough (proxies directly to backend) or custom handler
- Optionally supports streaming responses

Routes are loaded from:
1. `deploy_*.routes.json` (auto-discovered via OpenAPI)
2. `CHUTE_STATIC_ROUTES` (manually defined)

See the [Chutes SDK Cord Reference](https://chutes.ai/docs/sdk-reference/cord) for more details.

## License

MIT

