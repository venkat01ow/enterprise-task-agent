"""Development launcher for the Enterprise Task Agent."""
import uvicorn

from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=not settings.is_production,
        log_config=None,  # the app configures logging itself
    )
