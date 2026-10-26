"""FastAPI app. Dev: `npm run dev` (Vite proxies /api here). Built frontend is served if present."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fastapi.middleware.gzip import GZipMiddleware

from app.api.buildlab import router as buildlab_router
from app.api.learn import router as learn_router
from app.api.macro import router as macro_router
from app.api.routes import router
from app.config import REPO_ROOT
from app.seed.load import load_seed
from app.settings import Settings
from app.state import AppState, create_state

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("coach")

DIST = REPO_ROOT / "frontend" / "dist"


def create_app(state_factory: Callable[[], AppState] = create_state) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        st = state_factory()
        added = load_seed(st.cache)
        if added:
            log.info("Loaded %d seed responses into the cache", added)
        app.state.coach = st
        app.state.settings = Settings(st.db)
        yield

    app = FastAPI(title="Deadlock Coach", lifespan=lifespan)
    app.include_router(router, prefix="/api")
    app.include_router(buildlab_router, prefix="/api")
    app.include_router(macro_router, prefix="/api")
    app.include_router(learn_router, prefix="/api")
    app.add_middleware(GZipMiddleware, minimum_size=2000)

    if DIST.exists():
        app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            return FileResponse(DIST / "index.html")

    return app


app = create_app()
