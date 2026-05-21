import os
import xml.etree.ElementTree as ET
import sqlite3

DB_NAME = "streaming_platform.db"

def init_database():
    """Initializes the database schema for content, users, and interaction metrics."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Core media storage table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media (
            id TEXT PRIMARY KEY,
            title TEXT,
            type TEXT, -- 'movie' or 'series'
            genre TEXT,
            banner_url TEXT,
            stream_source TEXT,
            views INTEGER DEFAULT 0
        )
    ''')
    
    # Simple user authentication table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    
    # Interactions tracking table for cross-device state
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_interactions (
            user_id INTEGER,
            media_id TEXT,
            liked INTEGER DEFAULT 0,
            watch_position TEXT, -- Timestamp or status
            PRIMARY KEY (user_id, media_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def ingest_xml_feed(xml_path):
    """Parses structural XML feeds and upserts data safely into the database layer."""
    if not os.path.exists(xml_path):
        print(f"Error: Target file '{xml_path}' not found.")
        return

    print(f"Starting ingestion process for: {xml_path}")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        count = 0
        # Iterate over both movie and series tags safely
        for item in root.findall('.//*'):
            if item.tag in ['movie', 'series']:
                media_id = item.get('id')
                title = item.find('title').text if item.find('title') is not None else "Unknown Title"
                genre = item.find('genre').text if item.find('genre') is not None else "General"
                banner = item.find('banner_url').text if item.find('banner_url') is not None else "https://via.placeholder.com/300"
                source = item.find('stream_source').text if item.find('stream_source') is not None else ""
                
                # Insert or update if content matching id already exists
                cursor.execute('''
                    INSERT INTO media (id, title, type, genre, banner_url, stream_source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        title=excluded.title,
                        genre=excluded.genre,
                        banner_url=excluded.banner_url,
                        stream_source=excluded.stream_source
                ''', (media_id, title, item.tag, genre, banner, source))
                count += 1
                
        conn.commit()
        print(f"Successfully processed and synced {count} media entities.")
    except ET.ParseError:
        print("Fatal Error: Failed to parse XML. Verify your tags are closed properly.")
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()
    # Replace with the path to your main xml data repository descriptor
    ingest_xml_feed("library.xml")
