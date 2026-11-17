# BJT DC Bias — 3 Modes Implementation Plan (server-rendered, no JS)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่มโหมด Fixed และ Emitter ใน `dc_bias.py` โดยคงวิธีคำนวณ Divider เดิม และให้ฟอร์ม Flask เลือกโหมด/แสดงช่องที่ใช้ พร้อมผลหรือ error ที่ระบุโหมด

**Architecture:** สมการทั้งหมดอยู่ใน `dc_bias.py` เป็น 3 ฟังก์ชันที่คืนคีย์ชุดเดียวกัน; `app.py` แปลง kΩ→Ω, ตรวจเฉพาะช่องของโหมด, เลือกฟังก์ชันด้วย `if/elif`, แล้วเรนเดอร์ `index.html` ผ่าน Jinja ทั้งฟอร์มและผลลัพธ์ — ไม่มี JavaScript คำนวณ

**Tech Stack:** Python 3.12.7, Flask 3.1.3, Jinja2, unittest

**Spec:** `docs/superpowers/specs/2026-11-17-bjt-multi-mode-design.md`

## Global Constraints

- ใช้ `venv\Scripts\python.exe` (Python 3.12.7, Flask 3.1.3)
- ฟอร์มเป็น kΩ; แปลงเป็น Ω ครั้งเดียวใน `app.py`
- ห้ามมีสมการใน HTML/JS
- คีย์ผลลัพธ์คงแบบ Lab 2: `vb_V, ve_V, vc_V, vce_V, ib_uA, ic_mA, ie_mA, region, message, status`
- `status` = `"Success"` หรือ `"Error"`; `region` = `Active` / `Saturation` / `Cutoff`
- โหมดไม่รู้จัก → 400 "โหมดไม่ถูกต้อง" (ห้าม fallback เป็น Divider)
- ห้าม `git add venv/` หรือ `__pycache__/`

## Review Focus

1. `beta=0` หรือค่าติดลบ → 400 และตารางผลไม่มีตัวเลขค้างจากรอบก่อน
2. `mode` ไม่รู้จัก → 400 "โหมดไม่ถูกต้อง" ไม่ถูกตีความเป็น Divider
3. ฟิลด์ที่ไม่ใช้ในโหมดนั้นมีค่าติดลบ/ไม่ใช่ตัวเลข → ต้องไม่ทำให้ error
4. Divider ต้องได้ผลเท่า baseline A1 ทุกหลัก
5. `VBE` สูงจน IB ≤ 0 → region Cutoff ไม่มีค่า NaN/ติดลบ

---

### Task 1: `dc_bias.py` — ย้าย Divider เดิม + เพิ่ม Fixed/Emitter

**Files:**
- Create: `dc_bias.py`
- Test: `tests/test_dc_bias.py`
- Modify: `app.py` (ลบ `calculate_bjt_dc_bias` ออก แล้ว import จาก `dc_bias`)

**Interfaces:**
- Produces:
  - `calculate_fixed_bias(vcc, rb, rc, beta, vbe=0.7) -> dict`
  - `calculate_emitter_bias(vcc, rb, re, rc, beta, vbe=0.7) -> dict`
  - `calculate_divider_bias(vcc, r1, r2, rc, re, beta, vbe=0.7) -> dict`
  - ทุกฟังก์ชันคืนคีย์: `status, region, message, ib_uA, ic_mA, ie_mA, vb_V, ve_V, vc_V, vce_V`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
# tests/test_dc_bias.py
import unittest
from dc_bias import calculate_divider_bias, calculate_emitter_bias, calculate_fixed_bias

KEYS = {"status", "region", "message", "ib_uA", "ic_mA", "ie_mA",
        "vb_V", "ve_V", "vc_V", "vce_V"}


class BiasTests(unittest.TestCase):
    def test_divider_keeps_lab2_baseline(self):
        r = calculate_divider_bias(12.0, 100_000.0, 22_000.0,
                                   2_200.0, 1_000.0, 100.0)
        self.assertEqual(set(r), KEYS)
        self.assertEqual(r["region"], "Active")
        self.assertAlmostEqual(r["ib_uA"], 12.2985, places=3)
        self.assertAlmostEqual(r["ic_mA"], 1.2298, places=3)
        self.assertAlmostEqual(r["vb_V"], 1.9422, places=3)
        self.assertAlmostEqual(r["vce_V"], 8.0522, places=3)

    def test_fixed_bias(self):
        r = calculate_fixed_bias(12.0, 1_000_000.0, 2_200.0, 100.0)
        self.assertEqual(set(r), KEYS)
        self.assertAlmostEqual(r["ib_uA"], 11.3, places=3)
        self.assertAlmostEqual(r["ic_mA"], 1.13, places=3)
        self.assertEqual(r["ve_V"], 0.0)
        self.assertAlmostEqual(r["vb_V"], 0.7, places=3)
        self.assertAlmostEqual(r["vce_V"], 9.514, places=3)

    def test_emitter_bias(self):
        r = calculate_emitter_bias(12.0, 1_000_000.0, 1_000.0, 2_200.0, 100.0)
        self.assertEqual(set(r), KEYS)
        self.assertAlmostEqual(r["ib_uA"], 10.2634, places=3)
        self.assertAlmostEqual(r["ic_mA"], 1.0263, places=3)
        self.assertAlmostEqual(r["vb_V"], 1.7366, places=3)
        self.assertAlmostEqual(r["vce_V"], 8.7055, places=3)

    def test_cutoff_has_no_negative_current(self):
        r = calculate_divider_bias(12.0, 100_000.0, 22_000.0,
                                   2_200.0, 1_000.0, 100.0, vbe=2.5)
        self.assertEqual(r["region"], "Cutoff")
        self.assertEqual((r["ib_uA"], r["ic_mA"], r["ie_mA"]), (0, 0, 0))
        self.assertIn("Cutoff", r["message"])

    def test_saturation_warns_and_clamps_like_divider(self):
        r = calculate_divider_bias(12.0, 100_000.0, 22_000.0,
                                   10_000.0, 100.0, 100.0)
        self.assertEqual(r["region"], "Saturation")
        self.assertAlmostEqual(r["ic_mA"], 1.1683, places=3)
        self.assertAlmostEqual(r["vce_V"], 0.2, places=3)
        self.assertIn("Saturation", r["message"])
```

- [ ] **Step 2: รันให้ล้มเหลว**

Run: `venv\Scripts\python.exe -m unittest tests.test_dc_bias -v`
Expected: ERROR `ModuleNotFoundError: No module named 'dc_bias'`

- [ ] **Step 3: สร้าง `dc_bias.py`**

- คัดลอกตัวฟังก์ชัน `calculate_bjt_dc_bias` จาก `app.py` มาเป็น `calculate_divider_bias` โดย**คงสมการทุกบรรทัด**
- เพิ่ม `message` ให้ครบทั้ง Active / Saturation / Cutoff (ข้อความตาม §5.4 ของ spec)
- เขียน `calculate_fixed_bias` และ `calculate_emitter_bias` ตามสมการในใบงาน แล้วใช้ตรรกะ region/ข้อความชุดเดียวกับ Divider
- ลบ `calculate_bjt_dc_bias` ออกจาก `app.py` และเพิ่ม `from dc_bias import ...`

- [ ] **Step 4: รันให้ผ่าน**

Run: `venv\Scripts\python.exe -m unittest tests.test_dc_bias -v`
Expected: OK (5 tests)

- [ ] **Step 5: Commit**

```bash
git add dc_bias.py app.py tests/test_dc_bias.py
git commit -m "feat: add fixed and emitter bias calculations"
```

---

### Task 2: `app.py` — parse ตามโหมด, dispatch, routes

**Files:**
- Modify: `app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: ฟังก์ชันทั้งสามจาก Task 1
- Produces:
  - `MODE_LABELS = {"divider": "Voltage Divider Bias", "fixed": "Fixed Bias", "emitter": "Emitter Bias"}`
  - `class ValidationError(ValueError)`
  - `parse_and_solve(mode: str, data: Mapping[str, str]) -> dict` (แปลง kΩ→Ω, ตรวจเฉพาะช่องที่ใช้, เรียกฟังก์ชันตาม mode)
  - `GET /?mode=...` → HTML 200; mode ไม่รู้จัก → 400
  - `POST /calculate` → HTML 200 เมื่อสำเร็จ, 400 เมื่อ error
  - `POST /api/calculate` → JSON 200/400

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
# tests/test_app.py
import unittest
from app import app

FORM = {"mode": "divider", "vcc": "12", "r1": "100", "r2": "22",
        "rc": "2.2", "re": "1.0", "beta": "100", "vbe": "0.70"}


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_default_shows_divider_fields(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn('name="r1"', res.get_data(as_text=True))
        self.assertNotIn('name="rb"', res.get_data(as_text=True))

    def test_get_fixed_shows_only_rb(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertIn('name="rb"', body)
        self.assertNotIn('name="r1"', body)
        self.assertNotIn('name="re"', body)

    def test_unknown_mode_is_an_error(self):
        res = self.client.get("/?mode=hbridge")
        self.assertEqual(res.status_code, 400)
        self.assertIn("โหมดไม่ถูกต้อง", res.get_data(as_text=True))

    def test_post_calculate_renders_result(self):
        res = self.client.post("/calculate", data=FORM)
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("1.23", body)
        self.assertIn("Voltage Divider", body)

    def test_post_invalid_beta_has_no_stale_result(self):
        res = self.client.post("/calculate", data={**FORM, "beta": "0"})
        self.assertEqual(res.status_code, 400)
        body = res.get_data(as_text=True)
        self.assertIn("β ต้องมากกว่า 0", body)
        self.assertNotIn("1.23", body)

    def test_json_api_matches_form_result(self):
        res = self.client.post("/api/calculate", json=FORM)
        self.assertEqual(res.status_code, 200)
        self.assertAlmostEqual(res.get_json()["ic_mA"], 1.2298, places=3)
```

- [ ] **Step 2: รันให้ล้มเหลว**

Run: `venv\Scripts\python.exe -m unittest tests.test_app -v`
Expected: FAIL (ยังไม่มี `name="mode"` / ยังไม่มี route `/calculate`)

- [ ] **Step 3: เขียน `parse_and_solve` และ routes**

- `_positive(data, field, label)` และ `_number(...)` ภายใน: แปลง kΩ→Ω เฉพาะ RC, RB, RE, R1, R2
- `if mode == "fixed": ... elif mode == "emitter": ... elif mode == "divider": ... else: raise ValidationError("โหมดไม่ถูกต้อง")`
- อ่านเฉพาะคีย์ของโหมดนั้น (ฟิลด์ซ่อนที่ค่าผิดต้องไม่ทำให้ error)
- `GET /`: `mode = request.args.get("mode", "divider")`; ถ้าไม่อยู่ใน `MODE_LABELS` → `render_template(..., error="โหมดไม่ถูกต้อง", mode="divider"), 400`
- `POST /calculate`: จับ `ValidationError` → เรนเดอร์ฟอร์มพร้อม `error` และ `values=request.form` (ไม่มี `result`)
- `POST /api/calculate`: ใช้ `parse_and_solve` แล้ว `jsonify`

- [ ] **Step 4: รันให้ผ่าน**

Run: `venv\Scripts\python.exe -m unittest tests.test_app -v`
Expected: ผ่าน 6 tests (ข้อ GET ต้องรอ Task 3 — ถ้ายังไม่ผ่าน ให้ทำ Task 3 ต่อแล้วรันซ้ำ)

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: dispatch bias mode and render results server-side"
```

---

### Task 3: `index.html` — ฟอร์มเลือกโหมดแบบไม่ใช้ JS

**Files:**
- Modify: `templates/index.html`
- Modify: `static/css/style.css`
- Delete: `static/js/script.js`

**Interfaces:**
- Consumes: `mode`, `values`, `result`, `error`, `MODE_LABELS` จาก Task 2
- Produces: HTML ที่มี `name="mode"`, ช่องตามโหมด, ตารางผลจาก server

- [ ] **Step 1: แทนที่ฟอร์มและผลลัพธ์ด้วย Jinja**

- แถบโหมด: ลิงก์ 3 อัน `?mode=divider|fixed|emitter` พร้อมไฮไลต์โหมดปัจจุบัน
- `<form method="post" action="/calculate">` + `<input type="hidden" name="mode" value="{{ mode }}">`
- ค่าทุกช่องใช้ `value="{{ values.vcc|default('12.0') }}"`
- แสดงช่องด้วย `{% if mode in ('fixed', 'emitter') %}` (RB), `{% if mode == 'divider' %}` (R1, R2), `{% if mode != 'fixed' %}` (RE)
- ตารางผล: `{% if result %}` เติมค่าด้วย `"%.2f"|format(result.vb_V)` + หน่วย; `{% else %}` แสดง `—` ทุกช่อง
- badge: `{% if result %}` เลือกคลาสจาก `result.region` และแสดง `result.message`; `{% elif error %}` คลาส `badge-danger` + `error`; `{% else %}` badge กลาง ๆ
- หัวข้อ DC Bias Results ต่อท้ายด้วย `{{ mode_label }}`
- ลบบล็อก `<script>` คำนวณเดิมทั้งบล็อก (ไม่เพิ่ม script ใหม่)

- [ ] **Step 2: ปรับ SVG ตามโหมด**

- ห่อ R2 และกราวด์ซ้ายด้วย `{% if mode == 'divider' %}` / `{% endif %}`
- ห่อ RE ด้วย `{% if mode != 'fixed' %}`
- เพิ่มเส้น emitter ลงกราวด์เฉพาะ `{% if mode == 'fixed' %}`
- ข้อความ R1: `{{ 'RB' if mode != 'divider' else 'R1' }}`; ค่าใช้ `values.rb` หรือ `values.r1`

- [ ] **Step 3: เพิ่ม CSS และลบ JS ที่ไม่ใช้**

```css
.hidden { display: none !important; }
.mode-tabs { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
.mode-tabs a { padding: 0.35rem 0.7rem; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 0.8rem; text-decoration: none; }
.mode-tabs a.active { background: #0f766e; border-color: #0f766e; color: #fff; }
```

ลบ `static/js/script.js`

- [ ] **Step 4: รันเทสต์ทั้งหมด**

Run: `venv\Scripts\python.exe -m unittest discover -s tests -t . -v`
Expected: OK (11 tests)

- [ ] **Step 5: ตรวจด้วยเบราว์เซอร์**

Run: `venv\Scripts\python.exe -m flask --app app run`
1. `/?mode=divider` กรอกค่า A1 → ผล 1.94 / 1.24 / 9.29 / 8.05 / 12.3 µA / 1.23 mA / 1.24 mA
2. `/?mode=fixed` เห็นเฉพาะ RB (ไม่มี R1/R2/RE) → ได้ VCE 9.51 V
3. `/?mode=emitter` เห็น RB + RE → ได้ VCE 8.71 V
4. β=0 → badge แดง "β ต้องมากกว่า 0" และตารางเป็น `—`
5. `/?mode=abc` → ข้อความ "โหมดไม่ถูกต้อง"

- [ ] **Step 6: Commit**

```bash
git add templates/index.html static/css/style.css
git rm static/js/script.js
git commit -m "feat: server-rendered per-mode form and results"
```

---

### Task 4: Reproducibility

**Files:**
- Modify: `requirements.txt`
- Create: `.gitignore`, `README.md`

- [ ] **Step 1: เขียนไฟล์**

`requirements.txt` → `Flask==3.1.3`
`.gitignore` → `venv/`, `__pycache__/`, `*.pyc`
`README.md` → ภาพรวม 3 โหมด, วิธีติดตั้ง/รัน/ทดสอบ, หน่วย, ตาราง A1

- [ ] **Step 2: ตรวจและรันเทสต์สุดท้าย**

Run: `git status --short` → ต้องไม่มี `?? venv/`
Run: `venv\Scripts\python.exe -m unittest discover -s tests -t . -v` → OK (11 tests)

- [ ] **Step 3: Commit**

```bash
git add requirements.txt .gitignore README.md
git commit -m "docs: add reproducible setup and usage instructions"
```

---

## Self-Review

- สมการไม่ปรากฏใน HTML/JS (Task 3 ไม่มีสูตร) — ตรงคำสั่งใบงาน
- ชื่อคีย์/หน่วยตรงกันทั้งสามฟังก์ชันและทั้งสอง route (Task 1–2)
- โหมดไม่รู้จัก/ฟิลด์ผิดมีเทสต์ทั้งใน Task 2 และการตรวจเบราว์เซอร์ Task 3
- Divider ถูกย้ายโดยคงสมการเดิม และมีเทสต์เทียบ baseline A1
