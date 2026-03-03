"""
Freeze-Detektor und Action-Logging fuer Performance-Monitoring.

FreezeDetector: QTimer-basiert, tickt alle 250ms. Wenn ein Tick mehr als
500ms verspaetet eintrifft, wird ein UI-Freeze geloggt mit Dauer und Kontext.

@log_action: Decorator fuer Worker-Aufrufe. Loggt Startzeit, Endzeit,
Datensatzanzahl und Payload-Groesse nach logs/provision_performance.log.
"""

import os
import sys
import time
import logging
import functools
from logging.handlers import RotatingFileHandler
from typing import Callable, Optional, Any

from PySide6.QtCore import QObject, QTimer, QElapsedTimer, Signal, Qt


_TICK_INTERVAL_MS = 250
_FREEZE_THRESHOLD_MS = 500

_perf_logger: Optional[logging.Logger] = None


def _get_perf_logger() -> logging.Logger:
    """Lazy-Init des Performance-Loggers mit eigenem RotatingFileHandler."""
    global _perf_logger
    if _perf_logger is not None:
        return _perf_logger

    _perf_logger = logging.getLogger("provision.performance")
    _perf_logger.setLevel(logging.INFO)
    _perf_logger.propagate = False

    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "..")

    log_dir = os.path.join(base, "logs")
    log_file = os.path.join(log_dir, "provision_performance.log")

    try:
        os.makedirs(log_dir, exist_ok=True)
        handler = RotatingFileHandler(
            log_file,
            maxBytes=2 * 1024 * 1024,
            backupCount=2,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-5s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        _perf_logger.addHandler(handler)
    except (OSError, PermissionError):
        pass

    return _perf_logger


class FreezeDetector(QObject):
    """Erkennt UI-Freezes durch QTimer-Tick-Verspaetungen.

    Ein QTimer tickt alle 250ms. Kommt der Tick mehr als 500ms zu spaet,
    bedeutet das, dass der Main-Thread blockiert war. Der Freeze wird
    mit Dauer und aktivem Kontext geloggt und als Signal emittiert.

    Signals:
        freeze_detected(int, str): (dauer_ms, kontext)
    """

    freeze_detected = Signal(int, str)

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._context = ""
        self._elapsed = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._on_tick)

    def start(self) -> None:
        self._elapsed.start()
        self._timer.start(_TICK_INTERVAL_MS)

    def stop(self) -> None:
        self._timer.stop()

    def set_context(self, context: str) -> None:
        """Setzt den aktuellen Aktions-Kontext (z.B. Panel-Name, Action)."""
        self._context = context

    def _on_tick(self) -> None:
        elapsed_ms = self._elapsed.elapsed()
        self._elapsed.restart()

        if elapsed_ms > _FREEZE_THRESHOLD_MS:
            duration = elapsed_ms - _TICK_INTERVAL_MS
            ctx = self._context or "unknown"
            _get_perf_logger().warning(
                "UI-FREEZE | %4d ms | context=%s", duration, ctx
            )
            self.freeze_detected.emit(duration, ctx)


def log_action(
    action_name: str = "",
    count_key: str = "",
) -> Callable:
    """Decorator fuer Worker-Callables. Loggt Performance-Metriken.

    Args:
        action_name: Bezeichnung der Aktion (Default: Funktionsname).
        count_key: Schluessel im Result-Dict/-List fuer die Datensatzanzahl.
                   Wenn leer, wird len(result) versucht.

    Geloggt wird:
        - Aktionsname
        - Laufzeit in ms
        - Datensatzanzahl (wenn ermittelbar)
        - Payload-Groesse in Bytes (geschaetzt via sys.getsizeof)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            name = action_name or func.__qualname__
            start = time.perf_counter()

            result = func(*args, **kwargs)

            duration_ms = (time.perf_counter() - start) * 1000
            record_count = _extract_count(result, count_key)
            payload_bytes = _estimate_size(result)

            _get_perf_logger().info(
                "ACTION | %-40s | %7.1f ms | records=%s | payload=%s bytes",
                name, duration_ms,
                str(record_count) if record_count is not None else "?",
                str(payload_bytes) if payload_bytes is not None else "?",
            )

            return result
        return wrapper
    return decorator


def _extract_count(result: Any, key: str) -> Optional[int]:
    """Versucht die Datensatzanzahl aus dem Ergebnis zu ermitteln."""
    if result is None:
        return 0
    if key and isinstance(result, dict):
        val = result.get(key)
        if isinstance(val, (list, tuple)):
            return len(val)
        if isinstance(val, int):
            return val
    if isinstance(result, (list, tuple)):
        return len(result)
    if isinstance(result, dict) and not key:
        return len(result)
    return None


def _estimate_size(result: Any) -> Optional[int]:
    """Grobe Groessenschaetzung des Ergebnisses."""
    if result is None:
        return 0
    try:
        return sys.getsizeof(result)
    except TypeError:
        return None
