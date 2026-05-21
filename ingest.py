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

def clean_title_from_path(path_segments):
    """Parses folder names to create a human-readable title like 'Ben 10 - Season 2 - Episode 1'."""
    important_segments = []
    for seg in path_segments:
        # Ignore systemic MovieBox folders or root identifiers
        if not seg or "My Drive" in seg or "Movies" in seg or ".mbp_hls" in seg or seg.lower() == "video":
            continue
        important_segments.append(seg.title())
    
    if important_segments:
        return " - ".join(important_segments)
    return "Unknown Cloud Title"

def scan_folder_recursive(service, folder_id, current_path_segments, cursor):
    """Recursively crawls through subfolders to locate nested MovieBox streaming playlists."""
    total_found = 0
    
    # 1. Look for any video files or playlist index files in this folder
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    items = results.get('files', [])

    for item in items:
        name = item['name']
        file_id = item['id']
        mime_type = item['mimeType']

        # If it's a subfolder, dive into it recursively
        if mime_type == 'application/vnd.google-apps.folder':
            total_found += scan_folder_recursive(service, file_id, current_path_segments + [name], cursor)
        
        # Look for MovieBox index files or standalone videos
        elif name.endswith('.m3u8') or name.endswith('.mp4') or name.endswith('.mkv') or (current_path_segments and ".mbp_hls" in current_path_segments[-1]):
            # If we found the playlist tracker or a high-level video chunk container
            if name.endswith('.m3u8') or name == "video" or name.endswith('.mp4'):
                title = clean_title_from_path(current_path_segments)
                
                # We use the parent HLS folder or item ID as a unique primary key
                stream_url = f"https://drive.google.com/file/d/{file_id}/preview"
                
                cursor.execute('''
                    INSERT INTO media (id, title, type, genre, banner_url, stream_source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET title=excluded.title, stream_source=excluded.stream_source
                ''', (file_id, title, 'series' if 'season' in title.lower() else 'movie', 'Animation', 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=400', stream_url))
                total_found += 1
                print(f"Mapped Nested Content: {title}")
                
    return total_found

def auto_scan_all_google_drives():
    if not os.path.exists("credentials.json"):
        print("Error: 'credentials.json' is missing from your root directory!")
        return

    init_database()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)

    total_count = 0
    print("Connecting to Google Drive API... Beginning deep folder recursive crawl...")

    for folder_id in FOLDER_IDS:
        print(f"\nStarting Deep Scan on Base Folder ID: {folder_id}")
        try:
            total_count += scan_folder_recursive(service, folder_id, [], cursor)
        except Exception as e:
            print(f"Error accessing base folder entry {folder_id}: {e}")

    conn.commit()
    conn.close()
    print(f"\nSuccess! Deep crawl completed. Found and indexed {total_count} playable stream points.")

if __name__ == "__main__":
    auto_scan_all_google_drives()