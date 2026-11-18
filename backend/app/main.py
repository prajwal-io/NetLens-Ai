import logging
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from app.api.routes import router
from app.core.config import settings
from app.db.database import initialize
from app.services.model_service import model_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    if bool(settings.supabase_url) != bool(settings.supabase_publishable_key):
        raise RuntimeError("Set both NETSIGHT_SUPABASE_URL and NETSIGHT_SUPABASE_PUBLISHABLE_KEY, or leave both unset.")
    if settings.storage_backend == "supabase" and not settings.supabase_url:
        raise RuntimeError("Supabase storage requires NETSIGHT_SUPABASE_URL and NETSIGHT_SUPABASE_PUBLISHABLE_KEY.")
    if settings.storage_backend == "sqlite":
        initialize()
    model_service.load()
    app.state.supabase_auth_client = (
        httpx.AsyncClient(base_url=settings.supabase_url.rstrip("/"), timeout=httpx.Timeout(8.0, connect=3.0))
        if settings.supabase_url else None
    )
    try:
        yield
    finally:
        if app.state.supabase_auth_client is not None:
            await app.state.supabase_auth_client.aclose()

app = FastAPI(title="NetSight AI", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type"])
app.include_router(router)

@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.status_code, "message": str(exc.detail)}}, headers=exc.headers)

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    csv_routes = {"/api/v1/traffic/validate", "/api/v1/traffic/analyze"}
    missing_file = any(
        error.get("type") == "missing" and error.get("loc", ())[-1:] == ("file",)
        for error in exc.errors()
    )
    message = (
        "A CSV file is required in the multipart 'file' field."
        if request.url.path in csv_routes and missing_file
        else "Request parameters or fields are invalid."
    )
    return JSONResponse(status_code=422, content={"error": {"code": 422, "message": message}})

@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logging.getLogger(__name__).exception("Unhandled API error")
    return JSONResponse(status_code=500, content={"error": {"code": 500, "message": "An unexpected server error occurred."}})
