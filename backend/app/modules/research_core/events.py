"""Transactional draft events. No relay or external side effects run in the save path."""
from datetime import datetime, timezone
import hashlib
import json
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def record_draft_event(db: AsyncSession, version_id: str, action: str, before, after):
    # Caller holds the project/version lock. The per-version audit chain is serialized.
    actor_id = db.info["research_actor_context"][0]
    now = datetime.now(timezone.utc)
    head = (await db.execute(text("""SELECT sequence, event_hash FROM draft_audit_events
        WHERE version_id=:id ORDER BY sequence DESC LIMIT 1"""), {"id": version_id})).mappings().one_or_none()
    sequence, previous = (head["sequence"] + 1, head["event_hash"]) if head else (1, "")
    payload = {"before": before, "after": after}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256((previous + actor_id + action + version_id + canonical + now.isoformat()).encode()).hexdigest()
    values = {"id": str(uuid.uuid4()), "version": version_id, "actor": actor_id, "action": action,
              "payload": canonical, "time": now, "previous": previous, "hash": digest, "sequence": sequence}
    await db.execute(text("""INSERT INTO draft_audit_events
        (id,version_id,actor_id,action,payload,created_at,prev_hash,event_hash,sequence)
        VALUES (:id,:version,:actor,:action,CAST(:payload AS json),:time,:previous,:hash,:sequence)"""), values)
    await db.execute(text("""INSERT INTO outbox_events(id,version_id,actor_id,action,payload,created_at)
        VALUES (:id,:version,:actor,:action,CAST(:payload AS json),:time)"""), values)
