# Lab 03 — BJT DC Bias Web App

เว็บแอป Flask สำหรับคำนวณ DC Bias ของ BJT แบบ Common-Emitter 3 โหมด
สูตรการคำนวณทั้งหมดอยู่ใน `dc_bias.py` (Python) เท่านั้น — HTML/JavaScript ไม่มีสมการ

| โหมด | ฟังก์ชัน | สมการกระแสฐาน |
|---|---|---|
| Fixed Bias | `calculate_fixed_bias(vcc, rb, rc, beta, vbe)` | `IB = (VCC − VBE) / RB` |
| Emitter Bias | `calculate_emitter_bias(vcc, rb, re, rc, beta, vbe)` | `IB = (VCC − VBE) / (RB + (1 + β)·RE)` |
| Voltage Divider Bias | `calculate_divider_bias(vcc, r1, r2, rc, re, beta, vbe)` | `IB = (VTH − VBE) / (RTH + (1 + β)·RE)` |

จากนั้นทุกโหมดใช้ร่วมกัน:

```
IC  = β·IB
IE  = (1 + β)·IB
VE  = IE·RE            (Fixed Bias: RE = 0 → VE = 0)
VB  = VE + VBE
VC  = VCC − IC·RC
VCE = VC − VE
```

## หน่วย

| จุด | หน่วย |
|---|---|
| ฟอร์มความต้านทาน (RB, RC, RE, R1, R2) | kΩ |
| ฟอร์มแรงดัน (VCC, VBE) | V |
| ค่าที่ใช้คำนวณภายใน | Ω และ A |
| ผลลัพธ์ | V, mA, µA |

การแปลง kΩ → Ω เกิดขึ้นครั้งเดียวใน `app.py` (`_positive_resistance`)

## การติดตั้ง

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## การรัน

```powershell
.\venv\Scripts\python.exe -m flask --app app run
```

เปิด http://127.0.0.1:5000/ แล้วเลือกโหมดจากแท็บด้านบนฟอร์ม
การเลือกโหมดจะโหลดหน้าใหม่ (`/?mode=fixed|emitter|divider`) และแสดงเฉพาะช่องที่วงจรนั้นใช้
ไม่มีการใช้ JavaScript ในการคำนวณหรือสลับช่อง

## การทดสอบ

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

- `tests/test_dc_bias.py` — สมการทั้งสามโหมด, Cutoff, Saturation และคีย์ผลลัพธ์
- `tests/test_app.py` — การเลือกโหมด, การตรวจอินพุต, หน้า HTML และ JSON API

## ผลลัพธ์

ทุกฟังก์ชันคืนพจนานุกรมคีย์/หน่วยชุดเดียวกัน:

```json
{
  "status": "Success",
  "region": "Active",
  "message": "VCE = 8.05 V > 0.20 V (transistor in active region)",
  "ib_uA": 12.2986,
  "ic_mA": 1.2299,
  "ie_mA": 1.2422,
  "vb_V": 1.9422,
  "ve_V": 1.2422,
  "vc_V": 9.2943,
  "vce_V": 8.0522
}
```

- `status` = `"Success"` หรือ `"Error"` (ผลระดับคำขอ)
- `region` = `"Active"`, `"Saturation"` หรือ `"Cutoff"` (ตัวชี้ขาดสี/ข้อความบนหน้าเว็บ)

### Region

| เงื่อนไข | region | ผลลัพธ์ |
|---|---|---|
| `IB ≤ 0` | Cutoff | IB = IC = IE = 0, VE = 0, VCE = VC = VCC, VB = VTH (divider) หรือ VCC |
| `VCE ≤ 0.2 V` หรือ `IC ≥ IC(sat)` | Saturation | `IC = (VCC − 0.2 − IB·RE)/(RC + RE)`, `VCE = 0.2 V`, `IE = IC + IB`, `VE = IE·RE`, `VC = VE + 0.2 V` (KVL ปิดครบ) |
| อื่น ๆ | Active | ใช้ค่าที่คำนวณได้ตามสมการ |

## กรณีอ้างอิง (baseline Lab 2)

VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, β = 100, VBE 0.7 V (Divider Bias)

| ปริมาณ | ค่า |
|---|---|
| VB | 1.94 V |
| VE | 1.24 V |
| VC | 9.29 V |
| VCE | 8.05 V |
| IB | 12.3 µA |
| IC | 1.23 mA |
| IE | 1.24 mA |

## JSON API

`POST /api/calculate` รับ JSON (ความต้านทานเป็น kΩ) และคืน JSON ชุดเดียวกับฟังก์ชันใน `dc_bias.py`:

```powershell
curl -X POST http://127.0.0.1:5000/api/calculate `
  -H "Content-Type: application/json" `
  -d '{"mode":"divider","vcc":12,"r1":100,"r2":22,"rc":2.2,"re":1,"beta":100,"vbe":0.7}'
```

ข้อผิดพลาดคืน HTTP 400 พร้อม `{"status": "Error", "message": "..."}`
เช่น `โหมดไม่ถูกต้อง`, `β ต้องมากกว่า 0`, `RC ต้องมากกว่า 0`, `ไม่พบค่า RC`, `ข้อมูลต้องเป็น JSON object`

## โครงสร้างไฟล์

```
app.py                 Flask routes, การแปลงหน่วย, การตรวจอินพุต, if/elif เลือกโหมด
dc_bias.py             สมการ Fixed / Emitter / Divider และการจำแนก region
templates/index.html   ฟอร์มและผลลัพธ์แบบ server-rendered (Jinja)
tests/                 unittest
requirements.txt       Flask==3.1.3
docs/                  เอกสารออกแบบและแผนงาน
```
