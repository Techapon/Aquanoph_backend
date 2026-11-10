"""E2E: สร้าง user+pond จริง + ยิง sensor readings แล้วรอ worker บน Render ประมวล.

รันจากเครื่อง dev (เน็ตบล็อก PG ports ไม่กระทบ — ใช้ HTTPS 443 ผ่าน PostgREST/Auth API):
  python scripts/e2e_setup.py

ใช้ SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY จาก .env
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from typing import Any

# ---- load .env ----
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
RENDER = os.environ.get("RENDER_URL", "https://aquanoph-backend.onrender.com")
EMAIL = "e2e-pond@test.com"
DEV = "dev-e2e"


def rest(method: str, path: str, body: Any = None, apikey: str | None = None) -> tuple[int, Any]:
    """PostgREST / Auth admin call over HTTPS. คืน (status, parsed json)."""
    req = urllib.request.Request(
        URL + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "apikey": apikey or KEY,
            "Authorization": f"Bearer {apikey or KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, (json.loads(raw) if raw else {})
        except Exception:
            return e.code, {"raw": raw.decode(errors="replace")[:300]}


def main() -> int:
    # 1. user (admin API — ถ้ามีอยู่แล้วใช้ตัวเดิม)
    st, body = rest("POST", "/auth/v1/admin/users",
                    {"email": EMAIL, "password": "E2eTest1234!", "email_confirm": True})
    if st in (200, 201):
        uid = body.get("user", body).get("id")
        print(f"[1] created user {uid}")
    elif st == 422:  # email exists
        st2, lst = rest("GET", "/auth/v1/admin/users?per_page=100&page=1")
        users = lst.get("users", []) if isinstance(lst, dict) else []
        found = [u for u in users if u.get("email") == EMAIL]
        if not found:
            print(f"[1] email_exists but not listed (st2={st2})"); return 1
        uid = found[0]["id"]
        print(f"[1] reuse user {uid}")
    else:
        print(f"[1] user create failed {st}: {body}"); return 1

    # 2. profile → user_id (trigger สร้างให้แล้ว)
    st, prof = rest("GET", f"/rest/v1/profiles?user_id=eq.{uid}&select=user_id")
    if not isinstance(prof, list) or not prof:
        print(f"[2] profile missing: {st} {prof}"); return 1
    user_id = prof[0]["user_id"]
    print(f"[2] profile ok {user_id[:8]}...")

    # 3. device + pond
    st, _ = rest("POST", "/rest/v1/devices", {"device_id": DEV})
    if st not in (201, 200):
        st, _ = rest("GET", f"/rest/v1/devices?device_id=eq.{DEV}")
    st, ponds = rest("GET", f"/rest/v1/ponds?device_id=eq.{DEV}&select=id")
    if ponds:
        pond_id = ponds[0]["id"]
        print(f"[3] pond exists {pond_id}")
    else:
        st, created = rest("POST", "/rest/v1/ponds", {
            "user_id": user_id, "name": "e2e-pond", "area_m2": 10, "avg_depth_m": 1.5,
            "stocking_count": 100, "avg_weight_g": 400, "stocking_date": "2025-01-01",
            "device_id": DEV, "timezone": "Asia/Bangkok",
        })
        if st not in (200, 201):
            print(f"[3] pond create failed {st}: {created}"); return 1
        pond_id = created[0]["id"]
        print(f"[3] created pond {pond_id}")

    # 4. sensor readings — 2 แถว timestamp ต่างกัน (unique (device_id, measured_at))
    # measured_at ต้องมากกว่า cursor (last_reading_at) ถ้าเคยรันแล้ว — ใช้เวลาปัจจุบัน
    t0 = int(time.time())
    rows = []
    for i, (do, nh3) in enumerate([(2.1, 0.9), (2.0, 1.1)]):
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0 - (i + 1) * 60))
        rows.append({"device_id": DEV, "measured_at": ts, "DO": do, "pH": 6.8,
                     "NH3": nh3, "NO2": 0.2, "temperature": 31.5, "salinity": 0.1})
    st, body = rest("POST", "/rest/v1/sensor_readings", rows)
    print(f"[4] readings insert: {st} {body if st >= 400 else ''}")
    # jobs เก่ากว่า readings ไม่เกี่ยวกับรอบนี้
    t0_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0 - 120))

    # 5. wake worker ให้ poll เร็ว
    try:
        urllib.request.urlopen(urllib.request.Request(
            RENDER + "/wake", data=b"{}", method="POST",
            headers={"Content-Type": "application/json"}), timeout=60)
        print("[5] wake sent")
    except Exception as e:
        print(f"[5] wake fail: {e}")

    # 6. poll jobs ที่เกิดจาก readings รอบนี้เท่านั้น (timeout 180s)
    jobs: list[dict[str, Any]] = []
    for i in range(36):
        st, jobs = rest("GET",
            f"/rest/v1/analysis_jobs?pond_id=eq.{pond_id}&created_at=gte.{t0_iso}"
            f"&select=id,status,kinds,attempts,last_error,created_at&order=created_at.desc")
        jobs = jobs if isinstance(jobs, list) else []
        active = [j for j in jobs if j["status"] in ("queued", "running")]
        if jobs and not active:
            print(f"[6] all jobs settled: {json.dumps(jobs, indent=1)}")
            failed = [j for j in jobs if j["status"] == "failed"]
            if failed:
                print("FAILED:", failed[0].get("last_error"))
                return 2
            # เช็คว่า analysis_runs มี log (พิสูจน์ worker เขียนจริง)
            st, runs = rest("GET",
                f"/rest/v1/analysis_runs?pond_id=eq.{pond_id}&select=id,trigger_kind,duration_ms,error&order=created_at.desc&limit=5")
            print(f"[6] analysis_runs: {json.dumps(runs, indent=1) if isinstance(runs, list) else runs}")
            print("E2E PASS")
            return 0
        time.sleep(5)
    print(f"[6] TIMEOUT — jobs still: {jobs}")
    return 3


if __name__ == "__main__":
    sys.exit(main())
