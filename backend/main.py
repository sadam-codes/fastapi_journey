import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.database import close_db, init_db, is_db_connected
from controllers.auth_controller import router as auth_router
from controllers.form_controller import router as form_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Auth Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    await init_db()
    try:
        from helpers import onlyoffice_helper

        if onlyoffice_helper.onlyoffice_enabled():
            cb = f"{onlyoffice_helper.PUBLIC_APP_URL}/forms/internal/onlyoffice/callback"
            logger.info(
                "OnlyOffice: document server will POST saves to %s — bind the API on 0.0.0.0 "
                "(e.g. uvicorn main:app --host 0.0.0.0) so Docker can reach host.docker.internal.",
                cb,
            )
    except Exception:
        pass


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_db()


@app.get("/health")
async def health():
    """Lightweight check for load balancers and `docker exec … curl` from the document server."""
    return {"status": "ok"}


@app.get("/")
async def home():
    return {"message": "Backend is running", "db_connected": await is_db_connected()}


app.include_router(auth_router)
app.include_router(form_router)


if __name__ == "__main__":
    import uvicorn

    # 0.0.0.0 so OnlyOffice in Docker can call back via PUBLIC_APP_URL (e.g. host.docker.internal:8000).
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)