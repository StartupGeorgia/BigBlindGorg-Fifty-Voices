"""InXPhone recording sync service.

Periodically fetches recordings from MOR for InXPhone calls
and updates CallRecords with recording URLs and durations.
"""

import asyncio
import contextlib

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.settings import get_user_api_keys
from app.db.session import AsyncSessionLocal
from app.models.call_record import CallRecord
from app.services.telephony.inxphone_service import InXPhoneService

logger = structlog.get_logger()

SYNC_INTERVAL_SECONDS = 60  # Check for unsynced recordings every minute


class InXPhoneRecordingSync:
    """Background worker that syncs recordings from MOR to CallRecords."""

    def __init__(self):
        self.running = False
        self.logger = logger.bind(component="inxphone_recording_sync")
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the recording sync background task."""
        if self.running:
            self.logger.warning("Recording sync already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._run_loop())
        self.logger.info("InXPhone recording sync started")

    async def stop(self) -> None:
        """Stop the recording sync."""
        self.running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        self.logger.info("InXPhone recording sync stopped")

    async def _run_loop(self) -> None:
        """Main sync loop."""
        while self.running:
            try:
                await self._sync_recordings()
            except Exception:
                self.logger.exception("Error in recording sync loop")

            await asyncio.sleep(SYNC_INTERVAL_SECONDS)

    async def _sync_recordings(self) -> None:
        """Find InXPhone calls without recordings and fetch them from MOR."""
        async with AsyncSessionLocal() as db:
            # Find InXPhone calls that don't have recordings yet
            result = await db.execute(
                select(CallRecord)
                .where(
                    CallRecord.provider == "inxphone",
                    CallRecord.recording_url.is_(None),
                    CallRecord.status.in_(["completed", "in_progress"]),
                )
                .limit(50)
            )
            unsynced_records = result.scalars().all()

            if not unsynced_records:
                return

            self.logger.debug("Found unsynced InXPhone calls", count=len(unsynced_records))

            # Group by user_id + workspace_id to minimize service instantiation
            groups: dict[tuple, list[CallRecord]] = {}
            for record in unsynced_records:
                key = (record.user_id, record.workspace_id)
                groups.setdefault(key, []).append(record)

            for (user_id, workspace_id), records in groups.items():
                await self._sync_group(user_id, workspace_id, records, db)

    async def _sync_group(
        self,
        user_id,
        workspace_id,
        records: list[CallRecord],
        db: AsyncSession,
    ) -> None:
        """Sync recordings for a group of calls belonging to the same user/workspace."""
        user_settings = await get_user_api_keys(user_id, db, workspace_id=workspace_id)

        if (
            not user_settings
            or not user_settings.inxphone_username
            or not user_settings.inxphone_api_key
            or not user_settings.inxphone_device_id
            or not user_settings.inxphone_server_url
            or not user_settings.inxphone_ai_number
        ):
            return

        service = InXPhoneService(
            username=user_settings.inxphone_username,
            api_key=user_settings.inxphone_api_key,
            device_id=user_settings.inxphone_device_id,
            server_url=user_settings.inxphone_server_url,
            ai_number=user_settings.inxphone_ai_number,
        )

        try:
            for record in records:
                try:
                    recording = await service.get_recording_for_call(record.provider_call_id)

                    if not recording:
                        continue

                    # Update recording URL
                    mp3_url = recording.get("mp3_url") or recording.get("url")
                    if mp3_url:
                        record.recording_url = mp3_url

                    # Update duration
                    duration = recording.get("duration") or recording.get("billsec")
                    if duration:
                        record.duration_seconds = int(float(duration))

                    # Mark as completed if recording exists
                    if record.status == "in_progress":
                        record.status = "completed"

                    self.logger.info(
                        "Recording synced",
                        record_id=str(record.id),
                        recording_url=mp3_url,
                    )

                except Exception:
                    self.logger.exception(
                        "Failed to sync recording",
                        record_id=str(record.id),
                    )

            await db.commit()
        finally:
            await service.close()


# Global instance
_recording_sync: InXPhoneRecordingSync | None = None


async def start_recording_sync() -> InXPhoneRecordingSync:
    """Start the global recording sync worker."""
    global _recording_sync
    if _recording_sync is None:
        _recording_sync = InXPhoneRecordingSync()
        await _recording_sync.start()
    return _recording_sync


async def stop_recording_sync() -> None:
    """Stop the global recording sync worker."""
    global _recording_sync
    if _recording_sync:
        await _recording_sync.stop()
        _recording_sync = None
