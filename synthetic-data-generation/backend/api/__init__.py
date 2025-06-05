from fastapi import APIRouter

from .upload import router as upload_router
from .generate.generation import router as generation_router

router = APIRouter()

# Register routers
router.include_router(upload_router, prefix="/upload")
router.include_router(generation_router, prefix="/generation")

# Print debug info
print("API Routes registered:")
print(f"- /api/upload/* routes registered")
print(f"- /api/generation/* routes registered")
