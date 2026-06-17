from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.schemas import (
    FlowExportResponse,
    FlowResponse,
    MessageDetail,
    SessionDetail,
    SessionSummary,
    UploadResponse,
)
from app.services.upload_service import (
    get_message_detail,
    get_session_detail,
    get_session_flow,
    get_session_flow_export,
    get_upload,
    list_sessions,
    process_upload,
    upload_to_response,
)

router = APIRouter(prefix="/api")


@router.post("/uploads", response_model=UploadResponse)
async def upload_syslog(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    upload = await process_upload(db, file.filename, content)
    return upload_to_response(upload)


@router.get("/uploads/{upload_id}", response_model=UploadResponse)
async def read_upload(upload_id: str, db: AsyncSession = Depends(get_db)):
    upload = await get_upload(db, upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload_to_response(upload)


@router.get("/uploads/{upload_id}/sessions", response_model=list[SessionSummary])
async def read_sessions(
    upload_id: str,
    sid: str | None = Query(default=None),
    call_id: str | None = Query(default=None),
    from_header: str | None = Query(default=None, alias="from"),
    to_header: str | None = Query(default=None, alias="to"),
    method: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    upload = await get_upload(db, upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    return await list_sessions(
        db,
        upload_id,
        sid=sid,
        call_id=call_id,
        from_header=from_header,
        to_header=to_header,
        method=method,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def read_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await get_session_detail(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/flow", response_model=FlowResponse)
async def read_session_flow(session_id: str, db: AsyncSession = Depends(get_db)):
    flow = await get_session_flow(db, session_id)
    if flow is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return flow


@router.get("/sessions/{session_id}/flow/export", response_model=FlowExportResponse)
async def export_session_flow(session_id: str, db: AsyncSession = Depends(get_db)):
    export = await get_session_flow_export(db, session_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return export


@router.get("/messages/{message_id}", response_model=MessageDetail)
async def read_message(message_id: str, db: AsyncSession = Depends(get_db)):
    message = await get_message_detail(db, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return message
