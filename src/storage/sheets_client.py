import google.auth
from googleapiclient.discovery import build
from google.oauth2 import service_account
from ..config.config import settings
import os
import logging
import json

logger = logging.getLogger(__name__)

class SheetsClient:
    def __init__(self, spreadsheet_id: str = None):
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        self.credentials_path = settings.GOOGLE_SHEETS_CREDENTIALS_PATH
        self.spreadsheet_id = spreadsheet_id or settings.SPREADSHEET_ID
        self.backup_dir = "temp/backups"
        os.makedirs(self.backup_dir, exist_ok=True)
        self.service = self._authenticate()

    def _authenticate(self):
        if not os.path.exists(self.credentials_path):
            logger.warning(f"Credentials file not found at {self.credentials_path}. Google Sheets service will not be available. Using local fallback.")
            return None
        
        try:
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.scopes)
            return build('sheets', 'v4', credentials=creds)
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets: {e}")
            return None

    def save_versioned_local(self, turni):
        """Saves turni to a NEW timestamped JSON file."""
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.backup_dir, f"shifts_{ts}.json")
        with open(filepath, "w") as f:
            json.dump(turni, f, indent=4)
        logger.info(f"Versioned local backup saved: {filepath}")
        return filepath

    def get_latest_local_backup(self):
        """Returns data from the most recent JSON file in temp/backups."""
        files = [f for f in os.listdir(self.backup_dir) if f.endswith('.json')]
        if not files:
            return []
        # Sort by filename (which includes timestamp)
        files.sort(reverse=True)
        latest_file = os.path.join(self.backup_dir, files[0])
        try:
            with open(latest_file, "r") as f:
                return json.load(f)
        except:
            return []

    def create_new_sheet_tab(self, title, values):
        """Creates a new sheet tab and populates it with values."""
        if not self.service:
            return None
        
        try:
            # 1. Create the new sheet
            body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': title
                        }
                    }
                }]
            }
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id, body=body).execute()
            
            # 2. Add data to it
            range_name = f"'{title}'!A1"
            # Add header
            header = ["Data", "Giorno", "Utente", "Slot 1", "Slot 2", "Source"]
            all_rows = [header] + values
            
            body = {'values': all_rows}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id, range=range_name,
                valueInputOption='USER_ENTERED', body=body).execute()
            
            logger.info(f"Created and populated new sheet tab: {title}")
            return title
        except Exception as e:
            logger.error(f"Error creating versioned sheet: {e}")
            return None

    def get_latest_sheet_data(self):
        """Finds the most recent tab and returns its values."""
        if not self.service:
            return self.get_latest_local_backup()
        
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            if not sheets:
                return self.get_latest_local_backup()
            
            # Usually the last sheet is the newest one if created via addSheet
            # Or we could sort by title if we use timestamps
            # Let's assume the last one in the list (or we could filter by our naming convention)
            sheet_titles = [s['properties']['title'] for s in sheets if 'shifts_' in s['properties']['title']]
            if not sheet_titles:
                # Fallback to Sheet1 if no versioned sheets exist
                res = self.get_values('Sheet1!A:F')
                return res
            
            sheet_titles.sort(reverse=True) # Sort lexicographically by timestamp
            latest_title = sheet_titles[0]
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=f"'{latest_title}'!A:F").execute()
            return result.get('values', [])
        except Exception as e:
            logger.error(f"Error fetching latest sheet: {e}")
            return self.get_latest_local_backup()

    def get_values(self, range_name):
        """Legacy method for old sheets, or redirects to latest."""
        if not self.service:
            return self.get_latest_local_backup()
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=range_name).execute()
            return result.get('values', [])
        except:
            return self.get_latest_local_backup()

    def update_shift(self, target_date, target_user, new_values):
        """Finds a shift by date and user in the LATEST version and updates it."""
        # 1. Update Latest Local Version
        files = [f for f in os.listdir(self.backup_dir) if f.endswith('.json')]
        if files:
            files.sort(reverse=True)
            latest_file = os.path.join(self.backup_dir, files[0])
            try:
                with open(latest_file, "r") as f:
                    data = json.load(f)
                updated = False
                for i, row in enumerate(data):
                    if len(row) >= 3 and row[0] == target_date and row[2].lower() == target_user.lower():
                        data[i] = new_values
                        updated = True
                        break
                if updated:
                    with open(latest_file, "w") as f:
                        json.dump(data, f, indent=4)
                    logger.info(f"Updated latest local backup: {latest_file}")
            except Exception as e:
                logger.error(f"Error updating local version: {e}")

        # 2. Update Latest Sheets Tab
        if not self.service:
            return
            
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            sheet_titles = [s['properties']['title'] for s in sheets if 'shifts_' in s['properties']['title']]
            
            if not sheet_titles:
                # Try Sheet1
                sheet_title = 'Sheet1'
            else:
                sheet_titles.sort(reverse=True)
                sheet_title = sheet_titles[0]
            
            range_to_read = f"'{sheet_title}'!A:F"
            res = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range=range_to_read).execute()
            values = res.get('values', [])
            
            for i, row in enumerate(values):
                if len(row) >= 3 and row[0] == target_date and row[2].lower() == target_user.lower():
                    # Update this specific row + 1 (1-indexed)
                    range_to_update = f"'{sheet_title}'!A{i+1}:F{i+1}"
                    body = {'values': [new_values]}
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id, range=range_to_update,
                        valueInputOption='USER_ENTERED', body=body).execute()
                    logger.info(f"Updated row {i+1} in sheet tab: {sheet_title}")
                    break
        except Exception as e:
            logger.error(f"Error updating latest sheet: {e}")
