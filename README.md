# WellAtlas 2.6

**What changed vs 2.5**
- Map-first **Add Site** flow (2.0-style): from Customers, click **Add Site (map)** → you land on the map and click to place the new site.
- Restored the simplified **2.0 look** (lighter header, compact list UI).
- Kept all 2.5 features: category filter on map, Near Me, CRUD, Deleted tab, auto-seed when DB empty.

## Deploy on Render
- Build: `pip install -r requirements.txt`
- Start: (Procfile) `web: gunicorn -w 2 -k gthread -t 120 -b 0.0.0.0:$PORT app:app`
- Python pinned in `runtime.txt`

Optional env vars:
- `MAPTILER_KEY=<your key>` (satellite tiles). If not set, fallback uses OpenStreetMap.
- `FLASK_SECRET_KEY=<anything>`

## Add Site via Map
- Go to **Customers** → pick a customer → hit **Add Site via Map** (or use the button on customer detail).
- On the map page, a banner appears (Add Site Mode). Click the map to place the site. You can type a site name first.
- After creating, you’re redirected back to the customer page.

SQLite database file: `wellatlas.db`. The app seeds demo data only if the DB is empty.
