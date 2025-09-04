import os, sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "wellatlas.db")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

def ensure_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            customer TEXT,
            job_category TEXT,
            description TEXT,
            latitude REAL,
            longitude REAL,
            deleted INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('header_title', 'WellAtlas 2.7.5 — Classic Map (Improved)')")
    conn.commit(); conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_setting(key, default=""):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone(); conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO settings (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,value))
    conn.commit(); conn.close()

ensure_schema()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")

@app.route("/healthz")
def healthz():
    try:
        conn = get_db(); conn.execute("SELECT 1"); conn.close()
        return "ok", 200
    except Exception as e:
        return f"not ok: {e}", 500

@app.route("/")
def index():
    return render_template("index.html", header_title=get_setting("header_title","WellAtlas 2.7.5 — Classic Map (Improved)"))

@app.route("/api/sites")
def api_sites():
    q = request.args.get("q","").strip()
    job = request.args.get("job","").strip()
    clauses, params = ["deleted=0"], []
    if q:
        clauses.append("(name LIKE ? OR description LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if job:
        clauses.append("job_category=?")
        params.append(job)
    conn = get_db(); c = conn.cursor()
    sql = "SELECT * FROM sites WHERE " + " AND ".join(clauses) + " ORDER BY datetime(created_at) DESC"
    c.execute(sql, params); rows = [dict(r) for r in c.fetchall()]; conn.close()
    return jsonify(rows)

@app.route("/sites/create", methods=["POST"])
def create_site():
    name = request.form.get("name","").strip() or "Untitled Site"
    customer = request.form.get("customer","").strip()
    job_category = request.form.get("job_category","").strip()
    description = request.form.get("description","").strip()
    try:
        lat = float(request.form.get("latitude") or 0.0)
        lon = float(request.form.get("longitude") or 0.0)
    except ValueError:
        lat, lon = 0.0, 0.0
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO sites (name,customer,job_category,description,latitude,longitude,created_at) VALUES (?,?,?,?,?,?,?)",
              (name,customer,job_category,description,lat,lon,datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    flash("Site created.","success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)
