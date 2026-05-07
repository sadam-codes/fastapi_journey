from fastapi import FastAPI

from config.database import close_db, init_db, is_db_connected
from controllers.auth_controller import router as auth_router
from controllers.chat_controller import router as chat_router
from controllers.document_controller import router as document_router

app = FastAPI(title="Auth Backend")


@app.on_event("startup")
async def startup() -> None:
    await init_db()


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_db()


@app.get("/")
async def home():
    return {"message": "Backend is running", "db_connected": await is_db_connected()}


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(document_router)