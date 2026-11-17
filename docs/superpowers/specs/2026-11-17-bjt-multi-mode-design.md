# BJT DC Bias — รองรับ 3 โหมด (ฉบับปรับตามคำสั่งใบงาน)

- วันที่: 2026-11-17 (ปรับจากฉบับแรก)
- สถานะ: รออนุมัติแผน
- Baseline: `C:\B6639761\baseline-A1.md` (Divider: VB 1.94, VE 1.24, VC 9.29, VCE 8.05, IB 12.3 µA, IC 1.23 mA, IE 1.24 mA)

## 1. สิ่งที่เปลี่ยนจากฉบับแรก

| ฉบับแรก | ฉบับนี้ (ตามคำสั่ง) |
|---|---|
| คำนวณใน `app.py` ฟังก์ชันเดียว `solve()` | แยกโมดูล `dc_bias.py` มีฟังก์ชัน Fixed / Emitter / Divider คนละฟังก์ชัน |
| JS เรียก `/api/calculate` แล้วเรนเดอร์ | ฟอร์ม POST แบบดั้งเดิม, server เรนเดอร์ HTML, **ไม่เพิ่ม JavaScript** |
| ลบสูตรใน JS / เขียน `script.js` ใหม่ | ลบ inline script และลบ `static/js/script.js` ที่ไม่ได้ใช้ |
| ไม่ clamp ตอน Saturation | คงวิธีคำนวณ Divider เดิม (clamp ตามเดิม) และให้อีกสองโหมดทำเหมือนกัน |

## 2. เป้าหมาย

- G1 มี 3 โหมดตามสมการใบงาน; Fixed และ Emitter เป็นฟังก์ชันใหม่, Divider คงวิธีเดิม
- G2 สมการอยู่ใน Python เท่านั้น (ห้ามใน HTML/JS)
- G3 หน่วย: ฟอร์มเป็น kΩ, แปลงเป็น Ω ครั้งเดียวใน `app.py`, คำนวณเป็น Ω/A, แสดง V / mA / µA
- G4 ทั้งสามฟังก์ชันคืน **คีย์และหน่วยชุดเดียวกัน**
- G5 ตรวจเฉพาะช่องที่โหมดนั้นใช้; โหมดไม่รู้จัก = error (ไม่เดาเป็น Divider)
- G6 เลือกโหมดแล้วโหลดฟอร์มใหม่ เห็นเฉพาะช่องที่ใช้
- G7 ผล/error ระบุโหมด; เมื่อ error ต้องไม่เหลือผลรอบก่อน
- G8 คงผล A1 เดิม

## 3. ไม่ทำ

AC/กราฟ/deploy/auth/หน่วยเลือกได้/ระบบใหม่ทั้งโปรเจกต์

## 4. ไฟล์และฟังก์ชันเดิมที่ใช้ซ้ำ

| ของเดิม | ใช้อย่างไร |
|---|---|
| `app.py: calculate_bjt_dc_bias(vcc, r1, r2, rc, re, beta, vbe=0.7)` | ย้ายไป `dc_bias.py` เป็น `calculate_divider_bias` โดยคงสมการเดิม |
| `app.py: @app.route('/') index()` | ขยายให้รับ `?mode=` และส่งค่าฟอร์ม/ผลไป template |
| `app.py: @app.route('/api/calculate', methods=['POST'])` | คงไว้เป็น JSON API และใช้ตัว dispatch ร่วมกับฟอร์ม |
| `templates/index.html` ฟอร์ม `#bias-form`, id `vcc, r1, r2, rc, re, beta, vbe` | คง id เดิม เพิ่ม `rb` และ radio/ลิงก์ `mode` |
| `templates/index.html` ตาราง `#res-*`, badge `#status-card` | เปลี่ยนจากค่า hardcode เป็นค่าเรนเดอร์จาก server |
| `templates/index.html` SVG (`svg-r1-*`, `svg-r2-*`, `svg-re-*`) | ซ่อน/แสดงขาตามโหมดด้วย Jinja (ไม่ใช้ JS) |
| `static/css/style.css` `.badge-success/.badge-warning/.badge-danger`, `.form-row`, `.input-group` | ใช้ต่อ + เพิ่ม `.hidden` |

คีย์ผลลัพธ์沿用ชื่อ Lab 2 (อนุญาตตามใบงาน): `vb_V`, `ve_V`, `vc_V`, `vce_V`, `ib_uA`, `ic_mA`, `ie_mA`, `region`, `message`, `status`

## 5. การออกแบบ

### 5.1 `dc_bias.py`

```python
def calculate_fixed_bias(vcc, rb, rc, beta, vbe=0.7) -> dict
def calculate_emitter_bias(vcc, rb, re, rc, beta, vbe=0.7) -> dict
def calculate_divider_bias(vcc, r1, r2, rc, re, beta, vbe=0.7) -> dict
```

- รับค่าเป็น SI (V, Ω) ทั้งหมด
- สมการ: Fixed `IB=(VCC−VBE)/RB`, Emitter `IB=(VCC−VBE)/(RB+(β+1)RE)`, Divider ตามของเดิม
- `IC=βIB`, `IE=(β+1)IB`, `VE=IERE` (Fixed = 0), `VB=VE+VBE`, `VC=VCC−ICRC`, `VCE=VC−VE`
- คืนคีย์เดียวกันทั้งสามฟังก์ชัน: `status`, `region`, `message`, `ib_uA`, `ic_mA`, `ie_mA`, `vb_V`, `ve_V`, `vc_V`, `vce_V`

### 5.2 `app.py`

- `if / elif` ตาม `mode` ที่ส่งมา: `fixed` → `calculate_fixed_bias`, `emitter` → ..., `divider` → ...
- แปลง kΩ→Ω และตรวจ **เฉพาะช่องของโหมดนั้น**; ฟิลด์ที่โหมดไม่ใช้ไม่ถูกอ่าน
- `mode` ไม่รู้จัก → ข้อความ "โหมดไม่ถูกต้อง" (HTTP 400) ไม่ fallback เป็น Divider; ถ้าไม่ส่ง `mode` มาที่ `GET /` ใช้ divider เป็นค่าเริ่มต้นของฟอร์มเท่านั้น
- routes:
  - `GET /` และ `GET /?mode=...` → เรนเดอร์ฟอร์มตามโหมด
  - `POST /calculate` → ตรวจ/คำนวณ/เรนเดอร์ผลหรือ error (HTTP 400 เมื่อ error)
  - `POST /api/calculate` → JSON เดิม (ใช้ dispatch ชุดเดียวกัน)

### 5.3 `templates/index.html`

- แถบเลือกโหมดเป็นลิงก์ 3 อัน (`/?mode=divider|fixed|emitter`) ไม่ใช้ JavaScript
- ฟอร์ม `method="post" action="/calculate"` + hidden `mode`
- แสดงช่องด้วย Jinja: Fixed → `RB`; Emitter → `RB, RE`; Divider → `R1, R2, RE`; ทุกโหมดมี `VCC, RC, β, VBE`
- ผลลัพธ์: `{% if result %}` แสดงค่าและ badge ตาม `region`; หัวข้อผลระบุชื่อโหมด
- `{% elif error %}` แสดง badge แดงพร้อมข้อความ และตารางผลเป็น `—` ทั้งหมด
- ค่าที่ผู้ใช้กรอกถูกส่งกลับมาเติมในฟอร์ม (เห็นว่ากรอกอะไรผิด)
- SVG: ซ่อน `R2`/`RE`/เส้น emitter ลงกราวด์ด้วยเงื่อนไขโหมด; ข้อความ R1 เปลี่ยนเป็น RB ในโหมด Fixed/Emitter
- ลบบล็อก `<script>` คำนวณเดิมออก และไม่โหลด `static/js/script.js`

### 5.4 Region และข้อความ

- `IB ≤ 0` → `region="Cutoff"`, `status="Success"`, กระแส 0, `VCE=VCC`, ข้อความ "IB ≤ 0: อยู่ใน Cutoff (แบบจำลอง active region ใช้ไม่ได้)"
- `VCE < 0.2 V` → `region="Saturation"` และ clamp ตามวิธี Divider เดิม (IC=ICsat, VCE=0.2) พร้อมข้อความ "VCE ... < 0.2 V: Saturation (การประมาณ active region ใช้ไม่ได้)"
- ปกติ → `Active` พร้อมข้อความ "VCE = ... V > 0.2 V (transistor in active region)"

### 5.5 เทสต์

`tests/test_dc_bias.py` (สมการ) และ `tests/test_app.py` (route)

| กรณี | อินพุต | คาดหมาย |
|---|---|---|
| Divider A1 | 12 V, R1 100k, R2 22k, RC 2.2k, RE 1k, β=100 | IC 1.2298 mA, VCE 8.0522 V (ตรง baseline) |
| Fixed | RB 1 MΩ | IB 11.3 µA, IC 1.13 mA, VE 0, VB 0.7 V, VCE 9.514 V |
| Emitter | RB 1 MΩ, RE 1k | IB 10.2634 µA, IC 1.0263 mA, VCE 8.7055 V |
| Cutoff | Divider VBE 2.5 | กระแส 0, region Cutoff |
| Saturation | Divider RC 10k, RE 100Ω | region Saturation, IC = ICsat 1.1683 mA, VCE 0.2 V |
| โหมดผิด | `mode=hbridge` | 400 + "โหมดไม่ถูกต้อง" |
| ฟิลด์ผิด | β=0 | 400 + "β ต้องมากกว่า 0"; ตารางผลไม่มีตัวเลข |
| GET โหมด | `/?mode=fixed` | มีช่อง rb, ไม่มีช่อง r1/r2/re |

## 6. Decisions

1. ใช้ชื่อคีย์แบบ Lab 2 (`vb_V` ฯลฯ) ตามที่ใบงานอนุญาต
2. คงการ clamp ตอน Saturation ตามวิธี Divider เดิม เพื่อไม่ให้ผลสามโหมดต่างกัน
3. ลบ `static/js/script.js` (โค้ดตาย) และไม่เพิ่ม JS ใหม่
4. `POST /calculate` เป็นหน้า HTML; `POST /api/calculate` ยังเป็น JSON สำหรับทดสอบ
5. ข้อความ UI ภาษาไทยสั้น ๆ ตามข้อ 5.4

## 7. ความเสี่ยง

- `index.html` ยาว ~25 KB; แก้ด้วย Jinja ต้องคง id ที่ CSS/SVG อ้างถึง
- การย้ายฟังก์ชัน Divider ต้องคงสมการเดิมทุกบรรทัด มิฉะนั้น baseline A1 เพี้ยน
- `venv/` ยัง untracked และไม่มี `.gitignore`
