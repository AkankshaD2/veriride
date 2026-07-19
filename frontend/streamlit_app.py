import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:5000"

st.set_page_config(page_title="VeriRide", page_icon="🛺", layout="centered")

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

.vr-wordmark { font-family: 'Big Shoulders Display', sans-serif; font-weight: 800; font-size: 3rem;
    letter-spacing: 0.02em; text-transform: uppercase; color: var(--text); line-height: 1; margin: 0; }
.vr-wordmark span { color: var(--yellow); }
.vr-tagline { font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; letter-spacing: 0.15em;
    text-transform: uppercase; color: var(--text-muted); margin-top: 6px; }
.vr-signal-dots { display:flex; gap:6px; margin-top:10px; }
.vr-dot { width:9px; height:9px; border-radius:50%; }
.vr-dot.r { background: var(--red); } .vr-dot.a { background: var(--amber); } .vr-dot.g { background: var(--green); }
hr.vr-divider { border: none; border-top: 3px solid var(--yellow); margin: 20px 0 30px 0; width: 64px; }

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
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(245,197,24,0.25); }

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
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="vr-wordmark">🛺 VERI<span>RIDE</span></div>
<div class="vr-tagline">Verify before you ride</div>
<div class="vr-signal-dots"><div class="vr-dot r"></div><div class="vr-dot a"></div><div class="vr-dot g"></div></div>
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


tab1, tab2, tab3 = st.tabs(["01 · BOOK", "02 · VERIFY", "03 · HISTORY"])

with tab1:
    st.markdown('<div class="vr-step">Step 01</div><div class="vr-section-title">Book a ride</div>',
                unsafe_allow_html=True)
    expected_plate = st.text_input("Expected vehicle number (as shown in app)")
    if st.button("Book Ride"):
        if expected_plate:
            response = requests.post(
                f"{API_URL}/book", json={"expected_plate": expected_plate})
            if response.status_code == 201:
                data = response.json()
                st.session_state["last_booking_id"] = data["booking_id"]
                plate_card("Booking Confirmed — ID", data["booking_id"])
            else:
                st.error("Something went wrong booking the ride.")
        else:
            st.warning("Please enter a plate number.")

with tab2:
    st.markdown('<div class="vr-step">Step 02</div><div class="vr-section-title">Verify before boarding</div>',
                unsafe_allow_html=True)
    default_id = str(st.session_state.get("last_booking_id", ""))
    booking_id = st.text_input("Booking ID", value=default_id)
    uploaded_photo = st.file_uploader("Upload a photo of the plate", type=[
                                      "jpg", "jpeg", "png", "webp"])

    if st.button("Verify"):
        if booking_id and uploaded_photo:
            files = {"image": uploaded_photo}
            data = {"booking_id": booking_id}
            response = requests.post(
                f"{API_URL}/verify", data=data, files=files)
            if response.status_code == 201:
                result = response.json()
                status_banner(
                    result["match_status"], result["expected_plate"], result["extracted_plate"])
            else:
                st.error(
                    f"Verification failed: {response.json().get('error', 'unknown error')}")
        else:
            st.warning("Enter a booking ID and upload a photo.")

with tab3:
    st.markdown('<div class="vr-step">Step 03</div><div class="vr-section-title">Verification history</div>',
                unsafe_allow_html=True)
    response = requests.get(f"{API_URL}/history")
    if response.status_code == 200:
        history = response.json()
        if history:
            df = pd.DataFrame(history)
            colors = {"match": "background-color: rgba(76,175,109,0.2); color:#4CAF6D;",
                      "mismatch": "background-color: rgba(229,72,77,0.2); color:#E5484D;",
                      "uncertain": "background-color: rgba(232,163,61,0.2); color:#E8A33D;"}
            styled = df.style.map(lambda v: colors.get(
                v, ""), subset=["match_status"])
            st.dataframe(styled, use_container_width=True)
        else:
            st.info("No verifications yet.")
