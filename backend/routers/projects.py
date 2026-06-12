"""Projects (library) CRUD."""
from typing import Optional
from fastapi import APIRouter, HTTPException

from core.db import get_db, row_to_dict
from core.security import CurrentUser

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects(user: CurrentUser, kind: Optional[str] = None, limit: int = 100):
    db = await get_db()
    if kind:
        cur = await db.execute(
            "SELECT * FROM projects WHERE user_id = ? AND kind = ? ORDER BY created_at DESC LIMIT ?",
            (user["id"], kind, limit),
        )
    else:
        cur = await db.execute(
            "SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user["id"], limit),
        )
    return [row_to_dict(r) for r in await cur.fetchall()]


@router.get("/{project_id}")
async def get_project(project_id: str, user: CurrentUser):
    db = await get_db()
    cur = await db.execute(
        "SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, user["id"])
    )
    row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return row_to_dict(row)


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: CurrentUser):
    db = await get_db()
    cur = await db.execute(
        "DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, user["id"])
    )
    await db.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}
