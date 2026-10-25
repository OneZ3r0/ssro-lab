from itertools import count
from time import monotonic_ns

from fastapi import FastAPI, Request, Response
from starlette.types import ASGIApp, Receive, Scope, Send

records: list[dict] = []
arrival_counter = count(1)
handler_counter = count(1)


class ArrivalMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http" and scope["path"] == "/probe":
            state = scope.setdefault("state", {})
            state["arrival_ns"] = monotonic_ns()
            state["arrival_order"] = next(arrival_counter)
        await self.app(scope, receive, send)


app = FastAPI(title="SSRO Measurement Probe")
app.add_middleware(ArrivalMiddleware)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/probe")
async def probe(request: Request, run_id: str, request_id: int):
    handler_start_ns = monotonic_ns()
    record = {
        "run_id": run_id,
        "request_id": request_id,
        "arrival_order": request.state.arrival_order,
        "handler_order": next(handler_counter),
        "arrival_ns": request.state.arrival_ns,
        "handler_start_ns": handler_start_ns,
        "handler_end_ns": None,
        "body_bytes": None,
    }
    records.append(record)
    try:
        body_bytes = 0
        async for chunk in request.stream():
            body_bytes += len(chunk)
        record["body_bytes"] = body_bytes
        return Response(
            "ok", media_type="text/plain", headers={"Cache-Control": "no-store"}
        )
    finally:
        record["handler_end_ns"] = monotonic_ns()


def spread_ms(samples: list[dict], field: str) -> float | None:
    timestamps = [record[field] for record in samples]
    return (max(timestamps) - min(timestamps)) / 1_000_000 if timestamps else None


@app.get("/results")
async def results(run_id: str):
    samples = sorted(
        (record for record in records if record["run_id"] == run_id),
        key=lambda record: record["arrival_order"],
    )
    return {
        "run_id": run_id,
        "count": len(samples),
        "arrival_spread_ms": spread_ms(samples, "arrival_ns"),
        "handler_spread_ms": spread_ms(samples, "handler_start_ns"),
        "records": [
            {
                **record,
                "dispatch_delay_ms": (record["handler_start_ns"] - record["arrival_ns"])
                / 1_000_000,
                "handler_duration_ms": (
                    (record["handler_end_ns"] - record["handler_start_ns"]) / 1_000_000
                    if record["handler_end_ns"] is not None
                    else None
                ),
            }
            for record in samples
        ],
    }


@app.post("/reset")
async def reset(run_id: str):
    records[:] = [record for record in records if record["run_id"] != run_id]
    return {"ok": True}
