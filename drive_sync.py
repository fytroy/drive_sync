import os
import io
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from datetime import datetime

# --- Configuration ---
# <<<<< CHANGE THIS to your local folder path
LOCAL_FOLDER_PATH = 'C:\\Users\\gitongaR01\\Desktop\\py'
SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_FILE = 'token.json' # Stores your user access token after initial authentication

def authenticate_google_drive():
    """Authenticates with Google Drive API and returns the service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def get_drive_folder_id(service, folder_name, parent_id=None):
    """
    Gets the ID of a folder on Google Drive.
    If parent_id is None, it looks for the folder in the root.
    """
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']
    return None

def create_drive_folder(service, folder_name, parent_id=None):
    """Creates a new folder on Google Drive."""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
        
    folder = service.files().create(body=file_metadata, fields='id').execute()
    print(f"Created folder '{folder_name}' with ID: {folder.get('id')}")
    return folder.get('id')

def get_or_create_drive_folder_recursive(service, local_path, base_drive_folder_id):
    """
    Recursively gets or creates Google Drive folders corresponding to local paths.
    Returns the Drive ID of the deepest folder in the path.
    """
    path_parts = os.path.relpath(local_path, LOCAL_FOLDER_PATH).split(os.sep)
    current_drive_parent_id = base_drive_folder_id

    # If the path_parts is just '.', it means we are at the root of the sync folder.
    # We only process if there are actual subdirectories.
    if path_parts == ['.']:
        return base_drive_folder_id

    for part in path_parts:
        if part == '': # Handle cases like 'folder//subfolder' or paths ending with separator
            continue
        folder_id = get_drive_folder_id(service, part, current_drive_parent_id)
        if not folder_id:
            folder_id = create_drive_folder(service, part, current_drive_parent_id)
        current_drive_parent_id = folder_id
    return current_drive_parent_id


def sync_folder_to_drive(local_folder_path, drive_root_folder_id, service):
    """
    Syncs a local folder to a Google Drive folder, preserving subdirectory structure.
    Uploads new files and updates modified files.
    """
    print(f"\n--- Syncing '{os.path.basename(local_folder_path)}' to Drive ---")

    # This dictionary will map local relative paths (e.g., 'subfolder/file.txt')
    # to their corresponding Drive file IDs and info.
    # We'll build it by traversing Drive recursively, which is more complex.
    # For simplicity, and to handle initial creation, we'll fetch files per folder.
    # A more advanced sync would cache the entire Drive structure.

    for root, dirs, files in os.walk(local_folder_path):
        # Determine the corresponding Google Drive folder ID for the current local 'root'
        # This will create intermediate folders on Drive if they don't exist.
        current_drive_folder_id = get_or_create_drive_folder_recursive(service, root, drive_root_folder_id)
        
        # Get a list of files currently in this specific Drive folder
        drive_files_in_current_folder = {}
        page_token = None
        while True:
            response = service.files().list(
                q=f"'{current_drive_folder_id}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, modifiedTime, mimeType)",
                pageToken=page_token
            ).execute()
            for file in response.get('files', []):
                # Only consider files, not subfolders, for direct comparison
                if not file['mimeType'] == 'application/vnd.google-apps.folder':
                    drive_files_in_current_folder[file['name']] = {
                        'id': file['id'],
                        'modifiedTime': file['modifiedTime'],
                        'mimeType': file['mimeType']
                    }
            page_token = response.get('nextPageToken', None)
            if not page_token:
                break
                
        # Iterate through local files in the current directory (root)
        for filename in files:
            local_file_path = os.path.join(root, filename)
            
            if filename in drive_files_in_current_folder:
                # File exists on Drive in the correct folder, check if it needs update
                drive_file_info = drive_files_in_current_folder[filename]
                
                local_mod_time_sec = os.path.getmtime(local_file_path)
                local_mod_datetime = datetime.fromtimestamp(local_mod_time_sec)
                # Google Drive's modifiedTime includes milliseconds and 'Z' for UTC.
                # We need to parse it carefully.
                drive_mod_datetime_str = drive_file_info['modifiedTime']
                # Strip milliseconds and 'Z' for simpler parsing if present
                if '.' in drive_mod_datetime_str and 'Z' in drive_mod_datetime_str:
                    drive_mod_datetime = datetime.strptime(drive_mod_datetime_str.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                elif 'T' in drive_mod_datetime_str: # Basic ISO format
                    drive_mod_datetime = datetime.strptime(drive_mod_datetime_str, "%Y-%m-%dT%H:%M:%SZ")
                else: # Fallback for other formats if any
                    drive_mod_datetime = datetime.fromisoformat(drive_mod_datetime_str.replace('Z', '+00:00'))

                # Compare timestamps. Add a buffer for small differences.
                # Converting both to timestamp (seconds since epoch) for robust comparison.
                if local_mod_datetime.timestamp() > drive_mod_datetime.timestamp() + 1: # 1 second buffer
                    print(f"Updating '{filename}' in '{os.path.relpath(root, local_folder_path)}' (local is newer)...")
                    file_metadata = {'name': filename} # Name remains the same
                    media = MediaFileUpload(local_file_path, resumable=True)
                    service.files().update(
                        fileId=drive_file_info['id'],
                        body=file_metadata,
                        media_body=media
                    ).execute()
                else:
                    print(f"'{filename}' in '{os.path.relpath(root, local_folder_path)}' is up-to-date.")
            else:
                # File does not exist on Drive in this specific folder, upload it
                print(f"Uploading new file: '{filename}' to '{os.path.relpath(root, local_folder_path)}'...")
                file_metadata = {'name': filename, 'parents': [current_drive_folder_id]}
                media = MediaFileUpload(local_file_path, resumable=True)
                file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                print(f"Uploaded '{filename}' with ID: {file.get('id')}")

    # --- Optional: Handle deletions on Drive if local file is deleted ---
    # This part is significantly more complex with subdirectory support.
    # To implement this, you would need to:
    # 1. Recursively list ALL files and folders on Drive under drive_root_folder_id.
    # 2. Build a comprehensive map of Drive paths to IDs.
    # 3. Recursively list ALL files and folders locally under local_folder_path.
    # 4. Compare these two comprehensive lists and delete anything on Drive that isn't local.
    # This is a non-trivial addition and can be dangerous if not carefully implemented.
    print(f"--- Sync for '{os.path.basename(local_folder_path)}' complete! ---")


def main():
    # 1. Authenticate
    service = authenticate_google_drive()
    print("Successfully authenticated with Google Drive.")

    # 2. Get/Create the target Drive folder (the base folder for the entire sync)
    local_folder_name = os.path.basename(LOCAL_FOLDER_PATH)
    drive_folder_id = get_drive_folder_id(service, local_folder_name)

    if not drive_folder_id:
        print(f"Target folder '{local_folder_name}' not found on Google Drive. Creating it...")
        drive_folder_id = create_drive_folder(service, local_folder_name)
    else:
        print(f"Found existing Drive folder '{local_folder_name}' with ID: {drive_folder_id}")

    # 3. Sync the folder, now handling subdirectories
    sync_folder_to_drive(LOCAL_FOLDER_PATH, drive_folder_id, service)

if __name__ == '__main__':
    # Ensure the local folder exists
    if not os.path.exists(LOCAL_FOLDER_PATH):
        print(f"Error: Local folder '{LOCAL_FOLDER_PATH}' does not exist.")
        print("Please create the folder or update LOCAL_FOLDER_PATH in the script.")
    else:
        main()