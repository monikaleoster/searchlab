from fastapi import FastAPI
from .web.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="SearchLab", docs_url=None, redoc_url=None)
    app.include_router(router)
    return app


app = create_app()
