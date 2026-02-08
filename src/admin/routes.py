from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import logging
from ..storage.user_storage import (
    get_users, 
    add_user as storage_add_user, 
    delete_user as storage_delete_user,
    reset_user_key
)
from ..storage.settings_storage import settings_storage
from ..storage.shift_storage import shift_storage
from ..database import db_manager
from ..database.models import ActivityLog, Shift
from sqlalchemy import desc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="src/admin/templates")

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Main admin dashboard with database data"""
    try:
        # 1. Get users from database
        users = get_users()
        
        # 2. Get global settings from database
        global_settings = {
            "TARGET_USER_NAME": settings_storage.get_setting("TARGET_USER_NAME"),
            "GEMINI_API_KEY": settings_storage.get_setting("GEMINI_API_KEY"),
            "VISION_MODEL": settings_storage.get_setting("VISION_MODEL"),
            "NLP_MODEL": settings_storage.get_setting("NLP_MODEL"),
            "GOOGLE_MAPS_API_KEY": settings_storage.get_setting("GOOGLE_MAPS_API_KEY"),
        }
        
        # 3. Get prompts from database
        from ..ai.prompts import ShiftLogic
        prompts = {
            "vision_prompt": settings_storage.get_setting("VISION_PROMPT") or ShiftLogic.get_vision_prompt("{{ target_user }}"),
            "nlp_prompt": settings_storage.get_setting("NLP_PROMPT") or "Sei un assistente per i turni di lavoro. Rispondi alla domanda: {user_query} usando questo contesto: {context}"
        }
        
        # 4. Get recent activity logs
        with db_manager.get_session() as session:
            logs = session.query(ActivityLog).order_by(desc(ActivityLog.created_at)).limit(30).all()
            # Detach logs from session for template rendering
            session.expunge_all()
            
        # 5. Get recent shifts
        with db_manager.get_session() as session:
            recent_shifts = session.query(Shift).order_by(desc(Shift.created_at)).limit(50).all()
            session.expunge_all()

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "users": users,
            "dyn_settings": global_settings,
            "prompts": prompts,
            "logs": logs,
            "recent_shifts": recent_shifts
        })
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}")
        return HTMLResponse(content=f"Error: {str(e)}", status_code=500)

@router.post("/update_prompts")
async def update_prompts(
    vision_prompt: str = Form(...),
    nlp_prompt: str = Form(...)
):
    """Update AI prompts in database"""
    settings_storage.set_setting("VISION_PROMPT", vision_prompt)
    settings_storage.set_setting("NLP_PROMPT", nlp_prompt)
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/update_env")
async def update_env(
    target_user: str = Form(...),
    gemini_api_key: str = Form(...),
    vision_model: str = Form(...),
    nlp_model: str = Form(...),
    google_maps_key: str = Form(...)
):
    """Update global system settings in database"""
    settings_storage.set_setting("TARGET_USER_NAME", target_user)
    settings_storage.set_setting("GEMINI_API_KEY", gemini_api_key)
    settings_storage.set_setting("VISION_MODEL", vision_model)
    settings_storage.set_setting("NLP_MODEL", nlp_model)
    settings_storage.set_setting("GOOGLE_MAPS_API_KEY", google_maps_key)
    
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/add_user")
async def add_user(
    name: str = Form(...),
    display_name: str = Form(...),
    email: str = Form(...),
    avatar: str = Form(...)
):
    """Add new user to database"""
    user_data = {
        "name": name.upper(),
        "display_name": display_name,
        "email": email,
        "avatar": avatar
    }
    storage_add_user(user_data)
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/delete_user")
async def delete_user(user_id: int = Form(...)):
    """Deactivate user in database"""
    storage_delete_user(user_id)
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/reset_key")
async def reset_key(user_id: int = Form(...)):
    """Revoke old key and generate new one for user"""
    reset_user_key(user_id)
    return RedirectResponse(url="/admin", status_code=303)
