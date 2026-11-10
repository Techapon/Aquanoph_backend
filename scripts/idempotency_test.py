"""ทดสอบ idempotency ของ POST /recommendations/{id}/apply (มติข้อ 28).

ยิง apply id เดิม 2 ครั้ง → แถว rec ต้อง 1 เดิม, activity ห้ามเพิ่มซ้ำ
(ถ้ายิงครั้งแรกไม่ผ่านจะรายงาน rejected reason ให้ดู)

รัน: python scripts/idempotency_test.py
ใช้ SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_JWT_SECRET จาก .env
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from typing import Any

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
RENDER = "https://aquanoph-backend.onrender.com"
EMAIL = "e2e-pond@test.com"
PASSWORD = "E2eTest1234!"
POND = "0c3f2ee1-10d9-4bac-8780-c5395a9b4e7b"  # e2e pond จาก scripts/e2e_setup.py
REC_ID = "rec:e2e:applytest"


def rest(method: str, path: str, body: Any = None, base: str = URL, headers: dict | None = None) -> tuple[int, Any]:
    h = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=h,
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
    # 1. login → JWT ของ e2e user
    st, tok = rest("POST", "/auth/v1/token?grant_type=password",
                   {"email": EMAIL, "password": PASSWORD})
    if st != 200 or "access_token" not in tok:
        print(f"[1] login failed {st}: {str(tok)[:200]}"); return 1
    jwt = tok["access_token"]
    print("[1] login ok")

    # 2. fixture rec: reset เสมอ (rerun ได้) — ลบ activity rec เก่าก่อน
    now = int(time.time())
    rest("DELETE", f"/rest/v1/activities?source_rec_id=eq.{REC_ID}")
    rest("DELETE", f"/rest/v1/recommendations?id=eq.{REC_ID}")
    st, _ = rest("POST", "/rest/v1/recommendations", {
        "id": REC_ID, "pond_id": POND, "entry_id": "AERATE", "dedupe_key": "E2E:APPLY",
        "urgency": "urgent", "apply_mode": "fixed",
        "valid_from": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3600)),
        "valid_until": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + 5 * 3600)),
        "title": "t", "reason": "r", "based_on": "b", "guidance": ["g"],
        "proposed_activities": [{
            "type": "aeration",
            "startTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + 3600)),
            "endTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + 3 * 3600)),
        }],
        "status": "pending",
    })
    if st not in (200, 201):
        print(f"[2] rec create failed {st}"); return 1
    print("[2] rec fixture ready")

    def counts() -> tuple[int, int]:
        _, recs = rest("GET", f"/rest/v1/recommendations?id=eq.{REC_ID}&select=id")
        _, acts = rest("GET", f"/rest/v1/activities?source_rec_id=eq.{REC_ID}&select=id")
        return (len(recs) if isinstance(recs, list) else -1,
                len(acts) if isinstance(acts, list) else -1)

    # 3. apply ครั้งที่ 1
    st1, r1 = rest("POST", f"/recommendations/{REC_ID}/apply", {}, base=RENDER,
                   headers={"Authorization": f"Bearer {jwt}"})
    n_rec, n_act = counts()
    print(f"[3] apply#1 -> {st1} {json.dumps(r1)[:200]}")
    print(f"    recs={n_rec} activities={n_act}")
    if st1 != 200 or r1.get("status") != "applied":
        print("FAIL: first apply ไม่สำเร็จ"); return 2

    # 4. apply ครั้งที่ 2 — ห้ามเพิ่มแถว (มติข้อ 28)
    st2, r2 = rest("POST", f"/recommendations/{REC_ID}/apply", {}, base=RENDER,
                   headers={"Authorization": f"Bearer {jwt}"})
    n_rec2, n_act2 = counts()
    print(f"[4] apply#2 -> {st2} {json.dumps(r2)[:200]}")
    print(f"    recs={n_rec2} activities={n_act2}")

    ok = True
    if st2 != 200:
        print("FAIL: apply#2 ต้อง 200"); ok = False
    if n_rec2 != 1:
        print(f"FAIL: rec ต้อง 1 เดิม (ได้ {n_rec2})"); ok = False
    if n_act2 != n_act:
        print(f"FAIL: activities ห้ามเพิ่ม ({n_act} -> {n_act2})"); ok = False
    if r2.get("status") not in ("applied", "rejected"):
        print(f"FAIL: apply#2 status แปลก: {r2.get('status')}"); ok = False

    print("IDEMPOTENCY PASS" if ok else "IDEMPOTENCY FAIL")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
