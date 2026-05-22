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

# ====================== PLAYER PAGE ======================
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
        body { background:#000; font-family: 'Helvetica Neue', Arial, sans-serif; overflow:hidden; }
        .header { 
            position: fixed; top: 0; left: 0; width: 100%; padding: 15px 20px; 
            background: linear-gradient(to bottom, rgba(0,0,0,0.95), transparent); 
            display: flex; align-items: center; z-index: 1000; 
        }
        .back-btn { color: white; font-size: 32px; cursor: pointer; margin-right: 15px; }
        .title { color: white; font-size: 19px; font-weight: 500; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        iframe { width: 100vw; height: 100vh; border: none; }
    </style>
</head>
<body>
    <div class="header">
        <a href="/" class="back-btn">←</a>
        <div class="title">{{ title }}</div>
    </div>
    <iframe src="{{ stream_source }}" allowfullscreen allow="autoplay; encrypted-media"></iframe>
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
        .auth-btn, .refresh-btn { 
            background: var(--primary-red); padding: 8px 18px; border-radius: 4px; 
            font-weight: bold; border: none; color: white; cursor: pointer; 
        }
        .refresh-btn { background: #333; }

        .shelf { padding: 25px 4% 10px; }
        .shelf-title { font-size: 21px; font-weight: bold; margin-bottom: 15px; color: #e5e5e5; }
        .grid-container { display: flex; gap: 12px; overflow-x: auto; padding-bottom: 20px; }
        .media-card { 
            min-width: 200px; background: var(--card-bg); border-radius: 6px; 
            overflow: hidden; transition: transform 0.3s ease; cursor: pointer; 
        }
        .media-card:hover { transform: scale(1.08); }
        .media-card img { width: 100%; height: 280px; object-fit: cover; }
        .card-details { padding: 10px; font-size: 14.5px; }
    </style>
</head>
<body>
    <nav>
        <a href="/" class="logo">STREAMRED</a>
        <div class="nav-links">
            <button class="refresh-btn" onclick="refreshLibrary()">🔄 Refresh Library</button>
            {% if session.get('user_id') %}
                <span>{{ session['username'] }}</span>
                <a href="/logout">Sign Out</a>
            {% else %}
                <button class="auth-btn" onclick="openModal()">Sign In</button>
            {% endif %}
        </div>
    </nav>

    {% if history %}
    <div class="shelf">
        <div class="shelf-title">Continue Watching</div>
        <div class="grid-container">
            {% for item in history %}
            <div class="media-card" onclick="window.location.href='/play/{{ item.id }}'">
                <img src="{{ item.banner_url }}">
                <div class="card-details"><b>{{ item.title }}</b></div>
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

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

    <div class="modal" id="authModal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);justify-content:center;align-items:center;z-index:1000;">
        <div style="background:#181818;padding:40px;border-radius:8px;width:310px;">
            <h2 style="margin-top:0;">Sign In</h2>
            <form action="/auth" method="POST">
                <input type="text" name="username" placeholder="Username" required style="width:100%;padding:12px;margin:10px 0;background:#333;border:none;color:white;border-radius:4px;">
                <input type="password" name="password" placeholder="Password" required style="width:100%;padding:12px;margin:10px 0;background:#333;border:none;color:white;border-radius:4px;">
                <button type="submit" style="width:100%;padding:13px;background:#E50914;color:white;border:none;font-weight:bold;border-radius:4px;cursor:pointer;">Sign In / Register</button>
            </form>
        </div>
    </div>

    <script>
        function openModal() { document.getElementById('authModal').style.display = 'flex'; }

        function refreshLibrary() {
            if (confirm("Scan Google Drive for new videos?")) {
                fetch('/refresh', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        alert(data.message);
                        location.reload();
                    })
                    .catch(() => alert("Failed to refresh"));
            }
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
    if session.get('user_id'):
        history = db.execute('''
            SELECT m.* FROM media m 
            JOIN user_interactions i ON m.id = i.media_id 
            WHERE i.user_id = ? ORDER BY m.views DESC LIMIT 8
        ''', (session['user_id'],)).fetchall()
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
        db.execute('''
            INSERT INTO user_interactions (user_id, media_id, watch_position) 
            VALUES (?, ?, 'watching') 
            ON CONFLICT(user_id, media_id) DO UPDATE SET watch_position='watching'
        ''', (session['user_id'], media_id))
    db.commit()
    db.close()

    return render_template_string(PLAYER_TEMPLATE, title=media['title'], stream_source=media['stream_source'])

@app.route('/refresh', methods=['POST'])
def refresh_library():
    try:
        result = subprocess.run(['python', 'ingest.py'], capture_output=True, text=True, timeout=90)
        if result.returncode == 0:
            return jsonify({"message": "✅ Library refreshed successfully!"})
        else:
            return jsonify({"message": "⚠️ Refresh done with some issues."})
    except Exception as e:
        return jsonify({"message": f"❌ Error: {str(e)}"})

@app.route('/auth', methods=['POST'])
def auth():
    username = request.form['username']
    password = request.form['password']
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
    else:
        cursor = db.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        db.commit()
        session['user_id'] = cursor.lastrowid
        session['username'] = username
    db.close()
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)