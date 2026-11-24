# Browser Acceptance Validation

## A1–A5 — Lab 03 Analytical (คงเดิม ผ่านแล้ว)

**ค่าพารามิเตอร์พื้นฐานที่ใช้ร่วมกันใน A1–A5:**
- $V_{CC} = 12\text{ V}$
- $R_C = 2.2\text{ k}\Omega$
- $\beta = 100$
- $V_{BE} = 0.70\text{ V}$
- **เกณฑ์การยอมรับ:** ผลต่างไม่เกิน $0.01\text{ mA}$ สำหรับ $I_C$ และ $0.02\text{ V}$ สำหรับ $V_{CE}$

| กรณี | เลือกโหมดและกรอกค่า | คาดหมายก่อนรัน | เห็นจริง | วิธีตรวจ | สถานะ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A1 · โหมดเดิม** | Divider · $R_1 = 100\text{ k}\Omega, R_2 = 22\text{ k}\Omega, R_E = 1\text{ k}\Omega$ | ผลต้องตรงกับเมื่อรัน Lab 2 ก่อนแก้ และเทียบได้กับค่าอ้างอิงเดิม<br>$I_C = 1.23\text{ mA} \cdot V_{CE} = 8.05\text{ V}$ | **$I_C$ = 1.23 mA · $V_{CE}$ = 8.05 V**<br>$V_B$ 1.94 V · $V_E$ 1.24 V · $V_C$ 9.29 V · $I_B$ 12.3 µA · $I_E$ 1.24 mA | OpenCode Browser: เปิด `?mode=divider` → กรอกค่า → กด Calculate → อ่านตารางหลังโหลด (HTTP 200) | **PASS** |
| **A2 · Fixed** | Fixed · $R_B = 1\text{ M}\Omega$ | คำนวณได้โดยไม่ต้องกรอก $R_E$<br>$I_C = 1.13\text{ mA} \cdot V_{CE} = 9.51\text{ V}$ | **$I_C$ = 1.13 mA · $V_{CE}$ = 9.51 V**<br>$V_B$ 0.70 V · $V_E$ 0.00 V · $V_C$ 9.51 V · $I_B$ 11.3 µA · $I_E$ 1.14 mA | OpenCode Browser: เปิด `?mode=fixed` (ฟอร์มไม่มีช่อง $R_E$) → กรอก $R_B$ 1 MΩ → Calculate (HTTP 200) | **PASS** |
| **A3 · Emitter** | Emitter · $R_B = 1\text{ M}\Omega, R_E = 1\text{ k}\Omega$ | มีช่องและใช้ค่า $R_E$<br>$I_C = 1.03\text{ mA} \cdot V_{CE} = 8.71\text{ V}$ | **$I_C$ = 1.03 mA · $V_{CE}$ = 8.71 V**<br>$V_B$ 1.74 V · $V_E$ 1.04 V · $V_C$ 9.74 V · $I_B$ 10.3 µA · $I_E$ 1.04 mA | OpenCode Browser: เปิด `?mode=emitter` → กรอก $R_B$ 1 MΩ, $R_E$ 1 kΩ → Calculate (HTTP 200) | **PASS** |
| **A4 · เปลี่ยนค่าเดียว** | Emitter · เหมือน A3 แต่เปลี่ยน $R_E$ เป็น $2\text{ k}\Omega$ | ทำนายก่อนรันว่า $I_C$ จะลดลงจาก A3 (เหลือประมาณ $0.94\text{ mA}$) | **$I_C$ = 0.94 mA** (ลดจาก A3 0.09 mA) · **$V_{CE}$ = 8.03 V**<br>$V_B$ 2.60 V · $V_E$ 1.90 V · $V_C$ 9.93 V · $I_B$ 9.4 µA · $I_E$ 0.95 mA | OpenCode Browser: คงค่าเหมือน A3 เปลี่ยนเฉพาะ $R_E$ = 2 kΩ → Calculate (HTTP 200) | **PASS** |
| **A5 · อินพุตผิด** | Fixed · $R_B = 0$ | มีข้อความให้แก้ $R_B$ (ต้องมากกว่า 0) เว็บไม่ล่ม และไม่แสดงผลเดิมเป็นผลของรอบนี้ | **HTTP 400** · badge แดง "Calculation Error — Fixed Bias"<br>ข้อความ "RB ต้องมากกว่า 0" · ตารางผลเป็น — ทั้ง 7 ช่อง | OpenCode Browser: เปิด `?mode=fixed` ใส่ $R_B$ = 0 → Calculate → ตรวจ badge, ตาราง และ HTTP status | **PASS** |

---

## B1–B8 — Lab 04 SPICE acceptance

**สภาพแวดล้อมที่ใช้รันจริง (verify 2026-11-24):**

| รายการ | ผลตรวจ |
| :--- | :--- |
| Git | `main...origin/main` (ก่อน push: ahead 7 commits) |
| Python / Flask | Python 3.12.7, Flask 3.1.3, Werkzeug 3.1.9 (`venv/`) |
| ngspice | ngspice 47 portable — `C:\Users\B6639761\AppData\Local\ngspice\47\Spice64\bin\ngspice_con.exe` |
| Node.js LTS | v26.13.1, npm 11.20.0, npx 11.20.0 (fresh PATH จาก Machine+User) |
| Playwright MCP | v0.0.86 + Chromium connected — ใช้จริงสำหรับ B8 desktop/mobile |
| Impeccable | 4.10.0 — `impeccable doctor` → **No drift found**, exit 0 |

**Solver / model provenance ใช้ร่วมกันทุกเคส SPICE:** `ngspice` (แสดงเวอร์ชัน `ngspice-47`), engine version field = `ngspice-47`, model source = `provisional`, model = `.model QNPN NPN (BF=<beta> IS=1e-15 VAF=100)`. ยังไม่มี Starter Kit / `models/instructor.model` จึงแสดง badge **“provisional model — Starter Kit not found”** ทุกครั้ง (Limitation: ค่า SPICE เป็น generic NPN ไม่ใช่ model ของผู้สอน)

| Case | Method | Input | Expected/Reference | Observed | Evidence | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **B1** | OpenCode Browser จริง — fresh navigation, submit `/calculate` ของแต่ละโหมด, อ่านตาราง DOM | Divider `VCC=12, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70`; Fixed `RB=1 MΩ`; Emitter `RB=1 MΩ, RE=1 kΩ` | Analytical ต้องเท่าเดิมจาก Lab 03/A1–A3 ทุกตัวเลข | Divider **VB 1.94 V, VE 1.24 V, VC 9.29 V, VCE 8.05 V, IB 12.3 µA, IC 1.23 mA, IE 1.24 mA**; Fixed **IC 1.13 mA, VCE 9.51 V**; Emitter **IC 1.03 mA, VCE 8.71 V** — ตรง A1/A2/A3 ทุกค่า | HTTP 200; `#results-table` / `.results-table` 7 แถว; SPICE section ยังเป็น `Not run` | **PASS** |
| **B2** | OpenCode Browser จริง — `/?mode=divider` → เลือก `dc` → กด **Run Simulation** → อ่านผล + ไฟล์ `meta.json`/`op.csv` | เหมือน B1 divider; analysis=`dc`, `vin_amp=10 mV`, `vin_freq=1 kHz`, sweep 10 Hz–1 MHz, 10 ppd, `tran=5 ms/10 µs`, `RL=10 kΩ` | ได้ operating point จาก ngspice จริง แยก provenance จาก Analytical; ต้องมี run status, run_id, model source | **HTTP 200**, `Success — Analysis: dc`, engine `ngspice`, duration 24 ms; **VB 1.9576 V, VE 1.2395 V, VC 9.2984 V, VCE 8.0589 V, IB 11.4476 µA, IC 1.2288 mA, IE 1.2402 mA**; Cross-check Δ ต่อ Analytical: VB +0.0154 V, VE −0.0027 V, VC +0.0041 V, VCE +0.0067 V, IB −0.8510 µA, IC −0.0011 mA, IE −0.0020 mA | **run_id `20261124-170636-38be4c07`**; `instance/spice_runs/20261124-170636-38be4c07/` (`meta.json`, `circuit.cir`, `op.csv`, `ngspice.log`); `#spice-dc-table`, `#spice-crosscheck-table`, `#spice-run-id`, `#spice-model` | **PASS** |
| **B3** | OpenCode Browser จริง — fresh navigation, เปลี่ยน **เฉพาะ RE**, run `dc` อีกครั้ง | เหมือน B2 แต่ `RE = 2.0 kΩ` | Operating point ต้องเปลี่ยนจริง; ห้ามโชว์ run_id/ค่าของรันเก่า หรือกราฟค้าง | **HTTP 200**, run ใหม่ success; **VB 2.0527 V, VE 1.3505 V, VC 10.5280 V, VCE 9.1775 V, IB 6.1684 µA, IC 0.6691 mA, IE 0.6753 mA** — เปลี่ยนจาก B2 ทุกตัว (IC 1.2288 → 0.6691 mA); run_id เก่า `...170636-38be4c07` **ไม่ปรากฏใน DOM**; ไม่มี `sim-plot` ค้าง | **run_id `20261124-170644-68664813`**; `meta.json` status Success; `#spice-dc-table` ค่ใหม่; `oldRunIdPresent=false` | **PASS** |
| **B4** | OpenCode Browser จริง — analysis=`ac`, run แล้วอ่าน SVG axes/legend + `ac.csv` | `RE=1 kΩ`, sweep 10 Hz–1 MHz, 10 points/decade | Bode magnitude/phase ต้องมีแกน Hz/dB/degree และเป็นข้อมูลจาก ngspice ไม่ใช่ Analytical | **HTTP 200**, `Success — Analysis: ac`, **51 จุด**; 2 SVG polyline; axis labels `Frequency (Hz)`, `Gain (dB)`, `Phase (°)`; headings `Gain magnitude (dB)`, `Phase (degrees)`; ที่ 1 kHz จาก CSV: **gain 1.7485 dB, phase −179.8662°**; ไม่มี DC table / transient plot | **run_id `20261124-170655-1e1a7300`**; `ac.csv` 51 rows; `#spice-ac-plot`, `svg.sim-plot` ×2, legend `Gain`/`Phase` | **PASS** |
| **B5** | OpenCode Browser จริง — analysis=`tran`, 10 mV peak @1 kHz, อ่าน SVG + วิเคราะห์ `tran.csv` (phasor ที่ steady-state 2.973–5 ms) | `vin_amp=10 mV`, `vin_freq=1000 Hz`, `tran_stop=5 ms`, `step=10 µs`, `RL=10 kΩ`, `RE=1 kΩ` | กราฟ Vin/Vout vs ms ต้องแสดงและ output กลับเฟส ~180° | **HTTP 200**, `Success — Analysis: tran`; **508 จุด**, t=0–5 ms; axis `Time (ms)` / `Voltage (V)`; legend `Vin`, `Vout`; CSV: vin peak **10.015 mV**, vout peak **1.015 mV**, phase(Vout)−phase(Vin) = **175.42°** (กลับเฟส); gain ~0.0316 V/V | **run_id `20261124-170707-3c60f71f`**; `tran.csv` 508 rows; `#spice-tran-plot`, `svg.sim-plot` ×2 | **PASS** |
| **B6** | OpenCode Browser จริง — fresh navigation, เปลี่ยน amplitude + frequency แล้ว run `tran` อีกครั้ง | เหมือน B5 แต่ `vin_amp=20 mV`, `vin_freq=2000 Hz` | Waveform ต้องเปลี่ยนตามค่าใหม่จริง (ไม่ใช่กราฟเก่า) | **HTTP 200**, run ใหม่ success; netlist `VIN 2 0 DC 0 AC 1 SIN(0 0.02 2000.0)`; CSV vin peak **20.057 mV** (จาก 10.015 mV), phase diff **170.87°** ที่ 2 kHz; 508 จุด; axis/legend เหมือน B5 | **run_id `20261124-171025-97ab1b35`**; netlist ใน `#spice-netlist`; `tran.csv` 508 rows; เปรียบเทียบกับ B5 | **PASS** |
| **B7** | OpenCode Browser จริง — ตั้ง `RE = 0` แล้วกด Run Simulation; อ่าน network request + DOM | `RE = 0 kΩ`, analysis=`dc`, ค่าอื่นเหมือน B2 | ต้อง HTTP 400, มีข้อความ error, **ห้าม**มีกราฟ/ผล success ค้าง; ไม่ควรเรียก solver | **HTTP 400**; request body `...&re=0&...&analysis=dc`; badge แดง **“Calculation Error — Voltage Divider Bias / RE ต้องมากกว่า 0”**; `svg.sim-plot` = **0**, `Success — Analysis` = **0**, ไม่มี run_id ใหม่ (engine ไม่ถูกเรียก) | `browser.network.get` requestId `48f22ec4-a192-48e0-983d-2d9cd19ba9fb:221`; DOM `#status-card`, `#spice-status-card` ยังเป็น `Not run` | **PASS** |
| **B8** | **Playwright MCP** จริง (คนละ browser กับ in-app tab) — `browser_resize` desktop/mobile, evaluate layout, screenshot | Desktop `1296×886`; Mobile `390×844`; เปิด `/?mode=divider` | หน้าเว็บต้องอ่านได้และฟอร์ม SPICE ยังใช้งานได้ทั้ง 2 viewport; ต้องมีหลักฐาน screenshot | Desktop: wrapper **1080 px**, grid **342/327/312 px**, h1 ถูกต้อง, SPICE controls แสดง; Mobile: wrapper **343 px**, grid **285 px** (single column), SPICE controls แสดง; overflow เล็กน้อย 2 px จาก course badge (scrollWidth 377 vs clientWidth 375) และตาราง A1–A5 ใช้ `.table-scroll` แยก — ไม่บังฟอร์ม/กราฟ | `docs/evidence/lab4/b8-desktop.png` (192267 bytes), `docs/evidence/lab4/b8-mobile.png` (126709 bytes); `playwright browser_evaluate` ทั้ง 2 viewport | **PASS** (มีข้อสังเกตเรื่อง overflow 2 px) |

## หมายเหตุเพิ่มเติม

- ทุกเคส B2–B6 รันด้วย `ngspice_con -b` จริง ผ่าน `subprocess.run([...], cwd=instance/spice_runs/<run_id>, timeout=15, shell=False)` และมี `meta.json` ทุกครั้ง รวมรันที่ล้มเหลว (พบจาก unit test `test_timeout_keeps_run_dir_and_meta`)
- ผล SPICE มาจาก `spice_engine.py` parser ที่อ่าน CSV เท่านั้น; `app.py` ไม่คำนวณ AC/transient และ browser ไม่คำนวณแกนฟิสิกส์ (SVG ถูก render จาก `spice_plots.py`)
- Integration test จริง `RunTests.test_run_dc_with_real_ngspice` รันผ่าน (ไม่ skip) และชุดทดสอบทั้งหมด `Ran 66 tests ... OK` ก่อน Task 8
- Limitation หลัก: ยังใช้ provisional BJT model เพราะไม่มี Starter Kit/instructor model — ผล SPICE ถูกต้องสำหรับ model ที่ใช้ แต่ไม่เทียบตรงกับ model ของผู้สอนได้
