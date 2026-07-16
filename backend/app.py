from flask import Flask, request, jsonify
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


@app.route("/book", methods=["POST"])
def book_ride():
    data = request.get_json()
    expected_plate = data.get("expected_plate")

    if not expected_plate:
        return jsonify({"error": "expected_plate is required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO bookings (expected_plate) VALUES (%s) RETURNING id",
        (expected_plate,)
    )
    booking_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"booking_id": booking_id, "expected_plate": expected_plate}), 201


if __name__ == "__main__":
    app.run(debug=True)
