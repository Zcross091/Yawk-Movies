from flask import Flask, render_template_string, request, redirect, session, jsonify
import sqlite3
import subprocess

app = Flask(__name__)
app.secret_key = "netflix_red_secure_session_key"
DB_NAME = "streaming_platform.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ====================== MULTI-PLAYER TEMPLATE ======================
PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - StreamRed</title>
    <style>
        :root { --primary-red: #E50914; }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background:#000; font-family: 'Helvetica Neue', Arial, sans-serif; color:white; overflow:hidden; }
        .header { 
            position: fixed; top: 0; left: 0; width: 100%; padding: 15px 20px; 
            background: linear-gradient(to bottom, rgba(0,0,0,0.95), transparent); 
            display: flex; align-items: center; z-index: 1000; gap: 15px;
        }
        .back-btn { color: white; font-size: 32px; cursor: pointer; }
        .title { font-size: 19px; font-weight: 500; flex: 1; }
        
        .player-options {
            position: fixed; top: 70px; left: 50%; transform: translateX(-50%);
            background: rgba(0,0,0,0.85); padding: 8px; border-radius: 8px; 
            display: flex; gap: 8px; z-index: 999;
        }
        .player-btn {
            padding: 8px 16px; background: #333; color: white; border: none;
            border-radius: 6px; cursor: pointer; font-size: 14px;
        }
        .player-btn.active { background: var(--primary-red); }

        iframe, video { width: 100vw; height: 100vh; border: none; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="header">
        <a href="/" class="back-btn">←</a>
        <div class="title">{{ title }}</div>
    </div>

    <div class="player-options">
        <button class="player-btn active" onclick="switchPlayer(0)">Preview</button>
        <button class="player-btn" onclick="switchPlayer(1)">Direct Play</button>
        <button class="player-btn" onclick="switchPlayer(2)">HTML5 Player</button>
    </div>

    <!-- Player 1: Google Preview -->
    <iframe id="player0" src="{{ preview_url }}" allowfullscreen allow="autoplay; encrypted-media"></iframe>

    <!-- Player 2: Direct Download Link -->
    <iframe id="player1" src="{{ direct_url }}" class="hidden" allowfullscreen></iframe>

    <!-- Player 3: HTML5 Video Player -->
    <video id="player2" controls autoplay class="hidden" style="background:black;">
        <source src="{{ direct_url }}" type="video/mp4">
        <source src="{{ direct_url }}" type="video/webm">
        Your browser does not support video playback.
    </video>

    <script>
        function switchPlayer(n) {
            document.querySelectorAll('iframe, video').forEach(p => p.classList.add('hidden'));
            document.getElementById('player' + n).classList.remove('hidden');
            
            // Update active button
            document.querySelectorAll('.player-btn').forEach((btn, i) => {
                btn.classList.toggle('active', i === n);
            });
        }

        // Auto try HTML5 player if preview fails
        window.onload = function() {
            setTimeout(() => {
                const preview = document.getElementById('player0');
                if (preview && preview.contentDocument && preview.contentDocument.body.innerText.includes("No preview")) {
                    switchPlayer(2);
                }
            }, 3000);
        };
    </script>
</body>
</html>
"""

# ====================== HOME PAGE (unchanged) ======================
BASE_TEMPLATE = """ ... (Your previous home template - keeping it same for now) ... """

@app.route('/')
def home():
    db = get_db()
    trending = db.execute("SELECT * FROM media ORDER BY views DESC LIMIT 12").fetchall()
    library = db.execute("SELECT * FROM media ORDER BY title ASC").fetchall()
    
    history = []
    if session.get('user_id'):
        history = db.execute('SELECT m.* FROM media m JOIN user_interactions i ON m.id = i.media_id WHERE i.user_id = ? ORDER BY m.views DESC LIMIT 8', (session['user_id'],)).fetchall()
    db.close()
    return render_template_string(BASE_TEMPLATE, trending=trending, library=library, history=history)

@app.route('/play/<media_id>')
def play(media_id):
    db = get_db()
    media = db.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
    db.close()
    
    if not media:
        return "Video not found", 404

    # Log view
    db = get_db()
    db.execute("UPDATE media SET views = views + 1 WHERE id = ?", (media_id,))
    if session.get('user_id'):
        db.execute('INSERT INTO user_interactions (user_id, media_id, watch_position) VALUES (?, ?, "watching") ON CONFLICT(user_id, media_id) DO UPDATE SET watch_position="watching"', (session['user_id'], media_id))
    db.commit()
    db.close()

    preview_url = media['stream_source']  # Current one (preview or uc)
    direct_url = f"https://drive.google.com/uc?id={media['id']}&export=download"

    return render_template_string(PLAYER_TEMPLATE, 
                                title=media['title'], 
                                preview_url=preview_url,
                                direct_url=direct_url)

# Keep your /auth, /logout, /refresh routes...

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
