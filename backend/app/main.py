from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import time
import uuid
import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import Base, engine
from app.routers import products

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Caffeine Ratio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_request_id(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start = time.time()
    response = await call_next(request)
    elapsed_ms = round((time.time() - start) * 1000, 2)

    response.headers["X-Request-ID"] = request_id
    logger.info(
        "[%s] %s %s -> %s (%.2fms)",
        request_id[:8],
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# --------------- Exception Handlers ---------------


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "request_id": _get_request_id(request),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    return JSONResponse(
        status_code=422,
        content={
            "detail": jsonable_encoder(exc.errors()),
            "status_code": 422,
            "request_id": _get_request_id(request),
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning(
        "[%s] Database integrity error: %s",
        _get_request_id(request),
        str(exc.orig),
    )
    return JSONResponse(
        status_code=409,
        content={
            "detail": "Database integrity constraint violated",
            "status_code": 409,
            "request_id": _get_request_id(request),
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(
        "[%s] Value error: %s",
        _get_request_id(request),
        str(exc),
    )
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "status_code": 400,
            "request_id": _get_request_id(request),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "[%s] Unhandled exception: %s",
        _get_request_id(request),
        str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500,
            "request_id": _get_request_id(request),
        },
    )


# --------------- Routes ---------------

app.include_router(products.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
