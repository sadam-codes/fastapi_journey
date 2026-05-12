from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.database import close_db, init_db, is_db_connected
from controllers.auth_controller import router as auth_router
from controllers.form_controller import router as form_router

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


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_db()


@app.get("/")
async def home():
    return {"message": "Backend is running", "db_connected": await is_db_connected()}


app.include_router(auth_router)
app.include_router(form_router)