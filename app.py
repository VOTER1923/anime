from flask import Flask, render_template, request, redirect, session, jsonify, Response
import requests
import sqlite3
import time
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Use Zoro provider (more stable)
CONSUMET = "https://api.consumet.org/anime/zoro"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://github.com/"
}

# -----------------------------
# Database Setup
# -----------------------------
def db():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS watchlist (id INTEGER PRIMARY KEY, user_id INTEGER, anime_id TEXT, title TEXT)")
    conn.commit()
init_db()

# -----------------------------
# Helper: Fetch JSON safely
# -----------------------------
def fetch(url):
    for _ in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            return r.json()
        except:
            time.sleep(1)
    return None

# -----------------------------
# HOME PAGE
# -----------------------------
@app.get("/")
def home():
    return render_template("home.html")

# -----------------------------
# SEARCH PAGE
# -----------------------------
@app.get("/search")
def search():
    q = request.args.get("q")
    if not q:
        return render_template("search.html", query="", results=[])

    data = fetch(f"{CONSUMET}/{q}")
    results = data.get("results", []) if data else []

    return render_template("search.html", query=q, results=results)

# -----------------------------
# ANIME PAGE
# -----------------------------
@app.get("/anime/<anime_id>")
def anime_page(anime_id):
    data = fetch(f"{CONSUMET}/info/{anime_id}")

    if not data:
        return "Anime not found"

    anime = {
        "title": data.get("title"),
        "description": data.get("description")
    }

    episodes = []
    for ep in data.get("episodes", []):
        episodes.append({
            "id": ep.get("id"),
            "number": ep.get("number")
        })

    return render_template("anime.html", anime=anime, episodes=episodes)

# -----------------------------
# WATCH PAGE
# -----------------------------
@app.get("/watch/<episode_id>")
def watch(episode_id):
    data = fetch(f"{CONSUMET}/watch/{episode_id}")

    if not data or "sources" not in data:
        return "No sources found"

    source_url = data["sources"][0]["url"]

    anime_title = data.get("title", "Anime")
    episode_number = data.get("episode", "1")
    anime_id = data.get("id", "")

    return render_template(
        "watch.html",
        anime_title=anime_title,
        episode_number=episode_number,
        anime_id=anime_id,
        source_url=source_url
    )

# -----------------------------
# SIGNUP
# -----------------------------
@app.get("/signup")
def signup_page():
    return render_template("signup.html")

@app.post("/signup")
def signup():
    username = request.form["username"]
    password = request.form["password"]

    conn = db()
    conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()

    return redirect("/login")

# -----------------------------
# LOGIN
# -----------------------------
@app.get("/login")
def login_page():
    return render_template("login.html")

@app.post("/login")
def login():
    username = request.form["username"]
    password = request.form["password"]

    conn = db()
    user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()

    if user:
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect("/dashboard")

    return "Invalid login"

# -----------------------------
# DASHBOARD + WATCHLIST
# -----------------------------
@app.get("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = db()
    watchlist = conn.execute("SELECT * FROM watchlist WHERE user_id=?", (session["user_id"],)).fetchall()

    return render_template("dashboard.html", username=session["username"], watchlist=watchlist)

@app.get("/add_watchlist/<anime_id>/<title>")
def add_watchlist(anime_id, title):
    if "user_id" not in session:
        return redirect("/login")

    conn = db()
    conn.execute("INSERT INTO watchlist (user_id, anime_id, title) VALUES (?, ?, ?)",
                 (session["user_id"], anime_id, title))
    conn.commit()

    return redirect("/dashboard")

# -----------------------------
# LOGOUT
# -----------------------------
@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")

# -----------------------------
# RUN SERVER (Render-compatible)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
