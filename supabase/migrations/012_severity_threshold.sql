-- 012: severity_reports.threshold — snapshot ของ threshold ที่ใช้ตัดสิน ณ reading นั้น
-- ทำไม: threshold ไม่ใช่ค่าคงที่ (DO ขึ้นกับน้ำหนัก/ความหนาแน่น/อุณหภูมิ, salinity shift ตาม NH3/DO)
--        ถ้าไม่เก็บ แอปย้อนดูไม่ได้ว่า "ตอนนั้น Optimal คือ >= เท่าไร"
-- nullable: แถวก่อน migration นี้เป็น null (ไม่ backfill — re-run engine ย้อนหลังเป็นงานแยก)

alter table severity_reports add column threshold jsonb;

comment on column severity_reports.threshold is
  'Threshold ที่ใช้ตัดสินแถวนี้: level {kind:"level",levelType,optimal,stress,highRisk,critical} หรือ range {kind:"range",optimal:{min,max},stress:{...},highRisk:{...},critical:{...}}; null ใน {min,max} = ขอบเปิด (noMin/noMax)';
