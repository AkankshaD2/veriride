import streamlit as st
import sqlite3
import cv2
import numpy as np
import easyocr
import re
import pandas as pd
from urllib.parse import quote
from rapidfuzz import fuzz

try:
    from streamlit_geolocation import streamlit_geolocation
    GEO_OK = True
except Exception:
    GEO_OK = False

DB_PATH = "veriride.db"

st.set_page_config(page_title="VeriRide", page_icon="🛺", layout="centered")


@st.cache_resource
def get_reader():
    return easyocr.Reader(['en'])


reader = get_reader()


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expected_plate TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER REFERENCES bookings(id),
            extracted_plate TEXT,
            confidence REAL,
            match_status TEXT CHECK (match_status IN ('match', 'mismatch', 'uncertain')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS flagged_plates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT UNIQUE NOT NULL,
            flag_count INTEGER DEFAULT 1,
            last_flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


init_db()


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


def book_ride(expected_plate):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO bookings (expected_plate) VALUES (?)",
                (expected_plate,))
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()
    return booking_id


def verify_ride(booking_id, image_bytes):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT expected_plate FROM bookings WHERE id = ?",
                (booking_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return {"error": "booking_id not found"}
    expected_plate = row[0]

    file_bytes = np.frombuffer(image_bytes, np.uint8)
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

    return {
        "expected_plate": expected_plate,
        "extracted_plate": extracted_plate,
        "confidence": confidence,
        "match_status": match_status
    }


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
    return [
        {"id": r[0], "expected_plate": r[1], "extracted_plate": r[2],
         "confidence": r[3], "match_status": r[4], "created_at": r[5]}
        for r in rows
    ]


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@600;700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');
:root {
    --bg: #10131C; --surface: #1A1F2E; --surface-border: #2E3448;
    --yellow: #F5C518; --green: #4CAF6D; --amber: #E8A33D; --red: #E5484D;
    --text: #F2EFE6; --text-muted: #8890A6;
}
[data-testid="stAppViewContainer"], .stApp { background-color: var(--bg) !important; }
[data-testid="stHeader"] { background-color: transparent !important; }
html, body, p, span, div, label { font-family: 'IBM Plex Sans', sans-serif !important; color: var(--text); }
.vr-top-strip { position: fixed; top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, var(--red), var(--amber), var(--green)); z-index: 999; }
@keyframes vr-fade-up { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
.vr-hero-wrap { position: relative; animation: vr-fade-up 0.7s ease-out; padding-top: 14px; }
.vr-hero-glow { position: absolute; top: -50px; left: -60px; width: 260px; height: 260px;
    background: radial-gradient(circle, rgba(245,197,24,0.22) 0%, rgba(245,197,24,0) 70%);
    pointer-events: none; z-index: 0; }
.vr-wordmark { position: relative; z-index: 1; font-family: 'Big Shoulders Display', sans-serif; font-weight: 800;
    font-size: clamp(2.2rem, 6vw, 3rem); letter-spacing: 0.02em; text-transform: uppercase; color: var(--text); line-height: 1; margin: 0; }
.vr-wordmark span { color: var(--yellow); }
.vr-tagline { position: relative; z-index: 1; font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem;
    letter-spacing: 0.15em; text-transform: uppercase; color: var(--text-muted); margin-top: 6px; }
.vr-signal-dots { display:flex; gap:7px; margin-top:12px; position: relative; z-index: 1; }
.vr-dot { width:9px; height:9px; border-radius:50%; }
@keyframes vr-pulse-r { 0%,100%{opacity:0.3;} 16%{opacity:1;} 33%{opacity:0.3;} }
@keyframes vr-pulse-a { 0%,100%{opacity:0.3;} 50%{opacity:1;} 66%{opacity:0.3;} }
@keyframes vr-pulse-g { 0%,100%{opacity:0.3;} 83%{opacity:1;} 100%{opacity:0.3;} }
.vr-dot.r { background: var(--red); animation: vr-pulse-r 3s ease-in-out infinite; }
.vr-dot.a { background: var(--amber); animation: vr-pulse-a 3s ease-in-out infinite; }
.vr-dot.g { background: var(--green); animation: vr-pulse-g 3s ease-in-out infinite; }
hr.vr-divider { border: none; height: 3px; width: 70px; margin: 22px 0 30px 0;
    background-image: repeating-linear-gradient(90deg, var(--yellow) 0 8px, transparent 8px 14px); }
.vr-step { font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; letter-spacing: 0.15em;
    color: var(--yellow); text-transform: uppercase; margin-bottom: 4px; }
.vr-section-title { font-family: 'Big Shoulders Display', sans-serif; font-weight: 700; font-size: 1.8rem;
    text-transform: uppercase; margin: 0 0 18px 0; color: var(--text); }
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--surface-border); }
.stTabs [data-baseweb="tab"] { font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem;
    letter-spacing: 0.05em; text-transform: uppercase; color: var(--text-muted); background-color: transparent; }
.stTabs [aria-selected="true"] { color: var(--yellow) !important; border-bottom: 3px solid var(--yellow) !important; }
.stTextInput input { background-color: var(--surface) !important; border: 1px solid var(--surface-border) !important;
    color: var(--text) !important; font-family: 'IBM Plex Mono', monospace !important; border-radius: 6px !important; }
.stButton > button { background-color: var(--yellow) !important; color: #10131C !important;
    font-family: 'IBM Plex Sans', sans-serif !important; font-weight: 600 !important; border: none !important;
    border-radius: 6px !important; padding: 0.5rem 1.4rem !important; }
[data-testid="stFileUploaderDropzone"] { background-color: var(--surface) !important;
    border: 1.5px dashed var(--surface-border) !important; border-radius: 8px !important; }
.plate-card { position: relative; background: var(--surface); border: 1.5px solid var(--surface-border);
    border-radius: 10px; padding: 18px 24px; margin: 10px 0 18px 0; }
.plate-corner { position: absolute; width: 6px; height: 6px; border-radius: 50%; background: var(--surface-border); }
.plate-corner.tl { top: 8px; left: 8px; } .plate-corner.tr { top: 8px; right: 8px; }
.plate-corner.bl { bottom: 8px; left: 8px; } .plate-corner.br { bottom: 8px; right: 8px; }
.plate-label { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; letter-spacing: 0.12em;
    color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px; }
.plate-value { font-family: 'IBM Plex Mono', monospace; font-size: 1.5rem; font-weight: 600;
    letter-spacing: 0.08em; color: var(--text); }
.status-banner { display: flex; align-items: center; gap: 16px; border-radius: 10px; padding: 20px 24px;
    margin-top: 12px; border: 1.5px solid; }
.status-icon { font-size: 1.8rem; }
.status-label { font-family: 'Big Shoulders Display', sans-serif; font-weight: 800; font-size: 1.3rem; }
.status-message { font-family: 'IBM Plex Sans', sans-serif; font-size: 0.9rem; color: var(--text-muted); margin-top: 2px; }
.status-match { background: rgba(76,175,109,0.1); border-color: var(--green); }
.status-match .status-label { color: var(--green); }
.status-mismatch { background: rgba(229,72,77,0.1); border-color: var(--red); }
.status-mismatch .status-label { color: var(--red); }
.status-uncertain { background: rgba(232,163,61,0.1); border-color: var(--amber); }
.status-uncertain .status-label { color: var(--amber); }
 
div[role="radiogroup"] { gap: 4px; border-bottom: 1px solid var(--surface-border); padding-bottom: 2px; }
div[role="radiogroup"] label { background: transparent !important; padding: 6px 12px !important; border-radius: 6px 6px 0 0; cursor: pointer; }
div[role="radiogroup"] label > div:first-child { display: none !important; }
div[role="radiogroup"] label p { font-family: 'IBM Plex Mono', monospace !important; font-size: 0.8rem !important;
    letter-spacing: 0.05em; text-transform: uppercase; color: var(--text-muted) !important; }
div[role="radiogroup"] label:has(input:checked) { border-bottom: 3px solid var(--yellow); }
div[role="radiogroup"] label:has(input:checked) p { color: var(--yellow) !important; }
</style>
<div class="vr-top-strip"></div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="vr-hero-wrap">
<div class="vr-hero-glow"></div>
<div class="vr-wordmark">🛺 VERI<span>RIDE</span></div>
<div class="vr-tagline">Verify before you ride</div>
<div class="vr-signal-dots"><div class="vr-dot r"></div><div class="vr-dot a"></div><div class="vr-dot g"></div></div>
</div>
<hr class="vr-divider">
""", unsafe_allow_html=True)


def plate_card(label, value):
    st.markdown(f"""
    <div class="plate-card">
        <div class="plate-corner tl"></div><div class="plate-corner tr"></div>
        <div class="plate-corner bl"></div><div class="plate-corner br"></div>
        <div class="plate-label">{label}</div>
        <div class="plate-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def status_banner(status, expected, extracted):
    extracted = extracted or "no plate"
    config = {
        "match": ("✅", "MATCH", f"{extracted} confirmed. Safe to board."),
        "mismatch": ("🚫", "MISMATCH", f"Expected {expected}, detected {extracted}. Do not board!"),
        "uncertain": ("⚠️", "UNCERTAIN", f"Low confidence read ({extracted}). Please re-scan.")
    }
    icon, label, msg = config[status]
    st.markdown(f"""
    <div class="status-banner status-{status}">
        <span class="status-icon">{icon}</span>
        <div><div class="status-label">{label}</div><div class="status-message">{msg}</div></div>
    </div>
    """, unsafe_allow_html=True)


def empty_state(message):
    st.markdown(f"""
    <div class="plate-card" style="text-align:center; border-style:dashed;">
        <div class="plate-label">Nothing here yet</div>
        <div style="font-family:'IBM Plex Sans',sans-serif; color:var(--text-muted); font-size:0.9rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)


def whatsapp_link(number, message):
    digits = re.sub(r'\D', '', number or "")
    if len(digits) == 10:      # Indian number without country code
        digits = "91" + digits
    return f"https://wa.me/{digits}?text={quote(message)}"


PAGES = ["01 · BOOK", "02 · VERIFY", "03 · HISTORY"]

if "page" not in st.session_state:
    st.session_state["page"] = PAGES[0]


def handle_book():
    plate = st.session_state.get("plate_input", "").strip()
    if not plate:
        st.session_state["book_error"] = True
        return
    st.session_state["book_error"] = False
    st.session_state["last_booking_id"] = book_ride(plate)
    st.session_state["last_result"] = None
    st.session_state["emergency_contact"] = st.session_state.get(
        "contact_input", "")
    st.session_state["page"] = PAGES[1]   # jump straight to Verify


page = st.radio("Navigation", PAGES, horizontal=True,
                key="page", label_visibility="collapsed")

if page == PAGES[0]:
    st.markdown('<div class="vr-step">Step 01</div><div class="vr-section-title">Book a ride</div>',
                unsafe_allow_html=True)
    st.text_input("Expected vehicle number (as shown in app)",
                  key="plate_input")
    st.text_input("Emergency contact WhatsApp number (optional)",
                  key="contact_input")
    st.button("Book Ride", on_click=handle_book)
    if st.session_state.get("book_error"):
        st.warning("Please enter a plate number.")

elif page == PAGES[1]:
    st.markdown('<div class="vr-step">Step 02</div><div class="vr-section-title">Verify before boarding</div>',
                unsafe_allow_html=True)

    booking_id = st.session_state.get("last_booking_id")

    if not booking_id:
        st.warning(
            "Pehle '01 · BOOK' tab mein ride book kar, phir yahan scan kar.")
    else:
        photo = st.camera_input("Point camera at the plate")

        if st.button("Verify"):
            if photo:
                st.session_state["last_result"] = verify_ride(
                    booking_id, photo.getvalue())
            else:
                st.warning("Pehle plate ki photo click kar.")

        result = st.session_state.get("last_result")
        if result:
            if "error" in result:
                st.error(f"Verification failed: {result['error']}")
            else:
                status = result["match_status"]
                status_banner(
                    status, result["expected_plate"], result["extracted_plate"])
                contact = st.session_state.get("emergency_contact", "")

                if status == "match":
                    msg = f"Boarded safely. Vehicle {result['extracted_plate']} matches my booking. - VeriRide"
                    if contact:
                        st.link_button(
                            "Send 'boarded safely' on WhatsApp", whatsapp_link(contact, msg))
                    else:
                        st.info(
                            "Emergency contact number Book tab mein daalega to yahan one-tap share dikhega.")

                elif status == "mismatch":
                    lat = lon = None
                    if GEO_OK:
                        st.caption(
                            "Optional: neeche wala button daba ke apni live location attach kar (permission Allow karna).")
                        loc = streamlit_geolocation() or {}
                        lat, lon = loc.get("latitude"), loc.get("longitude")
                    msg = (f"ALERT: Vehicle mismatch! Expected {result['expected_plate']}, "
                           f"but saw {result['extracted_plate'] or 'unreadable plate'}. "
                           f"I may be in an unsafe ride.")
                    if lat and lon:
                        msg += f" My live location: https://www.google.com/maps?q={lat},{lon}"
                        st.success("Location attached.")
                    msg += " - VeriRide"
                    if contact:
                        st.link_button("Send ALERT on WhatsApp",
                                       whatsapp_link(contact, msg))
                    else:
                        st.info(
                            "Emergency contact number Book tab mein daalega to yahan one-tap share dikhega.")

else:
    st.markdown('<div class="vr-step">Step 03</div><div class="vr-section-title">Verification history</div>',
                unsafe_allow_html=True)
    history = get_history()
    if history:
        df = pd.DataFrame(history)
        colors = {"match": "background-color: rgba(76,175,109,0.2); color:#4CAF6D;",
                  "mismatch": "background-color: rgba(229,72,77,0.2); color:#E5484D;",
                  "uncertain": "background-color: rgba(232,163,61,0.2); color:#E8A33D;"}
        styled = df.style.map(lambda v: colors.get(
            v, ""), subset=["match_status"])
        st.dataframe(styled, use_container_width=True)
    else:
        empty_state("Book a ride in the first tab to get started.")
