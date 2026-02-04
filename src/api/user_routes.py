from fastapi import APIRouter, HTTPException
import json
import os

from ..storage.user_storage import get_users

router = APIRouter(prefix="/api/public", tags=["public"])

@router.get("/users")
async def list_public_users():
    return get_users()
