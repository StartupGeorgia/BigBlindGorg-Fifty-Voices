"""InXPhone (MOR/Kolmisoft) API endpoints.

Dedicated endpoints for MOR-specific features:
- Invoice retrieval
- Recording retrieval and sync
- SIP device status
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.telephony import get_inxphone_service
from app.core.auth import CurrentUser
from app.db.session import get_db
from app.models.call_record import CallRecord

router = APIRouter(prefix="/api/v1/inxphone", tags=["inxphone"])
logger = structlog.get_logger()


@router.get("/invoices")
async def get_invoices(
    current_user: CurrentUser,
    from_date: int = Query(..., description="Start timestamp (Unix epoch)"),
    till_date: int = Query(..., description="End timestamp (Unix epoch)"),
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Query(..., description="Workspace ID for API key isolation"),
) -> list[dict]:
    """Get invoices from MOR billing system.

    Args:
        current_user: Authenticated user
        from_date: Start timestamp (Unix epoch)
        till_date: End timestamp (Unix epoch)
        db: Database session
        workspace_id: Workspace ID for workspace-specific API keys

    Returns:
        List of invoice records
    """
    try:
        workspace_uuid = uuid.UUID(workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid workspace_id format") from e

    service = await get_inxphone_service(current_user.id, db, workspace_id=workspace_uuid)
    if not service:
        raise HTTPException(
            status_code=400,
            detail="InXPhone credentials not configured. Please add them in Settings.",
        )

    try:
        invoices = await service.get_invoices(from_date, till_date)
        return invoices
    except Exception as e:
        logger.exception("inxphone_invoices_error", error=str(e))
        raise HTTPException(status_code=502, detail=f"Failed to fetch invoices: {e}") from e
    finally:
        await service.close()


@router.get("/recordings")
async def get_recordings(
    current_user: CurrentUser,
    date_from: int = Query(..., description="Start timestamp (Unix epoch)"),
    date_till: int = Query(..., description="End timestamp (Unix epoch)"),
    source: str | None = Query(None, description="Filter by source number"),
    destination: str | None = Query(None, description="Filter by destination number"),
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Query(..., description="Workspace ID for API key isolation"),
) -> list[dict]:
    """Get call recordings from MOR.

    Args:
        current_user: Authenticated user
        date_from: Start timestamp (Unix epoch)
        date_till: End timestamp (Unix epoch)
        source: Filter by source number
        destination: Filter by destination number
        db: Database session
        workspace_id: Workspace ID for workspace-specific API keys

    Returns:
        List of recording records
    """
    try:
        workspace_uuid = uuid.UUID(workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid workspace_id format") from e

    service = await get_inxphone_service(current_user.id, db, workspace_id=workspace_uuid)
    if not service:
        raise HTTPException(
            status_code=400,
            detail="InXPhone credentials not configured. Please add them in Settings.",
        )

    try:
        recordings = await service.get_recordings(
            date_from=date_from,
            date_till=date_till,
            source=source,
            destination=destination,
        )
        return recordings
    except Exception as e:
        logger.exception("inxphone_recordings_error", error=str(e))
        raise HTTPException(status_code=502, detail=f"Failed to fetch recordings: {e}") from e
    finally:
        await service.close()


@router.post("/recordings/{call_id}/sync")
async def sync_recording(
    call_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Query(..., description="Workspace ID for API key isolation"),
) -> dict[str, str]:
    """Fetch recording from MOR and attach to CallRecord.

    Args:
        call_id: CallRecord ID (UUID)
        current_user: Authenticated user
        db: Database session
        workspace_id: Workspace ID for workspace-specific API keys

    Returns:
        Sync result
    """
    try:
        workspace_uuid = uuid.UUID(workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid workspace_id format") from e

    # Find the call record
    try:
        call_uuid = uuid.UUID(call_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid call_id format") from e

    result = await db.execute(
        select(CallRecord).where(
            CallRecord.id == call_uuid,
            CallRecord.provider == "inxphone",
        )
    )
    call_record = result.scalar_one_or_none()

    if not call_record:
        raise HTTPException(status_code=404, detail="InXPhone call record not found")

    service = await get_inxphone_service(current_user.id, db, workspace_id=workspace_uuid)
    if not service:
        raise HTTPException(
            status_code=400,
            detail="InXPhone credentials not configured.",
        )

    try:
        recording = await service.get_recording_for_call(call_record.provider_call_id)
        if not recording:
            return {"message": "No recording found for this call"}

        # Update call record with recording URL
        mp3_url = recording.get("mp3_url") or recording.get("url")
        if mp3_url:
            call_record.recording_url = mp3_url

        # Update duration if available
        duration = recording.get("duration") or recording.get("billsec")
        if duration:
            call_record.duration_seconds = int(float(duration))

        await db.commit()
        return {"message": "Recording synced successfully", "recording_url": mp3_url or ""}
    except Exception as e:
        logger.exception("inxphone_recording_sync_error", error=str(e))
        raise HTTPException(status_code=502, detail=f"Failed to sync recording: {e}") from e
    finally:
        await service.close()


@router.get("/device/status")
async def get_device_status(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Query(..., description="Workspace ID for API key isolation"),
) -> dict:
    """Get SIP device registration status from MOR.

    Args:
        current_user: Authenticated user
        db: Database session
        workspace_id: Workspace ID for workspace-specific API keys

    Returns:
        Device details including registration status
    """
    try:
        workspace_uuid = uuid.UUID(workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid workspace_id format") from e

    service = await get_inxphone_service(current_user.id, db, workspace_id=workspace_uuid)
    if not service:
        raise HTTPException(
            status_code=400,
            detail="InXPhone credentials not configured. Please add them in Settings.",
        )

    try:
        details = await service.get_device_details()
        return details
    except Exception as e:
        logger.exception("inxphone_device_status_error", error=str(e))
        raise HTTPException(status_code=502, detail=f"Failed to fetch device status: {e}") from e
    finally:
        await service.close()
