"""API-owned bounded queue orchestration. No worker imports or database writes."""
import asyncio
from contextlib import asynccontextmanager
import logging

from redis.exceptions import RedisError

from app.modules.compute_orchestrator.dispatcher import dispatch_compute_job
from app.modules.compute_orchestrator.errors import ComputeTimeout, ComputeUnavailable, InvalidComputeResult
from app.modules.compute_orchestrator.ingestion import discard_finding_result, fetch_finding_result
from shared.schemas.finding_result import FindingResult
from shared.schemas.job_bundle import JobBundle

logger = logging.getLogger(__name__)


def validate_result(bundle: JobBundle, finding: FindingResult) -> FindingResult:
    if (finding.job_id != bundle.job_id or finding.version_id != bundle.version_id
            or finding.target_entity_type != bundle.target_entity_type
            or finding.target_entity_id != bundle.target_entity_id
            or finding.bundle_sha256 != bundle.fingerprint()):
        raise InvalidComputeResult("Result does not match the staged input")
    if finding.diagnostic_code == "COMPUTE_TIMEOUT_EXCEEDED":
        raise ComputeTimeout("Compute execution timed out")
    layers = finding.layer_findings
    if (not layers or set(layers) != set(range(1, 7))
            or any(key != item.layer for key, item in layers.items())):
        raise InvalidComputeResult("Incomplete or mismatched pipeline layers")
    return finding


@asynccontextmanager
async def compute_job(bundle: JobBundle):
    """Yield one correlated result; caller commits before result disposal.

    Duplicate IDs fail closed. No background ingestion occurs after timeout or
    cancellation. Late worker results expire in Redis and cannot attach to a new
    UUID. A failed DB commit never becomes a successful HTTP response.
    """
    dispatched = False
    try:
        try:
            async with asyncio.timeout(bundle.timeout_seconds + 5):
                await dispatch_compute_job(bundle)
                dispatched = True
                while True:
                    finding = await fetch_finding_result(bundle.job_id)
                    if finding is not None:
                        finding = validate_result(bundle, finding)
                        break
                    await asyncio.sleep(0.05)
        except TimeoutError as exc:
            raise ComputeTimeout("Compute queue deadline exceeded") from exc
        except RedisError as exc:
            raise ComputeUnavailable("Compute queue is unavailable") from exc
        yield finding
    finally:
        if dispatched:
            try:
                async with asyncio.timeout(2):
                    await discard_finding_result(bundle.job_id)
            except (RedisError, TimeoutError):
                # Result TTL is the cleanup backstop; never mask a DB outcome.
                logger.warning("Compute result cleanup unavailable; expiration will remove it")
