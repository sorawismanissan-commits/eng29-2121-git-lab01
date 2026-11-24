# Browser Acceptance Validation

## A1–A5 — Lab 03 Analytical (historical record, unchanged)

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

## B1–B8 — Lab 04 SPICE acceptance (fresh Playwright MCP run, 2026-11-24)

### Execution method

Every B-case below was executed in a real Playwright MCP Chromium session against the running Flask app. Each case followed the required order: **Navigate → Snapshot → Select/Fill → Click → Snapshot → Read Values → Compare → Screenshot**. The Playwright MCP tool `browser_run_code_unsafe` drove actual `page.goto`, `page.locator('body').ariaSnapshot()`, `locator.fill`, `locator.check`, `locator.click`, `page.evaluate`, `page.screenshot`, and captured the real navigation `Response` status/post body. SPICE results were additionally cross-checked by reading the saved files in `instance/spice_runs/<run_id>/`.

No application code was edited before or during this acceptance run. Only this report and the screenshot files under `docs/captures/` were written.

### Verified environment and solver provenance

| Item | Verified value |
| :--- | :--- |
| Flask app | `http://127.0.0.1:5000/` — HTTP 200, title `BJT CE Amplifier Simulator`, listener PID 12236 on 127.0.0.1:5000 |
| Python / Flask | Python 3.12.7, Flask 3.1.3, Werkzeug 3.1.9 (from `venv/`) |
| Browser tooling | Playwright MCP connected Chromium; real navigations, clicks, snapshots, DOM reads and screenshots |
| ngspice binary | `C:\Users\B6639761\AppData\Local\ngspice\47\Spice64\bin\ngspice_con.exe` |
| Exact ngspice version | Banner: `ngspice-47 : Circuit level simulation program` (compiled with KLU Direct Linear Solver). App/engine version field: `ngspice-47`. |
| BJT model name | `QNPN` |
| Exact BJT model card | `.model QNPN NPN (BF=100 IS=1e-15 VAF=100)` |
| Model source | `provisional` — Starter Kit / instructor model not found; generic NPN model used. This limitation applies to all SPICE cases. |

### Acceptance results

| Case | Method | Input | Expected/Reference | Observed | Evidence | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **B1** | Playwright MCP real browser; three fresh navigations, snapshots before/after, fill, `Calculate DC Bias` click, DOM read, comparator, screenshot | Divider: `VCC=12, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70`. Fixed: same base plus `RB=1 MΩ`. Emitter: same base plus `RB=1 MΩ, RE=1 kΩ`. | Must reproduce Lab 03 A1/A2/A3 exactly; mode headings must switch. | Divider: **VB 1.94 V, VE 1.24 V, VC 9.29 V, VCE 8.05 V, IB 12.3 µA, IC 1.23 mA, IE 1.24 mA**. Fixed: **VB 0.70 V, VE 0.00 V, VC 9.51 V, VCE 9.51 V, IB 11.3 µA, IC 1.13 mA, IE 1.14 mA**. Emitter: **VB 1.74 V, VE 1.04 V, VC 9.74 V, VCE 8.71 V, IB 10.3 µA, IC 1.03 mA, IE 1.04 mA**. All comparators matched (0 mismatches); SPICE section remained `Not run`. | HTTP 200 each; 7 result rows each; aria snapshots 12,467–13,262 chars; headings `Voltage Divider Bias`, `Fixed Bias`, `Emitter Bias`; screenshots `docs/captures/b1-divider.png`, `b1-fixed.png`, `b1-emitter.png`. | **PASS** |
| **B2** | Playwright MCP real browser; fresh `/?mode=divider`, select `dc`, fill SPICE settings, `Run Simulation` click, snapshot, DOM read, artifact cross-check, screenshot | Baseline divider circuit; `vin_amp=10 mV`, `vin_freq=1000 Hz`, `ac=10 Hz…1 MHz, 10 ppd`, `tran=5 ms / 10 µs`, `RL=10 kΩ`, `analysis=dc`. | Real ngspice `.op` operating point with engine status, version, run_id and model provenance; values must match saved `op.csv`, not analytical equations. | `Success \| Analysis: dc`, engine `ngspice`, version `ngspice-47`, duration 58 ms, model `QNPN`. DOM DC table: **VB 1.9576 V, VE 1.2395 V, VC 9.2984 V, VCE 8.0589 V, IB 11.4476 µA, IC 1.2288 mA, IE 1.2402 mA**. Cross-check deltas vs analytical: VB +0.0154 V, VE −0.0027 V, VC +0.0041 V, VCE +0.0067 V, IB −0.8510 µA, IC −0.0011 mA, IE −0.0020 mA. | HTTP 200; run_id `20261124-183229-d0245cb4`; `instance/spice_runs/20261124-183229-d0245cb4/` contains `meta.json`, `circuit.cir`, `op.csv`, `ngspice.log`, `request.json`; `op.csv` raw values: VB 1.95763218, VE 1.23946122, VC 9.29835416, VCE 8.05889293, IC 1.22879744e-03 A, IB 1.14476286e-05 A; screenshot `docs/captures/b2-dc.png`. | **PASS** |
| **B3** | Playwright MCP real browser; fresh navigation, baseline filled, then **only** `RE` changed, `dc` re-run, snapshot, DOM/artifact comparison, screenshot | Same as B2 but `RE=2.0 kΩ` only. Browser form comparison showed `changedKeys=["re"]` (1.0 → 2.0). | Operating point must change from B2; run_id must be new; old run_id and stale plots must be absent. | New `Success \| Analysis: dc` run: **VB 2.0527 V, VE 1.3505 V, VC 10.5280 V, VCE 9.1775 V, IB 6.1684 µA, IC 0.6691 mA, IE 0.6753 mA**. IC changed 1.2288 → 0.6691 mA. Old run_id absent from body and post-snapshot; `#spice-run-id` count for old ID = 0; `svg.sim-plot` = 0. | HTTP 200; new run_id `20261124-183301-a234bb7c`; artifact netlist line `RE 6 0 2000.0`; `op.csv` raw VB 2.05270503, VE 1.35052729, VC 10.52798990, VCE 9.17746265, IC 6.69123767e-04 A, IB 6.16843658e-06 A; screenshot `docs/captures/b3-re-2k.png`. | **PASS** |
| **B4** | Playwright MCP real browser; fresh navigation, select `ac`, run, snapshot, SVG/DOM read, CSV cross-check, screenshot | Baseline divider, `RE=1 kΩ`, AC sweep 10 Hz…1 MHz, 10 points/decade; source 10 mV / 1 kHz. | Bode magnitude and phase must show `Frequency (Hz)`, `Gain (dB)`, `Phase (°)` and use actual ngspice AC data. At 1 kHz, magnitude from `ac.csv` is 1.74846117 V/V, i.e. **4.8531 dB**, phase −3.13925692 rad = **−179.8662°**. (The previous report's “1.7485 dB” was the linear magnitude mislabeled as dB.) | `Success \| Analysis: ac`; 51 scan points; two `svg.sim-plot` polylines with 51 points each; headings `Gain magnitude (dB)` and `Phase (degrees)`; legends `Gain`, `Phase`; SVG labels include `Frequency (Hz)`, `Gain (dB)`, `Phase (°)`. At 1 kHz: `ac.csv` row `1.00000000e+03  1.74846117e+00  1.00000000e+03 -3.13925692e+00` → 4.8531 dB, −179.8662°. No DC table or transient plot. Netlist: `ac dec 10 10.0 1000000.0` and `wrdata ac.csv vm(7) vp(7)`. | HTTP 200; run_id `20261124-183331-a2edddac`; `ac.csv` 51 rows; `ngspice.log` reports `No. of Data Rows : 51`; screenshot `docs/captures/b4-ac.png`. | **PASS** |
| **B5** | Playwright MCP real browser; fresh navigation, select `tran`, run with 10 mV / 1 kHz, snapshot, SVG/DOM read, CSV phasor analysis, screenshot | Divider baseline; `vin_amp=10 mV`, `vin_freq=1000 Hz`, `tran_stop=5 ms`, `max_step=10 µs`, `RL=10 kΩ`. | Vin/Vout waveforms vs time with `Time (ms)` and `Voltage (V)`; output inverted about 180°. With the measured AC gain ≈1.748 V/V, expected output peak ≈17.5 mV. (The previous report's 1.015 mV was inconsistent with the saved AC data.) | `Success \| Analysis: tran`; 508 points; 2 polylines with 508 points; heading `Input vs Output (V vs ms)`; legend `Vin`, `Vout`; SVG labels `Time (ms)` and `Voltage (V)`. Steady-state window 2.9828–5 ms (203 rows): vin peak **9.998 mV**, vout peak **17.491 mV**, V/V gain **1.749**, phase(Vout)−phase(Vin) = **−179.863°** (≈180° inversion). Netlist source `SIN(0 0.01 1000.0)`. | HTTP 200; run_id `20261124-183410-6bc79f78`; `tran.csv` 508 rows; `ngspice.log` reports `No. of Data Rows : 508`; screenshot `docs/captures/b5-tran.png`. | **PASS** |
| **B6** | Playwright MCP real browser; fresh navigation, baseline filled, change source amplitude and frequency, `tran` re-run, snapshot, DOM/CSV comparison, screenshot | Same as B5 but `vin_amp=20 mV` and `vin_freq=2000 Hz`. | Waveform and netlist must update dynamically; old hard-coded/mock/rundata must not appear. Expected source `SIN(0 0.02 2000.0)`, vin peak ≈20 mV, vout peak ≈35 mV, ≈180° inversion. | New `Success \| Analysis: tran` run; netlist contains `VIN 2 0 DC 0 AC 1 SIN(0 0.02 2000.0)`. Steady-state window 2.9828–5 ms: vin peak **19.992 mV** (was 9.998 mV), vout peak **34.963 mV** (was 17.491 mV), gain 1.749 V/V, phase difference **−179.932°**. 508 points, same axis/legend labels. Old B5 run_id absent from body and post-snapshot. | HTTP 200; new run_id `20261124-183501-a7735c1d`; `tran.csv` 508 rows; screenshot `docs/captures/b6-tran-20mv-2khz.png`. | **PASS** |
| **B7** | Playwright MCP real browser; fresh navigation, set `RE=0`, keep `analysis=dc`, click `Run Simulation`, capture navigation response/status, snapshot and DOM checks, screenshot | `RE=0 kΩ`, all other fields same as B2; `analysis=dc`. | HTTP 400; clear error; no fake `Success`, stale plots, result values, run_id or new solver directory. | Navigation HTTP **400**; request body contains `...&re=0&...&analysis=dc`. Red badge `Calculation Error: Voltage Divider Bias` / `RE ต้องมากกว่า 0`; all 7 analytical cells `—`; SPICE status `Not run`; `#spice-run-id` count 0; `Success` text count 0; `svg.sim-plot` 0; DC/AC/transient plot counts all 0. Run directory count after B7 = 91, latest still B6 `20261124-183501-a7735c1d` — no new run. One console error is the expected browser log for the HTTP 400 response. | `POST http://127.0.0.1:5000/spice` → 400; screenshot `docs/captures/b7-invalid-re0.png`; directory listing of `instance/spice_runs/`. | **PASS** |
| **B8** | Playwright MCP real browser; `page.setViewportSize`, fresh navigation across divider/fixed/emitter plus live AC run at each viewport, aria snapshots, layout `evaluate`, screenshots | Desktop viewport 1280×886; mobile viewport 390×844. Modes checked: divider, fixed, emitter, AC Bode plots. | Graphs, units and buttons readable with no clipping; forms and SPICE controls usable at both widths. | Desktop: viewport 1280×886, `clientWidth=scrollWidth=1265`, page overflow 0 px; buttons 44 px high (308 px wide); AC SVG 468 px inside 486 px frame (fits); axis labels `Frequency (Hz)`, `Gain (dB)`, `Phase (°)`. Mobile: viewport 390×844, `clientWidth=scrollWidth=375`, page overflow 0 px; buttons 44 px high (288 px wide); AC SVG 302 px inside 320 px frame (fits); same axis labels. The 116 off-viewport nodes on mobile are all inside the intentionally scrollable `.table-scroll` validation-history table; `overflowOutsideTable=0`. Zero console errors on the successful AC runs. | Screenshots `docs/captures/b8-desktop-divider.png`, `b8-desktop-fixed.png`, `b8-desktop-emitter.png`, `b8-desktop-ac.png`, `b8-mobile-divider.png`, `b8-mobile-fixed.png`, `b8-mobile-emitter.png`, `b8-mobile-ac.png`; Playwright `browser_evaluate` layout metrics; console check 0 errors. | **PASS** |

### Saved ngspice artifacts used as independent proof

| Case | run_id | Artifact proof |
| :--- | :--- | :--- |
| B2 | `20261124-183229-d0245cb4` | `circuit.cir` includes `.model QNPN NPN (BF=100 IS=1e-15 VAF=100)` and `wrdata op.csv v(4) v(6) v(5) v(5)-v(6) @q1[ic] @q1[ib]`; `op.csv` raw values match the DOM table after formatting; `meta.json` status `Success`, engine `ngspice`, model source `provisional`. |
| B3 | `20261124-183301-a234bb7c` | `circuit.cir` line `RE 6 0 2000.0`; new `op.csv` values differ from B2; `meta.json` status `Success`. |
| B4 | `20261124-183331-a2edddac` | `circuit.cir` has `ac dec 10 10.0 1000000.0`; `ac.csv` has 51 rows; 1 kHz row shows 1.74846117 V/V and −3.13925692 rad; `ngspice.log` reports 51 data rows. |
| B5 | `20261124-183410-6bc79f78` | `circuit.cir` has `VIN ... SIN(0 0.01 1000.0)` and `tran 0.000009999999999999999 0.005`; `tran.csv` has 508 rows; steady-state analysis gives 9.998 mV / 17.491 mV peaks and −179.863° phase difference. |
| B6 | `20261124-183501-a7735c1d` | `circuit.cir` has `VIN ... SIN(0 0.02 2000.0)`; `tran.csv` has 508 rows; steady-state peaks 19.992 mV / 34.963 mV and −179.932° phase difference. |
| B7 | none | No new run directory was created; latest artifact remains the B6 run. |

### Correction to the previous B-table

- The previous B4 cell reported `gain 1.7485 dB`. `spice_engine.py` computes `gain_db = 20 * log10(mag)` from ngspice `vm(7)`, so `1.74846117` is **linear V/V** and the correct dB value is **4.8531 dB**. The browser SVG axis and ticks (`4.73`…`4.86`) are consistent with the corrected value.
- The previous B5 cell reported `vout peak 1.015 mV`. That is inconsistent with the measured AC gain (≈1.748 V/V) and with this fresh transient run. The fresh measured value is **17.491 mV** for a 10 mV peak input, with ≈180° inversion.

### Limitation

All SPICE numbers are correct for the model actually used, but the app still uses the provisional generic NPN model because the instructor Starter Kit / model file is absent. Results therefore should not be treated as validated against the course instructor's BJT model.

### Screenshot index

- B1: `docs/captures/b1-divider.png`, `b1-fixed.png`, `b1-emitter.png`
- B2: `docs/captures/b2-dc.png`
- B3: `docs/captures/b3-re-2k.png`
- B4: `docs/captures/b4-ac.png`
- B5: `docs/captures/b5-tran.png`
- B6: `docs/captures/b6-tran-20mv-2khz.png`
- B7: `docs/captures/b7-invalid-re0.png`
- B8: `docs/captures/b8-desktop-divider.png`, `b8-desktop-fixed.png`, `b8-desktop-emitter.png`, `b8-desktop-ac.png`, `b8-mobile-divider.png`, `b8-mobile-fixed.png`, `b8-mobile-emitter.png`, `b8-mobile-ac.png`

---

## Dashboard refactor verification (2026-11-24)

Scope: verification of the 3-column engineering-dashboard refactor (commits `be0a772` … `d6e317c`, plus post-review fixes). The A1–A5 records and B1–B8 acceptance behavior remain the baseline. The pre-existing B4/B5 corrections above were deliberately retained — the refactor did not rewrite those historical findings.

### Baseline

- `GET http://127.0.0.1:5000/` → **HTTP 200** (page title `Lab 04: BJT CE Amplifier Simulator`).
- `.\venv\Scripts\python.exe -m unittest discover -s tests -v` → **Ran 83 tests, OK** (0 failures, 0 errors).
- Verification browser: Playwright MCP Chromium, real navigations/clicks at **1280×886** and **390×844**.

### Real ngspice runs in the refactored UI

| Analysis | run_id | DOM value | Independent saved-data check | Status |
| :--- | :--- | :--- | :--- | :--- |
| DC | `20261124-191500-92bf974a` | VB 1.9576 V, VE 1.2395 V, VC 9.2984 V, VCE 8.0589 V, IB 11.4476 µA, IC 1.2288 mA, IE 1.2402 mA | `op.csv` raw 1.95763218, 1.23946122, 9.29835416, 8.05889293, 1.22879744e−03 A, 1.14476286e−05 A; `meta.json` `Success`, model source `provisional`, duration 29 ms | **PASS** |
| AC | `20261124-191516-743bb7e2` | Gain @ 1000 Hz **4.85 dB**, phase @ source **−179.9°**, midband reference 4.85 dB, 10 Hz–1 MHz, 51 points, “No −3 dB point within sweep” | `ac.csv` 51 rows; 1 kHz row 1.74846117 V/V → **4.8531 dB**, phase −3.13925692 rad → **−179.866°**; `meta.json` `Success`, duration 258 ms | **PASS** |
| Transient | `20261124-191530-f9806542` | Vin peak 10.00 mV, Vout peak 17.49 mV, gain 1.749×, phase difference −179.9°, inversion detected | `tran.csv` 508 rows; steady-state peaks 9.998452 mV / 17.491627 mV → 1.7494×; fitted phase difference −179.87° (Vin ≈ −0.01°, Vout ≈ −179.87°) | **PASS** |
| AC (mobile repeat) | `20261124-191559-38576827` | Same 4.85 dB / −179.9° / 51-point summary inside the stacked mobile layout | `meta.json` `Success`, two `svg.sim-plot` charts rendered | **PASS** |

All four runs used the unchanged model card `.model QNPN NPN (BF=100 IS=1e-15 VAF=100)` with `model_source=provisional` and the unchanged `v(2)` input / `v(7)` output nodes. The transient series remain distinct and out of phase; no mock or hard-coded curves were present.

### Layout and chart-fix evidence

| Check | Desktop 1280×886 | Mobile 390×844 |
| :--- | :--- | :--- |
| Page overflow | `scrollWidth = clientWidth = 1265` (0 px) | `scrollWidth = clientWidth = 375` (0 px) |
| Grid | `369.8px 405.0px 352.2px` — Circuit & Parameters / Simulation & Plots / Engineering Results | `317px` — the three cards stack at the same x |
| Header | `rgb(16, 54, 88)` (`#103658`), `CE Amplifier Lab`, `DC Bias / AC / Transient` | same navy header, stacked text |
| Buttons | Calculate 44 px, Run Simulation 48 px; both full column width | Calculate 44 px, Run Simulation 48 px; both 283 px wide |
| AC plots (as validated) | 2 `svg.sim-plot` charts stacked, each 353 px inside a 371 px frame | 2 charts stacked, each 265 px inside a 283 px frame; no tick outside the SVG viewBox |
| Fixed / emitter forms | `name="rb"` present, no Run Simulation button | same; no horizontal overflow |

Chart-label fixes observed in the live SVG DOM: the transient zero tick now renders as `0` (not `-0.0000`) at `x=100.00, text-anchor=start`; the rightmost AC tick `1e+06` is at `x=672.00, text-anchor=end`; Y ticks sit at `x=88` while the rotated `Voltage (V)` / `Gain (dB)` title sits at `translate(18, …) rotate(-90)`, so the title no longer overlaps the tick text. Plot counts matched the selected analysis (DC 0, AC 2, transient 1).

### Screenshots and limitation

- Desktop: `docs/captures/refactor-desktop-divider.png`, `refactor-desktop-dc.png`, `refactor-desktop-ac.png`, `refactor-desktop-tran.png`
- Mobile: `docs/captures/refactor-mobile-divider.png`, `refactor-mobile-fixed.png`, `refactor-mobile-emitter.png`, `refactor-mobile-ac.png`
- Verification used DOM/geometry measurements and saved artifacts; the PNGs are retained for human visual review. The provisional-model limitation from the B-table still applies.

---

## Post-review fixes and re-verification (2026-11-24)

A read-only code review of `bcbce9b..d6e317c` produced one Important and several Minor findings. The corrections below were implemented and verified; no simulation engine, parser, netlist line, route, form field name, or analytical formula was changed.

### Fixes

- **`templates/index.html`** — the two Bode charts in the center column now stack (`.plot-grid { grid-template-columns: 1fr; }`) instead of shrinking to ~162 px in a two-up desktop grid. Axis text was enlarged to `24px` ticks / `26px` axis titles in SVG user units. The historical A7 acceptance text now shows the current `—` empty-cell glyph instead of the stale `ไม่มีค่า`.
- **`spice_summary.py`** — `-3 dB` cutoff detection now uses sign crossings between adjacent sweep points with a tolerance, so a sweep with only one edge no longer reports two boundaries. `log10` is called only for positive frequencies; a docstring note records that `engine` stays in the summary contract while the status box continues to read raw `spice` metadata so its provenance wording stays byte-identical. Redundant `_phasor` branches were removed.
- **`tests/test_spice_summary.py`** — added characterization tests for upper-edge-only and lower-edge-only sweeps and for phase behavior at the ±180° wrap: a true 180° inversion is detected, while two fitted phases of +179.94° and −179.94° are correctly treated as in phase. The reviewer's phase-wrap concern was verified against the math and rejected as a change; its behavior is now pinned by tests instead.
- **`tests/test_app.py`** — added a template regression test for the stacked plot grid and the larger axis fonts.
- **`app.py`** — no functional change. The review noted that fields for an unselected analysis are filled with form defaults during validation; this behavior predates the refactor and is required so a DC run does not need AC/transient inputs. It was left intact.

### Fresh evidence

- `.\venv\Scripts\python.exe -m unittest discover -s tests -v` → **Ran 88 tests, OK** (0 failures, 0 errors; full output in `.superpowers/sdd/2026-11-24-3column-dashboard/final-tests.log`).
- `GET http://127.0.0.1:5000/` → **HTTP 200**, page length 62061.
- Desktop 1280×886 AC run `20261124-193429-c4438298` and transient run `20261124-193451-7522e877`: `.plot-grid` resolves to a single `371.016px` column; each SVG is 353 px wide; effective CSS font sizes measure **11.8 px** for ticks and **12.7 px** for axis titles; `scrollWidth = clientWidth = 1265`.
- Mobile 390×844 AC run `20261124-193402-7363798c`: plot column 283 px, each SVG 265 px, `scrollWidth = clientWidth = 375`; the AC summary still reads 4.85 dB / −179.9° / 51 points / no −3 dB point in sweep.
- Across the final AC and transient SVGs, no tick's bounding box falls outside the 720-unit viewBox (`worstLeft = 5.2` for the transient zero tick, `worstRight = 673.3` for the rightmost Bode tick). The transient summary still reports Vin 10.00 mV, Vout 17.49 mV, gain 1.749×, phase −179.9°, with inversion detected.
- Refreshed screenshots: `docs/captures/refactor-desktop-ac.png`, `refactor-desktop-tran.png`, `refactor-mobile-ac.png` (the other five refactor captures are unchanged). As before, verification relied on live DOM geometry and saved artifacts; this model cannot visually ingest the PNGs, so they remain for human review.
