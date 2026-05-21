from flask import Flask, render_template_string, request, redirect, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "super_secret_netflix_red_key_change_this"
DB_NAME = "streaming_platform.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --- HTML CSS JAVASCRIPT MONOLITHIC JINJA TEMPLATE ---
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StreamRed - Private Engine</title>
    <style>
        :root { --primary-red: #E50914; --dark-bg: #141414; --card-bg: #181818; --text-main: #FFFFFF; }
        body { background-color: var(--dark-bg); color: var(--text-main); font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 0; padding: 0; }
        
        /* Navigation styling */
        nav { display: flex; justify-content: space-between; align-items: center; padding: 20px 4%; background: linear-gradient(to bottom, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0) 100%); position: sticky; top: 0; z-index: 10; }
        .logo { color: var(--primary-red); font-size: 28px; font-weight: bold; text-decoration: none; letter-spacing: 1px; }
        .nav-links a, .auth-btn { color: white; text-decoration: none; margin-left: 20px; font-size: 14px; cursor: pointer; }
        .auth-btn { background: var(--primary-red); padding: 7px 17px; border-radius: 3px; border: none;}

        /* Showcase main screen layout */
        .hero { height: 50vh; display: flex; flex-direction: column; justify-content: center; padding: 0 4%; background: linear-gradient(rgba(20,20,20,0.2), rgba(20,20,20,1)), url('https://images.unsplash.com/photo-1536440136628-849c177e76a1?q=80&w=1200') no-repeat center/cover; }
        .hero h1 { font-size: 48px; margin: 0 0 10px 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.6); }

        /* Shelf Row structures */
        .shelf { padding: 20px 4%; }
        .shelf-title { font-size: 20px; font-weight: bold; margin-bottom: 15px; color: #e5e5e5; }
        .grid-container { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 15px; scroll-behavior: smooth; }
        .grid-container::-webkit-scrollbar { height: 8px; }
        .grid-container::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }

        .media-card { min-width: 200px; max-width: 200px; background: var(--card-bg); border-radius: 4px; overflow: hidden; transition: transform 0.3s ease; position: relative; cursor: pointer; }
        .media-card:hover { transform: scale(1.05); z-index: 2; }
        .media-card img { width: 100%; height: 280px; object-fit: cover; }
        .card-details { padding: 10px; font-size: 14px; }
        .card-meta { display: flex; justify-content: space-between; color: #aaa; font-size: 11px; margin-top: 5px; }

        /* Interactive player module viewport */
        .player-viewport { width: 100%; height: 500px; background: #000; display: none; position: relative; border-bottom: 4px solid var(--primary-red); }
        .player-viewport iframe, .player-viewport video { width: 100%; height: 100%; border: none; }
        .close-player { position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.7); color: white; border: none; padding: 10px 15px; font-size: 16px; cursor: pointer; border-radius: 50%; z-index: 100; }

        /* Basic modal system */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); justify-content: center; align-items: center; z-index: 1000; }
        .modal-content { background: #181818; padding: 40px; border-radius: 8px; width: 320px; border: 1px solid #222; }
        .modal-content h2 { margin-top: 0; color: white; }
        .modal-content input { width: 100%; padding: 10px; margin: 10px 0; background: #333; border: none; color: white; border-radius: 4px; box-sizing: border-box; }
        .modal-content button { width: 100%; padding: 12px; background: var(--primary-red); color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; margin-top: 10px; }
    </style>
</head>
<body>

    <nav>
        <a href="/" class="logo">STREAMRED</a>
        <div class="nav-links">
            {% if session.get('user_id') %}
                <span style="color: #aaa;">Hello, <b>{{ session['username'] }}</b></span>
                <a href="/logout">Sign Out</a>
            {% else %}
                <button class="auth-btn" onclick="openModal()">Sign In</button>
            {% endif %}
        </div>
    </nav>

    <!-- Embedded Video Playback Station -->
    <div class="player-viewport" id="viewport">
        <button class="close-player" onclick="closeVideo()">✕</button>
        <div id="video-mount" style="width:100%; height:100%;"></div>
    </div>

    <div class="hero">
        <h1>Private Aggregator Portal</h1>
        <p style="max-width: 500px; color:#cccccc;">Explore cross-device unified feeds compiled cleanly from your ingested system networks.</p>
    </div>

    <!-- Shelf Component 1: Most Viewed Tracking -->
    <div class="shelf">
        <div class="shelf-title">Trending / Most Viewed</div>
        <div class="grid-container">
            {% for item in trending %}
            <div class="media-card" onclick="playMedia('{{ item.id }}', '{{ item.stream_source }}')">
                <img src="{{ item.banner_url }}" alt="{{ item.title }}">
                <div class="card-details">
                    <div><b>{{ item.title }}</b></div>
                    <div class="card-meta"><span>{{ item.genre }}</span><span>👁 {{ item.views }}</span></div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Shelf Component 2: Standard Filter Shelf -->
    <div class="shelf">
        <div class="shelf-title">All Curated Titles</div>
        <div class="grid-container">
            {% for item in library %}
            <div class="media-card" onclick="playMedia('{{ item.id }}', '{{ item.stream_source }}')">
                <img src="{{ item.banner_url }}" alt="{{ item.title }}">
                <div class="card-details">
                    <div><b>{{ item.title }}</b></div>
                    <div class="card-meta"><span>{{ item.genre }}</span><span>{{ item.type|upper }}</span></div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Auth Input Modal Window Container -->
    <div class="modal" id="authModal" onclick="closeModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <h2>Sign In / Register</h2>
            <form action="/auth" method="POST">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Continue to Dashboard</button>
            </form>
        </div>
    </div>

    <script>
        function openModal() { document.getElementById('authModal').style.display = 'flex'; }
        function closeModal(e) { document.getElementById('authModal').style.display = 'none'; }
        
        function playMedia(id, src) {
            // Log analytics hit to database back-end layer
            fetch(`/view/${id}`, { method: 'POST' });

            const viewport = document.getElementById('viewport');
            const mount = document.getElementById('video-mount');
            viewport.style.display = 'block';
            window.scrollTo({ top: 0, behavior: 'smooth' });

            // Handle clean iframe embed wrapper vs direct link rendering logic
            if (src.includes('embed') || !src.endsWith('.mp4') && !src.includes('.m3u8')) {
                mount.innerHTML = `<iframe src="${src}" allowfullscreen allow="autoplay; encrypted-media"></iframe>`;
            } else {
                mount.innerHTML = `<video src="${src}" controls autoplay></video>`;
            }
        }

        function closeVideo() {
            document.getElementById('viewport').style.display = 'none';
            document.getElementById('video-mount').innerHTML = '';
        }
    </script>
</body>
</html>
"""

# --- ROUTING LOGIC CHANNELS ---

@app.route('/')
def home():
    db = get_db()
    # Fetch content sorted by descending view counters (Most Viewed Shelf)
    trending = db.execute("SELECT * FROM media ORDER BY views DESC LIMIT 10").fetchall()
    # Fetch general default listing library
    library = db.execute("SELECT * FROM media ORDER BY title ASC").fetchall()
    db.close()
    return render_template_string(BASE_TEMPLATE, trending=trending, library=library)

@app.route('/auth', methods=['POST'])
def auth():
    username = request.form['username']
    password = request.form['password'] # Note: Use safe hashing like werkzeug in real production builds
    
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
    else:
        # Dynamic inline onboarding auto-registration path
        cursor = db.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        db.commit()
        session['user_id'] = cursor.lastrow_index if hasattr(cursor, 'lastrow_index') else cursor.lastrowid
        session['username'] = username
        
    db.close()
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/view/<media_id>', methods=['POST'])
def register_view(media_id):
    db = get_db()
    db.execute("UPDATE media SET views = views + 1 WHERE id = ?", (media_id,))
    db.commit()
    db.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
