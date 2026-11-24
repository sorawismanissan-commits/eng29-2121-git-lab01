# Design: 3-column engineering dashboard for Lab 04

Date: 2026-11-24

## Intent

The Lab 4 handout specifies a 3-column engineering dashboard. The current page uses a 3-column grid, but the columns are Inputs / Circuit / Results, and the circuit graphic is only a DC bias sketch. The goal is to refactor the UI to the requested wireframe while preserving all working Lab 3 analytical bias modes and all real `ngspice` simulations.

## Goals

- Desktop (~1280 px): navy top header plus three columns — Circuit & Parameters, Simulation & Plots, Engineering Results.
- Mobile (~390 px): the columns stack cleanly with no clipped controls, plots, units or buttons.
- Left column: complete CE voltage-divider schematic (VCC, R1, R2, RC, RE, Q1 NPN, Cin, Cout, RL, Vin, Vout, GND), grouped circuit/source inputs, accessible Lab 3 bias-mode selector, and a prominent full-width Run Simulation button.
- Center column: DC / AC / Transient selector at the top and real server-rendered `ngspice` plots in clean plot cards.
- Right column: stacked DC / AC / transient summaries with analytical reference values, a -3 dB cutoff status, and a bottom engine/status box.
- Keep every existing form field name, route, netlist line, parser and analytical equation intact.
- Fix SVG chart margin/label defects and add regression coverage for the transient series mapping.

## Non-goals

- No new solver, no mock or illustrative curves, and no client-side recomputation of physics.
- No change to Lab 3 bias formulas, validation rules, or the provisional BJT model provenance.
- No change to the saved-run artifact format or run_id behaviour.
- No new CSS framework or JavaScript dependency.

## Constraints

- Flask + Jinja template with inline `<style>` and a small inline `<script>`; no separate asset pipeline.
- `spice_plots.line_chart()` returns trusted SVG strings; `app._attach_plots()` builds them from parsed CSV data.
- Existing tests: 71 tests currently pass. They must continue to pass.
- Browser acceptance evidence exists for B1–B8; the refactor must not regress those behaviours.
- The instructor BJT model is absent, so `provisional` model status remains.

## Approaches considered

1. **Restyle-only.** Move existing cards around with CSS. Lowest risk, but cannot provide the requested schematic, right-column summary sections, or data-derived cutoff/phase status. Rejected.
2. **Full data-bound dashboard rebuild (chosen).** Rebuild the template into the wireframe, expand the schematic, and derive all right-column summaries server-side from the same parsed `ngspice` data that feeds the plots. Larger template diff but preserves data provenance and meets the handout.
3. **Client-side JS summaries.** Compute summary values in the browser from existing DOM/CSV text. Fewer server changes, but fragile and weaker provenance. Rejected.

## Design

### Layout and template

- Replace `.main-header` with a full-width navy bar (`#103658`) containing white `CE Amplifier Lab` on the left and `DC Bias / AC / Transient` on the right. Keep course/context text as a small secondary line if useful, without reintroducing the old light-blue badge.
- Keep the existing three-column grid at desktop widths and stack to one column below ~920 px. Use a tighter mobile breakpoint (~520 px) for padding and sticky actions.
- Left column card, titled `Circuit & Parameters`:
  - Put the expanded CE schematic SVG at the top.
  - Group DC bias fields (`VCC`, `R1`, `R2`, `RC`, `RE`, `RB`, `β`, `VBE`) by mode exactly as today.
  - Group source/load fields (`RL`, source amplitude in mV, source frequency in Hz with a kHz hint), AC sweep settings and transient settings in a compact details panel.
  - Keep the Lab 3 mode links (`divider`, `fixed`, `emitter`) visible.
  - Keep `Calculate DC Bias` for analytical modes and make `Run Simulation` the visually dominant full-width button (`#e7f3ef` fill, `#13645c` text).
- Center column card, titled `Simulation & Plots`:
  - Move the existing `DC`, `AC`, `Transient` radio tabs to the top of this card.
  - Render only the plots produced by `spice.plots` for the selected analysis; show a neutral `Not run` card otherwise.
  - Keep netlist/log details below the plots, collapsed by default.
- Right column card, titled `Engineering Results`:
  - `DC Operating Point`: real ngspice `VB`, `VE`, `VC`, `VCE`, `IC`, with Lab 3 analytical values and deltas beside them. Show `Not run` placeholders when there is no SPICE result.
  - `AC Frequency Response`: gain magnitude, phase at the source frequency, sweep range, and `-3 dB cutoff` status derived from the real AC points.
  - `Transient Response`: Vin peak, Vout peak, voltage gain, and phase-inversion status derived from the real transient points.
  - Bottom status box (`#e7f3ef` fill, `#a7cfc2` border) showing `Engine: ngspice`, live run status, `ngspice-47`, model name `QNPN`, units and provisional-model note.
  - Keep the analytical DC results table available, folded into the DC summary so Lab 3 output is not lost.

### Server-side summary data

- Add a small summary builder in `app.py` (or a new pure helper module if it stays clearer) that receives the parsed `spice` dict, analytical `result`, and source frequency.
- DC summary: format `spice.dc` and `result` side by side; no recomputation.
- AC summary:
  - sort real points by frequency;
  - report gain/phase at the point nearest the selected source frequency;
  - define midband reference as the maximum measured `gain_db`;
  - report the first and last frequencies where gain falls to `reference - 3 dB`; if no crossing exists, state `No -3 dB point within sweep` and show the sweep range.
- Transient summary:
  - use the steady-state window covering the last three source periods (or all available points when shorter);
  - compute Vin/Vout peaks and their ratio;
  - estimate phase with a single-frequency phasor fit on that window;
  - label inversion when the absolute phase difference is about `180°` (150–210° tolerance), otherwise show the measured difference.
- Pass the summary into `_render()` as `spice_summary`; the template only displays these values. No physics is calculated in Jinja or JavaScript.

### Chart fixes (`spice_plots.py`)

- Increase the left gutter from 64 to about 100 px and the right gutter from 20 to about 48 px.
- Move the rotated Y-axis label into its own gutter and anchor X tick labels dynamically: first tick `start`, last tick `end`, middle ticks `middle`, so `1e+06` cannot clip.
- Snap tick values within a small tolerance of zero to exactly `0`, and make `_fmt()` avoid scientific notation for small-but-representable tick values where practical.
- Add unit tests for zero formatting, first/last tick anchors, and non-overlapping gutter geometry.

### Transient series regression

- No node remapping is planned: `VIN ... SIN(...)` at node 2 and `RL` output at node 7 are already correct, and `parse_tran_csv()` already reads `row[1]` and `row[3]`.
- Add a test that builds the transient netlist and asserts `v(2)` / `v(7)` are the written vectors, plus a parser test that the two series differ, so the reported overlap cannot silently return.

## Files expected to change

- `templates/index.html` — layout, header, schematic, summary sections, CSS, small JS adjustments.
- `app.py` — build and pass `spice_summary`.
- `spice_plots.py` — margins, tick anchoring, zero formatting.
- `tests/test_app.py`, `tests/test_spice_plots.py`, `tests/test_spice_engine.py` — regression tests.
- `docs/superpowers/specs/2026-11-24-3column-dashboard-design.md` — this design.

## Verification outline

- Run the full unit test suite and require zero failures.
- Run real ngspice DC, AC and transient runs and cross-check the right-column summary values against `meta.json` and saved CSVs.
- Use Playwright MCP at 1280×886 and 390×844 to check layout metrics, screenshots, readable units/buttons, no page-level horizontal overflow, and no clipped/chart-label collisions.
- Re-run representative B1–B8 acceptance checks after implementation; report any regression honestly.
