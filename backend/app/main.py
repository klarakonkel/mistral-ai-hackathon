from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.utils.wandb_tracking import init_weave


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    if settings.wandb_api_key:
        init_weave(settings.wandb_project)
    yield


app = FastAPI(title="KotoFlow API", version="0.1.0", lifespan=lifespan)

settings = Settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes import router  # noqa: E402
from app.api.websocket import router as ws_router  # noqa: E402

app.include_router(router, prefix="/api")
app.include_router(ws_router, prefix="/ws")
