import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from api import router as api_router
from api.websockets import router as ws_router

from config.db import connect_db

connect_db()

app = FastAPI(
    title="Synthetic Data Generation",
    docs_url=None if Config.ENV == "prod" else "/docs",
    redoc_url=None if Config.ENV == "prod" else "/redoc",
)

# Configure CORS - Update these settings
origins = [
    "http://localhost:3000",  # React default port
    "http://localhost:5173",  # Vite default port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://localhost:5174",  # Another common Vite port
    "http://localhost:8000",  # Another common dev port
    "http://localhost",       # Any port on localhost
    "*",                      # For development, allow all origins (remove in production)
    # Add any other origins you need
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if Config.ENV == "prod" else ["*"],  # More permissive in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Print debugging information at startup
print(f"API running in {Config.ENV} mode")
print(f"CORS origins: {origins if Config.ENV == 'prod' else 'All origins (*) allowed in development'}")

# Include routers
app.include_router(api_router, prefix="/api")
app.include_router(ws_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to the Synthetic Data Generation API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=Config.API_PORT)
