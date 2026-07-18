![VeriRide](assets/banner.png)

# VeriRide

**Verify before you ride.**

[![Status](https://img.shields.io/badge/status-building-orange)]()
[![Python](https://img.shields.io/badge/python-3.10+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

You book a ride. The app shows a vehicle number. The auto that pulls up has a
*different* one. You get in anyway — because what else are you supposed to do,
stand there comparing digits at 11pm?

That gap is the problem. **VeriRide closes it** — point your camera at the actual
plate, it reads the number, checks it against what you booked, tells you in
under a second if something's off.

## ⚙️ How it works

![Architecture](assets/architecture.png)

```
📸 photo of plate → 🔍 contour-based plate detection → 🔤 EasyOCR reads text
   → 🧮 RapidFuzz matches vs booking → ✅ match / ⚠️ uncertain / 🚫 mismatch
```

## 🧱 Built with

| Layer | Tool |
|---|---|
| Plate detection | OpenCV contour detection (YOLOv8 planned as v2 upgrade) |
| Text extraction | EasyOCR |
| Fuzzy matching | RapidFuzz |
| Backend | Flask + SQLite (local) |
| Frontend | Streamlit *(next up)* |

## 📊 Phase 1 results — OCR baseline

Tested on 12 real auto-rickshaw plate photos (varied angles/lighting):

- **~42% usable, correct plate reads** on the first pass
- **33% plate-detection failure rate** — contour-based detection struggles on
  cluttered backgrounds or low-contrast plates
- Remaining failures are character-level OCR confusion (O↔0, 1↔I↔L) — a known,
  documented challenge in ANPR systems, not unique to this pipeline

This is an honest baseline, not a polished number — it's exactly why the fuzzy
matching layer (RapidFuzz) exists downstream: OCR confidence alone isn't a
reliable correctness signal, so the system treats low-confidence reads as
"uncertain" rather than a false match or false mismatch.

## ✅ Phase 2 progress — backend is live

`/book` and `/verify` are working end-to-end: book a ride with an expected
plate, upload a photo, and the API runs detection → OCR → fuzzy matching →
returns a verdict, logged straight to the database. First real test correctly
flagged a genuine mismatch between the expected and photographed plate —
exactly the failure case this project exists to catch.

## 📍 Where this stands

- [x] Architecture + planning
- [x] OCR pipeline — baseline accuracy benchmarked (42% on real photos)
- [x] Flask API + database (`/book`, `/verify`)
- [x] Fuzzy match engine (integrated into `/verify`)
- [ ] 🔧 `/history` route + Streamlit frontend *(currently here)*
- [ ] Deployed demo + video walkthrough

## 🔮 Planned (V2)

- [ ] **Driver identity verification** — match the driver's actual photo against
      their registered profile photo at booking time, flagging a mismatch if a
      different person shows up. Same "expected vs actual" pattern as plate
      verification, applied to identity instead of just the vehicle.
- [ ] Swap contour-based detection for a fine-tuned YOLOv8 model to improve on
      the 33% detection-failure rate documented above.

## 🎯 Why build this

Vehicle-number mismatches in ride-hailing bookings are a real, reported safety
gap — small enough to ignore, big enough to matter at 11pm alone. This isn't a
toy dataset project; it's an end-to-end CV pipeline (detection → OCR → fuzzy
matching) aimed at an actual problem, with honestly benchmarked results.

> **Note:** standalone prototype — the "booked plate" is entered manually here
> to simulate what a ride app would provide via its own booking API.

## 🚀 Getting started

```bash
git clone https://github.com/AkankshaD2/veriride.git
cd veriride/backend
pip install -r requirements.txt
python app.py
```

`POST /book` with `{"expected_plate": "..."}` to create a booking, then
`POST /verify` (form-data: `booking_id`, `image`) to check a plate against it.

---

⭐ if this is useful, and PRs welcome once the MVP lands.
