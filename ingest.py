import os
import re
import sqlite3
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

DB_NAME = "streaming_platform.db"

FOLDER_IDS = [
    "1Qv15HXr0h0qbX9DDu81j6MESfojHolYv",
    "1i9Fu-8tZmAgnmiKxxHLbK8N2zv5OKsft",
    "1y_JIB1lZj-NZ9I-Te8uvge-UrCd_Bvlu"
]

def init_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media (
            id TEXT PRIMARY KEY, title TEXT, type TEXT, 
            genre TEXT, banner_url TEXT, stream_source TEXT, 
            views INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_interactions (
            user_id INTEGER, media_id TEXT, liked INTEGER DEFAULT 0, 
            watch_position TEXT, PRIMARY KEY (user_id, media_id)
        )
    ''')
    conn.commit()
    conn.close()

def clean_title_from_filename(filename):
    name, _ = os.path.splitext(filename)
    clean_name = re.sub(r'[\.\-_]', ' ', name)
    clean_name = re.sub(r'(1080p|720p|4k|bluray|x264|h264|webrip|web-dl|1080|720)', '', clean_name, flags=re.IGNORECASE)
    return clean_name.strip().title()

def auto_scan_all_google_drives():
    cred_json = os.getenv("GOOGLE_CREDENTIALS")
    if not cred_json:
        print("❌ GOOGLE_CREDENTIALS not found!")
        return

    try:
        if cred_json.startswith('"') and cred_json.endswith('"'):
            cred_json = cred_json[1:-1]
        creds_dict = json.loads(cred_json)
    except:
        print("❌ Invalid GOOGLE_CREDENTIALS JSON")
        return

    init_database()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        total_count = 0
        found_ids = set()
        print("🔄 Scanning Google Drive...")

        for folder_id in FOLDER_IDS:
            try:
                query = f"'{folder_id}' in parents and trashed = false and (mimeType contains 'video/' or name contains '.mp4' or name contains '.mkv' or name contains '.mov' or name contains '.m4v' or name contains '.avi' or name contains '.webm')"

                results = service.files().list(q=query, fields="files(id, name, mimeType)", pageSize=1000).execute()
                files = results.get('files', [])

                for f in files:
                    file_id = f['id']
                    title = clean_title_from_filename(f['name'])
                    
                    # Best working link for MovieBox files
                    stream_url = f"https://drive.google.com/uc?id={file_id}&export=download"
                    
                    cursor.execute('''
                        INSERT INTO media (id, title, type, genre, banner_url, stream_source)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET 
                            title=excluded.title, 
                            stream_source=excluded.stream_source
                    ''', (file_id, title, 'movie', 'Cloud Media', 
                          'https://images.unsplash.com/photo-1594909122845-11baa439b7bf?w=400', 
                          stream_url))
                    
                    found_ids.add(file_id)
                    total_count += 1
                    print(f"✅ Indexed: {title}")

            except Exception as e:
                print(f"❌ Error scanning folder {folder_id}: {e}")

        if found_ids:
            placeholders = ",".join("?" for _ in found_ids)
            cursor.execute(f"DELETE FROM media WHERE id NOT IN ({placeholders})", tuple(found_ids))

        conn.commit()
        print(f"\n🎉 Success! Synced {total_count} videos.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    auto_scan_all_google_drives()
