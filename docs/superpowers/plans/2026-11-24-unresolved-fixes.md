# Close remaining Impeccable audit findings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear every unresolved audit issue while preserving calculations, modes, plots and units.

**Architecture:** Mode-aware request validation in `app.py`, accessible SVG generation in
`spice_plots.py`, and template-only UX affordances (error focus, loading state, language,
provisional gloss, detector copy/contrast cleanup) in `templates/index.html`.

**Tech Stack:** Flask/Jinja2, server-rendered SVG, unittest, Playwright MCP, Impeccable detector.

**Spec:** `docs/superpowers/specs/2026-11-24-unresolved-fixes-design.md`

## Global Constraints

- Modify only `app.py`, `spice_plots.py`, `templates/index.html` and existing tests.
- Do not change formulas in `dc_bias.py`, netlist construction in `spice_engine.py`, data, units or modes.
- Keep the suite at 71 tests.
- Verify on the live Flask server with Playwright at 1280×886 and 390×844.

## Review Focus

- Empty AC/transient fields while analysis is dc or tran: run succeeds with documented defaults.
- Invalid AC fields while analysis is ac: still rejected with the same message.
- SVG consumed by a screen reader: root has a meaningful label; no invalid `height="auto"`.
- Failed submit: error card receives focus and is scrolled into view without losing its text.
- Slow ngspice run: loading state appears before navigation and disappears on the result page.

---

### Task 1: Mode-aware SPICE validation

**Files:** Modify `app.py:90-151`, `tests/test_app.py:204-213`

- [x] **Step 1: Revise the two existing tests to the new contract** — AC settings rejected only under `analysis="ac"` and ignored with defaults under dc; transient settings rejected only under `analysis="tran"`.
- [x] **Step 2: Run those tests and watch them fail for the expected reason** — RED: `ไม่พบค่า AC stop` / `ไม่พบค่า Transient stop`.
- [x] **Step 3: Implement validation branches and SI defaults in `parse_spice_request`.**
- [x] **Step 4: Run the full 71-test suite and confirm PASS** — `Ran 71 tests ... OK`.
- [x] **Step 5: Verify via Flask test client that dc with empty ac/tran fields returns 200** — covered by the updated unit tests; live browser check in Task 4.

### Task 2: Accessible SVG root

**Files:** Modify `spice_plots.py:64-66`, `tests/test_spice_plots.py:7-17`, `tests/test_app.py:368-376`

- [x] **Step 1: Add assertions for `aria-label="Voltage (V) versus Time (ms); series: Vout"` and absence of `height="auto"` to the plot test.
- [x] **Step 2: Run it and watch it fail because the SVG lacks both** — RED: 2 failures.
- [x] **Step 3: Emit an escaped aria-label from x/y labels and series names, and a numeric height.
- [x] **Step 4: Run the full 71-test suite and confirm PASS** — `Ran 71 tests ... OK`.

### Task 3: Template UX and detector cleanup

**Files:** Modify `templates/index.html`, `tests/test_app.py:333-336,356-366`

- [x] **Step 1: Add assertions for `lang="th"`, `id="sim-loading"`, `tabindex="-1"` on error cards, provisional gloss text, `formnovalidate` on Calculate, and no prose em-dash beyond the seven placeholders.
- [x] **Step 2: Run them and watch them fail. RED on lang/loading/tabindex, required, gloss/count and formnovalidate.
- [x] **Step 3: Implement the loading/error-focus script, conditional `required`, `formnovalidate`, language, gloss, copy/contrast changes. Fixed two GREEN-time regressions: analysis selector leaked into fixed mode (template conditional) and neutral cards lacked tabindex (all status cards focusable).
- [x] **Step 4: Run the full 71-test suite and confirm PASS.** `Ran 71 tests ... OK`; `detect --json --changed` → `[]` exit 0.

### Task 4: Live verification and audit

- [x] **Step 1: Run `impeccable.cmd detect --json --changed`; expect zero findings/advisories. `[]` exit 0 (full scan also `[]`).
- [x] **Step 2: Reload Flask; use Playwright MCP at both viewports to assert no console errors, loading state, error focus/scroll, and real AC plots. Verified: 0 console errors on success, loading `hidden=false`, error focus `inViewport=true`, AC aria-labels + numeric heights, 1265/1265 and 375/375.
- [x] **Step 3: Run the full 71-test suite. `Ran 71 tests in 0.234s ... OK`.
- [x] **Step 4: Write the post-fix audit snapshot and report with fresh evidence. `.impeccable/audit/2026-11-24T11-24-43Z__templates-index-html.md` (18/20 Excellent).
