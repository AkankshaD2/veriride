from flask import Flask, request, jsonify
import sqlite3
import cv2
import numpy as np
import easyocr
import re
from rapidfuzz import fuzz

app = Flask(__name__)
reader = easyocr.Reader(['en'])


def get_connection():
    return sqlite3.connect("veriride.db")


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    with open("schema.sql", "r") as f:
        cur.executescript(f.read())
    conn.commit()
    conn.close()


def find_plate_candidates(img, top_n=3):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    edged = cv2.Canny(gray, 30, 200)
    contours, _ = cv2.findContours(
        edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:30]
    candidates = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        aspect = w / float(h) if h > 0 else 0
        area = w * h
        if 2.0 <= aspect <= 6.0 and area > 1000:
            candidates.append((x, y, w, h))
    return candidates[:top_n]


def clean_text(text):
    text = text.upper()
    text = re.sub(r'\bIND[I]?A?\b', '', text)
    return re.sub(r'[^A-Z0-9]', '', text)


def get_final_plate(img):
    candidates = find_plate_candidates(img)
    best_result, best_conf = None, 0
    for (x, y, w, h) in candidates:
        crop = img[y:y+h, x:x+w]
        results = reader.readtext(crop)
        combined = " ".join([r[1] for r in results])
        cleaned = clean_text(combined)
        conf = max([r[2] for r in results], default=0)
        if 7 <= len(cleaned) <= 12 and conf > best_conf:
            best_result, best_conf = cleaned, conf
    return best_result, best_conf


def get_match_status(expected, extracted, confidence):
    if not extracted:
        return "uncertain"
    similarity = fuzz.ratio(expected.upper(), extracted.upper())
    if similarity >= 85 and confidence >= 0.5:
        return "match"
    elif similarity < 50:
        return "mismatch"
    return "uncertain"


@app.route("/book", methods=["POST"])
def book_ride():
    data = request.get_json()
    expected_plate = data.get("expected_plate")
    if not expected_plate:
        return jsonify({"error": "expected_plate is required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO bookings (expected_plate) VALUES (?)",
                (expected_plate,))
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"booking_id": booking_id, "expected_plate": expected_plate}), 201


@app.route("/verify", methods=["POST"])
def verify_ride():
    booking_id = request.form.get("booking_id")
    if not booking_id:
        return jsonify({"error": "booking_id is required"}), 400
    if "image" not in request.files:
        return jsonify({"error": "image file is required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT expected_plate FROM bookings WHERE id = ?",
                (booking_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "booking_id not found"}), 404
    expected_plate = row[0]

    file = request.files["image"]
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    extracted_plate, confidence = get_final_plate(img)
    match_status = get_match_status(
        expected_plate, extracted_plate or "", confidence)

    cur.execute(
        "INSERT INTO verifications (booking_id, extracted_plate, confidence, match_status) VALUES (?, ?, ?, ?)",
        (booking_id, extracted_plate, confidence, match_status)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "booking_id": booking_id,
        "expected_plate": expected_plate,
        "extracted_plate": extracted_plate,
        "confidence": round(confidence, 2),
        "match_status": match_status
    }), 201


@app.route("/history", methods=["GET"])
def get_history():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT verifications.id, bookings.expected_plate, verifications.extracted_plate,
               verifications.confidence, verifications.match_status, verifications.created_at
        FROM verifications
        JOIN bookings ON verifications.booking_id = bookings.id
        ORDER BY verifications.created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "id": row[0],
            "expected_plate": row[1],
            "extracted_plate": row[2],
            "confidence": row[3],
            "match_status": row[4],
            "created_at": row[5]
        })

    return jsonify(history), 200


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
