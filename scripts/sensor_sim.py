"""Simulator: สอด sensor readings ค่าสุ่มง่าย ๆ เข้า DB ทุก 5 นาที (device dev-315).

รันจากเครื่อง dev ทิ้งไว้ (HTTPS 443 อย่างเดียว — ไม่แตะ PG ports):
  python scripts/sensor_sim.py            # รัน loop ตลอด (Ctrl+C หยุด)
  python scripts/sensor_sim.py --once     # ยิงครั้งเดียวจบ

ใช้ SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY จาก .env
trigger ใน DB จะ enqueue_analysis เอง -> worker บน Render ประมวลต่อ
"""
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# ---- load .env (เหมือน scripts/e2e_setup.py) ----
with open(os.path.join(os.path.dirname(__file__), "..", ".env"), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if v and not v.startswith("["):
                os.environ.setdefault(k.strip(), v)

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
DEVICE = "dev-315"
EVERY_SEC = 300  # 5 นาที

# ค่าสุ่มง่าย ๆ — ช่วงกว้างพอให้เจอ warning/critical บ้าง
RANGES = {
    "DO":          (2.0, 8.5),   # mg/L
    "pH":          (6.2, 8.8),
    "temperature": (26.0, 34.0), # °C
    "NH3":         (0.05, 1.6),  # mg/L
    "NO2":         (0.05, 0.9),
    "salinity":    (0.1, 0.6),
}


def post_reading() -> tuple[int, dict]:
    row = {"device_id": DEVICE, "measured_at": datetime.now(timezone.utc).isoformat()}
    row.update({k: round(random.uniform(*v), 2) for k, v in RANGES.items()})
    req = urllib.request.Request(
        URL + "/rest/v1/sensor_readings",
        data=json.dumps(row).encode(),
        headers={
            "apikey": KEY,
            "Authorization": f"Bearer {KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",  # DB ตอบ 201 เปล่า ๆ ก็พอ
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, row
    except urllib.error.HTTPError as e:
        return e.code, {"row": row, "body": e.read().decode(errors="replace")[:300]}


def main() -> int:
    once = "--once" in sys.argv
    n = 0
    while True:
        st, info = post_reading()
        n += 1
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        if st == 201:
            print(f"[{ts}] #{n} OK  DO={info['DO']} pH={info['pH']} tem={info['temperature']} "
                  f"NH3={info['NH3']} NO2={info['NO2']} sal={info['salinity']}", flush=True)
        else:
            print(f"[{ts}] #{n} HTTP {st}: {info}", flush=True)
        if once:
            return 0 if st == 201 else 1
        time.sleep(EVERY_SEC)


if __name__ == "__main__":
    sys.exit(main())
