"""Login API: status, log in, log out (see app/auth.py)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.auth import COOKIE, SESSION_DAYS, Locked

router = APIRouter()


class LoginIn(BaseModel):
    password: str


def _https(request: Request) -> bool:
    # Tunnels end HTTPS and forward plain HTTP to this PC, saying so in this header.
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


@router.get("/auth/status")
def status(request: Request):
    auth = request.app.state.auth
    return {"required": request.app.state.require_login, "logged_in": auth.valid(request.cookies.get(COOKIE))}


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response):
    try:
        token = request.app.state.auth.login(body.password)
    except Locked as e:
        raise HTTPException(429, str(e))
    if token is None:
        raise HTTPException(401, "Wrong password.")
    response.set_cookie(
        COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax", secure=_https(request), path="/",
    )
    return {"logged_in": True}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"logged_in": False}
