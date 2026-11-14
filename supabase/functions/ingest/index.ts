// Edge Function: ingest — [BUOY] ส่ง sensor readings ด้วย device secret (DB_DESIGN §3.1 E1)
//
// POST https://<project>.functions.supabase.co/functions/v1/ingest
//   header:  x-device-key: <secret>        (หรือใส body.secret — อย่างใดอย่างหนึ่ง)
//   body: { "device_id": "dev-315",
//           "measured_at": "2026-11-14T07:00:00Z",   // ข้ามได้ = now
//           "DO":5.2, "pH":7.1, "temperature":30.0,
//           "NH3":0.4, "NO2":0.2, "salinity":0.3 }
//
// ต้องตั้ง secret ใน project ก่อน (Dashboard → Edge Functions → Secrets):
//   SUPABASE_SERVICE_ROLE_KEY
//
// flow หลัง insert เป็นของ DB เอง: trigger ตั้ง late + enqueue_analysis('reading') → worker Render
import { createClient } from "jsr:@supabase/supabase-js@2";

const url = Deno.env.get("SUPABASE_URL");
// dashboard บังคับชื่อ secret ตัวพิมพ์เล็ก — รับได้ทั้งสองแบบ (ปกติตัวพิมพ์ใหญ่มี inject ให้อยู่แล้ว)
const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? Deno.env.get("supabase_service_role_key");
if (!url || !key) throw new Error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set");
const db = createClient(url, key, { auth: { persistSession: false } });

const PARAMS = ["DO", "pH", "NH3", "NO2", "temperature", "salinity"] as const;

function json(status: number, obj: unknown) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return json(405, { error: "method_not_allowed" });

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return json(400, { error: "bad_json" });
  }

  const deviceId = body.device_id;
  const secret = req.headers.get("x-device-key") ?? body.secret;
  if (typeof deviceId !== "string" || typeof secret !== "string" || !secret) {
    return json(400, { error: "device_id and secret required" });
  }

  // ตรวจ device + secret (อ่านด้วย service role — ไม่ต้องมี JWT)
  const { data: device, error: devErr } = await db
    .from("devices")
    .select("secret")
    .eq("device_id", deviceId)
    .maybeSingle();
  if (devErr) return json(500, { error: "device_lookup_failed" });
  if (!device?.secret || device.secret !== secret) return json(401, { error: "unauthorized" });

  // ค่าวัดต้องเป็น finite number — NaN/Inf ห้ามเข้า (§86, engine จะ raise)
  const row: Record<string, string | number> = { device_id: deviceId };
  let n = 0;
  for (const p of PARAMS) {
    const v = body[p];
    if (v === undefined || v === null) continue;
    if (typeof v !== "number" || !Number.isFinite(v)) {
      return json(422, { error: `value_${p}_not_finite` });
    }
    row[p] = v;
    n++;
  }
  if (n === 0) return json(422, { error: "no_measurements" });

  let ts: Date;
  if (typeof body.measured_at === "string") {
    ts = new Date(body.measured_at);
    if (isNaN(ts.getTime())) return json(422, { error: "bad_measured_at" });
  } else {
    ts = new Date();
  }
  // ponytail: ไม่บังคับ measured_at <= now — เพิ่ม reject future xa ถ้า clock buoy เพี้ยน
  row.measured_at = ts.toISOString();

  const { error } = await db.from("sensor_readings").insert(row);
  if (error?.code === "23505") return json(409, { error: "duplicate_measured_at" });
  if (error) return json(500, { error: error.message });
  return json(200, { ok: true });
});
