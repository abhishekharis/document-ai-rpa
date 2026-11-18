"""Background OCR worker: python -m app.worker

Pops document IDs from the Redis queue and runs the processing pipeline on them.
"""
import asyncio
import logging
import signal
import time

from app.config import settings
from app.database import db
from app.logging_config import configure_logging
from app.services.job_queue import JobQueue, create_job_queue
from app.services.pipeline import run_processing
from app.services.processing_service import ProcessingService
from app.services.repository import InvoiceRepository
from app.models.invoice import InvoiceStatus
from app.storage.file_storage import file_storage

logger = logging.getLogger("app.worker")

# How often (seconds) the worker runs the recovery sweep while idle
RECOVERY_SWEEP_INTERVAL = 60


async def process_job(repo: InvoiceRepository, processing_service: ProcessingService, document_id: str) -> None:
    """Claim and process one queued document; silently skips if already claimed."""
    invoice = await repo.get_by_document_id(document_id)
    if not invoice:
        logger.warning("Skipping %s: not found", document_id)
        return
    if invoice.status != InvoiceStatus.PROCESSING:
        logger.warning("Skipping %s: status is %s, not PROCESSING", document_id, invoice.status.value)
        return

    file_path = file_storage.get_original_file(document_id)
    if not file_path or not file_path.exists():
        # Mark error only if the status hasn't moved on (avoid stomping a concurrent finisher)
        await repo.update_status(document_id, InvoiceStatus.ERROR, InvoiceStatus.PROCESSING)
        logger.error("Original file missing for %s", document_id)
        return

    token = await repo.claim_ocr_job(
        document_id,
        stale_threshold_minutes=settings.processing_token_timeout_minutes,
    )
    if token is None:
        logger.info("Skipping %s: already claimed by another worker", document_id)
        return

    status = await run_processing(
        repo, processing_service, document_id, file_path.read_bytes(), invoice.original_filename,
        processing_token=token,
    )
    logger.info("Processed %s -> %s", document_id, status.value)


async def recovery_sweep(repo: InvoiceRepository, queue: JobQueue) -> int:
    """Re-queue PROCESSING documents with no token or a stale claim, so they are not lost.

    Documents claimed recently (within the timeout window) are left alone — they are
    still being processed by their worker.
    """
    stale_threshold = settings.processing_token_timeout_minutes
    stuck = await repo.find_unclaimed_processing_jobs(stale_threshold_minutes=stale_threshold)
    for document_id in stuck:
        await queue.enqueue(document_id)
        logger.info("Recovery sweep re-queued %s", document_id)
    if stuck:
        logger.info("Recovery sweep re-queued %d document(s)", len(stuck))
    return len(stuck)


async def run_worker(stop: asyncio.Event) -> None:
    queue = create_job_queue()
    if queue is None:
        raise SystemExit("REDIS_URL is not set; nothing for the worker to consume")
    db.connect()
    repo = InvoiceRepository(db.get_database())
    processing_service = ProcessingService()

    requeued = await recovery_sweep(repo, queue)
    logger.info("Worker started (re-queued %d interrupted documents)", requeued)

    last_sweep = time.monotonic()
    try:
        while not stop.is_set():
            try:
                document_id = await queue.dequeue(timeout=2)
                if document_id:
                    await process_job(repo, processing_service, document_id)
            except Exception:
                logger.exception("Worker iteration failed")
                await asyncio.sleep(2)

            # Periodic recovery sweep for jobs that slipped through (Redis restart, etc.)
            if time.monotonic() - last_sweep >= RECOVERY_SWEEP_INTERVAL:
                await recovery_sweep(repo, queue)
                last_sweep = time.monotonic()
    finally:
        await queue.close()
        db.close()
        logger.info("Worker stopped")


def main() -> None:
    configure_logging(settings.log_level, json_logs=settings.environment != "development")
    loop = asyncio.new_event_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    loop.run_until_complete(run_worker(stop))


if __name__ == "__main__":
    main()
