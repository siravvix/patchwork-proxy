"""Core reverse-proxy request handler."""

import logging
import threading
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, urlunparse

import urllib.request
import urllib.error

from patchwork.config import ProxyConfig

logger = logging.getLogger(__name__)


class ProxyHandler(BaseHTTPRequestHandler):
    """HTTP handler that forwards requests based on the current routing config."""

    # Injected by the server; access via class attribute for thread safety.
    _config: ProxyConfig = None
    _config_lock: threading.RLock = threading.RLock()

    log_message = lambda self, fmt, *args: logger.debug(fmt, *args)  # noqa: E731

    @classmethod
    def update_config(cls, config: ProxyConfig) -> None:
        with cls._config_lock:
            cls._config = config
            logger.info("ProxyHandler config updated (%d routes)", len(config.routes))

    def _get_config(self) -> ProxyConfig:
        with self.__class__._config_lock:
            return self.__class__._config

    def do_request(self) -> None:
        config = self._get_config()
        if config is None:
            self._respond(503, b"Proxy not configured")
            return

        rule = config.match_route(self.path, self.command)
        if rule is None:
            self._respond(404, b"No matching route")
            return

        rewritten = rule.rewrite(self.path)
        target_url = rule.target.rstrip("/") + rewritten

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else None

        req = urllib.request.Request(target_url, data=body, method=self.command)
        for key, val in self.headers.items():
            if key.lower() not in ("host", "connection"):
                req.add_header(key, val)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                self.send_response(resp.status)
                for key, val in resp.headers.items():
                    self.send_header(key, val)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as exc:
            self._respond(exc.code, exc.read())
        except Exception as exc:  # noqa: BLE001
            logger.error("Upstream error: %s", exc)
            self._respond(502, f"Bad gateway: {exc}".encode())

    def _respond(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_request
