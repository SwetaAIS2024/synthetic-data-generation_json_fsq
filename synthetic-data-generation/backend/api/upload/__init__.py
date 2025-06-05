from fastapi import APIRouter
from .routes import router as index_router

router = APIRouter()

router.include_router(index_router)
