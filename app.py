from flask import Flask, render_template, request, jsonify
import os, sqlite3, random
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "wellatlas.db")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

CUSTOMERS = ["Washington","Lincoln","Jefferson","Roosevelt","Kennedy"]
MINING_TERMS = ["Mother Lode","Pay Dirt","Sluice Box","Stamp Mill","Placer Claim","Drift Mine","Hydraulic Pit","Gold Pan","Tailings","Bedrock",
"Pick and Shovel","Ore Cart","Quartz Vein","Mine Shaft","Black Sand","Rocker Box","Prospect Hole","Hard Rock","Assay Office","Grubstake",
"Lode Claim","Panning Dish","Cradle Rocker","Dust Gold","Nugget Patch","Timbering","Creek Claim","Pay Streak","Ventilation Shaft","Bucket Line",
"Dredge Cut","Amalgam Press","Prospector’s Camp","Claim Jumper","Mining Camp","Gold Dust","Mine Portal","Crosscut Drift","Incline Shaft","Strike Zone",
"Wash Plant","Headframe","Drill Core","Stope Chamber","Milling House","Hoist House","Smelter Works","Ore Bin","Tunnel Bore","Grizzly Screen"]
CATEGORIES = ["Domestic","Drilling","Ag","Electrical"]
PHOTO_FILES = ["demo1.jpg","demo2.jpg","demo3.jpg","demo4.jpg","demo5.jpg"]

def ensure_schema():
    conn=sqlite3.connect(DB_PATH); cur=conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS sites (id INTEGER PRIMARY KEY, name TEXT, customer TEXT, job_number TEXT, job_category TEXT, description TEXT, latitude REAL, longitude REAL, deleted INTEGER, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, site_id INTEGER, body TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS photos (id INTEGER PRIMARY KEY, site_id INTEGER, filename TEXT, caption TEXT, created_at TEXT)")
    conn.commit(); conn.close()

def seed_demo():
    conn=sqlite3.connect(DB_PATH); cur=conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sites")
    if cur.fetchone()[0]>0: conn.close(); return
    coords=[(40.385,-122.280),(40.178,-122.240),(39.927,-122.180),(39.728,-121.837),(39.747,-122.194)]
    terms=MINING_TERMS.copy(); random.shuffle(terms)
    deleted_sites=random.sample(range(50),2)
    job_number=25001
    for i in range(50):
        customer=CUSTOMERS[i//10]; site_name=terms[i]; job_cat=random.choice(CATEGORIES); lat,lon=random.choice(coords)
        desc=f"Job #{job_number} established at the {site_name} site."
        deleted_flag=1 if i in deleted_sites else 0
        cur.execute("INSERT INTO sites (name,customer,job_number,job_category,description,latitude,longitude,deleted,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (site_name,customer,str(job_number),job_cat,desc,lat,lon,deleted_flag,datetime.utcnow().isoformat()))
        sid=cur.lastrowid
        cur.execute("INSERT INTO notes (site_id,body,created_at) VALUES (?,?,?)",(sid,"Initial site survey complete.",datetime.utcnow().isoformat()))
        cur.execute("INSERT INTO photos (site_id,filename,caption,created_at) VALUES (?,?,?,?)",(sid,random.choice(PHOTO_FILES),"Demo photo",datetime.utcnow().isoformat()))
        job_number+=1
    conn.commit(); conn.close()

ensure_schema(); seed_demo()

app=Flask(__name__,static_folder="static",template_folder="templates")

@app.route('/healthz')
def healthz():
    try:
        conn=sqlite3.connect(DB_PATH); conn.execute("SELECT 1"); conn.close()
        return "ok",200
    except Exception as e: return str(e),500

@app.route('/')
def index():
    return render_template('index.html', header_title="WellAtlas 2.7.5 — Classic Map (Improved) by Henry Suden")

@app.route('/api/sites')
def api_sites():
    q=request.args.get('q',''); job=request.args.get('job','')
    clauses=["deleted=0"]; params=[]
    if q: clauses.append("(name LIKE ? OR description LIKE ? OR id IN (SELECT site_id FROM notes WHERE body LIKE ?))"); params+=["%"+q+"%"]*3
    if job: clauses.append("job_category=?"); params.append(job)
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; cur=conn.cursor()
    cur.execute("SELECT * FROM sites WHERE "+ " AND ".join(clauses),params)
    rows=[dict(r) for r in cur.fetchall()]; conn.close(); return jsonify(rows)
