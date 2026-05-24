from fastapi import APIRouter

from app.services.runtime_stats import runtime_stats


router = APIRouter(prefix="/api/runtime", tags=["runtime"])


@router.get("/stats")
def get_runtime_stats() -> dict:
    return runtime_stats.snapshot()
