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

# ====================== MULTI PLAYER TEMPLATE ======================
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
        .header { position: fixed; top: 0; left: 0; width: 100%; padding: 15px 20px; background: linear-gradient(to bottom, rgba(0,0,0,0.95), transparent); display: flex; align-items: center; z-index: 1000; gap: 15px; }
        .back-btn { color: white; font-size: 32px; cursor: pointer; }
        .title { font-size: 19px; font-weight: 500; flex: 1; }
        
        .player-options { position: fixed; top: 70px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.9); padding: 8px; border-radius: 8px; display: flex; gap: 8px; z-index: 999; }
        .player-btn { padding: 8px 16px; background: #333; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
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
        <button class="player-btn" onclick="switchPlayer(1)">Direct</button>
        <button class="player-btn" onclick="switchPlayer(2)">HTML5</button>
    </div>

    <iframe id="player0" src="{{ preview_url }}" allowfullscreen allow="autoplay; encrypted-media"></iframe>
    <iframe id="player1" src="{{ direct_url }}" class="hidden" allowfullscreen></iframe>
    <video id="player2" controls autoplay class="hidden" style="background:black;">
        <source src="{{ direct_url }}" type="video/mp4">
        Your browser does not support the video tag.
    </video>

    <script>
        function switchPlayer(n) {
            document.querySelectorAll('iframe, video').forEach(p => p.classList.add('hidden'));
            document.getElementById('player' + n).classList.remove('hidden');
            document.querySelectorAll('.player-btn').forEach((btn, i) => btn.classList.toggle('active', i === n));
        }
    </script>
</body>
</html>
"""

# ====================== HOME PAGE ======================
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StreamRed Portal</title>
    <style>
        :root { --primary-red: #E50914; --dark-bg: #141414; --card-bg: #181818; }
        body { background: var(--dark-bg); color: white; font-family: 'Helvetica Neue', Arial, sans-serif; margin:0; padding:0; }
        nav { display: flex; justify-content: space-between; align-items: center; padding: 20px 4%; background: linear-gradient(to bottom, rgba(0,0,0,0.8), transparent); position: sticky; top: 0; z-index: 100; }
        .logo { color: var(--primary-red); font-size: 28px; font-weight: bold; text-decoration: none; }
        .nav-links { display: flex; align-items: center; gap: 15px; }
        .auth-btn, .refresh-btn { background: var(--primary-red); padding: 8px 18px; border-radius: 4px; font-weight: bold; border: none; color: white; cursor: pointer; }
        .refresh-btn { background: #333; }
        .shelf { padding: 25px 4% 10px; }
        .shelf-title { font-size: 21px; font-weight: bold; margin-bottom: 15px; color: #e5e5e5; }
        .grid-container { display: flex; gap: 12px; overflow-x: auto; padding-bottom: 20px; }
        .media-card { min-width: 200px; background: var(--card-bg); border-radius: 6px; overflow: hidden; transition: transform 0.3s; cursor: pointer; }
        .media-card:hover { transform: scale(1.08); }
        .media-card img { width: 100%; height: 280px; object-fit: cover; }
        .card-details { padding: 10px; }
    </style>
</head>
<body>
    <nav>
        <a href="/" class="logo">STREAMRED</a>
        <div class="nav-links">
            <button class="refresh-btn" onclick="refreshLibrary()">🔄 Refresh</button>
            {% if session.get('user_id') %}
                <span>{{ session['username'] }}</span>
                <a href="/logout">Sign Out</a>
            {% else %}
                <button class="auth-btn" onclick="openModal()">Sign In</button>
            {% endif %}
        </div>
    </nav>

    <div class="shelf">
        <div class="shelf-title">Most Viewed</div>
        <div class="grid-container">
            {% for item in trending %}
            <div class="media-card" onclick="window.location.href='/play/{{ item.id }}'">
                <img src="{{ item.banner_url }}">
                <div class="card-details"><b>{{ item.title }}</b></div>
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="shelf">
        <div class="shelf-title">All Movies & Shows</div>
        <div class="grid-container">
            {% for item in library %}
            <div class="media-card" onclick="window.location.href='/play/{{ item.id }}'">
                <img src="{{ item.banner_url }}">
                <div class="card-details"><b>{{ item.title }}</b></div>
            </div>
            {% endfor %}
        </div>
    </div>

    <script>
        function openModal() { alert("Sign In feature coming soon!"); }
        function refreshLibrary() {
            fetch('/refresh', {method:'POST'}).then(r=>r.json()).then(data=>{alert(data.message); location.reload();});
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    db = get_db()
    trending = db.execute("SELECT * FROM media ORDER BY views DESC LIMIT 12").fetchall()
    library = db.execute("SELECT * FROM media ORDER BY title ASC").fetchall()
    history = []
    db.close()
    return render_template_string(BASE_TEMPLATE, trending=trending, library=library, history=history)

@app.route('/play/<media_id>')
def play(media_id):
    db = get_db()
    media = db.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
    db.close()

    if not media:
        return "Video not found", 404

    preview_url = media['stream_source']
    direct_url = f"https://drive.google.com/uc?id={media['id']}&export=download"

    return render_template_string(PLAYER_TEMPLATE, title=media['title'], preview_url=preview_url, direct_url=direct_url)

@app.route('/refresh', methods=['POST'])
def refresh_library():
    try:
        result = subprocess.run(['python', 'ingest.py'], capture_output=True, text=True, timeout=90)
        return jsonify({"message": "✅ Library refreshed!"})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"})

@app.route('/auth', methods=['POST'])
def auth():
    # Simple auth (you can improve later)
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)