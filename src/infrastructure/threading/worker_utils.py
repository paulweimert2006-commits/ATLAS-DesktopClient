"""
Zentrale Worker-Infrastruktur fuer asynchrone Operationen.

Stellt GenericWorker und run_worker() bereit, um beliebige Callables
in einem QThread auszufuehren. Ersetzt manuelles Worker-Boilerplate
und bietet request_id-Tracking, Debouncing und Cancellation.

Usage:
    from infrastructure.threading.worker_utils import run_worker

    # Einfach (API-Call im Hintergrund):
    run_worker(self, lambda w: repo.get_data(), self._on_data_loaded)

    # Mit Fehlerbehandlung:
    run_worker(self, lambda w: repo.save(data),
               self._on_saved, on_error=self._on_save_error)

    # Mit Cancel-Check (langlebige Operation):
    def load_all(worker):
        results = []
        for item in items:
            if worker.is_cancelled():
                return None
            results.append(process(item))
        return results
    run_worker(self, load_all, self._on_done)

    # Mit Debounce (Filter/Suche):
    run_worker(self, lambda w: self._filter_data(query),
               self._on_filtered, debounce_ms=300)

    # Mit Progress:
    def export_all(worker):
        for i, row in enumerate(rows):
            if worker.is_cancelled():
                return None
            worker.report_progress(i + 1)
            export(row)
        return len(rows)
    run_worker(self, export_all, self._on_export_done,
               on_progress=self._on_export_progress)
"""

import uuid
import logging
import warnings
from typing import Callable, Optional, Any

from PySide6.QtCore import QObject, QThread, Signal, QTimer

logger = logging.getLogger(__name__)

_WORKER_ATTR = '_gw_active_worker'
_REQUEST_ATTR = '_gw_latest_request_id'
_TIMER_ATTR = '_gw_debounce_timer'
_detached_workers: set = set()


class GenericWorker(QThread):
    """Fuehrt ein beliebiges Callable in einem QThread aus.

    Das Callable erhaelt die Worker-Instanz als erstes Argument,
    sodass es Cancel-Status und Progress-Reporting nutzen kann.

    Signals:
        finished(str, object): (request_id, result) bei Erfolg
        error(str, str): (request_id, error_message) bei Fehler
        progress(str, object): (request_id, value) fuer Fortschritt
    """
    finished = Signal(str, object)
    error = Signal(str, str)
    progress = Signal(str, object)

    def __init__(self, task: Callable, request_id: Optional[str] = None,
                 parent: QObject = None):
        super().__init__(parent)
        self._task = task
        self.request_id = request_id or str(uuid.uuid4())
        self._cancelled = False

    def cancel(self):
        """Setzt Cancel-Flag. Das Callable prueft via is_cancelled()."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def report_progress(self, value: Any) -> None:
        """Hilfsmethode fuer Progress-Reports aus dem Task heraus."""
        if not self._cancelled:
            self.progress.emit(self.request_id, value)

    def run(self):
        try:
            result = self._task(self)
            if not self._cancelled:
                self.finished.emit(self.request_id, result)
        except Exception as e:
            if not self._cancelled:
                logger.error(
                    "GenericWorker error [%s]: %s", self.request_id[:8], e
                )
                self.error.emit(self.request_id, str(e))
        finally:
            if self._cancelled:
                self.finished.emit(self.request_id, None)


def run_worker(
    parent: QObject,
    task: Callable,
    on_success: Callable,
    on_error: Optional[Callable] = None,
    on_progress: Optional[Callable] = None,
    request_id: Optional[str] = None,
    debounce_ms: int = 0,
) -> GenericWorker:
    """Startet task in QThread, liefert Ergebnis via Signal.

    Cancelt automatisch einen laufenden Worker auf demselben parent.
    Veraltete Ergebnisse (von gecancelten Workern) werden verworfen
    via request_id-Vergleich.

    Args:
        parent: QObject das die Worker-Referenz haelt (Lifecycle).
        task: Callable(worker: GenericWorker) -> result.
        on_success: Callback(result) bei Erfolg.
        on_error: Callback(error_msg: str) bei Fehler.
        on_progress: Callback(value) fuer Fortschrittsmeldungen.
        request_id: Optionale ID; auto-generiert wenn None.
        debounce_ms: Verzoegerung in ms bevor der Worker startet.
                     Jeder neue Aufruf resettet den Timer.

    Returns:
        GenericWorker-Instanz (laeuft bereits oder wartet auf Debounce).
    """
    rid = request_id or str(uuid.uuid4())

    _cancel_active_worker(parent)

    setattr(parent, _REQUEST_ATTR, rid)

    worker = GenericWorker(task, request_id=rid)

    def handle_finished(req_id: str, result: object) -> None:
        if getattr(parent, _REQUEST_ATTR, None) != req_id:
            logger.debug("Stale result verworfen [%s]", req_id[:8])
            return
        on_success(result)

    def handle_error(req_id: str, msg: str) -> None:
        if getattr(parent, _REQUEST_ATTR, None) != req_id:
            return
        if on_error:
            on_error(msg)
        else:
            logger.error("Worker-Fehler (unbehandelt): %s", msg)

    worker.finished.connect(handle_finished)
    worker.error.connect(handle_error)

    if on_progress:
        def handle_progress(req_id: str, value: object) -> None:
            if getattr(parent, _REQUEST_ATTR, None) != req_id:
                return
            on_progress(value)

        worker.progress.connect(handle_progress)

    worker.finished.connect(lambda *_: _cleanup_worker(parent, worker))
    worker.error.connect(lambda *_: _cleanup_worker(parent, worker))

    setattr(parent, _WORKER_ATTR, worker)

    if debounce_ms > 0:
        _setup_debounce(parent, worker, debounce_ms)
    else:
        worker.start()

    return worker


def detach_worker(worker) -> None:
    """Trennt alle Signals eines laufenden Workers, um veraltete Callbacks zu verhindern.

    Nuetzlich in Presentern, wenn ein neuer Worker gestartet wird und der alte
    noch laeuft. Der alte Worker beendet sich natuerlich, aber seine Ergebnisse
    werden nicht mehr verarbeitet.

    Haelt eine Referenz auf den Worker bis dessen Thread beendet ist, um
    'QThread: Destroyed while thread is still running'-Crashes zu verhindern.
    """
    if worker is None:
        return
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for sig_name in ('finished', 'error', 'progress'):
            sig = getattr(worker, sig_name, None)
            if sig is not None:
                try:
                    sig.disconnect()
                except (RuntimeError, TypeError):
                    pass

    if worker.isRunning():
        _detached_workers.add(worker)

        def _release(*args):
            _detached_workers.discard(worker)
            worker.deleteLater()

        worker.finished.connect(_release)
        worker.error.connect(_release)


def cancel_worker(parent: QObject) -> None:
    """Cancelt den aktiven Worker auf parent (falls vorhanden).

    Nuetzlich fuer explizites Cancel bei closeEvent / Panel-Wechsel.
    """
    _cancel_active_worker(parent)


def _cancel_active_worker(parent: QObject) -> None:
    """Cancelt und bereinigt einen laufenden Worker."""
    timer = getattr(parent, _TIMER_ATTR, None)
    if timer is not None:
        timer.stop()

    old = getattr(parent, _WORKER_ATTR, None)
    if old is not None and isinstance(old, GenericWorker):
        if old.isRunning():
            old.cancel()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                for sig_name in ('finished', 'error', 'progress'):
                    try:
                        getattr(old, sig_name).disconnect()
                    except (RuntimeError, TypeError):
                        pass
            _detached_workers.add(old)

            def _release(*args):
                _detached_workers.discard(old)
                old.deleteLater()

            old.finished.connect(_release)
        else:
            old.deleteLater()
        setattr(parent, _WORKER_ATTR, None)


def _setup_debounce(parent: QObject, worker: GenericWorker,
                    ms: int) -> None:
    """Richtet Debounce-Timer ein. Startet Worker erst nach ms Ruhe."""
    timer = getattr(parent, _TIMER_ATTR, None)
    if timer is None:
        timer = QTimer(parent)
        timer.setSingleShot(True)
        setattr(parent, _TIMER_ATTR, timer)

    timer.stop()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        try:
            timer.timeout.disconnect()
        except (RuntimeError, TypeError):
            pass

    timer.timeout.connect(worker.start)
    timer.start(ms)


def _cleanup_worker(parent: QObject, worker: GenericWorker) -> None:
    """Bereinigt Worker-Referenz nach Abschluss."""
    if getattr(parent, _WORKER_ATTR, None) is worker:
        setattr(parent, _WORKER_ATTR, None)
    worker.deleteLater()
