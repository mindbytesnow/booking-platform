import os
from flask import Flask, render_template, request, redirect, flash, jsonify
from flask_socketio import SocketIO, emit
import psycopg2
import psycopg2.extras
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me")
socketio = SocketIO(app, cors_allowed_origins="*")

DATABASE_URL = os.getenv("DATABASE_URL")
PGSSLMODE = os.getenv("PGSSLMODE", "require")

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set in environment variables.")
    return psycopg2.connect(DATABASE_URL, sslmode=PGSSLMODE)

# --- Multi-tenant helper ---
def get_client_id():
    host = request.host.split('.')[0]  # subdomain detection
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM clients WHERE subdomain=%s", (host,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return row[0]
    return None

# --- Ensure tables exist ---
def ensure_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            subdomain TEXT UNIQUE NOT NULL,
            logo TEXT,
            theme_colors TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id SERIAL PRIMARY KEY,
            client_id INT REFERENCES clients(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            email TEXT,
            role TEXT,
            schedule JSONB
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            client_id INT REFERENCES clients(id) ON DELETE CASCADE,
            staff_id INT REFERENCES staff(id),
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            service TEXT,
            date DATE NOT NULL,
            time TIME NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    client_id = get_client_id()
    if not client_id:
        return "Client not found. Contact platform admin.", 404

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        service = request.form.get("service", "").strip()
        date = request.form.get("date", "").strip()
        time = request.form.get("time", "").strip()

        if not all([name, email, date, time]):
            flash("Please fill in all fields.")
            return render_template("index.html")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bookings (client_id, name, email, service, date, time) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (client_id, name, email, service, date, time)
        )
        booking_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        # Notify dashboard via SocketIO
        socketio.emit("new_booking", {
            "id": booking_id,
            "name": name,
            "email": email,
            "service": service,
            "date": date,
            "time": time
        }, broadcast=True)

        flash("Booking saved. Thank you!")
        return redirect("/")

    return render_template("index.html", client_id=client_id)

@app.route("/dashboard")
def dashboard():
    client_id = get_client_id()
    if not client_id:
        return "Client not found.", 404
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM bookings WHERE client_id=%s ORDER BY created_at DESC", (client_id,))
    bookings = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("dashboard.html", bookings=bookings)

# Optional API endpoint
@app.route("/api/bookings")
def api_bookings():
    client_id = get_client_id()
    if not client_id:
        return jsonify([]), 404
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM bookings WHERE client_id=%s ORDER BY created_at DESC", (client_id,))
    bookings = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(b) for b in bookings])

if __name__ == "__main__":
    ensure_tables()
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
