import json
import sys
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

EMAIL = "23f3003379@ds.study.iitm.ac.in"
START = time.monotonic()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

REQUEST_COUNT = 0                  # the live counter
LOGS = deque(maxlen=1000)          # in-memory ring buffer of log entries


@app.middleware("http")
async def instrument(request: Request, call_next):
    global REQUEST_COUNT
    REQUEST_COUNT += 1             # counts every request to any endpoint
    request_id = str(uuid.uuid4())
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        entry = {
            "level": "INFO" if status < 500 else "ERROR",
            "ts": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path,
            "request_id": request_id,
            "method": request.method,
            "status": status,
        }
        LOGS.append(entry)
        print(json.dumps(entry), file=sys.stdout, flush=True)   # structured JSON to stdout too


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/work")
def work(n: int = Query(1, ge=0)):
    total = 0
    for i in range(min(n, 1_000_000)):     # K units of (cheap) work
        total += i
    return {"email": EMAIL, "done": n}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return (
        "# HELP http_requests_total Total HTTP requests received.\n"
        "# TYPE http_requests_total counter\n"
        f"http_requests_total {REQUEST_COUNT}\n"
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": float(time.monotonic() - START)}


@app.get("/logs/tail")
def logs_tail(limit: int = Query(50, ge=1, le=1000)):
    return list(LOGS)[-limit:]
