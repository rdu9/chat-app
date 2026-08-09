from fastapi import FastAPI
from src.chat.routes import chat_router
from contextlib import asynccontextmanager
from src.db.main import init_db
import structlog
from src.requests.routes import request_router
from src.auth.routes import auth_router
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from fastapi.responses import FileResponse
from src.config import Config
from .errors import register_all_errors

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app.starting", domain=Config.DOMAIN)
    await init_db()

    yield
    logger.info("app.shutting_down")

version = "v1"

app = FastAPI(
    version=version,
    title="Chat app",
    description="A simple chat app",
    lifespan=lifespan
)

STATIC = Path(__file__).parent / "static"

app.mount("/static", StaticFiles(directory=STATIC), name="static")

@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


# register errors / middleware

register_all_errors(app)


# register all routes

app.include_router(chat_router, prefix=f"/api/{version}/chat", tags = ["Chat"])
app.include_router(auth_router, prefix=f"/api/{version}/auth", tags = ["Auth"])
app.include_router(request_router, prefix=f"/api/{version}/requests", tags = ["Requests"])

