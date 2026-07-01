from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health", summary="Health check")
async def health():
    return {"status": "ok", "version": settings.app_version}
