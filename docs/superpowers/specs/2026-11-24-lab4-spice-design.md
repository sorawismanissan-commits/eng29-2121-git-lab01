# Lab 04 — เชื่อม ngspice เข้ากับ CE Voltage Divider Bias

- วันที่: 2026-11-24
- สถานะ: อนุมัติ design แล้ว (2026-11-24) — ใช้ provisional model ไปก่อน
- Baseline: Lab 03 (`6dee8fa`) — Analytical DC Bias 3 โหมด, Flask server-rendered, ngspice 47 ติดตั้งในเครื่องแล้ว
- ขอบเขต v1: **Voltage Divider Bias เท่านั้น** สำหรับเส้นทาง SPICE
- ใบงานอ้างอิง: `C:\Users\B6639761\Downloads\Lab04_BJT_Amplifier_Simulator_2-2569.html`

## 1. บริบทและเหตุผล

Lab 03 คำนวณ DC Bias ด้วยสมการ Analytical ใน `dc_bias.py` และแสดงผลผ่าน Flask/Jinja
Lab 04 ต้องพิสูจน์ว่าแบบจำลอง Analytical สอดคล้องกับ SPICE จริง โดยไม่ทิ้งของเดิม

ภาพ Architecture Delta และใบงาน Lab 04 กำหนดทิศทางไว้ชัด:

- คง `dc_bias.py` และผล Analytical เดิม
- ขยาย `app.py` ให้เลือกเส้นทาง Analytical / SPICE
- เพิ่ม `spice_engine.py` สำหรับสร้าง netlist, เรียก ngspice ผ่าน subprocess และ parse ผล
- แสดงผล DC / AC / Transient เฉพาะ CE Voltage Divider
- แยกป้ายแหล่งที่มาของผล Analytical กับ SPICE อย่างชัดเจน
- เก็บหลักฐาน: netlist, engine status, plot values, units, saved run หรือ error
- ใช้ **Analysis Mode selector** แยก DC / AC / Transient ตามใบงาน

ngspice เป็นโปรแกรมภายนอก ไม่ใช่ Python package จึงต้องตรวจการมีอยู่, exit code, timeout และความถูกต้องของไฟล์ผลทุกครั้ง

## 2. เป้าหมาย

- G1 เพิ่มเส้นทาง SPICE สำหรับ Voltage Divider โดยไม่แก้สมการ Analytical
- G2 เรียก ngspice 47 ผ่าน `ngspice_con.exe` แบบ batch และ parse ผล `.op`, `.ac`, `.tran`
- G3 แสดงผล Analytical และ SPICE แยกกัน พร้อมป้ายแหล่งที่มาและหน่วย
- G4 แสดงกราฟ AC (magnitude/phase) และ Transient (input/output) แบบ server-rendered SVG
- G5 เก็บ netlist, CSV, log และ metadata ของทุก run ไว้ตรวจสอบย้อนหลัง
- G6 จัดการกรณี ngspice ไม่มีใน PATH, timeout, exit code ผิด, ไฟล์ผลหาย และ parse ไม่ได้
- G7 คงพฤติกรรมเดิมของ Lab 03 ทั้ง 3 โหมดและ JSON API เดิม
- G8 มีเทสต์อัตโนมัติและ browser acceptance B1–B8 สำหรับเส้นทางใหม่
- G9 ให้ผู้ใช้เลือก Analysis Mode ก่อน Run และไม่แสดงผลของ analysis ที่ไม่ได้รัน

## 3. ไม่ทำ (Non-goals)

- ไม่ทำ SPICE สำหรับ Fixed Bias หรือ Emitter Bias ใน v1
- ไม่เปลี่ยนสมการหรือผลลัพธ์ Analytical เดิม
- ไม่สร้างโปรเจกต์ใหม่ / ไม่เปลี่ยน framework / ไม่ย้าย UI ไป JS
- ไม่รับ netlist จากผู้ใช้โดยตรง และไม่ให้ผู้ใช้แก้ netlist ผ่านฟอร์ม
- ไม่ทำ interactive zoom/pan หรือ real-time simulation
- ไม่ทำ Emitter Bypass (CE) ใน baseline — ใบงานกำหนดให้เป็นงานต่อยอด
- ไม่รันทั้ง 3 analysis พร้อมกันในคำขอเดียว; ใช้ Analysis Mode selector
- ไม่ติดตั้ง Playwright MCP หรือ Impeccable ในงานนี้ (แยกงาน)
- ไม่ commit โฟลเดอร์ run artifacts หรือ `venv/`
- ไม่รับประกันค่าตรงใบงาน Lab 4 สำหรับ BJT model จนกว่าจะได้ Starter Kit

## 4. Anti-goals

- ห้ามเอาค่าจาก SPICE ไปทับหรือรวมเป็นค่าเดียวกับ Analytical
- ห้ามแสดงผล SPICE โดยไม่มีป้ายบอกแหล่งที่มา
- ห้ามรายงานว่า Success ถ้า ngspice ไม่ได้รันจริง, timeout, หรือไฟล์ผลไม่ครบ
- ห้ามใส่สมการลง HTML/JavaScript
- ห้ามใช้ `shell=True` หรือต่อคำสั่งจากค่าที่ผู้ใช้กรอก
- ห้ามแสดงกราฟ/ค่าจาก run ก่อนหน้าหลงเหลือเมื่อ run ใหม่ล้มเหลว
- ห้ามทำให้โหมด Fixed/Emitter เดิมพังหรือช้ากว่าปัจจุบัน

## 5. ทางเลือกที่พิจารณา

### 5.1 Server-rendered SVG + persistent run artifacts (เลือก)

- `spice_engine.py` คืนข้อมูลดิบและ metadata
- `spice_plots.py` แปลงจุดข้อมูลเป็น SVG
- Template แสดงผลโดยไม่ต้องมี JavaScript
- เก็บ run artifacts ใต้ `instance/spice_runs/<run_id>/`
- ข้อดี: ตรวจสอบได้, test ได้, ไม่ต้องลง chart library, เข้ากับสไตล์ Lab 03
- ข้อเสีย: กราฟเป็นภาพนิ่ง ไม่มี interaction

### 5.2 Client-side chart library + JSON API

- ใช้ Chart.js/Plotly วาดกราฟใน browser
- ข้อดี: interactive, ดูสวย
- ข้อเสีย: เพิ่ม JS/CDN, ต้องจัดการ offline, test ยากขึ้น และขัดกับแนวทาง server-rendered เดิม
- ไม่เลือกสำหรับ v1

### 5.3 Engine-only spike ก่อน

- ทำ CLI/netlist/parser ให้เสร็จก่อน แล้วค่อยผูก UI
- ข้อดี: ความเสี่ยงต่ำ
- ข้อเสีย: ไม่ตอบโจทย์ end-to-end จากฟอร์มถึงกราฟในรอบเดียว
- ใช้เป็นลำดับการทดสอบภายในได้ แต่ไม่ใช่สถาปัตยกรรมสุดท้าย

## 6. วงจร SPICE v1 — CE Voltage Divider

ใช้มาตรฐาน common-emitter amplifier ที่มี voltage divider bias และ **ไม่มี emitter bypass** ตามใบงาน:

```text
VCC ──┬── R1 ──┬── base
      │        │
      │        R2
      │        │
      │       GND
      │
      RC
      │
      collector ── COUT ── RL ── GND
      │
     Q1 (NPN)
      │
      emitter ── RE ── GND
```

- `CIN` คัปปลิ้งสัญญาณเข้าที่ base
- `COUT` คัปปลิ้งสัญญาณออกจาก collector ไปยัง `RL`
- ไม่มี `CE` ใน baseline; ถ้าจะทำภายหลังให้เพิ่มเป็น option แยก
- ที่ DC capacitor เปิดวงจร ทำให้ bias point ยังเทียบกับ Lab 03 ได้
- ค่าเริ่มต้น: `CIN = 10 µF`, `COUT = 10 µF`, `RL = 10 kΩ`

### 6.1 Netlist template

ค่าทุกตัวถูก format เป็นตัวเลขจาก Python ก่อนใส่ netlist ห้ามต่อ string ดิบจากผู้ใช้
netlist ถูกสร้างเฉพาะ analysis ที่เลือก:

```spice
* Lab 04 CE Voltage Divider Bias
VCC 1 0 {vcc}
VIN 2 0 DC 0 AC 1 SIN(0 {vin_amp} {vin_freq})
CIN 2 4 10u
R1 1 4 {r1}
R2 4 0 {r2}
RC 1 5 {rc}
RE 6 0 {re}
Q1 5 4 6 QNPN
COUT 5 7 10u
RL 7 0 {rl}
{model_card}

.control
{analysis_block}
.endc
.end
```

`analysis_block` เป็นอย่างใดอย่างหนึ่ง:

```spice
* DC
op
wrdata op.csv v(4) v(6) v(5) v(5)-v(6) @q1[ic] @q1[ib]
```

```spice
* AC
ac dec {ac_ppd} {ac_start} {ac_stop}
wrdata ac.csv vm(7) vp(7)
```

```spice
* Transient
tran {tran_step} {tran_stop}
wrdata tran.csv v(2) v(7)
```

หมายเหตุ: วิธีนี้ใช้ `.control` + `wrdata` กับ `ngspice_con -b` และทดสอบกับ ngspice 47 แล้ว
ไม่ผสมกับ `-o`/`-r` ของ batch mode เพื่อเลี่ยงความกำกวมเรื่อง output format

### 6.2 Analysis modes

| Mode | คำสั่ง | ข้อมูลที่แสดง |
|---|---|---|
| `dc` | `.op` | V_B, V_E, V_C, V_CE, I_B, I_C, I_E + model/status |
| `ac` | `.ac` | Frequency, gain magnitude (dB), phase (degrees) |
| `tran` | `.tran` | Time (ms), Vin, Vout, amplitude/phase inversion |

- `analysis` ต้องเป็น `dc`, `ac`, หรือ `tran` เท่านั้น
- โหมดอื่น → HTTP 400
- ไม่มี `all` ใน v1; ถ้าต้องการรันครบให้กด Run ทีละ mode

### 6.3 ค่าเริ่มต้นของ analysis

| พารามิเตอร์ | ค่าเริ่มต้น | หน่วย |
|---|---:|---|
| `vin_amp` | 10 | mV peak (ใช้กับ transient) |
| `vin_freq` | 1 000 | Hz |
| `ac_start` | 10 | Hz |
| `ac_stop` | 1 000 000 | Hz |
| `ac_ppd` | 10 | points/decade |
| `tran_stop` | 5 | ms |
| `tran_step` | 10 | µs |
| `rl` | 10 | kΩ |
| timeout | 15 | s |

### 6.4 BJT model และ Starter Kit

- ลำดับการหา model:
  1. environment variable `SPICE_MODEL_PATH` (path เต็มของไฟล์ model)
  2. `models/instructor.model` ในโปรเจกต์ (ถ้ามี)
  3. **provisional generic model** ใน `spice_engine.py` (ใช้เฉพาะเมื่อยังไม่มี Starter Kit) — **ได้รับอนุมัติให้ใช้ใน v1 แล้ว**
- model ที่ใช้จริงต้องถูกบันทึกใน `SpiceResult.model` และแสดงบนหน้าเว็บ
- ถ้าใช้ provisional model ต้องแสดง badge **“provisional model — Starter Kit not found”**
- ค่า `VBE` ในฟอร์มยังใช้กับ Analytical เท่านั้น; SPICE ใช้ VBE จาก model
- ห้ามอ้างว่า B2 ผ่านสมบูรณ์แบบ instructor model ถ้าใช้ provisional model
- เมื่อได้ Starter Kit ให้วางไฟล์ model แล้วตั้ง `SPICE_MODEL_PATH`; ไม่ต้องแก้ parser

provisional model ที่ใช้ทดสอบ local:

```spice
.model QNPN NPN (BF={beta} IS=1e-15 VAF=100)
```

### 6.5 ค่าอ้างอิงจากการทดลองจริง (baseline, ไม่มี CE)

ทดลองด้วย VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, β = 100, VBE = 0.70 V:

| ปริมาณ | Analytical | SPICE (provisional model) |
|---|---:|---:|
| V_B | 1.9422 V | 1.9576 V |
| V_E | 1.2421 V | 1.2395 V |
| V_C | 9.2943 V | 9.2984 V |
| V_CE | 8.0522 V | 8.0589 V |
| I_B | 12.2985 µA | 11.4476 µA |
| I_C | 1.2298 mA | 1.2288 mA |

- AC midband (1 kHz, ไม่มี CE): gain ≈ **1.748 V/V ≈ 4.85 dB**, phase ≈ **-179.9°**
- Transient 1 kHz: 508 จุด, output ถูกขยายและกลับเฟสเมื่อเทียบกับ input
- ค่าเหล่านี้เป็น baseline สำหรับ smoke test ไม่ใช่เกณฑ์ใบงาน Lab 4
- ค่า SPICE จะเปลี่ยนเมื่อใช้ model จาก Starter Kit

## 7. `spice_engine.py`

### 7.1 Public API

```python
class SpiceError(Exception):
    kind: str          # not_found | timeout | process_error | artifact_error | parse_error | model_error
    message: str
    run_id: str | None
    artifacts: dict | None

def find_ngspice() -> str
def find_model() -> tuple[str, str]   # (model_card, source)
def build_netlist(request: SpiceRequest) -> str
def run_ngspice(request: SpiceRequest, timeout: float = 15.0) -> SpiceResult
def parse_op_csv(path: Path) -> dict
def parse_ac_csv(path: Path) -> list[dict]
def parse_tran_csv(path: Path) -> list[dict]
```

### 7.2 `SpiceRequest`

รับค่า SI จาก `app.py`: V, Ω, Hz, s, A
ฟิลด์ขั้นต่ำ:

- analysis: `dc` | `ac` | `tran`
- bias: `vcc_V`, `r1_ohm`, `r2_ohm`, `rc_ohm`, `re_ohm`, `beta`, `vbe_V`
- source: `vin_amp_V`, `vin_freq_Hz`
- AC: `ac_start_Hz`, `ac_stop_Hz`, `ac_ppd`
- transient: `tran_stop_s`, `tran_step_s`
- load: `rl_ohm`

### 7.3 `SpiceResult`

```python
{
    "engine": "ngspice",
    "engine_version": "ngspice-47",
    "status": "Success",
    "analysis": "dc",
    "run_id": "20261124-160000-a1b2c3d4",
    "duration_ms": 123,
    "model": "QNPN NPN (BF=100 IS=1e-15 VAF=100)",
    "model_source": "provisional",
    "netlist": "...",
    "dc": {"vb_V": ..., "ve_V": ..., "vc_V": ..., "vce_V": ...,
           "ib_uA": ..., "ic_mA": ..., "ie_mA": ...},
    "ac": {"points": [...], "gain_db_mid": ..., "phase_deg_mid": ...},
    "tran": {"points": [...]},
    "warnings": [],
    "artifacts": {"dir": "...", "netlist": "...", "op": "...",
                  "ac": "...", "tran": "...", "log": "...", "meta": "..."}
}
```

- `dc` ใช้คีย์เดียวกับ `dc_bias.py` เพื่อให้ template เทียบกันได้
- `ac.points`: `freq_Hz`, `gain_db`, `phase_deg`
- `tran.points`: `time_ms`, `vin_V`, `vout_V`
- `analysis` ระบุว่าผลชุดใดถูก populate; ชุดอื่นเป็น `None`/ว่าง
- `run_id` สร้างจาก timestamp + uuid 8 hex ฝั่ง server เท่านั้น

### 7.4 การหา ngspice

ลำดับ:

1. environment variable `NGSPICE_BIN` (path เต็ม)
2. `shutil.which("ngspice_con")`
3. `shutil.which("ngspice_con.exe")`
4. `shutil.which("ngspice")` (ใช้ได้บน Linux; บน Windows อาจเป็น GUI)

ถ้าไม่พบ → `SpiceError(kind="not_found")`
ถ้าพบเฉพาะ GUI `ngspice.exe` บน Windows → แจ้งข้อผิดพลาดว่าให้ใช้ `ngspice_con.exe`

**ข้อกำหนดสำคัญ:** Flask และ integration tests ต้องถูกรันใน environment ที่ `ngspice_con` อยู่ใน PATH
ถ้า PATH ของ process ไม่มี (เช่น shell เก่าที่เปิดก่อนติดตั้ง) ให้ตั้ง `$env:NGSPICE_BIN` เป็น path เต็ม
การข้าม integration test ไม่ถือว่า PASS; ต้องบันทึก `NOT RUN` พร้อมเหตุผล

### 7.5 การรันและ run artifacts

```python
subprocess.run(
    [ngspice, "-b", "circuit.cir"],
    cwd=run_dir,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=timeout,
)
```

- สร้าง `run_dir = instance/spice_runs/<run_id>/` **ก่อน** เรียก ngspice
- เขียน `request.json`/`meta.json` ตั้งแต่ต้น; เขียนสถานะสุดท้ายใน `finally`
- ไม่ใช้ `shell=True`
- `stdout` + `stderr` เขียนลง `ngspice.log`
- ตรวจ `returncode == 0`
- ตรวจไฟล์ผลเฉพาะ analysis ที่รันว่ามีและไม่ว่าง
- สแกน log หา fatal patterns: `Error`, `singular matrix`, `timestep too small`, `no such vector`
- ถ้า timeout → kill process แล้วคืน `SpiceError(kind="timeout", run_id=..., artifacts=...)`
- ถ้า exit code ผิด → `process_error` พร้อม log ท้าย 20 บรรทัด
- ถ้าไฟล์หาย/ว่าง → `artifact_error`
- ถ้า parse ไม่ได้ → `parse_error`
- **ทุกกรณีที่เรียก engine แล้วล้มเหลว ต้องมี run dir และ meta.json** เพื่อเป็นหลักฐาน
- หน้า error ต้องแสดง `run_id` และ path ของ run dir

### 7.6 การ parse CSV

`ngspice wrdata` เขียน scale ซ้ำก่อนทุก vector เช่น

```text
1.00000000e+01  9.99077690e+00  1.00000000e+01 -1.62402937e+00
```

- แต่ละแถวมี `2 * จำนวน vector` คอลัมน์
- ใช้คอลัมน์คู่ (index 0, 2, 4, ...) เป็น scale และคอลัมน์คี่เป็นค่า
- `op.csv`: 6 vectors → 12 คอลัมน์; ใช้ค่า V(4), V(6), V(5), V(5)-V(6), IC, IB
- `ac.csv`: 2 vectors (vm, vp) → 4 คอลัมน์; `vp` เป็นเรเดียน → แปลงเป็นองศา
- `tran.csv`: 2 vectors (v(2), v(7)) → 4 คอลัมน์
- ปัดค่าเฉพาะตอนแสดงผล ไม่ปัดในข้อมูลดิบ

## 8. `spice_plots.py`

- ฟังก์ชัน pure Python คืน SVG string
- `line_chart(series, x_label, y_label, log_x=False, ...)`
- AC magnitude: แกน x เป็น log frequency, แกน y เป็น dB
- AC phase: แกน x เป็น log frequency, แกน y เป็น degrees
- Transient: แกน x เป็น ms, แกน y เป็น V; มี input และ output คนละสี
- ขนาด viewBox คงที่, ใช้ `aria-label`, ไม่มี JavaScript
- ถ้าข้อมูลว่าง → คืน placeholder "ไม่มีข้อมูล"

## 9. `app.py`

### 9.1 Routes

| Route | Method | หน้าที่ |
|---|---|---|
| `/` | GET | ฟอร์มเดิม + SPICE settings (divider เท่านั้น) |
| `/calculate` | POST | Analytical เดิม (ไม่เปลี่ยน) |
| `/spice` | POST | Analytical + SPICE สำหรับ divider ตาม `analysis` |
| `/api/calculate` | POST | JSON Analytical เดิม (ไม่เปลี่ยน) |
| `/api/spice` | POST | JSON สำหรับทดสอบ engine (เพิ่มใหม่) |

### 9.2 `POST /spice`

1. ตรวจ `mode == "divider"`; ถ้าไม่ใช่ → 400 พร้อมข้อความ "SPICE v1 รองรับเฉพาะ Voltage Divider Bias"
2. ใช้ `parse_and_solve("divider", data)` เพื่อตรวจ input และได้ผล Analytical
3. อ่าน `analysis`; ต้องเป็น `dc`, `ac`, `tran` เท่านั้น
4. อ่านค่า SPICE settings และตรวจ:
   - `vin_amp_mV > 0`
   - `vin_freq_Hz > 0`
   - `0 < ac_start_Hz < ac_stop_Hz`
   - `ac_ppd` เป็นจำนวนเต็ม 1–100
   - `0 < tran_step_s < tran_stop_s`
   - `rl_kohm > 0`
5. เรียก `spice_engine.run_ngspice` เฉพาะ analysis ที่เลือก
6. สำเร็จ → render หน้าเดิมพร้อม `result` (Analytical) และ `spice` (SPICE) → HTTP 200
7. `SpiceError` → render หน้าเดิมพร้อม `result` + `spice_error` + `run_id` → HTTP 502 (timeout ใช้ 504)
8. ValidationError ของ Analytical → render หน้าเดิมพร้อม error → HTTP 400 และไม่มีผลค้าง
9. ValidationError ของ SPICE settings → render Analytical ที่ถูกต้อง + `spice_error` → HTTP 400; ไม่มีกราฟ/ค่า SPICE ค้าง

### 9.3 `POST /api/spice`

- รับ JSON object
- สำเร็จ → `{"status": "Success", "analytical": {...}, "spice": {...}}`
- validation → 400
- engine error → 502/504 พร้อม `{"status": "Error", "kind": ..., "message": ..., "run_id": ...}`

## 10. UI

### 10.1 ฟอร์ม

- คง 3 คอลัมน์เดิม
- ในคอลัมน์ Input เพิ่ม `<details>` "SPICE Settings" เฉพาะ `mode == 'divider'`:
  - Source amplitude (mV)
  - Source frequency (Hz)
  - AC start/stop (Hz)
  - AC points/decade
  - Transient stop (ms)
  - Max step (µs)
  - Load resistor (kΩ)
- เพิ่ม Analysis Mode selector: **DC / AC / Transient** (radio หรือ segmented control แบบ server-rendered)
- ปุ่มเดิม: "Calculate DC Bias" → `/calculate`
- ปุ่มใหม่: "Run Simulation" → `/spice` พร้อม `analysis` ที่เลือก
- ไม่ใช้ JavaScript ในการสลับ/คำนวณ

### 10.2 ผลลัพธ์

- คงการ์ด "DC Bias Results — ..." เดิม และเพิ่มป้าย **Analytical (dc_bias.py)**
- เพิ่ม section ใหม่เต็มความกว้างใต้ 3 คอลัมน์: **SPICE Results — CE Voltage Divider (ngspice 47)**
  - Status badge: Success / Error / Not run
  - Engine info: version, run id, duration, analysis, model + model_source
  - DC mode: DC table V_B, V_E, V_C, V_CE, I_B, I_C, I_E พร้อมหน่วย
  - Cross-check table: Analytical vs SPICE vs Δ (แยกคอลัมน์และป้าย)
  - AC mode: AC magnitude (dB) และ phase (degrees)
  - Transient mode: input/output (V vs ms)
  - `<details>` netlist
  - `<details>` engine log / warnings
  - path ของ saved run
- ถ้าโหมดไม่ใช่ divider → แสดง note ว่า v1 รองรับเฉพาะ Voltage Divider และไม่มีปุ่ม SPICE
- ถ้า error → แสดง badge แดงพร้อม kind/message/run id และไม่แสดงกราฟ/ค่าค้างจาก run ก่อน
- ถ้าใช้ provisional model → แสดง warning ชัดเจนว่า Starter Kit model ยังไม่ถูกใช้

### 10.3 หลักฐาน

- แสดง `run_id` และ path `instance/spice_runs/<run_id>/`
- เก็บ `circuit.cir`, `request.json`, `meta.json`, `ngspice.log`, และ CSV ของ analysis ที่รัน
- `instance/` ถูกเพิ่มใน `.gitignore`
- ไม่ลบ run อัตโนมัติใน v1
- หน้า error ต้องแสดง run id/path ถ้ามี run dir

## 11. เทสต์

### 11.1 Unit tests

- `find_ngspice` คืน path จาก `NGSPICE_BIN` และจาก PATH
- `find_model` ใช้ `SPICE_MODEL_PATH`/`models/instructor.model` และ fallback เป็น provisional
- `build_netlist` มีค่าที่คาดหมาย, ไม่มี string ดิบ, มี analysis ที่เลือกเท่านั้น
- `parse_op_csv` ค่าตรง baseline
- `parse_ac_csv` แปลง rad → degree ถูกต้อง และมีจุดครบ
- `parse_tran_csv` มีเวลา/input/output ครบ
- `parse_*` กับไฟล์ว่าง/รูปแบบผิด → `SpiceError`
- `run_ngspice` timeout (mock subprocess)
- `run_ngspice` exit code ผิด (mock)
- `run_ngspice` ไฟล์ผลหาย (mock)
- failed run ต้องมี run dir + meta.json และ `SpiceError.run_id`

### 11.2 Flask tests

- `POST /spice` โหมด dc สำเร็จ → 200, มี "SPICE", "ngspice", "Analytical", "run_id"
- `POST /spice` โหมด ac สำเร็จ → 200 และมีกราฟ AC
- `POST /spice` โหมด tran สำเร็จ → 200 และมีกราฟ Transient
- `POST /spice` ด้วยโหมด fixed → 400
- `POST /spice` ด้วย `analysis=all` → 400
- `POST /spice` ด้วย `vin_freq_hz=0` → 400, Analytical แสดง, ไม่มีกราฟ SPICE ค้าง
- `POST /spice` เมื่อ ngspice ไม่อยู่ → 502 และหน้าเว็บไม่ล่ม
- `POST /spice` ต้องยังแสดง Analytical แม้ SPICE error
- `POST /api/spice` สำเร็จ → JSON มี `analytical` และ `spice`
- เทสต์เดิม 25 รายการต้องผ่านทั้งหมด

### 11.3 Integration tests

- ต้องรันกับ ngspice จริงใน environment ที่มี `ngspice_con`; ถ้าไม่มีให้ skip และรายงาน NOT RUN (ไม่นับ PASS)
- รัน baseline จริงและตรวจ:
  - `ic_mA` ต่างจาก Analytical ไม่เกิน 0.05 mA
  - `vce_V` ต่างไม่เกิน 0.1 V
  - AC มีจุด > 10 และ midband gain อยู่ในช่วง 1.5–2.0 V/V (baseline ไม่มี CE)
  - Transient มีจุด > 100
- ต้องมี evidence run id และ artifact path

### 11.4 Browser acceptance B1–B8

ใช้ OpenCode Browser (Playwright MCP ยังไม่มี):

| Case | Action | ตรวจ |
|---|---|---|
| B1 | เปิด Fixed/Emitter/Divider ใส่ค่าจาก Lab 3 | ผล Analytical เดิมตรง baseline และสลับโหมดได้ |
| B2 | เลือก Divider + Run DC | เห็น V_B/V_E/V_C/V_CE/I_C จาก ngspice, model, run status |
| B3 | เปลี่ยน RE ค่าเดียวแล้ว Run DC ซ้ำ | ค่า operating point เปลี่ยนตาม run ใหม่ ไม่ค้างค่าเดิม |
| B4 | Run AC | Bode magnitude/phase พร้อมแกน/หน่วยและค่าจาก run จริง |
| B5 | Run Transient 10 mV peak 1 kHz | Vin/Vout ตามเวลา, มีแกน ms/V, เห็นการกลับเฟส |
| B6 | เปลี่ยน amplitude/frequency แล้ว Run Transient ซ้ำ | waveform เปลี่ยนตามค่าใหม่ ไม่ใช่กราฟ hard-code |
| B7 | ใส่ RE = 0 | error 400, ไม่มีผลสำเร็จปลอม/กราฟค้าง |
| B8 | Desktop + mobile viewport | กราฟ/หน่วย/ปุ่มอ่านง่าย ไม่ถูกตัด |

หลักฐาน: `docs/validation.md` (เพิ่ม section B1–B8) + ภาพใน `docs/evidence/` (ถ้าจับภาพได้)
Playwright MCP = NOT RUN ถ้าไม่มี; ห้ามอ้างว่าเป็นผล Playwright MCP

## 12. ไฟล์ที่แตะ

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `spice_engine.py` | ใหม่ — netlist, subprocess, parser, artifacts, model discovery |
| `spice_plots.py` | ใหม่ — SVG charts |
| `app.py` | เพิ่ม validation, `/spice`, `/api/spice`, ส่งข้อมูลไป template |
| `templates/index.html` | เพิ่ม SPICE settings, analysis selector, ผลลัพธ์, กราฟ, netlist |
| `tests/test_spice_engine.py` | ใหม่ |
| `tests/test_spice_plots.py` | ใหม่ |
| `tests/test_app.py` | เพิ่มเทสต์ route ใหม่ |
| `README.md` | วิธีใช้ SPICE, ngspice/PATH, model, requirements |
| `.gitignore` | เพิ่ม `instance/` |
| `docs/validation.md` | เพิ่ม B1–B8 + evidence |
| `docs/superpowers/specs/2026-11-24-lab4-spice-design.md` | เอกสารนี้ |

## 13. ความเสี่ยงและการลดความเสี่ยง

| ความเสี่ยง | การลด |
|---|---|
| ngspice บน Windows เป็น GUI | บังคับใช้ `ngspice_con.exe`; แจ้ง error ชัดเจน |
| PATH ของ process เก่าไม่มี ngspice | README ให้เปิด terminal ใหม่ หรือตั้ง `NGSPICE_BIN`; integration test ต้องรันจริง |
| Starter Kit/model ไม่มี | ใช้ provisional model + badge เตือน; รับ model ผ่าน `SPICE_MODEL_PATH`; ไม่กล่าวอ้างว่า verified |
| ค่าจาก SPICE ต่างจาก Analytical | แยก provenance + cross-check + ระบุ model |
| netlist ผิดเพราะ topology | ใช้ netlist ที่ทดลองแล้ว; unit test ค่าใน netlist |
| CSV format เปลี่ยน | parser แยกตามจำนวน vector; test ด้วยไฟล์จริง |
| timeout | 15 s + kill + error 504 + run artifacts |
| path traversal | `run_id` สร้างฝั่ง server; ไม่รับชื่อไฟล์จากผู้ใช้ |
| graph code ทำให้ template ซับซ้อน | แยก `spice_plots.py` + test SVG |
| Playwright MCP/Impeccable ไม่มี | ใช้ OpenCode Browser; รายงาน NOT RUN ตามจริง |
| รัน 3 analysis พร้อมกันทำให้ parse ผิด | Analysis Mode selector + netlist เฉพาะ mode |

## 14. ผลตรวจเครื่องมือและ Starter Kit (2026-11-24)

| รายการ | ผล |
|---|---|
| Git + GitHub | `main...origin/main` sync; Lab 3 commit `6dee8fa`; มี untracked design doc และสำเนา validation เก่า |
| Python + Flask | Python 3.12.7; Flask 3.1.3; Flask PID 2752; `GET /` = 200; title `Lab 03` |
| เทสต์เดิม | 25 tests OK (exit 0) |
| ngspice | ngspice 47 ติดตั้งที่ `%LOCALAPPDATA%\ngspice\47\Spice64\bin`; `ngspice_con -v` ใช้งานได้ |
| PATH | User PATH มี bin แล้ว; shell เก่าของ OpenCode ยังไม่เห็น ต้อง set fresh PATH/`NGSPICE_BIN` |
| OpenCode + Superpowers | OpenCode v2.2.6; plugin superpowers โหลดได้ |
| Playwright MCP | `No MCP servers configured`; ไม่มี node/npx → NOT RUN |
| Impeccable | ไม่พบ skill; ไม่มี node/npx → NOT RUN |
| ใบงาน Lab 04 | พบ `Lab04_BJT_Amplifier_Simulator_2-2569.html` ใน Downloads (2 สำเนา hash ตรงกัน) |
| Starter Kit | **ไม่พบ** netlist/model/adapter/spice_engine.py จากผู้สอน |
| BJT model | ยังไม่มี instructor model; ใช้ provisional generic model สำหรับ local test เท่านั้น |

## 15. สิ่งที่ยังต้องรอ/ตัดสินใจภายหลัง

- Starter Kit: BJT model, netlist/adapter ที่ instructor verify
- ค่า tolerance ที่ผู้สอนต้องการสำหรับ Lab 4
- จะติดตั้ง Playwright MCP/Impeccable หรือไม่ (ต้องมี Node.js; แยกงาน)
- จะเพิ่ม SPICE สำหรับ Fixed/Emitter หรือ Emitter Bypass ในรุ่นถัดไปหรือไม่

## 16. Decisions จาก builder check

1. **Real run เป็น gate** — integration test ที่ skip ไม่นับ PASS; ต้องรันจริงและเก็บ run id/artifacts
2. **Failed run เก็บหลักฐาน** — สร้าง run dir ก่อนเรียก ngspice, เขียน meta.json ใน `finally`, `SpiceError` มี `run_id`
3. **SPICE settings ผิด** — แสดง Analytical ที่ถูกต้อง + SPICE error; Analytical ผิดจึงแสดงตารางว่าง
4. **Analysis แยก mode** — ไม่รันทั้งสามในคำขอเดียว; ใช้ selector ตามใบงาน
5. **Baseline ไม่มี CE** — ตามใบงาน; CE เป็นงานต่อยอด
6. **Model มี provenance** — instructor model ถ้ามี; provisional model ต้องมี badge เตือน

## 17. ลำดับการทำหลังอนุมัติ

1. เขียนแผนงาน (`writing-plans`)
2. เตรียม environment: ตรวจ `ngspice_con`, ตั้ง `NGSPICE_BIN` ถ้าจำเป็น, ตรวจ model
3. `spice_engine.py` + unit tests (dc/ac/tran, errors, artifacts)
4. `spice_plots.py` + tests
5. `app.py` routes + tests
6. `templates/index.html` UI + analysis selector
7. Integration test กับ ngspice จริง
8. Browser acceptance B1–B8 + `docs/validation.md`
9. อัปเดต README/.gitignore
10. ตรวจ `git status`, tests, แล้ว commit/push ตามคำสั่ง
