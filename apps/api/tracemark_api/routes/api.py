from fastapi import APIRouter

from . import assets, auth, jobs, system, workflows

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(assets.router)
api_router.include_router(jobs.router)
api_router.include_router(system.router)
api_router.include_router(workflows.router)

