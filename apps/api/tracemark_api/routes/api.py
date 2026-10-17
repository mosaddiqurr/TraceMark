from fastapi import APIRouter

from . import workflows

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(workflows.router)
