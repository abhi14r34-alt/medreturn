"""MedReturn API entrypoint.

    uvicorn app.main:app --reload --port 8000

Swagger UI: http://localhost:8000/docs
"""

import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import admin, auth, collector, hospital, household, notifications
from app.core.config import settings
from app.ml import inference

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("medreturn")

app = FastAPI(
    title="MedReturn API",
    version="1.0.0",
    description=(
        "Smart mobile medical-waste collection and segregation system "
        "(SIH26115). Hospital segregation with a confidence gate, and "
        "household medicine return with pickup, tracking and credits.\n\n"
        "Simulated behaviour is always reported as such: responses that come "
        "from the demo path carry `inference_mode: DEMO` and `is_simulated: "
        "true`."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uploaded images. In production put these behind object storage and a
# signed-URL layer rather than serving the directory directly.
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

for router in (auth, household, hospital, admin, collector, notifications):
    app.include_router(router.router, prefix=settings.API_PREFIX)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Turn Pydantic errors into one readable sentence per field."""
    problems = []
    for error in exc.errors():
        field = ".".join(str(p) for p in error["loc"] if p not in ("body", "query"))
        problems.append(f"{field}: {error['msg']}" if field else error["msg"])
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Please check the form.", "problems": problems},
    )


@app.exception_handler(SQLAlchemyError)
async def database_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Never leak connection strings or SQL to the client."""
    logger.exception("Database error", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The database is unavailable. Try again shortly."},
    )


@app.get("/api/health", tags=["system"])
def health() -> dict:
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "inference": inference.model_status(),
    }


@app.on_event("startup")
def on_startup() -> None:
    state = inference.model_status()
    if state["mode"] == "DEMO":
        logger.warning(
            "DEMO MODE ACTIVE - no trained checkpoint loaded (%s). Analysis "
            "results are simulated and are labelled as such in every response.",
            state["load_error"],
        )
    else:
        logger.info("Real inference active: %s classes loaded.",
                    len(state["supported_classes"]))
