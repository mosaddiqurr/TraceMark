from __future__ import annotations

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text

from ..schemas import HealthResponse

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request, response: Response) -> HealthResponse:
    database = "ready"
    sessions = "ready"
    try:
        with request.app.state.session_factory() as session:
            session.execute(text("SELECT 1"))
    except Exception:
        database = "unavailable"
    try:
        if request.app.state.redis is not None:
            await request.app.state.redis.ping()
    except Exception:
        sessions = "unavailable"
    overall = "ready" if database == sessions == "ready" else "degraded"
    if overall != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status=overall, database=database, sessions=sessions)

