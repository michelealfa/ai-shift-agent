from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import logging

from .bot.handlers import handle_webhook
from .admin.routes import router as admin_router
from .api.shift_routes import router as shift_router
from .api.user_routes import router as user_router
from .database import init_db, close_db
from .cache import init_cache, close_cache

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Shift Agent API")

# Ensure directories exist
os.makedirs("src/admin/templates", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True) # Ensure main templates directory exists

# Configure Jinja2Templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register Admin Router
app.include_router(admin_router)
app.include_router(shift_router)
app.include_router(user_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database and cache on startup"""
    logger.info("🚀 Starting AI Shift Agent API...")
    
    try:
        # Initialize database
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"⚠️  Database initialization failed: {e}")
        logger.warning("Application will continue without database features")
    
    try:
        # Initialize Redis cache
        init_cache()
        logger.info("✅ Redis cache initialized")
    except Exception as e:
        logger.error(f"⚠️  Redis cache initialization failed: {e}")
        logger.warning("Application will continue without caching")
    
    logger.info("✅ AI Shift Agent API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database and cache connections on shutdown"""
    logger.info("🛑 Shutting down AI Shift Agent API...")
    
    try:
        close_db()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
    
    try:
        close_cache()
        logger.info("✅ Redis cache connections closed")
    except Exception as e:
        logger.error(f"Error closing cache: {e}")
    
    logger.info("✅ AI Shift Agent API shut down successfully")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint with database and cache status"""
    from .database import db_manager
    from .cache import redis_cache
    
    db_healthy = db_manager.health_check()
    cache_healthy = redis_cache.health_check()
    
    return {
        "status": "ok" if (db_healthy and cache_healthy) else "degraded",
        "database": "healthy" if db_healthy else "unhealthy",
        "cache": "healthy" if cache_healthy else "unhealthy"
    }

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    await handle_webhook(data)
    return {"status": "ok"}

