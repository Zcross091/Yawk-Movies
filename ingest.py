import os
import re
import sqlite3
from google.oauth2 import service_account
from googleapiclient.discovery import build

DB_NAME = "streaming_platform.db"

# 🔴 CONFIGURATION: Paste your 3 Google Drive Folder IDs here separated by commas
FOLDER_IDS = [ "1Qv15HXr0h0qbX9DDu81j6MESfojHolYv",
 "1i9Fu-8tZmAgnmiKxxHLbK8N2zv5OKsft",
  "1y_JIB1lZj-NZ9I-Te8uvge-UrCd_Bvlu"
]

def init_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media (
            id TEXT PRIMARY KEY, title TEXT, type TEXT, genre TEXT, banner_url TEXT, stream_source TEXT, views INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_interactions (user_id INTEGER, media_id TEXT, liked INTEGER DEFAULT 0, watch_position TEXT, PRIMARY KEY (user_id, media_id))')
    conn.commit()
    conn.close()

def clean_title_from_filename(filename):
    name, _ = os.path.splitext(filename)
    clean_name = re.sub(r'[\.\-_]', ' ', name)
    clean_name = re.sub(r'(1080p|720p|4k|bluray|x264|h264|webrip|mp4|mkv)', '', clean_name, flags=re.IGNORECASE)
    return clean_name.strip().title()

def auto_scan_all_google_drives():
    if not os.path.exists("credentials.json"):
        print("Error: 'credentials.json' is missing! Rename your MYTV5X55INCH file to credentials.json in the sidebar.")
        return

    init_database()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)

    total_count = 0
    print("Connecting to Google Drive API...")

    for folder_id in FOLDER_IDS:
        print(f"Scanning Folder: {folder_id}...")
        try:
            query = f"'{folder_id}' in parents and mimeType contains 'video/' and trashed = false"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])

            for f in files:
                file_id = f['id']
                file_name = f['name']
                title = clean_title_from_filename(file_name)
                stream_url = f"https://drive.google.com/file/d/{file_id}/preview"
                
                cursor.execute('''
                    INSERT INTO media (id, title, type, genre, banner_url, stream_source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET title=excluded.title, stream_source=excluded.stream_source
                ''', (file_id, title, 'movie', 'Cloud Media', 'https://images.unsplash.com/photo-1594909122845-11baa439b7bf?w=400', stream_url))
                total_count += 1
        except Exception as e:
            print(f"Error reading folder {folder_id}: {e}")

    conn.commit()
    conn.close()
    print(f"\nSuccess! Automatically aggregated {total_count} movies across all connected Google Drives.")

if __name__ == "__main__":
    auto_scan_all_google_drives()