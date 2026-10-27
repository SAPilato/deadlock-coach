"""FastAPI app. Dev: `npm run dev` (Vite proxies /api here). Built frontend is served if present."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from fastapi.middleware.gzip import GZipMiddleware

from app.api.auth import router as auth_router
from app.api.buildlab import router as buildlab_router
from app.api.learn import router as learn_router
from app.api.macro import router as macro_router
from app.api.routes import router
from app.auth import COOKIE, Auth
from app.config import REPO_ROOT
from app.seed.load import load_seed
from app.settings import Settings
from app.state import AppState, create_state

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("coach")

DIST = REPO_ROOT / "frontend" / "dist"


# API paths reachable without logging in (the login screen needs them).
OPEN_API = {"/api/auth/status", "/api/auth/login", "/api/auth/logout"}


def create_app(state_factory: Callable[[], AppState] = create_state, require_login: bool | None = None) -> FastAPI:
    """`require_login` (default: env COACH_REQUIRE_LOGIN=1, set by `npm run share`) puts every
    API call behind the app password, for sharing through a public tunnel."""
    if require_login is None:
        require_login = os.environ.get("COACH_REQUIRE_LOGIN") == "1"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        st = state_factory()
        app.state.auth = Auth(st.db)
        if require_login and not app.state.auth.has_password:
            raise RuntimeError("No app password yet. Run `npm run set-password` first.")
        added = load_seed(st.cache)
        if added:
            log.info("Loaded %d seed responses into the cache", added)
        app.state.coach = st
        app.state.settings = Settings(st.db)
        yield

    # No interactive API docs when shared: nothing public should describe the API.
    docs = {} if not require_login else {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(title="Deadlock Coach", lifespan=lifespan, **docs)
    app.state.require_login = require_login

    @app.middleware("http")
    async def login_required(request: Request, call_next):
        path = request.url.path
        if require_login and path.startswith("/api") and path not in OPEN_API:
            if not request.app.state.auth.valid(request.cookies.get(COOKIE)):
                return JSONResponse({"detail": "login required"}, status_code=401)
        return await call_next(request)

    app.include_router(auth_router, prefix="/api")
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
