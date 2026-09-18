"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import health, optimize
from app.config import get_settings
from app.core.exceptions import GridWiseError, to_http_exception
from app.core.logging import get_logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    log = get_logger("startup")
    settings = get_settings()
    log.info(
        "app_starting",
        app=settings.app_name,
        env=settings.app_env,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
    )
    yield
    log.info("app_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="GridWise API",
        version="0.1.0",
        description="LLM-assisted smart campus energy optimization",
        lifespan=lifespan,
    )

    # Routes
    app.include_router(health.router)
    app.include_router(optimize.router)

    # ---- Exception handlers ----
    @app.exception_handler(GridWiseError)
    async def gridwise_handler(request: Request, exc: GridWiseError):
        http_exc = to_http_exception(exc)
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"error": http_exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"error": "Invalid request", "detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        log = get_logger("error")
        log.error("unhandled_exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )

    return app


app = create_app()