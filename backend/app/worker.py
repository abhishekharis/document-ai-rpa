"""Background OCR worker: python -m app.worker

Pops document IDs from the Redis queue and runs the processing pipeline on them.
"""
import asyncio
import logging
import signal

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


async def process_job(repo: InvoiceRepository, processing_service: ProcessingService, document_id: str) -> None:
    """Run one queued document; documents that are gone or no longer PROCESSING are skipped."""
    invoice = await repo.get_by_document_id(document_id)
    if not invoice or invoice.status != InvoiceStatus.PROCESSING:
        logger.warning("Skipping %s: %s", document_id, invoice.status.value if invoice else "not found")
        return
    file_path = file_storage.get_original_file(document_id)
    if not file_path or not file_path.exists():
        await repo.update_status(document_id, InvoiceStatus.ERROR, InvoiceStatus.PROCESSING)
        logger.error("Original file missing for %s", document_id)
        return
    status = await run_processing(
        repo, processing_service, document_id, file_path.read_bytes(), invoice.original_filename
    )
    logger.info("Processed %s -> %s", document_id, status.value)


async def requeue_interrupted(repo: InvoiceRepository, queue: JobQueue) -> int:
    """Re-queue documents left in PROCESSING by a worker that died mid-job."""
    stuck = await repo.list_document_ids_by_status(InvoiceStatus.PROCESSING)
    for document_id in stuck:
        await queue.enqueue(document_id)
    return len(stuck)


async def run_worker(stop: asyncio.Event) -> None:
    queue = create_job_queue()
    if queue is None:
        raise SystemExit("REDIS_URL is not set; nothing for the worker to consume")
    db.connect()
    repo = InvoiceRepository(db.get_database())
    processing_service = ProcessingService()
    requeued = await requeue_interrupted(repo, queue)
    logger.info("Worker started (re-queued %d interrupted documents)", requeued)
    try:
        while not stop.is_set():
            try:
                document_id = await queue.dequeue(timeout=2)
                if document_id:
                    await process_job(repo, processing_service, document_id)
            except Exception:
                logger.exception("Worker iteration failed")
                await asyncio.sleep(2)
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
