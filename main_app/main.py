from fastapi import FastAPI
from database import engine  , Base
from models import *

from routers.users import router as users_router
from routers.categories import router as categories_router
from routers.products import router as products_router
from routers.orders import router as orders_router
from routers.shopping_cart import router as shopping_cart_router
from routers.monitoring import router as monitoring_router
import redis.asyncio as redis
import time
from fastapi import Request
from fastapi.responses import FileResponse, RedirectResponse, PlainTextResponse
from pathlib import Path
from core.logging_config import logger
from prometheus_fastapi_instrumentator import Instrumentator


app = FastAPI(title="E-Commerce app")
#Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
Instrumentator().instrument(app).expose(app)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(products_router)
app.include_router(categories_router)
app.include_router(orders_router)
app.include_router(shopping_cart_router)
app.include_router(monitoring_router)

from core.metrics import metrics_data

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    metrics_data["total_requests"] += 1

    try:
        response = await call_next(request)
        if response.status_code >= 500:
            metrics_data["total_errors"] += 1
    except Exception as exc:
        metrics_data["total_errors"] += 1
        duration = round(time.time() - start_time, 4)
        metrics_data["total_response_time"] += duration
        logger.error(f"{request.method} {request.url.path} Status: 500 Duration: {duration}s - {str(exc)}")
        raise

    duration = round(time.time() - start_time, 4)
    metrics_data["total_response_time"] += duration

    logger.info(
        f"{request.method} "
        f"{request.url.path} "
        f"Status: {response.status_code} "
        f"Duration: {duration}s"
    )

    return response

@app.get("/health")
def health_check():
    logger.debug("Health check requested")
    return {"status": "ok", "service": "E-Commerce API"}

async def get_redis():
    client = redis.from_url("redis://localhost:6379")
    try:
        yield client
    finally:
        await client.close() 

# ==========================================
# Serve Frontend Static Files
# ==========================================
FRONTEND_ROOT = Path(__file__).resolve().parent.parent / "frontend"

def safe_path(route):
    candidate = (FRONTEND_ROOT / route).resolve()
    try:
        candidate.relative_to(FRONTEND_ROOT)
    except ValueError:
        return None
    return candidate

@app.get("/{route:path}")
async def frontend(route: str, incoming: Request):
    if route.endswith(".html"):
        clean_route = route[:-5]
        location = "/" if clean_route == "index" else f"/{clean_route}"
        if incoming.url.query:
            location = f"{location}?{incoming.url.query}"
        return RedirectResponse(location, status_code=301)

    if not route or route == "/":
        route = "index.html"

    file_path = safe_path(route)
    if file_path and file_path.is_file():
        return FileResponse(file_path)

    if file_path and file_path.is_dir() and (file_path / "index.html").is_file():
        return FileResponse(file_path / "index.html")

    if "." not in Path(route).name:
        html_path = safe_path(f"{route}.html")
        if html_path and html_path.is_file():
            return FileResponse(html_path)

    return PlainTextResponse("Not found", status_code=404)
