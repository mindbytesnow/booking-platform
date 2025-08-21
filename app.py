import os
from flask import Flask, render_template, request, redirect, flash, jsonify
import psycopg2
import psycopg2.extras
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me")
socketio = SocketIO(app, cors_allowed_origins="*")

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Add it in your Render service settings.")
    return psycopg2.connect(DATABASE_URL, sslmode=os.getenv("PGSSLMODE", "require"))

def ensure_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        date = data.get("date", "").strip()
        time = data.get("time", "").strip()

        if not all([name, email, date, time]):
            return jsonify({"error": "Please fill in all fields."}), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            "INSERT INTO bookings (name, email, date, time) VALUES (%s, %s, %s, %s) RETURNING *",
            (name, email, date, time)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        # Emit new booking event to dashboard
        socketio.emit("new_booking", dict(row))
        return jsonify({"success": True, "booking": dict(row)})

    return render_template("index.html")

@app.route("/bookings")
def list_bookings():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM bookings ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("bookings.html", rows=rows)

@app.route("/api/bookings")
def api_bookings():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM bookings ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(row) for row in rows])

if __name__ == "__main__":
    ensure_table()
    # Use socketio.run instead of app.run for SocketIO support
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
