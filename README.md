# Booking Platform (Flask + PostgreSQL)

A minimal booking system ready for free deployment on Render.

## Features
- Booking form: name, email, date, time
- Stores bookings in PostgreSQL
- `/bookings` page to view submissions
- Auto-creates the `bookings` table if it doesn't exist
- Production-ready via Gunicorn

## Local Run (optional)
```bash
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgres://user:pass@host:5432/db   # PowerShell: setx DATABASE_URL "..."
python app.py
```

## Deploy to Render (Free)
1. Push this folder to a new GitHub repo.
2. In Render, click **New → Web Service** and select your repo.
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `gunicorn app:app`
5. After the service is created, add **Environment Variables**:
   - `DATABASE_URL` → from your Render PostgreSQL (create a free DB in **Databases**)
   - `SECRET_KEY` → any random string
   - `PGSSLMODE` → `require`
6. Visit your app URL. The first request will auto-create the `bookings` table.

## SQL (if you prefer manual table creation)
```sql
CREATE TABLE IF NOT EXISTS bookings (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  date DATE NOT NULL,
  time TIME NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Notes
- Free tiers may sleep when inactive. First request may be slower.
- Add a domain & SSL in Render when you're ready.
