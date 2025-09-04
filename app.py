\
import os, random
from datetime import datetime
from math import radians, cos, sin, sqrt, atan2

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy

ensure_schema()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///wellatlas.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------------- Models ----------------
class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    sites = db.relationship("Site", backref="customer", cascade="all, delete-orphan")

class Site(db.Model):
    __tablename__ = "sites"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    jobs = db.relationship("Job", backref="site", cascade="all, delete-orphan")

class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Domestic, Ag, Drilling, Electrical
    status = db.Column(db.String(50), default="Open")
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False)
    deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

# ---------- one-time init & seed ----------
_inited = False
def init_and_seed_once():
    global _inited
    if _inited:
        return
    db.create_all()
    if not Customer.query.first():
        presidents = ["Washington", "Jefferson", "Lincoln", "Roosevelt", "Kennedy"]
        towns = [
            ("Corning", 39.9271, -122.1792),
            ("Orland", 39.7471, -122.1969),
            ("Chico", 39.7285, -121.8375),
            ("Cottonwood", 40.3863, -122.2803),
            ("Durham", 39.6468, -121.8005),
        ]
        cats = ["Domestic", "Ag", "Drilling", "Electrical"]
        rnd = random.Random(42)
        for p in presidents:
            cust = Customer(name=f"{p} Water Co"); db.session.add(cust); db.session.flush()
            for si in range(10):
                town = towns[si % len(towns)]
                lat = town[1] + (rnd.random()-0.5)*0.08
                lng = town[2] + (rnd.random()-0.5)*0.08
                site = Site(name=f"{town[0]} Site {si+1}", latitude=lat, longitude=lng, customer_id=cust.id)
                db.session.add(site); db.session.flush()
                for c in cats:
                    job = Job(job_number=f"{town[0][:3].upper()}-{si+1}-{c[:3].upper()}",
                              category=c, status="Open", site_id=site.id)
                    db.session.add(job)
        db.session.commit()
    _inited = True

@app.before_request
def _ensure_db():
    init_and_seed_once()

# ---------- helpers ----------
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

def soft_delete(obj):
    obj.deleted = True
    obj.deleted_at = datetime.utcnow()

def restore(obj):
    obj.deleted = False
    obj.deleted_at = None

# ---------- routes: map ----------
@app.get("/")
def index():
    key = os.getenv("MAPTILER_KEY", "")
    add_site_customer_id = request.args.get("add_site", type=int)
    # Build site payload incl categories present at each site
    sites = Site.query.filter_by(deleted=False).all()
    data = []
    for s in sites:
        cats = {j.category for j in s.jobs if not j.deleted}
        data.append({"id": s.id, "name": s.name, "lat": s.latitude, "lng": s.longitude,
                     "customer": s.customer.name, "categories": sorted(list(cats))})
    return render_template("index.html", MAPTILER_KEY=key, sites=data, add_site_customer_id=add_site_customer_id)

@app.post("/sites/create_at")
def create_site_at():
    """Create a site at clicked coordinates from the map 'add site' flow."""
    data = request.get_json(force=True)
    cid = int(data.get("customer_id"))
    name = (data.get("name") or "New Site").strip()
    lat = float(data.get("lat"))
    lng = float(data.get("lng"))
    c = db.session.get(Customer, cid)
    if not c or c.deleted:
        return jsonify({"ok": False, "error": "Customer not found"}), 400
    s = Site(name=name, latitude=lat, longitude=lng, customer_id=cid)
    db.session.add(s); db.session.commit()
    return jsonify({"ok": True, "site_id": s.id, "customer_id": cid})

@app.post("/nearby")
def nearby():
    data = request.get_json(silent=True) or {}
    lat = float(data.get("lat", 0))
    lng = float(data.get("lng", 0))
    radius_km = float(data.get("radius_km", 40.0))
    out = []
    for s in Site.query.filter_by(deleted=False).all():
        d = haversine_km(lat, lng, s.latitude, s.longitude)
        if d <= radius_km:
            out.append({"id": s.id, "name": s.name, "lat": s.latitude, "lng": s.longitude,
                        "customer": s.customer.name, "km": round(d, 2)})
    out.sort(key=lambda x: x["km"])
    return jsonify(out)

# ---------- routes: customers ----------
@app.get("/customers")
def customers():
    cs = Customer.query.filter_by(deleted=False).order_by(Customer.name.asc()).all()
    return render_template("customers.html", customers=cs)

@app.post("/customers/new")
def new_customer():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Customer name required", "error"); return redirect(url_for("customers"))
    if Customer.query.filter_by(name=name).first():
        flash("Customer already exists", "error"); return redirect(url_for("customers"))
    db.session.add(Customer(name=name)); db.session.commit()
    flash("Customer added", "ok"); return redirect(url_for("customers"))

@app.post("/customers/<int:cid>/edit")
def edit_customer(cid):
    c = db.session.get(Customer, cid)
    if not c or c.deleted:
        flash("Customer not found", "error"); return redirect(url_for("customers"))
    new_name = request.form.get("name","").strip()
    if not new_name:
        flash("Name cannot be empty","error"); return redirect(url_for("customers"))
    exists = Customer.query.filter(Customer.id != cid, Customer.name == new_name).first()
    if exists:
        flash("Another customer already has that name","error"); return redirect(url_for("customers"))
    c.name = new_name
    db.session.commit()
    flash("Customer updated","ok")
    return redirect(url_for("customers"))

@app.get("/customers/<int:cid>")
def customer_detail(cid):
    c = db.session.get(Customer, cid)
    if not c or c.deleted:
        flash("Customer not found", "error"); return redirect(url_for("customers"))
    sites = Site.query.filter_by(customer_id=cid, deleted=False).order_by(Site.name.asc()).all()
    return render_template("customer_detail.html", customer=c, sites=sites)

@app.post("/customers/<int:cid>/delete")
def delete_customer(cid):
    c = db.session.get(Customer, cid)
    if not c:
        flash("Customer not found", "error")
    else:
        soft_delete(c)
        for s in c.sites:
            soft_delete(s)
            for j in s.jobs: soft_delete(j)
        db.session.commit()
        flash("Customer deleted", "ok")
    return redirect(url_for("customers"))

# ---------- routes: sites ----------
@app.post("/customers/<int:cid>/sites/new")
def new_site(cid):
    # Keep classic form path (not used by map-flow, but still available)
    c = db.session.get(Customer, cid)
    if not c or c.deleted:
        flash("Customer not found", "error"); return redirect(url_for("customers"))
    name = request.form.get("name","").strip()
    lat = request.form.get("lat","").strip()
    lng = request.form.get("lng","").strip()
    try:
        lat = float(lat); lng = float(lng)
    except:
        flash("Latitude/Longitude required", "error"); return redirect(url_for("customer_detail", cid=cid))
    s = Site(name=name or "New Site", latitude=lat, longitude=lng, customer_id=cid)
    db.session.add(s); db.session.commit()
    flash("Site added","ok"); return redirect(url_for("customer_detail", cid=cid))

@app.get("/sites/<int:sid>")
def site_detail(sid):
    s = db.session.get(Site, sid)
    if not s or s.deleted:
        flash("Site not found", "error"); return redirect(url_for("customers"))
    jobs = Job.query.filter_by(site_id=sid, deleted=False).order_by(Job.job_number.asc()).all()
    return render_template("site.html", site=s, jobs=jobs)

@app.post("/sites/<int:sid>/delete")
def delete_site(sid):
    s = db.session.get(Site, sid)
    if not s:
        flash("Site not found", "error")
        return redirect(url_for("customers"))
    soft_delete(s)
    for j in s.jobs: soft_delete(j)
    db.session.commit()
    flash("Site deleted", "ok")
    return redirect(url_for("customer_detail", cid=s.customer_id))

# ---------- routes: jobs ----------
@app.post("/sites/<int:sid>/jobs/new")
def new_job(sid):
    s = db.session.get(Site, sid)
    if not s or s.deleted:
        flash("Site not found", "error"); return redirect(url_for("customers"))
    job_number = request.form.get("job_number","").strip() or f"JOB-{sid}-{random.randint(100,999)}"
    category = request.form.get("category","Domestic")
    status = request.form.get("status","Open")
    j = Job(job_number=job_number, category=category, status=status, site_id=sid)
    db.session.add(j); db.session.commit()
    flash("Job added","ok"); return redirect(url_for("site_detail", sid=sid))

@app.get("/jobs/<int:jid>")
def job_detail(jid):
    j = db.session.get(Job, jid)
    if not j or j.deleted:
        flash("Job not found", "error"); return redirect(url_for("customers"))
    return render_template("job.html", job=j)

@app.post("/jobs/<int:jid>/delete")
def delete_job(jid):
    j = db.session.get(Job, jid)
    if not j:
        flash("Job not found", "error"); return redirect(url_for("customers"))
    soft_delete(j); db.session.commit()
    flash("Job deleted","ok"); return redirect(url_for("site_detail", sid=j.site_id))

# ---------- Deleted tab (soft-deleted) ----------
@app.get("/deleted")
def deleted_items():
    customers = Customer.query.filter_by(deleted=True).all()
    sites = Site.query.filter_by(deleted=True).all()
    jobs = Job.query.filter_by(deleted=True).all()
    return render_template("deleted.html", customers=customers, sites=sites, jobs=jobs)

@app.post("/deleted/<string:kind>/<int:item_id>/restore")
def restore_item(kind, item_id):
    model = {"customer": Customer, "site": Site, "job": Job}.get(kind)
    if not model: flash("Unknown type","error"); return redirect(url_for("deleted_items"))
    obj = db.session.get(model, item_id)
    if not obj: flash("Not found","error"); return redirect(url_for("deleted_items"))
    restore(obj)
    db.session.commit()
    flash(f"{kind.title()} restored","ok")
    return redirect(url_for("deleted_items"))

@app.post("/deleted/<string:kind>/<int:item_id>/purge")
def purge_item(kind, item_id):
    model = {"customer": Customer, "site": Site, "job": Job}.get(kind)
    if not model: flash("Unknown type","error"); return redirect(url_for("deleted_items"))
    obj = db.session.get(model, item_id)
    if not obj: flash("Not found","error"); return redirect(url_for("deleted_items"))
    db.session.delete(obj)
    db.session.commit()
    flash(f"{kind.title()} permanently deleted","ok")
    return redirect(url_for("deleted_items"))

# ---------- health ----------
@app.get("/healthz")
def healthz():
    return {"ok": True}, 200

if __name__ == "__main__":
    init_and_seed_once()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","5000")), debug=True)
