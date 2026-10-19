from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.schemas import AnalysisResponse
from app.services.upload_service import parse_upload

router = APIRouter(prefix="/api")


@router.post("/uploads", response_model=AnalysisResponse)
async def upload_syslog(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    return parse_upload(file.filename, content)
