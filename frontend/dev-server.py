from pathlib import Path
from urllib import error, request
import argparse
import json

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response


FRONTEND_ROOT = Path(__file__).resolve().parent
BACKEND_URL = "http://127.0.0.1:8000"

app = FastAPI(title="HNU Store Frontend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def safe_path(route):
    candidate = (FRONTEND_ROOT / route).resolve()
    try:
        candidate.relative_to(FRONTEND_ROOT)
    except ValueError:
        return None
    return candidate


def response_from_backend(status, headers, body):
    response_headers = {
        key: value
        for key, value in headers.items()
        if key.lower() not in {"connection", "content-length", "transfer-encoding", "content-encoding"}
    }
    return Response(content=body, status_code=status, headers=response_headers)


async def proxy_to_backend(incoming, backend_path):
    body = await incoming.body()
    query = str(incoming.url.query)
    url = f"{BACKEND_URL}{backend_path}"
    if query:
        url = f"{url}?{query}"

    headers = {
        key: value
        for key, value in incoming.headers.items()
        if key.lower() not in {"host", "connection", "content-length"}
    }
    data = body if body else None
    proxied = request.Request(url, data=data, headers=headers, method=incoming.method)

    try:
        with request.urlopen(proxied, timeout=30) as proxied_response:
            return response_from_backend(proxied_response.status, proxied_response.headers, proxied_response.read())
    except error.HTTPError as exc:
        return response_from_backend(exc.code, exc.headers, exc.read())
    except error.URLError as exc:
        return JSONResponse({"detail": f"Backend is not reachable: {exc.reason}"}, status_code=502)


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def api_proxy(path: str, incoming: Request):
    return await proxy_to_backend(incoming, f"/api/{path}")


@app.api_route("/metrics", methods=["GET", "OPTIONS"])
async def metrics_proxy(incoming: Request):
    return await proxy_to_backend(incoming, "/metrics")


@app.get("/{route:path}")
async def frontend(route: str, incoming: Request):
    if route.endswith(".html"):
        clean_route = route[:-5]
        location = "/" if clean_route == "index" else f"/{clean_route}"
        if incoming.url.query:
            location = f"{location}?{incoming.url.query}"
        return RedirectResponse(location, status_code=301)

    if not route:
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


def main():
    parser = argparse.ArgumentParser(description="Serve the frontend with FastAPI and proxy API calls to FastAPI backend.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5500)
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    global BACKEND_URL
    BACKEND_URL = args.backend.rstrip("/")

    print(f"Frontend FastAPI: http://{args.host}:{args.port}/home")
    print(f"Backend FastAPI proxy: {BACKEND_URL}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
