# Google Drive Sync Script

This Python script synchronizes a local folder with a folder on Google Drive. It's designed to upload new files and update existing ones in your Google Drive, mirroring the structure of your local directory.

## Features

- **Authentication:** Securely authenticates with your Google Account using OAuth 2.0. Access tokens are stored locally in `token.json` for subsequent runs.
- **Recursive Sync:** Syncs the entire directory tree, preserving the subdirectory structure from your local folder to Google Drive.
- **New File Upload:** Detects and uploads new files from the local folder to the corresponding folder in Google Drive.
- **Update Modified Files:** Checks for modifications in existing files (based on last modified timestamp) and updates them on Google Drive if the local version is newer.
- **Automatic Folder Creation:** If the target folder (named after your local folder) or any subdirectories do not exist on Google Drive, the script creates them automatically.

## Prerequisites

Before running this script, ensure you have the following:

1.  **Python 3.x:** Installed on your system.
2.  **Google Cloud Project:**
    *   Create a project on the [Google Cloud Console](https://console.cloud.google.com/).
    *   Enable the **Google Drive API** for your project.
    *   Create OAuth 2.0 credentials (for a "Desktop app").
    *   Download the credentials JSON file and rename it to `credentials.json`. Place this file in the same directory as the `drive_sync.py` script.
3.  **Local Folder:** The local folder you want to sync must exist.

## How to Use

1.  **Install Dependencies:**
    Open your terminal or command prompt and install the required Google API client libraries for Python:
    ```bash
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
    ```

2.  **Configure `LOCAL_FOLDER_PATH`:**
    Open the `drive_sync.py` script and modify the `LOCAL_FOLDER_PATH` variable to the absolute path of the local folder you wish to sync. For example:
    ```python
    # <<<<< CHANGE THIS to your local folder path
    LOCAL_FOLDER_PATH = 'C:\Users\YourUser\Desktop\MySyncFolder'
    # or for Linux/macOS:
    # LOCAL_FOLDER_PATH = '/home/youruser/documents/MySyncFolder'
    ```

3.  **Run the Script (First Time):**
    Execute the script from your terminal:
    ```bash
    python drive_sync.py
    ```
    On the first run, a web browser window will open, prompting you to authorize the script to access your Google Drive. Follow the on-screen instructions. After successful authorization, a `token.json` file will be created in the script's directory. This file stores your access token, so you won't need to re-authorize every time.

4.  **Subsequent Runs:**
    Simply run the script again:
    ```bash
    python drive_sync.py
    ```
    The script will use the saved `token.json` to authenticate and proceed with the synchronization.

## Configuration Variables

-   `LOCAL_FOLDER_PATH`: (String) The absolute path to the local folder you want to sync with Google Drive. **You must change this value before running.**
-   `SCOPES`: (List of strings) Defines the level of access the script requests to your Google Drive. Default is `['https://www.googleapis.com/auth/drive']`, which grants full access.
-   `TOKEN_FILE`: (String) The name of the file where the script stores your OAuth 2.0 access token. Default is `token.json`.
-   `credentials.json`: (File) This file, obtained from Google Cloud Console, is required for the OAuth flow. It must be in the same directory as the script.

## Important Notes & Limitations

-   **One-Way Sync (Local to Drive):** This script performs a one-way synchronization from your local machine to Google Drive. Changes made directly on Google Drive (e.g., deleting a file synced by the script) will not be reflected back locally. If a local file is deleted, it will not be automatically deleted from Google Drive by this script.
-   **No Deletion Handling (Default):** The script primarily handles uploading new files and updating existing ones. It does not currently delete files from Google Drive if they are removed locally. This is a safety measure to prevent accidental data loss. Implementing deletion requires careful consideration and is a common area for future enhancement.
-   **Error Handling:** Basic error handling is in place, but it can be expanded for more robust operation in various scenarios.
-   **Large Files:** For very large files, the upload process might take a significant amount of time. The script uses resumable uploads, which helps in case of interruptions.
-   **API Quotas:** Be mindful of Google Drive API usage quotas. For very frequent or large-scale synchronizations, you might encounter rate limits.

This script provides a foundation for synchronizing local files to Google Drive and can be extended with more advanced features like two-way sync, deletion handling, and more sophisticated conflict resolution.
