# Chutes Wrappers

A toolkit for wrapping Docker images and deploying them on [Chutes.ai](https://chutes.ai).

For full Chutes SDK documentation, see the [Image API Reference](https://chutes.ai/docs/sdk-reference/image).

## Overview

This repo provides:

- **`setup.sh`** - Quick environment setup (venv, dependencies, registration)
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

This will interactively prompt for startup delay and probe timeout, then:
1. Start your Docker image with GPU access
2. Wait for services to initialize
3. Probe for OpenAPI endpoints (`/openapi.json`, `/docs.json`, etc.)
4. Generate `deploy_myservice.routes.json`

For services without OpenAPI, define `CHUTE_STATIC_ROUTES` in your module instead.

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
├── setup.sh                     # Environment setup (venv, deps, registration)
├── deploy.sh                    # Main CLI (interactive + flags)
├── requirements.txt             # Python dependencies
├── deploy_example.py            # Template for new chutes
├── tools/
│   ├── __init__.py
│   ├── chute_wrappers.py        # Image building & route registration
│   └── discover_routes.py       # Route auto-discovery
├── deploy_*.routes.json         # Generated route manifests (gitignored)
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CHUTES_USERNAME` | Override username | from ~/.chutes/config.ini |
| `CHUTES_ROUTE_MANIFEST` | Path to routes JSON file | auto-detected from module name |
| `CHUTES_ROUTE_MANIFEST_JSON` | Inline JSON route manifest | - |
| `CHUTES_SKIP_ROUTE_REGISTRATION` | Skip route registration (used during discovery) | - |
| `CHUTES_EXECUTION_CONTEXT` | Runtime context (`REMOTE` for deployed) | - |
| `CHUTE_PORTS` | Comma-separated service ports | 8020,8080 |

### Chute Module Variables

In your `deploy_*.py`:

| Variable | Required | Description |
|----------|----------|-------------|
| `CHUTE_NAME` | Yes | Unique name for your chute |
| `CHUTE_TAG` | Yes | Version tag for the image |
| `CHUTE_BASE_IMAGE` | Yes | Docker image to wrap |
| `SERVICE_PORTS` | Yes | List of ports to wait for on startup |
| `CHUTE_ENV` | No | Environment variables dict (passed to container during route discovery) |
| `CHUTE_STATIC_ROUTES` | No | Routes to always include (merged with discovered routes) |
| `CHUTE_TAGLINE` | No | Short description for chute listing |
| `ENTRYPOINT` | No | Container entrypoint (used by route discovery) |

### Helper Functions (from `tools/chute_wrappers.py`)

| Function | Description |
|----------|-------------|
| `build_wrapper_image(username, name, tag, base_image)` | Create a Chutes-compatible image from a base Docker image |
| `load_route_manifest(static_routes=None)` | Load routes from `.routes.json` (auto-detected from caller filename) and merge with static routes |
| `register_passthrough_routes(chute, routes, default_port)` | Register all routes as passthrough cords on the chute |
| `wait_for_services(ports, timeout=600)` | Async: block until all service ports accept connections |
| `probe_services(ports, timeout=5)` | Async: check service health, returns list of error strings |
| `parse_service_ports(env_value=None)` | Parse comma-separated port string (from `CHUTE_PORTS` env) to list of ints |

**Note:** `load_route_manifest()` auto-detects the manifest path from the caller's filename. For `deploy_myservice.py`, it looks for `deploy_myservice.routes.json` automatically.

## Route Discovery

### OpenAPI-based Discovery

For services with OpenAPI specs:

```bash
./deploy.sh --discover deploy_myservice
```

Interactive prompts will ask for:
- **Startup delay** (default: 120s) - time to wait before probing
- **Probe timeout** (default: 180s) - how long to retry each port
- **Docker --gpus** (default: all) - GPU access for container

The tool probes these OpenAPI paths:
- `/openapi.json`
- `/swagger.json`
- `/docs/openapi.json`
- `/docs.json`

### Direct Discovery Tool Usage

```bash
# Probe a running service directly
python tools/discover_routes.py --base-url http://127.0.0.1:8020 --port 8020

# Auto-run container from chute file
python tools/discover_routes.py --chute-file deploy_myservice.py \
    --startup-delay 120 --probe-timeout 180 --docker-gpus all

# Pass environment variables to container
python tools/discover_routes.py --chute-file deploy_myservice.py \
    --docker-env "MODEL_NAME=large" --docker-env "DEBUG=1"
```

### Static Routes

For services without OpenAPI (e.g., whisper.cpp), define routes manually:

```python
CHUTE_STATIC_ROUTES = [
    {"path": "/inference", "method": "POST", "port": 8080, "target_path": "/inference"},
    {"path": "/health", "method": "GET", "port": 8080, "target_path": "/health"},
]
```

Static routes are merged with discovered routes (duplicates by path+method are skipped).

### Route Filtering

The following routes are automatically filtered out:
- Path parameters (`{param}`) - Chutes SDK limitation
- File extensions (`.txt`, `.ico`, etc.)
- Root path (`/`)
- Internal routes: `/static`, `/assets`, `/svelte`, `/login`, `/logout`, `/gradio_api`, `/theme`, `/__*`

## Deploy Script Commands

### Interactive Mode

Running `./deploy.sh` without arguments opens an interactive menu:

```
1) List images          5) Run dev mode (host)
2) List chutes          6) Deploy chute
3) Build chute          7) Chute status
4) Run in Docker (GPU)  8) Delete chute
                        9) Account info
```

### Command-Line Flags

```bash
./deploy.sh --help                              # Show all options

# Listing
./deploy.sh --list-images                       # List built images
./deploy.sh --list-chutes                       # List deployed chutes
./deploy.sh --status myservice                  # Get chute status

# Route Discovery
./deploy.sh --discover deploy_myservice         # Discover routes (interactive)

# Building
./deploy.sh --build deploy_myservice --local    # Local build (no upload)
./deploy.sh --build deploy_myservice            # Remote build (requires $50 balance)
./deploy.sh --build deploy_myservice --debug    # Build with debug output

# Running Locally
./deploy.sh --run-docker deploy_myservice       # Run in Docker with GPU
./deploy.sh --run deploy_myservice              # Run on host (dev mode)
./deploy.sh --run deploy_myservice --port 9000  # Custom port

# Deploying
./deploy.sh --deploy deploy_myservice --accept-fee  # Accept fees non-interactively
./deploy.sh --deploy deploy_myservice --public      # Public deployment

# Management
./deploy.sh --delete myservice                  # Delete a chute (interactive confirm)
```

### Run Modes

| Mode | Command | Use Case |
|------|---------|----------|
| Docker GPU | `--run-docker` | Wrapped services (XTTS, Whisper) that need GPU |
| Host Dev | `--run` | Python chutes, debugging on host |

Both modes poll until the chute is ready and show live logs.

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
2. Installing Python 3.12 and system dependencies (cmake, git, curl, libclblast, OpenCL, etc.)
3. Setting up a non-root `chutes` user with proper permissions
4. Configuring Python paths via `.pth` file (auto-discovers `/app`, `/workspace`, `/srv`)
5. Installing `uv` package manager and configuring pip for user installs
6. Clearing entrypoint to allow Chutes runtime control

The resulting image can be built locally (`--local`) or remotely via Chutes' build infrastructure.

### Route Registration

Routes are registered as "cords" on your chute. Each cord:
- Maps a public API path to an internal service port
- Supports GET, POST, PUT, PATCH, DELETE methods
- Uses passthrough mode (proxies directly to backend service)
- Optionally supports streaming responses (`"stream": true`)

Routes are loaded from (in order):
1. `CHUTES_ROUTE_MANIFEST_JSON` env var (inline JSON)
2. `CHUTES_ROUTE_MANIFEST` env var (file path)
3. `deploy_*.routes.json` (auto-detected from caller filename)
4. `CHUTE_STATIC_ROUTES` (merged, duplicates skipped)

See the [Chutes SDK Cord Reference](https://chutes.ai/docs/sdk-reference/cord) for more details.

### Build Flow

1. **Route Discovery** (optional): `./deploy.sh --discover` runs your base image in Docker, probes for OpenAPI, generates `.routes.json`
2. **Build**: `./deploy.sh --build` uses `CHUTES_ROUTE_MANIFEST` env var to pass manifest to chutes CLI
3. **Deploy**: `./deploy.sh --deploy` uploads and schedules the chute on Chutes.ai infrastructure

## License

MIT

