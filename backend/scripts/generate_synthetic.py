"""Deterministic SIMULATED astronaut data. NOT real astronaut measurements."""
import csv, math, pathlib, random
from datetime import datetime, timedelta

SEED = 20261114
START = datetime(2026, 9, 1)
DAYS = 45
MISSING_P = 0.03
OUT = pathlib.Path(__file__).resolve().parents[2] / "data" / "synthetic"

ASTRONAUTS = [
    {"astronaut_id": "AG-001", "name": "Demo Astronaut Alpha", "age": 38, "sex": "F",
     "height_cm": 168, "mass_kg": 62,
     "medical_history": "Fictional: no significant history; endurance athlete.",
     "p": dict(hr=62, hr_sd=3.0, sbp=112, dbp=70, spo2=98.0, rr=13, temp=33.8, eda=2.1,
               sleep=7.2, grip=32, rad=0.22, bmd=1.18, hb=13.4, wbc=6.1, rbc=4.5, plt=240)},
    {"astronaut_id": "AG-002", "name": "Demo Astronaut Bravo", "age": 45, "sex": "M",
     "height_cm": 182, "mass_kg": 86,
     "medical_history": "Fictional: mild seasonal allergies; prior knee surgery (2019).",
     "p": dict(hr=74, hr_sd=4.0, sbp=124, dbp=80, spo2=97.0, rr=15, temp=33.2, eda=3.0,
               sleep=6.4, grip=45, rad=0.25, bmd=1.12, hb=15.0, wbc=7.0, rbc=5.0, plt=265)},
    {"astronaut_id": "AG-003", "name": "Demo Astronaut Charlie", "age": 41, "sex": "M",
     "height_cm": 175, "mass_kg": 74,
     "medical_history": "Fictional: none significant.",
     "p": dict(hr=68, hr_sd=3.5, sbp=118, dbp=76, spo2=96.5, rr=14, temp=33.5, eda=2.5,
               sleep=7.0, grip=39, rad=0.23, bmd=1.15, hb=14.6, wbc=6.5, rbc=4.9, plt=250)},
]

ISOLATED = {("AG-002", 19, 12): {"hr": 35},
            ("AG-003", 32, 8): {"temp": 1.0},
            ("AG-003", 24, 4): {"spo2": -4.0}}

def shift(aid, d):
    if aid == "AG-001" and d >= 27:
        r = min(1.0, (d - 26) / 5)
        return {"hr": 14*r, "spo2": -1.8*r, "rr": 3*r, "sleep": -1.2*r, "eda": 0.8*r}
    return {}

rows = []
def add(aid, ts, var, val, unit, source, quality="good"):
    day = (ts.date() - START.date()).days + 1
    phase = "pre_mission" if day <= 0 else ("learning" if day <= 14 else "monitoring")
    rows.append([aid, ts.isoformat(timespec="minutes"), phase, day, var,
                 round(val, 3), unit, "SIMULATED: " + source, quality, "true"])

for a in ASTRONAUTS:
    aid, p = a["astronaut_id"], a["p"]
    rng = random.Random(f"{SEED}-{aid}")

    for d in range(-30, 0):
        ts = START + timedelta(days=d, hours=8)
        pre = [("heart_rate", p["hr"] - 2 + rng.gauss(0, p["hr_sd"]), "bpm"),
               ("bp_systolic", p["sbp"] + rng.gauss(0, 4), "mmHg"),
               ("bp_diastolic", p["dbp"] + rng.gauss(0, 3), "mmHg"),
               ("spo2", min(100, p["spo2"] + rng.gauss(0, 0.6)), "%"),
               ("resp_rate", p["rr"] + rng.gauss(0, 1), "breaths/min")]
        for var, v, u in pre:
            if rng.random() > 0.10:
                add(aid, ts, var, v, u, "pre-mission clinic record")
        tst = p["sleep"] + rng.gauss(0, 0.5)
        add(aid, ts - timedelta(hours=2), "sleep_total_h", tst, "h", "pre-mission sleep log")
        add(aid, ts - timedelta(hours=2), "sleep_time_in_bed_h",
            tst + 0.5 + abs(rng.gauss(0, 0.6)), "h", "pre-mission sleep log")

    for d, tag in ((-365, "previous"), (-20, "pre-mission")):
        add(aid, START + timedelta(days=d, hours=9), "bone_density",
            p["bmd"] + rng.gauss(0, 0.01), "g/cm2", f"DXA lumbar spine ({tag})", "good")
    for d in (-20, 13, 27):
        ts = START + timedelta(days=d, hours=9)
        add(aid, ts, "hemoglobin", p["hb"] + rng.gauss(0, 0.3), "g/dL", "lab panel")
        add(aid, ts, "wbc", p["wbc"] + rng.gauss(0, 0.5), "10^9/L", "lab panel")
        add(aid, ts, "rbc", p["rbc"] + rng.gauss(0, 0.15), "10^12/L", "lab panel")
        add(aid, ts, "platelets", p["plt"] + rng.gauss(0, 12), "10^9/L", "lab panel")

    for d in range(DAYS):
        sh = shift(aid, d)
        for hour in (0, 4, 8, 12, 16, 20):
            ts = START + timedelta(days=d, hours=hour)
            circ = -math.cos(2 * math.pi * (hour - 4) / 24)
            ex = hour == 16 and d % 2 == 0
            iso = ISOLATED.get((aid, d, hour), {})
            add(aid, ts, "activity_level", 2 if ex else (0 if hour in (0, 4) else 1),
                "0-2 scale", "activity annotation")
            vals = {
                "heart_rate": (p["hr"] + 4*circ + (25 if ex else 0) + sh.get("hr", 0)
                               + iso.get("hr", 0) + rng.gauss(0, p["hr_sd"]), "bpm"),
                "bp_systolic": (p["sbp"] + 2*circ + (15 if ex else 0) + rng.gauss(0, 4), "mmHg"),
                "bp_diastolic": (p["dbp"] + circ + (5 if ex else 0) + rng.gauss(0, 3), "mmHg"),
                "spo2": (min(100, p["spo2"] + sh.get("spo2", 0) + iso.get("spo2", 0)
                             + rng.gauss(0, 0.6)), "%"),
                "resp_rate": (p["rr"] + (6 if ex else 0) + sh.get("rr", 0) + rng.gauss(0, 1.0),
                              "breaths/min"),
                "skin_temp": (p["temp"] + 0.3*circ + iso.get("temp", 0) + rng.gauss(0, 0.25), "degC"),
                "eda": (p["eda"] + sh.get("eda", 0) + rng.gauss(0, 0.3), "uS"),
            }
            for var, (v, u) in vals.items():
                if var.startswith("bp_") and hour not in (8, 20):
                    continue
                if rng.random() < MISSING_P:
                    continue
                q = "fair" if (rng.random() < 0.05 or (ex and var == "spo2")) else "good"
                add(aid, ts, var, v, u, "wearable/cuff stream", q)

        tst = p["sleep"] + sh.get("sleep", 0) + rng.gauss(0, 0.5)
        tib = tst + 0.5 + abs(rng.gauss(0, 0.6))
        ts6 = START + timedelta(days=d, hours=6)
        add(aid, ts6, "sleep_total_h", tst, "h", "wearable accelerometer estimate", "fair")
        add(aid, ts6, "sleep_time_in_bed_h", tib, "h", "wearable accelerometer estimate", "fair")
        add(aid, START + timedelta(days=d, hours=8), "hydration_index",
            62 + rng.gauss(0, 4), "index 0-100 (estimate)", "bioimpedance estimate", "fair")
        boost = 1.5 if (aid == "AG-003" and 34 <= d <= 36) else 1.0
        absd = p["rad"] * boost + rng.gauss(0, 0.02)
        add(aid, START + timedelta(days=d, hours=23), "radiation_absorbed_dose",
            absd, "mGy/day", "simulated dosimeter")
        add(aid, START + timedelta(days=d, hours=23), "radiation_dose_equivalent",
            absd * (2.2 + rng.gauss(0, 0.1)), "mSv/day", "simulated dosimeter")
        if d % 7 == 0:
            add(aid, START + timedelta(days=d, hours=10), "grip_strength",
                p["grip"] - 0.03*d + rng.gauss(0, 1.2), "kg", "dynamometer test")

rows.sort(key=lambda r: (r[0], r[1], r[4]))
OUT.mkdir(parents=True, exist_ok=True)
with open(OUT / "measurements.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["astronaut_id", "timestamp", "phase", "mission_day", "variable",
                "value", "unit", "source", "quality", "is_simulated"])
    w.writerows(rows)

fields = ["astronaut_id", "name", "age", "sex", "height_cm", "mass_kg", "medical_history"]
with open(OUT / "astronauts.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields + ["mission_start", "mission_days", "is_simulated"])
    w.writeheader()
    for a in ASTRONAUTS:
        w.writerow({**{k: a[k] for k in fields},
                    "mission_start": START.date().isoformat(), "mission_days": DAYS,
                    "is_simulated": "true"})
print(f"measurements.csv: {len(rows)} rows -> {OUT}")