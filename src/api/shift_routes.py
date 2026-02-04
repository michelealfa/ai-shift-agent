from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header, Depends
from celery.result import AsyncResult
import os
import uuid
import json
import httpx
from datetime import datetime
from ..tasks.worker import process_shift_image_task
from ..utils.logger import logger
from ..storage.sheets_client import SheetsClient
from ..config.config import settings
from ..ai.gemini_client import GeminiClient

router = APIRouter(prefix="/api/shifts", tags=["shifts"])

from ..storage.user_storage import get_user_by_key

UPLOAD_DIR = "temp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Security Dependency - Dynamic User Mapping
async def verify_api_key(x_api_key: str = Header(None, alias="X-API-KEY")):
    # 1. Check user storage
    matching_user = get_user_by_key(x_api_key)
    if matching_user:
        return matching_user
    
    # 2. Fallback to settings.X_API_KEY for legacy support
    if x_api_key and x_api_key == settings.X_API_KEY:
        return {"name": settings.TARGET_USER_NAME}
        
    raise HTTPException(status_code=403, detail="Invalid API Key")

@router.post("/upload")
async def upload_shift_image(
    file: UploadFile = File(...),
    user_data: dict = Depends(verify_api_key)
):
    """Uploads an image and triggers the AI processing task."""
    target_user = user_data.get("name", "UTENTE")
    file_extension = os.path.splitext(file.filename)[1]
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_extension}")
    
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"File uploaded: {file_path} for user {target_user}")
        
        # Trigger Celery Task with user settings
        user_settings = {
            "gemini_api_key": user_data.get("gemini_api_key"),
            "spreadsheet_id": user_data.get("spreadsheet_id")
        }
        task = process_shift_image_task.delay(file_path, None, None, target_user, True, user_settings)
        
        return {
            "task_id": task.id,
            "status": "processing",
            "message": "Image uploaded successfully. Processing started."
        }
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{task_id}")
async def get_task_status(task_id: str, user_data: dict = Depends(verify_api_key)):
    """Checks the status of the AI processing task."""
    task_result = AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task_result.status
    }
    
    if task_result.status == 'SUCCESS':
        response["result"] = task_result.result
    elif task_result.status == 'FAILURE':
        response["error"] = str(task_result.info)
        
    return response

@router.post("/commit")
async def commit_shifts(data: dict, user_data: dict = Depends(verify_api_key)):
    """Saves the validated shift data to database and syncs to Google Sheets."""
    from ..storage.shift_storage import shift_storage
    from datetime import datetime
    
    turni = data.get('turni', [])
    
    logger.info(f"Commit request received: {len(turni)} shifts from user {user_data.get('name')}")

    if not turni:
        raise HTTPException(status_code=400, detail="No 'turni' data provided.")

    try:
        user_id = int(user_data.get("id", 0))
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found")
        
        target_user = user_data.get("name", "UTENTE")
        logger.info(f"Processing commit for user_id={user_id}, name={target_user}")
        
        # Prepare shift data for bulk save
        shifts_data = []
        for t in turni:
            shift_entry = {
                'date': t.get('data', ''),
                'slot_1': t.get('slot_1', ''),
                'slot_2': t.get('slot_2', ''),
                'notes': t.get('notes', '')
            }
            shifts_data.append(shift_entry)
            logger.debug(f"Prepared shift: {shift_entry}")
        
        # Save to database (will also sync to Sheets)
        logger.info(f"Calling bulk_save_shifts with {len(shifts_data)} shifts")
        saved_shifts = shift_storage.bulk_save_shifts(
            user_id=user_id,
            shifts_data=shifts_data,
            source='ocr',
            sync_to_sheets=True
        )
        
        logger.info(f"✅ Successfully committed {len(saved_shifts)} shifts for user {target_user} (user_id={user_id})")
        return {
            "status": "success", 
            "saved_count": len(saved_shifts),
            "message": f"Saved {len(saved_shifts)} shifts to database and Google Sheets"
        }
    except Exception as e:
        logger.error(f"❌ Error committing shifts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_shifts(user_data: dict = Depends(verify_api_key)):
    """Fetches shifts from database, showing current week with focus on today."""
    try:
        from ..storage.shift_storage import shift_storage
        from datetime import date, timedelta
        
        user_id = int(user_data.get("id", 0))
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found")
        
        # Try to get shifts from database first
        all_shifts = shift_storage.get_user_shifts(user_id)
        
        # If no shifts in DB, try syncing from Google Sheets
        if not all_shifts:
            logger.info(f"No shifts in DB for user {user_id}, syncing from Sheets...")
            synced_count = shift_storage.sync_from_sheets(user_id)
            if synced_count > 0:
                all_shifts = shift_storage.get_user_shifts(user_id)
        
        # Get current week shifts for initial display
        current_week_shifts = shift_storage.get_current_week_shifts(user_id)
        
        # Convert to API format
        def shift_to_dict(shift):
            return {
                "data": shift.shift_date.strftime("%Y-%m-%d"),
                "giorno": shift.shift_date.strftime("%A"),  # Day name
                "slot_1": shift.slot_1 or "",
                "slot_2": shift.slot_2 or "",
                "notes": shift.notes or "",
                "is_today": shift.shift_date == date.today()
            }
        
        current_week_data = [shift_to_dict(s) for s in current_week_shifts]
        all_shifts_data = [shift_to_dict(s) for s in all_shifts]
        
        return {
            "turni": all_shifts_data,  # All shifts
            "current_week": current_week_data,  # Current week for carousel
            "today": date.today().strftime("%Y-%m-%d"),
            "user": user_data.get("display_name", user_data.get("name", "UTENTE")),
            "storage_status": "database",
            "total_shifts": len(all_shifts_data),
            "week_shifts": len(current_week_data)
        }
    except Exception as e:
        logger.error(f"Error listing shifts: {e}")
        return {
            "turni": [], 
            "current_week": [],
            "error": str(e),
            "storage_status": "error"
        }


@router.post("/update")
async def update_shift(data: dict, user_data: dict = Depends(verify_api_key)):
    """Updates an existing shift in database."""
    from ..storage.shift_storage import shift_storage
    from datetime import datetime
    
    turno = data.get('turno')
    if not turno or 'data' not in turno:
        raise HTTPException(status_code=400, detail="Missing shift data")
    
    try:
        user_id = int(user_data.get("id", 0))
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found")
        
        # Parse date
        shift_date = datetime.strptime(turno.get('data'), '%Y-%m-%d').date()
        
        # Save shift (will update if exists)
        shift = shift_storage.save_shift(
            user_id=user_id,
            shift_date=shift_date,
            slot_1=turno.get('slot_1'),
            slot_2=turno.get('slot_2'),
            notes=turno.get('notes'),
            source='manual',
            sync_to_sheets=True
        )
        
        return {
            "status": "success",
            "shift_id": shift.id,
            "message": "Shift updated successfully"
        }
    except Exception as e:
        logger.error(f"Update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/traffic")
async def get_traffic(origin: str = "Origgio", user_data: dict = Depends(verify_api_key)):
    """Calculates travel time to Arese. Handles coordinates from GPS. Falls back to OSRM if Google fails."""
    
    # Coordinates for "Il Centro Arese"
    dest_coords = "45.5606,9.0560" 
    
    # Resolve origin if it's a known label
    resolved_origin = origin
    if origin.lower() == "origgio":
        resolved_origin = "45.5947,9.0175" # Approx coords for Origgio
    elif origin.lower() == "altro":
        resolved_origin = "Milan"
        
    try:
        from ..storage.settings_storage import settings_storage
        # 1. Try Google Maps if key exists (user-specific or global)
        user_id = int(user_data.get("id", 0))
        maps_key = settings_storage.get_google_maps_api_key(user_id)
        
        if maps_key:
            # Added arrival_time or departure_time=now + traffic_model=best_guess for accurate traffic data
            url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={resolved_origin}&destinations={dest_coords}&departure_time=now&traffic_model=best_guess&key={maps_key}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                data = resp.json()
                
                if data['status'] == 'OK' and data['rows'][0]['elements'][0]['status'] == 'OK':
                    element = data['rows'][0]['elements'][0]
                    # duration_in_traffic is only available if departure_time is specified
                    duration_text = element.get('duration_in_traffic', element['duration'])['text']
                    duration_value = element.get('duration_in_traffic', element['duration'])['value']
                    
                    color = "green"
                    label = "Assente"
                    if duration_value > 1500: label, color = "Elevato", "red"
                    elif duration_value > 900: label, color = "Medio", "yellow"
                    
                    return {
                        "duration": duration_text, 
                        "traffic_state": color, 
                        "traffic_label": label,
                        "is_live": True,
                        "method": "google"
                    }
                else:
                    logger.warning(f"Google Maps failed ({data.get('status')}), falling back to OSRM. Details: {data.get('error_message', 'No details')}")
        
        # 2. Fallback to OSRM (No-Key)
        # OSRM expects {lng},{lat}
        def parse_coords(c):
            if ',' in c:
                parts = c.split(',')
                return f"{parts[1].strip()},{parts[0].strip()}"
            return c

        osrm_origin = parse_coords(resolved_origin)
        osrm_dest = parse_coords(dest_coords)
        
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{osrm_origin};{osrm_dest}?overview=false"
        async with httpx.AsyncClient() as client:
            resp = await client.get(osrm_url)
            data = resp.json()
            if data.get('code') == 'Ok':
                duration_sec = data['routes'][0]['duration']
                mins = round(duration_sec / 60)
                
                return {
                    "duration": f"{mins} min",
                    "traffic_state": "yellow", # Estimated color
                    "traffic_label": "Stima (No-Traffic)",
                    "is_live": False,
                    "method": "osrm"
                }

        return {"error": "All traffic engines failed"}
    except Exception as e:
        logger.error(f"Traffic error: {e}")
        return {"error": f"Errore calcolo: {str(e)}"}

@router.post("/query")
async def query_ai(data: dict, user_data: dict = Depends(verify_api_key)):
    """NLP Query about shifts."""
    question = data.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="Missing question")
    
    try:
        from ..storage.shift_storage import shift_storage
        gemini = GeminiClient(api_key=user_data.get("gemini_api_key"))
        user_id = int(user_data.get("id", 0))
        target_user = user_data.get("display_name", user_data.get("name", "UTENTE"))
        
        # Get user's shifts from database
        all_shifts = shift_storage.get_user_shifts(user_id)
        
        # Format shifts for context
        shifts_context_list = []
        for s in all_shifts[-30:]: # Last 30 shifts for context
            shifts_context_list.append({
                "data": s.shift_date.isoformat(),
                "slot_1": s.slot_1,
                "slot_2": s.slot_2,
                "note": s.notes
            })
        
        from ..ai.prompts import ShiftLogic
        context_str = json.dumps(shifts_context_list)
        prompt = ShiftLogic.get_nlp_prompt(question, context_str)
        
        result = await gemini.chat(prompt)
        return {"response": result.get("response", "Spiacente, non ho potuto elaborare la richiesta.")}
    except Exception as e:
        logger.error(f"Query AI error: {e}")
        return {"response": f"Errore durante l'elaborazione della domanda: {str(e)}"}
