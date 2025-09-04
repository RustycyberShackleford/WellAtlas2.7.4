# WellAtlas 2.7.5 — Classic Map (Improved) by Henry Suden

- 5 Customers: Washington, Lincoln, Jefferson, Roosevelt, Kennedy
- 50 mining-themed demo sites (Job #25001–25050)
- Random Job Categories (Domestic, Drilling, Ag, Electrical)
- Notes and Photos per site (5 demo images)
- 2 demo sites pre-deleted, restore via Deleted Sites tab
- Leaflet map auto-zoom with pins in North State towns
- Header locked to version/author
- Conditional demo seeding only if DB empty

![Screenshot](static/screenshot.jpg)

### Deploy on Render
Start Command:
```
gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
```
