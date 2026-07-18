from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)


def get_connection():
    conn = sqlite3.connect("veriride.db")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    with open("schema.sql", "r") as f:
        cur.executescript(f.read())
    conn.commit()
    conn.close()


@app.route("/book", methods=["POST"])
def book_ride():
    data = request.get_json()
    expected_plate = data.get("expected_plate")

    if not expected_plate:
        return jsonify({"error": "expected_plate is required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO bookings (expected_plate) VALUES (?)",
        (expected_plate,)
    )
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"booking_id": booking_id, "expected_plate": expected_plate}), 201


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
