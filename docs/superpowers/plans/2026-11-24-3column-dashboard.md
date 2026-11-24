# 3-Column Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Lab 04 UI into the handout's 3-column engineering dashboard while preserving all analytical bias modes, real ngspice runs, and data provenance; also fix SVG chart margin/label defects.

**Architecture:** Add a pure `spice_summary.py` helper that derives right-column values from already-parsed ngspice CSV data, wire it through `app.py` into the Jinja template, rebuild `templates/index.html` layout/CSS/schematic with inline server-rendered content, and adjust `spice_plots.py` gutter geometry and tick formatting. No solver, route, form field name, or physics calculation changes.

**Tech Stack:** Python 3.12.7, Flask 3.1.3, Jinja templates with inline CSS/JS, unittest, Playwright MCP, real `ngspice-47`.

**Spec:** `docs/superpowers/specs/2026-11-24-3column-dashboard-design.md`

## Global Constraints

- Do not change existing form field names: `vcc`, `r1`, `r2`, `rb`, `rc`, `re`, `beta`, `vbe`, `vin_amp_mv`, `vin_freq_hz`, `ac_start_hz`, `ac_stop_hz`, `ac_ppd`, `tran_stop_ms`, `tran_step_us`, `rl_kohm`, `analysis`, `mode`.
- Do not change `/`, `/calculate`, `/api/calculate`, `/spice`, `/api/spice` routes or the saved-run artifact format.
- Do not modify `dc_bias.py`, `spice_engine.py` netlist text, or the provisional model card `.model QNPN NPN (BF=<beta> IS=1e-15 VAF=100)`.
- Header must be navy `#103658` with white text; Run Simulation fill `#e7f3ef`, text `#13645c`; status box fill `#e7f3ef`, border `#a7cfc2`.
- Desktop target 1280×886; mobile target 390×844. No page-level horizontal overflow; plots and labels must fit their frames.
- Engine version `ngspice-47`; model name `QNPN`; model source `provisional` must remain visible in the status box.
- Baseline is 71 passing tests: `.\venv\Scripts\python.exe -m unittest discover -s tests -v`.
- No new dependencies and no mock/illustrative simulation data.

## Review Focus

- Missing or failed SPICE run: summary must show `Not run` placeholders and never stale values — pinned by `test_build_summary_handles_empty_spice` in Task 1.
- AC sweep with no -3 dB crossing: must say the cutoff is outside the sweep, not invent a frequency — pinned by `test_ac_summary_reports_no_cutoff_in_sweep` in Task 1.
- Transient phase wrap-around near -180°: must report inversion, not a +180° mismatch — pinned by `test_tran_summary_detects_inversion_with_wraparound` in Task 1.
- Non-divider analytical modes: fixed/emitter must still hide SPICE controls and keep all Lab 3 values — pinned by `test_fixed_and_emitter_modes_keep_lab3_form` in Task 4.
- Mobile clipping: at 390 px, page scrollWidth must equal clientWidth and SVG labels must fit; pinned by the Playwright check in Task 5.

---

### Task 1: Pure SPICE summary helper

**Files:**
- Create: `spice_summary.py`
- Test: `tests/test_spice_summary.py`

**Interfaces:**
- Consumes: `spice` dict from `run_ngspice()` with keys `analysis`, `dc`, `ac`, `tran`, `engine`, `engine_version`, `status`, `run_id`, `model`, `model_source`, `duration_ms`, `netlist`; analytical `result` from `parse_and_solve()`; `source_freq_Hz: float`.
- Produces: `build_summary(spice, result, source_freq_Hz) -> dict` with keys `dc`, `ac`, `tran`, `engine`. Each analysis value is `None` when unavailable.

- [ ] **Step 1: Write failing tests**

Create `tests/test_spice_summary.py` with these tests and exact expectations:

```python
from spice_summary import build_summary

def test_build_summary_handles_empty_spice():
    s = build_summary({}, None, 1000.0)
    assert s == {"dc": None, "ac": None, "tran": None, "engine": None}

def test_dc_summary_pairs_analytical_and_spice():
    spice = {"dc": {"vb_V": 1.9576, "ve_V": 1.2395, "vc_V": 9.2984,
                    "vce_V": 8.0589, "ic_mA": 1.2288, "ib_uA": 11.4476,
                    "ie_mA": 1.2402}}
    result = {"vb_V": 1.9422, "ve_V": 1.2422, "vc_V": 9.2943,
              "vce_V": 8.0522, "ic_mA": 1.2299, "ib_uA": 12.2986,
              "ie_mA": 1.2422}
    dc = build_summary(spice, result, 1000.0)["dc"]
    assert dc["rows"][0] == {"label": "VB", "analytical": 1.9422,
                             "spice": 1.9576, "delta": 0.0154, "unit": "V"}
    assert dc["rows"][4]["label"] == "IC"

def test_ac_summary_reports_no_cutoff_in_sweep():
    points = [{"freq_Hz": 10, "gain_db": 4.7, "phase_deg": -179},
              {"freq_Hz": 1000, "gain_db": 4.85, "phase_deg": -180},
              {"freq_Hz": 1000000, "gain_db": 4.84, "phase_deg": -180}]
    ac = build_summary({"ac": points}, None, 1000.0)["ac"]
    assert ac["at_freq_Hz"] == 1000
    assert ac["gain_db"] == 4.85
    assert ac["phase_deg"] == -180
    assert ac["cutoff_low_Hz"] is None
    assert ac["cutoff_high_Hz"] is None
    assert "outside sweep" in ac["cutoff_status"]

def test_tran_summary_detects_inversion_with_wraparound():
    points = [{"time_ms": i * 0.1,
               "vin_V": 0.01 * math.sin(2 * math.pi * 1000 * (i * 0.0001)),
               "vout_V": -0.0175 * math.sin(2 * math.pi * 1000 * (i * 0.0001))}
              for i in range(30)]
    tran = build_summary({"tran": points}, None, 1000.0)["tran"]
    assert abs(tran["gain"] - 1.75) < 0.1
    assert tran["inversion"] is True
    assert abs(abs(tran["phase_diff_deg"]) - 180) < 10
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.\venv\Scripts\python.exe -m unittest tests.test_spice_summary -v`
Expected: FAIL — module `spice_summary` does not exist.

- [ ] **Step 3: Implement `spice_summary.py`**

Define `build_summary(spice, result, source_freq_Hz)` and private helpers `_dc_rows`, `_ac_summary`, `_tran_summary`, `_phasor`. Use `math` only. AC: sort by `freq_Hz`; choose the point nearest `source_freq_Hz` by `abs(log10(f/source))`; reference gain is the maximum `gain_db`; threshold is `reference - 3`; low/high cutoffs are first/last point at or below threshold. Transient: select the last three source periods (`3000 / source_freq_Hz` ms) or all points when shorter; use peak absolute Vin/Vout and a single-frequency phasor fit; `inversion = 150 <= abs(phase_diff_deg) <= 210`.

- [ ] **Step 4: Run tests to verify pass**

Run: `.\venv\Scripts\python.exe -m unittest tests.test_spice_summary -v`
Expected: 4 tests OK.

- [ ] **Step 5: Commit**

```bash
git add spice_summary.py tests/test_spice_summary.py
git commit -m "feat: derive dashboard summary values from parsed SPICE data"
```

### Task 2: Wire summary into Flask render context

**Files:**
- Modify: `app.py` imports, `_render()` at ~206, successful `/spice` render call at ~301.
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `build_summary` from Task 1.
- Produces: template variable `spice_summary`, always present (all-`None` dict when no SPICE result).

- [ ] **Step 1: Write failing test**

Add to `tests/test_app.py`:

```python
def test_spice_template_receives_summary(self):
    with patch("app.run_ngspice", return_value=self.fake_spice_dc()):
        response = self.client.post("/spice", data=self.spice_form())
    self.assertEqual(response.status_code, 200)
    self.assertIn("Engine: ngspice", response.get_data(as_text=True))
    self.assertIn("DC Operating Point", response.get_data(as_text=True))
```

Use the existing fake-SPICE fixture style in the file; do not call real ngspice in this test.

- [ ] **Step 2: Run test to verify failure**

Run: `.\venv\Scripts\python.exe -m unittest tests.test_app.SpiceTemplateTests -v`
Expected: FAIL — summary text absent.

- [ ] **Step 3: Implement wiring**

Import `build_summary`; add `source_freq_Hz=None` to `_render()`; call `build_summary(spice, result, source_freq_Hz or 1000.0)` and pass `spice_summary` to `render_template`. In `/spice`, pass `source_freq_Hz=spice_request.vin_freq_Hz` on the successful render path. Leave all validation/error paths calling `_render()` without a source frequency.

- [ ] **Step 4: Run app tests**

Run: `.\venv\Scripts\python.exe -m unittest tests.test_app -v`
Expected: all `test_app` tests OK.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: pass SPICE summaries into dashboard template"
```

### Task 3: Fix SVG chart margins, zero ticks and clipping

**Files:**
- Modify: `spice_plots.py:12-126`
- Test: `tests/test_spice_plots.py`

**Interfaces:**
- Consumes: existing `line_chart(series, x_label, y_label, *, log_x=False, width=720, height=320) -> str`.
- Produces: same signature; SVG with new gutter geometry and dynamic tick anchors.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_spice_plots.py`:

```python
def test_zero_tick_is_formatted_as_zero(self):
    svg = line_chart([{"name": "Vin", "color": "#000",
                       "points": [(0, 0), (1, 0.001), (2, 0)]}],
                     "Time (ms)", "Voltage (V)")
    self.assertNotIn("1e-05", svg)
    self.assertIn(">0</text>", svg)

def test_last_x_tick_is_right_anchored(self):
    svg = line_chart([{"name": "Gain", "color": "#000",
                       "points": [(10, 1), (100, 2), (1000000, 3)]}],
                     "Frequency (Hz)", "Gain (dB)", log_x=True)
    self.assertIn('x="672.00" y="262" text-anchor="end"', svg)
    self.assertIn("1e+06", svg)

def test_y_axis_label_has_own_gutter(self):
    svg = line_chart([{"name": "Vout", "color": "#000",
                       "points": [(0, 0), (1, 1)]}], "Time (ms)", "Voltage (V)")
    self.assertIn('transform="translate(18,', svg)
    self.assertIn('x="88"', svg)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.\venv\Scripts\python.exe -m unittest tests.test_spice_plots -v`
Expected: three new tests FAIL.

- [ ] **Step 3: Implement plot fixes**

Set `left, right, top, bottom = 100, 48, 24, 80`. Draw Y ticks at `left - 12` with `text-anchor="end"`. Draw X ticks with `text-anchor` `start` for `i == 0`, `end` for `i == 4`, otherwise `middle`. Put the rotated Y label at `translate(18, top + plot_h/2)`. In tick label generation, snap `abs(value) < 1e-9` to `0`; keep `_fmt()` but avoid `.2g` for magnitudes `>= 1e-4` so readable decimals are preferred.

- [ ] **Step 4: Run plot tests and full suite**

Run: `.\venv\Scripts\python.exe -m unittest tests.test_spice_plots -v`
Expected: all plot tests OK.

Then run: `.\venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: 73+ tests OK, 0 failures.

- [ ] **Step 5: Commit**

```bash
git add spice_plots.py tests/test_spice_plots.py
git commit -m "fix: prevent SVG axis label overlap and Bode tick clipping"
```

### Task 4: Rebuild the 3-column dashboard template

**Files:**
- Modify: `templates/index.html` (CSS ~12-765, header ~770-789, left card ~795-989, circuit SVG ~991-1068, results/spice cards ~1070-1305, JS ~1393-1438)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `spice_summary` from Task 2, `spice.plots` from `_attach_plots()`, existing `values`, `result`, `mode`, `mode_labels`, `spice`, `spice_error`.
- Produces: rendered page with IDs `dashboard-header`, `circuit-schematic`, `input-parameters`, `simulation-controls`, `engineering-results`, `spice-status-box`.

- [ ] **Step 1: Write failing template tests**

Add to `tests/test_app.py`:

```python
def test_dashboard_has_three_columns_and_navy_header(self):
    html = self.client.get("/?mode=divider").get_data(as_text=True)
    for marker in ('id="dashboard-header"', 'id="circuit-schematic"',
                   'id="input-parameters"', 'id="simulation-controls"',
                   'id="engineering-results"'):
        self.assertIn(marker, html)
    self.assertIn("#103658", html)
    self.assertIn("CE Amplifier Lab", html)

def test_fixed_and_emitter_modes_keep_lab3_form(self):
    for mode in ("fixed", "emitter"):
        html = self.client.get("/?mode=" + mode).get_data(as_text=True)
        self.assertIn('name="rb"', html)
        self.assertNotIn("Run Simulation", html)
        self.assertIn('href="/?mode=divider"', html)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.\venv\Scripts\python.exe -m unittest tests.test_app.SpiceTemplateTests -v`
Expected: new tests FAIL.

- [ ] **Step 3: Rebuild template**

Replace the header markup with `#dashboard-header`, navy background and white text. Keep `.grid-container` but relabel columns: left `Circuit & Parameters` with expanded schematic above grouped inputs; center `Simulation & Plots` with `DC`, `AC`, `Transient` radios at top and plot cards below; right `Engineering Results` with three separated summary sections and `#spice-status-box`. Keep all existing form field names, form actions, mode links, error badges and `#spice-*` IDs used by tests. Add responsive rules so the grid stacks below 920 px and mobile padding shrinks below 520 px. Keep the submit JS but update the loading text only if needed.

- [ ] **Step 4: Run full test suite**

Run: `.\venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: all tests OK, including the two new template tests and all previous acceptance-related tests.

- [ ] **Step 5: Commit**

```bash
git add templates/index.html tests/test_app.py
git commit -m "feat: rebuild UI as three-column engineering dashboard"
```

### Task 5: Verify real runs, desktop/mobile and chart fixes

**Files:**
- Modify: `docs/validation.md` (append refactor verification section only; do not erase B1–B8 history)
- Screenshots: `docs/captures/refactor-desktop-*.png`, `docs/captures/refactor-mobile-*.png`

**Interfaces:**
- Consumes: completed app from Tasks 1–4 and running Flask server at `http://127.0.0.1:5000/`.
- Produces: honest verification evidence and updated report.

- [ ] **Step 1: Confirm server and baseline**

Run `GET http://127.0.0.1:5000/` and require HTTP 200. Run the full unittest suite and require zero failures.

- [ ] **Step 2: Playwright desktop verification**

Using Playwright MCP at 1280×886: navigate `/?mode=divider`, snapshot, capture `b8`-style layout metrics, screenshot to `docs/captures/refactor-desktop-divider.png`; then run real DC, AC and transient analyses and screenshot `refactor-desktop-dc.png`, `refactor-desktop-ac.png`, `refactor-desktop-tran.png`. Assert no page-level overflow, button height at least 44 px, `svg.sim-plot` count matches the selected analysis, and axis labels are present.

- [ ] **Step 3: Playwright mobile verification**

Resize to 390×844 and repeat the divider/fixed/emitter and AC checks. Assert `document.documentElement.scrollWidth === clientWidth`, plot SVGs fit their `.plot-frame`, and buttons remain readable/tappable. Save `refactor-mobile-divider.png`, `refactor-mobile-fixed.png`, `refactor-mobile-emitter.png`, `refactor-mobile-ac.png`.

- [ ] **Step 4: Cross-check real ngspice values**

For each successful run, read `meta.json` and the matching CSV from `instance/spice_runs/<run_id>/`; confirm right-column DC/AC/transient summary values match the saved data and that the transient series remain distinct (~1.75× gain, ~180° inversion).

- [ ] **Step 5: Report and commit docs**

Append a short refactor verification section to `docs/validation.md` with date, run IDs, screenshots, layout metrics and any limitations. Commit only the report and new screenshots:

```bash
git add docs/validation.md docs/captures/refactor-*.png
git commit -m "docs: record dashboard refactor verification"
```
