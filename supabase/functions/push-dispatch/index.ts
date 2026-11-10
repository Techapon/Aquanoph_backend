// push-dispatch (E2/Edge Function, Deno) — ส่ง push notification ตาม §7 ข้อ 8
//
// ทริกเกอร์ 2 ทาง:
//   W2: DB Webhook POST จาก notifications insert (push_eligible) → payload มี record
//   retry: cron นาทีละครั้ง (pg_cron log หรือยิงซ้ำ) → payload ว่าง → คิว from pushed_at is null
//
// Secret ที่ต้องตั้ง (Dashboard → Edge Functions → push-dispatch → Secrets):
//   FIREBASE_SERVICE_ACCOUNT = JSON string ของ Firebase service account
//     (Firebase Console → Project settings → Service accounts → Generate new private key)
//
// behavior:
//   - ไม่มี push_tokens ของ user → mark pushed_at (ไม่มีอะไรส่ง ไม่ retry ฟรี)
//   - token ตาย (UNREGISTERED/INVALID_ARGUMENT) → ลบ token ทิ้ง
//   - error ชั่วคราว (5xx/network) → ปล่อย pushed_at null ให้ retry
import { createClient } from "npm:@supabase/supabase-js@2";
import { importPKCS8, SignJWT } from "npm:jose@5";

const FCM_SCOPES = "https://www.googleapis.com/auth/firebase.messaging";

type NotificationRow = {
  id: number;
  pond_id: string;
  user_id: string;
  kind: string;
  target_id: string;
  reason_key: string | null;
  text: string | null;
  facts: Record<string, unknown>;
  push_eligible: boolean;
  pushed_at: string | null;
};

function env(name: string): string {
  const v = Deno.env.get(name);
  if (!v) throw new Error(`missing secret: ${name}`);
  return v;
}

// ---- FCM HTTP v1: access token จาก service account (RS256 JWT) ----
async function fcmAccessToken(sa: {
  project_id: string;
  client_email: string;
  private_key: string;
}): Promise<string> {
  const key = await importPKCS8(sa.private_key, "RS256");
  const now = Math.floor(Date.now() / 1000);
  const jwt = await new SignJWT({ scope: FCM_SCOPES })
    .setProtectedHeader({ alg: "RS256", typ: "JWT" })
    .setIssuer(sa.client_email)
    .setAudience("https://oauth2.googleapis.com/token")
    .setIssuedAt(now)
    .setExpirationTime(now + 3600)
    .sign(key);
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${encodeURIComponent(jwt)}`,
  });
  if (!res.ok) throw new Error(`token exchange failed: ${res.status} ${await res.text()}`);
  const data = await res.json();
  return data.access_token as string;
}

type SendResult = "ok" | "dead" | "transient";

async function sendOne(
  accessToken: string,
  projectId: string,
  token: string,
  title: string,
  body: string,
  data: Record<string, string>,
): Promise<SendResult> {
  const res = await fetch(
    `https://fcm.googleapis.com/v1/projects/${projectId}/messages:send`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: {
          token,
          notification: { title, body },
          data,
        },
      }),
    },
  );
  if (res.ok) return "ok";
  const errText = await res.text();
  // token ตายถาวร → ลบ; ชั่วคราว → retry
  if (
    errText.includes("UNREGISTERED") ||
    errText.includes("INVALID_ARGUMENT") ||
    errText.includes("NOT_FOUND")
  ) {
    console.warn(`dead token ${token.slice(0, 16)}…: ${errText.slice(0, 200)}`);
    return "dead";
  }
  console.warn(`transient FCM error ${res.status}: ${errText.slice(0, 200)}`);
  return "transient";
}

Deno.serve(async (req) => {
  const supabase = createClient(
    env("SUPABASE_URL"),
    env("SUPABASE_SERVICE_ROLE_KEY"),
  );
  const sa = JSON.parse(env("FIREBASE_SERVICE_ACCOUNT")) as {
    project_id: string;
    client_email: string;
    private_key: string;
  };

  // payload จาก W2: { record: {...notification} } — retry: {} หรือไม่มี record
  let payload: { record?: NotificationRow } = {};
  try {
    payload = await req.json();
  } catch {
    /* retry caller อาจไม่ส่ง body */
  }

  let query = supabase
    .from("notifications")
    .select("*")
    .eq("push_eligible", true)
    .is("pushed_at", null)
    .limit(50);
  if (payload.record?.id) {
    query = query.eq("id", payload.record.id);
  }
  const { data: rows, error } = await query;
  if (error) {
    console.error("select notifications:", error);
    return new Response(JSON.stringify({ error: error.message }), { status: 500 });
  }
  if (!rows || rows.length === 0) {
    return new Response(JSON.stringify({ sent: 0 }), { status: 200 });
  }

  let accessToken = "";
  try {
    accessToken = await fcmAccessToken(sa);
  } catch (e) {
    console.error("fcm access token:", e);
    return new Response(JSON.stringify({ error: String(e) }), { status: 500 });
  }

  // user → tokens (cache ใน request เดียว)
  const userIds = [...new Set(rows.map((r) => r.user_id))];
  const { data: tokens, error: tokErr } = await supabase
    .from("push_tokens")
    .select("id, user_id, token")
    .in("user_id", userIds);
  if (tokErr) {
    console.error("select push_tokens:", tokErr);
    return new Response(JSON.stringify({ error: tokErr.message }), { status: 500 });
  }
  const tokensByUser = new Map<string, { id: number; token: string }[]>();
  for (const t of tokens ?? []) {
    const list = tokensByUser.get(t.user_id) ?? [];
    list.push({ id: t.id, token: t.token });
    tokensByUser.set(t.user_id, list);
  }

  let sent = 0;
  for (const n of rows as NotificationRow[]) {
    const userTokens = tokensByUser.get(n.user_id) ?? [];
    const title = n.kind === "severityCritical" ? "Critical alert" : "Aquanoph";
    const body = n.text ?? "You have a new notification";
    const data: Record<string, string> = {
      notificationId: String(n.id),
      kind: n.kind,
      targetId: n.target_id,
      reasonKey: n.reason_key ?? "",
    };

    if (userTokens.length === 0) {
      // ไม่มี device ลงทะเบียน — mark ไม่งั้น retry ฟรีทุกนาที
      await supabase
        .from("notifications")
        .update({ pushed_at: new Date().toISOString() })
        .eq("id", n.id);
      continue;
    }

    let anyTransient = false;
    const deadTokenIds: number[] = [];
    for (const t of userTokens) {
      const result = await sendOne(accessToken, sa.project_id, t.token, title, body, data);
      if (result === "ok") sent++;
      else if (result === "dead") deadTokenIds.push(t.id);
      else anyTransient = true;
    }
    if (deadTokenIds.length > 0) {
      await supabase.from("push_tokens").delete().in("id", deadTokenIds);
    }
    if (!anyTransient) {
      // ส่งครบ (หรือทุก token ตายและถูกลบแล้ว) → ปิดแถว
      await supabase
        .from("notifications")
        .update({ pushed_at: new Date().toISOString() })
        .eq("id", n.id);
    }
  }

  return new Response(JSON.stringify({ processed: rows.length, sent }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
});
