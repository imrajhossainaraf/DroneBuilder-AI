from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from models.database import connect_db, close_db
from routes.chat import router as chat_router
from routes.components import router as components_router
from routes.guides import router as guides_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="DroneMate API",
    description="Intelligent drone building and troubleshooting assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS – allow frontend served from any origin (localhost dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(chat_router)
app.include_router(components_router)
app.include_router(guides_router)

# Serve frontend static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
frontend_path = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

if os.path.exists(frontend_path):
    print(f"✅ Found frontend at: {frontend_path}")
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))
    
    @app.get("/{path:path}", include_in_schema=False)
    async def catch_all(path: str):
        file_path = os.path.join(frontend_path, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_path, "index.html"))


if __name__ == "__main__":
    import uvicorn
    from config import APP_HOST, APP_PORT, APP_DEBUG
    uvicorn.run("app:app", host=APP_HOST, port=APP_PORT, reload=APP_DEBUG)
