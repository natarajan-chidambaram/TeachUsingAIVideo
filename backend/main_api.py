import time as time_module
import logging
import os
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic_classes import *
from sql_alchemy import *
from database import get_db, integrity_error_detail
from routers import video as video_router
from routers import subtitle as subtitle_router
from routers import scene as scene_router
from routers import playersettings as playersettings_router
from routers import playersettings_methods as playersettings_methods_router
from routers import player_languages as player_languages_router
from routers import character as character_router
from routers import audiotrack as audiotrack_router
from routers import animation as animation_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title='Class_Diagram API',
    description='Auto-generated REST API with full CRUD operations, relationship management, and advanced features',
    version='1.0.0',
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "System", "description": "System health and statistics"},
        {"name": "Video", "description": "Operations for Video entities"},
        {"name": "Video Relationships", "description": "Manage Video relationships"},
        {"name": "Subtitle", "description": "Operations for Subtitle entities"},
        {"name": "Subtitle Relationships", "description": "Manage Subtitle relationships"},
        {"name": "Scene", "description": "Operations for Scene entities"},
        {"name": "Scene Relationships", "description": "Manage Scene relationships"},
        {"name": "PlayerSettings", "description": "Operations for PlayerSettings entities"},
        {"name": "PlayerSettings Relationships", "description": "Manage PlayerSettings relationships"},
        {"name": "PlayerSettings Methods", "description": "Execute PlayerSettings methods"},
        {"name": "Character", "description": "Operations for Character entities"},
        {"name": "Character Relationships", "description": "Manage Character relationships"},
        {"name": "AudioTrack", "description": "Operations for AudioTrack entities"},
        {"name": "AudioTrack Relationships", "description": "Manage AudioTrack relationships"},
        {"name": "Animation", "description": "Operations for Animation entities"},
        {"name": "Animation Relationships", "description": "Manage Animation relationships"},
    ]
)

# Enable CORS for all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or restrict to ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

############################################
#
#   Middleware
#
############################################

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses."""
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to all responses."""
    start_time = time_module.time()
    response = await call_next(request)
    process_time = time_module.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

############################################
#
#   Exception Handlers
#
############################################

# Global exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions."""
    # The client sees a 400; the server log keeps the traceback of the real cause.
    logger.exception("ValueError on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Bad Request",
            "message": str(exc),
            "detail": "Invalid input data provided"
        }
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors."""
    logger.error(f"Database integrity error: {exc}")

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "Conflict",
            "message": "Data conflict occurred",
            "detail": integrity_error_detail(exc)
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Handle general SQLAlchemy errors."""
    logger.exception(f"Database error: {exc}", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "Database operation failed",
            "detail": "An internal database error occurred"
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format.

    `detail` carries the endpoint's actual message — clients (including the
    generated frontend dialog) read it to show the user what went wrong.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "message": exc.detail,
            "detail": exc.detail
        }
    )

############################################
#
#   Routers
#
############################################

app.include_router(video_router.router)
app.include_router(subtitle_router.router)
app.include_router(scene_router.router)
app.include_router(playersettings_router.router)
app.include_router(playersettings_methods_router.router)
app.include_router(player_languages_router.router)
app.include_router(character_router.router)
app.include_router(audiotrack_router.router)
app.include_router(animation_router.router)

############################################
#
#   Global API endpoints
#
############################################

@app.get("/", tags=["System"])
def root():
    """Root endpoint - API information"""
    return {
        "name": app.title,
        "version": app.version,
        "status": "running"
    }


@app.get("/health", tags=["System"])
def health_check(database: Session = Depends(get_db)):
    """Health check endpoint for monitoring.

    Actually touches the database — a health check that hardcodes
    "connected" is worse than none.
    """
    from datetime import datetime
    from sqlalchemy import text as _sql_text
    try:
        database.execute(_sql_text("SELECT 1"))
        db_status = "connected"
    except Exception:
        raise HTTPException(status_code=503, detail={
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database": "error",
        })
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
    }


@app.get("/statistics", tags=["System"])
def get_statistics(database: Session = Depends(get_db)):
    """Get database statistics for all entities"""
    stats = {}
    stats["video_count"] = database.query(Video).count()
    stats["subtitle_count"] = database.query(Subtitle).count()
    stats["scene_count"] = database.query(Scene).count()
    stats["playersettings_count"] = database.query(PlayerSettings).count()
    stats["character_count"] = database.query(Character).count()
    stats["audiotrack_count"] = database.query(AudioTrack).count()
    stats["animation_count"] = database.query(Animation).count()
    stats["total_entities"] = sum(stats.values())
    return stats


############################################
#
#   Static media and the built frontend
#
############################################
# The lesson's poster, audio and subtitle files live under backend/media, and
# the production build of the React frontend under frontend/dist. Both are
# served by this same process.
#
# The media mount is registered first and the frontend is served by an
# explicit catch-all route at the very bottom: a `app.mount("/", ...)` placed
# anywhere above the API routes would swallow every one of them, because
# Starlette matches mounts in registration order.

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)

_MEDIA_DIR = os.path.join(_BACKEND_DIR, "media")
if os.path.isdir(_MEDIA_DIR):
    app.mount("/media", StaticFiles(directory=_MEDIA_DIR), name="media")

_FRONTEND_DIST = os.path.join(_PROJECT_ROOT, "frontend", "dist")

if os.path.isdir(_FRONTEND_DIST):
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        """Serve the built React app, falling back to index.html for client routes."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = os.path.normpath(os.path.join(_FRONTEND_DIST, full_path))
        # Never escape the dist directory.
        if candidate.startswith(_FRONTEND_DIST) and os.path.isfile(candidate):
            return FileResponse(candidate)
        index_file = os.path.join(_FRONTEND_DIST, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Not Found")


############################################
# Maintaining the server
############################################
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)