import os
from flask import Flask, render_template, request, redirect, flash
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me")

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Add it in your Render service settings.")
    return psycopg2.connect(DATABASE_URL, sslmode=os.getenv("PGSSLMODE", "require"))

def ensure_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )
    conn.commit()
    cur.close()
    conn.close()

# Ensure table exists on startup (works on Render + local)
ensure_table()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        date = request.form.get("date", "").strip()
        time = request.form.get("time", "").strip()

        if not all([name, email, date, time]):
            flash("Please fill in all fields.")
            return render_template("index.html")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bookings (name, email, date, time) VALUES (%s, %s, %s, %s)",
            (name, email, date, time)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Booking saved. Thank you!")
        return redirect("/")

    return render_template("index.html")

@app.route("/bookings")
def list_bookings():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, name, email, date, time, created_at FROM bookings ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("bookings.html", rows=rows)

if __name__ == "__main__":
    # Local run
    port = int(os.environ.get("PORT", 5000))  # Render sets PORT automatically
    app.run(host="0.0.0.0", port=port)
