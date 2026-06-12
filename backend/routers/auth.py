"""Auth router: register, login, logout, me."""
import uuid
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field

from core.config import ACCESS_TOKEN_MINUTES
from core.db import get_db
from core.security import (hash_password, verify_password, create_access_token,
                           now_iso, CurrentUser)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=80)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def _set_cookie(response: Response, token: str):
    response.set_cookie("access_token", token, httponly=True, samesite="lax",
                        max_age=ACCESS_TOKEN_MINUTES * 60, path="/")


@router.post("/register")
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower().strip()
    db = await get_db()
    cur = await db.execute("SELECT id FROM users WHERE email = ?", (email,))
    if await cur.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO users (id, email, name, password_hash, role, plan, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (user_id, email, payload.name, hash_password(payload.password), "user", "free", now_iso()),
    )
    await db.commit()
    token = create_access_token(user_id, email)
    _set_cookie(response, token)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user_id, "email": email, "name": payload.name, "role": "user"},
    }


@router.post("/login")
async def login(payload: LoginIn, response: Response):
    email = payload.email.lower().strip()
    db = await get_db()
    cur = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = await cur.fetchone()
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], email)
    _set_cookie(response, token)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "email": user["email"], "name": user["name"],
                 "role": user["role"]},
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: CurrentUser):
    return user
