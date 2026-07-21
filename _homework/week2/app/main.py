import uvicorn

from app.api.app import create_fastapi_app
from app.config import Settings
from app.ioc import create_container

settings = Settings()
container = create_container(settings)
app = create_fastapi_app(settings, container)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.reload,
    )
