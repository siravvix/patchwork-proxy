# patchwork-proxy

A minimal reverse proxy with hot-reloadable routing rules for local development workflows.

---

## Installation

```bash
pip install patchwork-proxy
```

Or install from source:

```bash
git clone https://github.com/yourname/patchwork-proxy.git
cd patchwork-proxy
pip install -e .
```

---

## Usage

Define your routing rules in a `routes.yaml` file:

```yaml
routes:
  - match: /api
    target: http://localhost:8080
  - match: /static
    target: http://localhost:9000
  - match: /
    target: http://localhost:3000
```

Start the proxy:

```bash
patchwork-proxy --config routes.yaml --port 5000
```

The proxy listens on `http://localhost:5000` and forwards requests based on the matched prefix. Edit `routes.yaml` at any time — changes are picked up automatically without restarting the server.

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--config` | `routes.yaml` | Path to routing config file |
| `--port` | `5000` | Port to listen on |
| `--host` | `127.0.0.1` | Host address to bind |
| `--reload-interval` | `1` | Seconds between config polls |

---

## Requirements

- Python 3.8+
- No external dependencies (stdlib only)

---

## License

MIT © 2024 Your Name