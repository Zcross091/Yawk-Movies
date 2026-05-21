from flask import Flask, render_template_string, request, redirect, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "netflix_red_secure_session_key"
DB_NAME = "streaming_platform.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --- DYNAMIC JINJA INTERFACE LAYOUT ---
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StreamRed Portal</title>
    <style>
        :root { --primary-red: #E50914; --dark-bg: #141414; --card-bg: #181818; --text-main: #FFFFFF; }
        body { background-color: var(--dark-bg); color: var(--text-main); font-family: 'Helvetica Neue', Arial, sans-serif; margin: 0; padding: 0; overflow-x: hidden; }
        
        nav { display: flex; justify-content: space-between; align-items: center; padding: 20px 4%; background: linear-gradient(to bottom, rgba(0,0,0,0.8), transparent); position: sticky; top: 0; z-index: 100; }
        .logo { color: var(--primary-red); font-size: 26px; font-weight: bold; text-decoration: none; letter-spacing: 1px; }
        .nav-links a, .auth-btn { color: white; text-decoration: none; margin-left: 20px; font-size: 14px; cursor: pointer; }
        .auth-btn { background: var(--primary-red); padding: 7px 17px; border-radius: 3px; border: none; font-weight: bold;}

        .player-viewport { width: 100%; height: 550px; background: #000; display: none; position: relative; border-bottom: 4px solid var(--primary-red); }
        .player-viewport iframe { width: 100%; height: 100%; border: none; }
        .player-controls { position: absolute; bottom: 20px; left: 4%; z-index: 110; display: flex; gap: 15px; }
        .control-btn { background: rgba(255,255,255,0.2); border: none; color: white; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; backdrop-filter: blur(5px); }
        .control-btn:hover { background: var(--primary-red); }
        .close-player { position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.7); color: white; border: none; padding: 10px 15px; font-size: 16px; cursor: pointer; border-radius: 50%; z-index: 110; }

        .shelf { padding: 20px 4%; }
        .shelf-title { font-size: 20px; font-weight: bold; margin-bottom: 15px; color: #e5e5e5; }
        .grid-container { display: flex; gap: 12px; overflow-x: auto; padding-bottom: 15px; }
        .grid-container::-webkit-scrollbar { height: 6px; }
        .grid-container::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }

        .media-card { min-width: 200px; max-width: 200px; background: var(--card-bg); border-radius: 4px; overflow: hidden; transition: transform 0.3s ease; cursor: pointer; position: relative; }
        .media-card:hover { transform: scale(1.05); z-index: 5; }
        .media-card img { width: 100%; height: 280px; object-fit: cover; }
        .card-details { padding: 10px; font-size: 14px; }
        
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); justify-content: center; align-items: center; z-index: 1000; }
        .modal-content { background: #181818; padding: 40px; border-radius: 8px; width: 300px; border: 1px solid #222; }
        .modal-content input { width: 100%; padding: 12px; margin: 10px 0; background: #333; border: none; color: white; border-radius: 4px; box-sizing: border-box; }
        .modal-content button { width: 100%; padding: 12px; background: var(--primary-red); color: white; border: none; font-weight: bold; border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>

    <nav>
        <a href="/" class="logo">STREAMRED</a>
        <div class="nav-links">
            {% if session.get('user_id') %}
                <span style="color: #aaa;">User: <b>{{ session['username'] }}</b></span>
                <a href="/logout">Sign Out</a>
            {% else %}
                <button class="auth-btn" onclick="openModal()">Sign In</button>
            {% endif %}
        </div>
    </nav>

    <div class="player-viewport" id="viewport">
        <button class="close-player" onclick="closeVideo()">✕</button>
        <div class="player-controls">
            <button class="control-btn" id="like-btn">❤ Add to Favorites</button>
        </div>
        <div id="video-mount" style="width:100%; height:100%;"></div>
    </div>

    {% if history %}
    <div class="shelf">
        <div class="shelf-title">Continue Watching</div>
        <div class="grid-container">
            {% for item in history %}
            <div class="media-card" onclick="playMedia('{{ item.id }}', '{{ item.stream_source }}')">
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
            <div class="media-card" onclick="playMedia('{{ item.id }}', '{{ item.stream_source }}')">
                <img src="{{ item.banner_url }}">
                <div class="card-details">
                    <div><b>{{ item.title }}</b></div>
                    <div style="color:#aaa; font-size:11px; margin-top:5px;">👁 {{ item.views }} views</div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="shelf">
        <div class="shelf-title">All Movies & Shows</div>
        <div class="grid-container">
            {% for item in library %}
            <div class="media-card" onclick="playMedia('{{ item.id }}', '{{ item.stream_source }}')">
                <img src="{{ item.banner_url }}">
                <div class="card-details"><b>{{ item.title }}</b></div>
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="modal" id="authModal">
        <div class="modal-content">
            <h2 style="margin-top:0;">Sign In</h2>
            <form action="/auth" method="POST">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Sign In / Register</button>
            </form>
        </div>
    </div>

    <script>
        let currentActiveMediaId = null;
        function openModal() { document.getElementById('authModal').style.display = 'flex'; }
        
        function playMedia(id, src) {
            currentActiveMediaId = id;
            fetch(`/view/${id}`, { method: 'POST' });

            const viewport = document.getElementById('viewport');
            const mount = document.getElementById('video-mount');
            viewport.style.display = 'block';
            window.scrollTo({ top: 0, behavior: 'smooth' });

            mount.innerHTML = `<iframe src="${src}" allowfullscreen allow="autoplay; encrypted-media"></iframe>`;
            
            document.getElementById('like-btn').onclick = function() {
                fetch(`/like/${currentActiveMediaId}`, { method: 'POST' })
                    .then(res => res.json())
                    .then(data => alert(data.message));
            };
        }

        function closeVideo() {
            document.getElementById('viewport').style.display = 'none';
            document.getElementById('video-mount').innerHTML = '';
        }
    </script>
</body>
</html>
"""

# --- BACKEND SERVER ROUTING CONTROLS ---

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
            WHERE i.user_id = ? ORDER BY m.views DESC LIMIT 6
        ''', (session['user_id'],)).fetchall()
    db.close()
    return render_template_string(BASE_TEMPLATE, trending=trending, library=library, history=history)

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

@app.route('/view/<media_id>', methods=['POST'])
def log_view(media_id):
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
    return jsonify({"status": "indexed"})

@app.route('/like/<media_id>', methods=['POST'])
def log_like(media_id):
    if not session.get('user_id'):
        return jsonify({"message": "Please log in to save favorites!"})
    db = get_db()
    db.execute('''
        INSERT INTO user_interactions (user_id, media_id, liked) 
        VALUES (?, ?, 1) 
        ON CONFLICT(user_id, media_id) DO UPDATE SET liked=1
    ''', (session['user_id'], media_id))
    db.commit()
    db.close()
    return jsonify({"message": "Added to your cross-device favorites row!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)