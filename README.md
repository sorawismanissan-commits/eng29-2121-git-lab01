# Lab 04 — BJT CE Amplifier Simulator

เว็บแอป Flask สำหรับ **Common-Emitter Voltage Divider Amplifier** ที่แสดงผลสองแหล่งที่มาแยกกันชัดเจน:

| แหล่ง | ไฟล์ | สิ่งที่ทำ |
|---|---|---|
| **Analytical** | `dc_bias.py` | สมการ DC Bias เดิมของ Lab 03 (Fixed / Emitter / Divider) ไม่เปลี่ยน |
| **SPICE** | `spice_engine.py` | รัน `ngspice_con` จริง แล้ว parse ผล `.op` / `.ac` / `.tran` |

หน้าเว็บแสดง provenance ของแต่ละชุดเสมอ — ห้ามรวมค่าทั้งสองเป็นตัวเลขเดียว ตาราง Cross-check แสดง Analytical, SPICE และ Δ แยกคอลัมน์

> หมายเหตุ: SPICE v1 รองรับเฉพาะ `mode == "divider"` โหมด Fixed/Emitter ยังใช้ได้ปกติแต่ไม่มีปุ่ม Run Simulation

## สมการ Analytical (คงไว้จาก Lab 03)

| โหมด | ฟังก์ชัน | สมการกระแสฐาน |
|---|---|---|
| Fixed Bias | `calculate_fixed_bias(vcc, rb, rc, beta, vbe)` | `IB = (VCC − VBE) / RB` |
| Emitter Bias | `calculate_emitter_bias(vcc, rb, re, rc, beta, vbe)` | `IB = (VCC − VBE) / (RB + (1 + β)·RE)` |
| Voltage Divider Bias | `calculate_divider_bias(vcc, r1, r2, rc, re, beta, vbe)` | `IB = (VTH − VBE) / (RTH + (1 + β)·RE)` |

จากนั้นทุกโหมดใช้ร่วมกัน: `IC = β·IB`, `IE = (1 + β)·IB`, `VE = IE·RE`, `VB = VE + VBE`, `VC = VCC − IC·RC`, `VCE = VC − VE`

## หน่วย

| จุด | หน่วย |
|---|---|
| ฟอร์มความต้านทาน (RB, RC, RE, R1, R2, RL) | kΩ |
| ฟอร์มแรงดัน (VCC, VBE) | V |
| Source amplitude | mV peak |
| AC start/stop | Hz |
| Transient stop / max step | ms / µs |
| ค่าที่ส่งเข้า engine | SI (V, Ω, Hz, s) |
| ผลลัพธ์ | V, mA, µA, dB, degrees, ms |

การแปลงหน่วยอยู่ใน `app.py` (`_positive_resistance`, `parse_spice_request`) ส่วน `spice_engine.py` รับค่า SI เท่านั้น

## วงจรที่จำลอง

CE amplifier มาตรฐาน: `VCC → RC → Q1 → RE → GND`, ตัวหาร `R1/R2` ที่ฐาน, `CIN` และ `COUT` (10 µF) พร้อม `RL`
**ไม่มี emitter bypass capacitor (CE)** ตาม baseline ของใบงาน — ดังนั้น gain midband อยู่ที่ประมาณ `RC || RL / RE` ไม่ใช่ `−gm·RC`

Analysis Mode มี 3 แบบ (ไม่มี `all`):

| Mode | คำสั่ง ngspice | ผล |
|---|---|---|
| `dc` | `.op` | V_B, V_E, V_C, V_CE, I_B, I_C, I_E |
| `ac` | `.ac dec ...` | Frequency, gain (dB), phase (degrees) — แกน X แบบ log |
| `tran` | `.tran ...` | Time (ms), Vin, Vout |

กราฟทั้งหมดเป็น **SVG ที่ render บนเซิร์ฟเวอร์** (`spice_plots.py`) ไม่มี JavaScript คำนวณหรือวาดกราฟ

## ติดตั้ง

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### ngspice

ต้องใช้ **ngspice 47** และต้องเรียก `ngspice_con.exe` (console build) — `ngspice.exe` เป็น GUI และไม่พิมพ์ผลออก console จึงใช้ไม่ได้

ตัวอย่าง portable install:

```powershell
$env:NGSPICE_BIN = "$env:LOCALAPPDATA\ngspice\47\Spice64\bin\ngspice_con.exe"
```

ถ้าไม่ตั้ง `NGSPICE_BIN` โปรแกรมจะหา `ngspice_con` จาก `PATH` ก่อน

### BJT model

ลำดับการหา model:

1. `SPICE_MODEL_PATH` = path เต็มของไฟล์ model
2. `models/instructor.model` ในโปรเจกต์
3. **provisional model** (ใช้ได้ใน v1 แต่ต้องมี badge เตือน):

```spice
.model QNPN NPN (BF=<beta from form> IS=1e-15 VAF=100)
```

เมื่อยังไม่มี Starter Kit ให้ใช้ provisional model ได้ แต่ **ห้ามกล่าวอ้างว่า B2 ผ่านด้วย instructor model** — หน้าเว็บจะแสดงข้อความ `provisional model — Starter Kit not found` ทุกครั้งที่ใช้

ค่า `VBE` ในฟอร์มใช้กับ Analytical เท่านั้น; SPICE ใช้ VBE จาก model

## การรัน

```powershell
$env:NGSPICE_BIN = "$env:LOCALAPPDATA\ngspice\47\Spice64\bin\ngspice_con.exe"
.\venv\Scripts\python.exe -m flask --app app run
```

เปิด http://127.0.0.1:5000/ → เลือก `?mode=divider` → กรอกค่า → กด **Run Simulation** หลังเลือก Analysis Mode
ปุ่ม **Calculate DC Bias** ยังให้ผล Analytical เหมือนเดิม การเลือกโหมดโหลดหน้าใหม่แบบ server-side ไม่มี JavaScript

## การทดสอบ

```powershell
$env:NGSPICE_BIN = "$env:LOCALAPPDATA\ngspice\47\Spice64\bin\ngspice_con.exe"
.\venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

| ไฟล์ | สิ่งที่ทดสอบ | ต้องมี ngspice? |
|---|---|---|
| `tests/test_dc_bias.py` | สมการ 3 โหมด, Cutoff, Saturation | ไม่ |
| `tests/test_app.py` | ฟอร์ม, validation, routes, template, กราฟ | ไม่ (patch `app.run_ngspice`) |
| `tests/test_spice_engine.py` | netlist, parser, `run_ngspice` จริง | **ใช่** สำหรับ `RunTests.test_run_dc_with_real_ngspice` |
| `tests/test_spice_plots.py` | SVG server-rendered, log axis, escape | ไม่ |

Integration test ที่ skip ไม่นับว่า PASS — ต้องเห็น `test_run_dc_with_real_ngspice ... ok`

## หลักฐานรัน (run artifacts)

ทุกครั้งที่รันจะสร้าง `instance/spice_runs/<run_id>/` (ไม่ลบอัตโนมัติใน v1):

```
circuit.cir      netlist ที่ส่งให้ ngspice จริง
request.json     ค่าขาเข้า SI
meta.json        status, kind, ระยะเวลา, model, run_id — เขียนแม้รันล้มเหลว
ngspice.log      stdout + stderr
op.csv / ac.csv / tran.csv   เฉพาะ analysis ที่รัน
```

`instance/` อยู่ใน `.gitignore` แล้ว

## HTTP API

| Route | หน้าที่ |
|---|---|
| `POST /calculate` | Analytical เดิม |
| `POST /api/calculate` | JSON Analytical เดิม |
| `POST /spice` | Analytical + SPICE (HTML) |
| `POST /api/spice` | `{"status", "analytical", "spice"}` |

Error: SPICE settings ผิด → 400 พร้อม Analytical ที่ยังถูกต้อง; engine error → 502 (timeout → 504) พร้อม `kind`, `message`, `run_id`

## Browser acceptance

หลักฐาน B1–B8 อยู่ใน `docs/validation.md` รันด้วย OpenCode Browser / Playwright MCP (Chrome จริง)
ข้อจำกัดปัจจุบัน: ใช้ provisional model เพราะยังไม่มี Starter Kit — ผล SPICE เป็น generic NPN ไม่ใช่ model จากผู้สอน

## โครงสร้างไฟล์

```
app.py                 Flask routes, validation, แปลงหน่วย, สร้าง plots
dc_bias.py             สมการ Fixed / Emitter / Divider และ region
spice_engine.py        netlist, subprocess, parser, run artifacts
spice_plots.py         SVG charts แบบ server-rendered
templates/index.html   ฟอร์ม + ผล Analytical + ผล SPICE (Jinja)
tests/                 unittest
requirements.txt       Flask==3.1.3
docs/                  spec, plan, validation
```
