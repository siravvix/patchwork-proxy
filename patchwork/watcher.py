"""File watcher that triggers a callback when the config file changes."""

import logging
import os
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)


class ConfigWatcher:
    """Poll a file for modifications and invoke a reload callback."""

    def __init__(
        self,
        config_path: str,
        on_change: Callable[[str], None],
        poll_interval: float = 1.0,
    ) -> None:
        self.config_path = config_path
        self.on_change = on_change
        self.poll_interval = poll_interval
        self._last_mtime: float = self._get_mtime()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="config-watcher")

    def _get_mtime(self) -> float:
        try:
            return os.path.getmtime(self.config_path)
        except OSError:
            return 0.0

    def _run(self) -> None:
        logger.debug("ConfigWatcher started for %s", self.config_path)
        while not self._stop_event.wait(self.poll_interval):
            mtime = self._get_mtime()
            if mtime != self._last_mtime:
                logger.info("Config change detected: %s", self.config_path)
                self._last_mtime = mtime
                try:
                    self.on_change(self.config_path)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Reload callback failed: %s", exc)

    def start(self) -> None:
        """Start the background watcher thread."""
        self._thread.start()

    def stop(self) -> None:
        """Signal the watcher thread to stop and wait for it."""
        self._stop_event.set()
        self._thread.join(timeout=self.poll_interval * 2)
        logger.debug("ConfigWatcher stopped")
