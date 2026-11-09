import logging
import msvcrt
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import text

from app.infrastructure.persistence.database import SessionLocal

logger = logging.getLogger(__name__)

LOCK_PATH = Path(__file__).resolve().parents[2] / "watchdog.lock"
WATCHDOG_TIMEOUT_SECONDS = 300
HEARTBEAT_INTERVAL = 60
HANDSHAKE_TIMEOUT = 5


class Watchdog:
    def __init__(self):
        self._lock_file = None
        self._stop_event = threading.Event()

    # ---------- Bloqueo OS (msvcrt) ----------
    def _acquire_os_lock(self) -> bool:
        """
        Adquiere un bloqueo de archivo a nivel de sistema operativo en
        watchdog.lock. Windows lo libera automáticamente si el proceso
        muere. Sin archivos .pid.
        """
        try:
            self._lock_file = open(LOCK_PATH, "a+b")
            self._lock_file.seek(0)
            if self._lock_file.read(1) == b"":
                self._lock_file.write(b"\0")
                self._lock_file.flush()
            self._lock_file.seek(0)
            msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            logger.info("Watchdog: bloqueo OS adquirido.")
            return True
        except OSError:
            logger.debug("Watchdog: otro proceso tiene el bloqueo. Saliendo.")
            if self._lock_file:
                self._lock_file.close()
                self._lock_file = None
            return False

    def _release_os_lock(self):
        if self._lock_file:
            try:
                self._lock_file.seek(0)
                msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            finally:
                self._lock_file.close()
                self._lock_file = None
                logger.info("Watchdog: bloqueo OS liberado.")

    # ---------- Adquisición atómica de un run ----------
    def _acquire_run(self, run_id: int, new_lock: str) -> bool:
        """
        Adquisición atómica con lease token.

        Recuperar si:
        - status='queued'  AND (lock_id IS NULL OR locked_at IS NULL OR locked_at < :timeout)
        - status IN activos AND (lock_id IS NULL OR locked_at IS NULL OR locked_at < :timeout)

        NO recuperar si:
        - status con lock vigente (locked_at >= timeout)
        - status IN ('partial_failure','failed','completed','completed_no_opportunities','cancelled')
        """
        db = SessionLocal()
        try:
            timeout = datetime.utcnow() - timedelta(seconds=WATCHDOG_TIMEOUT_SECONDS)
            result = db.execute(
                text("""
                    UPDATE research_runs
                    SET lock_id = :lock, locked_at = :now, status = 'searching'
                    WHERE id = :id
                      AND (
                        status = 'queued'
                        OR status IN ('searching','extracting','analyzing','corroborating')
                      )
                      AND (
                        lock_id IS NULL
                        OR locked_at IS NULL
                        OR locked_at < :timeout
                      )
                """),
                {"lock": new_lock, "now": datetime.utcnow(), "id": run_id, "timeout": timeout},
            )
            db.commit()
            return result.rowcount == 1
        except Exception as e:
            db.rollback()
            logger.error(f"Watchdog: error adquiriendo run {run_id}: {e}")
            return False
        finally:
            db.close()

    def _release_run_if_owner(
        self, run_id: int, lock_id: str, new_status: str,
        error_msg: Optional[str] = None,
    ) -> bool:
        db = SessionLocal()
        try:
            params = {"id": run_id, "lock": lock_id, "status": new_status}
            sql = "UPDATE research_runs SET lock_id = NULL, locked_at = NULL, status = :status"
            if error_msg is not None:
                sql += ", error_summary = :err"
                params["err"] = error_msg
            sql += " WHERE id = :id AND lock_id = :lock"
            result = db.execute(text(sql), params)
            db.commit()
            return result.rowcount == 1
        except Exception as e:
            db.rollback()
            logger.error(f"Watchdog: error liberando run {run_id}: {e}")
            return False
        finally:
            db.close()

    # ---------- Handshake con tres estados distinguibles ----------
    def _launch_orchestrator(self, run_id: int, lock_id: str):
        """
        Lanza el Orchestrator con handshake. Distingue:
        1. Inicializado correctamente -> el Orchestrator gestiona el lease.
        2. Terminó antes de inicializar -> liberar lock, marcar 'failed'.
        3. Timeout con hilo vivo -> NO liberar lock (el contrato transaccional
           del Orchestrator protege contra escrituras tras pérdida de lease).
        """
        initialized = threading.Event()
        finished = threading.Event()
        error_container: dict = {"error": None}

        def _runner():
            try:
                from app.modules.opportunity_engine.orchestrator import ResearchOrchestrator
                orch = ResearchOrchestrator()
                orch.run(run_id, lock_id, on_started=lambda: initialized.set())
            except Exception as e:
                error_container["error"] = e
                logger.error(f"Watchdog: error en Orchestrator run {run_id}: {e}")
            finally:
                finished.set()

        thread = threading.Thread(target=_runner, daemon=True, name=f"orch-{run_id}")
        thread.start()

        deadline = datetime.utcnow() + timedelta(seconds=HANDSHAKE_TIMEOUT)
        while datetime.utcnow() < deadline:
            if initialized.is_set() or finished.is_set():
                break
            threading.Event().wait(0.1)

        if initialized.is_set():
            logger.info(f"Watchdog: run {run_id} inicializado correctamente.")
            return

        if finished.is_set():
            err = error_container["error"]
            logger.error(f"Watchdog: run {run_id} terminó antes de inicializar: {err}")
            self._release_run_if_owner(
                run_id, lock_id, "failed",
                f"Hilo terminó antes de inicializar: {err}",
            )
            return

        logger.warning(
            f"Watchdog: handshake timeout para run {run_id} con hilo VIVO. "
            f"No se libera el lock. El contrato transaccional del Orchestrator "
            f"protege contra escrituras de este hilo si otro proceso recupera el run."
        )

    # ---------- Bucle ----------
    def _loop_iteration(self):
        db = SessionLocal()
        try:
            timeout = datetime.utcnow() - timedelta(seconds=WATCHDOG_TIMEOUT_SECONDS)
            rows = db.execute(
                text("""
                    SELECT id FROM research_runs
                    WHERE (status = 'queued'
                           OR status IN ('searching','extracting','analyzing','corroborating'))
                      AND (lock_id IS NULL
                           OR locked_at IS NULL
                           OR locked_at < :timeout)
                """),
                {"timeout": timeout},
            ).fetchall()
        finally:
            db.close()

        for (run_id,) in rows:
            new_lock = str(uuid.uuid4())
            if self._acquire_run(run_id, new_lock):
                logger.info(f"Watchdog: run {run_id} adquirido con lease {new_lock[:8]}...")
                self._launch_orchestrator(run_id, new_lock)

    def run(self):
        if not self._acquire_os_lock():
            return
        try:
            logger.info("Watchdog: iniciado.")
            while not self._stop_event.is_set():
                try:
                    self._loop_iteration()
                except Exception as e:
                    logger.error(f"Watchdog: error en iteración: {e}")
                self._stop_event.wait(HEARTBEAT_INTERVAL)
        finally:
            self._release_os_lock()

    def stop(self):
        self._stop_event.set()