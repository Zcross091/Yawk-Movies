import os
import xml.etree.ElementTree as ET
import sqlite3

DB_NAME = "streaming_platform.db"

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

def ingest_library(xml_path):
    if not os.path.exists(xml_path):
        print(f"Error: Target '{xml_path}' data layer descriptor missing.")
        return

    init_database()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        count = 0
        
        for item in root.findall('.//*'):
            if item.tag in ['movie', 'series', 'show']:
                media_id = item.get('id')
                title = item.find('title').text if item.find('title') is not None else "Untitled"
                genre = item.find('genre').text if item.find('genre') is not None else "General"
                banner = item.find('banner_url').text if item.find('banner_url') is not None else "https://via.placeholder.com/400"
                source = item.find('stream_source').text if item.find('stream_source') is not None else ""
                
                cursor.execute('''
                    INSERT INTO media (id, title, type, genre, banner_url, stream_source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET stream_source=excluded.stream_source, title=excluded.title
                ''', (media_id, title, item.tag, genre, banner, source))
                count += 1
                
        conn.commit()
        print(f"Database successfully updated. Synchronized {count} Google Drive entries.")
    except Exception as e:
        print(f"Parsing engine failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    ingest_library("library.xml")