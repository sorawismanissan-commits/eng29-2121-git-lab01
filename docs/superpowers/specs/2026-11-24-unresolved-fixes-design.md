# Close remaining Impeccable audit findings — design

Intent: finish the six unresolved items from the 2026-11-24 audit without changing any
calculation, mode choice, plot data or unit. Users should only enter values relevant to
the analysis they run, get accessible real plots, and always see errors and progress.

Non-goals: no redesign, no new framework, no placeholder art, no backend solver changes.

Constraints:
- Files allowed: `app.py`, `spice_plots.py`, `templates/index.html`, and existing tests.
- The running Flask app at `http://127.0.0.1:5000/?mode=divider` is the verification target.
- Keep the unittest suite at 71 tests; revise tests that encode the old behavior.

Approaches considered:
1. Skip validation only for fields absent from the netlist for the selected analysis
   (chosen: smallest behavior change, keeps DC/source/load validation intact).
2. Drop all SPICE validation when analysis is dc (rejected: `build_netlist` still renders
   source amplitude/frequency and load resistor for DC, so missing values would break runs).
3. Validate every field but supply silent defaults (rejected: hides genuine input errors).

Implementation decisions:
- `parse_spice_request` validates AC fields only for `analysis == "ac"` and transient
  fields only for `analysis == "tran"`. Unused fields take fixed SI defaults equal to the
  form defaults already shown in the UI. Source, load and DC bias fields remain required
  for every analysis.
- `line_chart` emits `aria-label="<y label> versus <x label>; series: <names>"` and a
  numeric `height` attribute; CSS keeps responsive `height:auto` behavior.
- Template: `lang="th"`; `tabindex="-1"` on error cards plus a small DOM-ready script that
  focuses/scrolls the first visible `.badge-danger`; hidden `aria-live` loading card shown
  on submit with native validation preserved; `required` on AC/transient inputs toggled by
  the selected analysis so Calculate DC Bias and DC runs do not demand unused values;
  short provisional gloss next to `Model source`; prose em-dashes replaced with Thai
  punctuation while keeping the seven `—` result placeholders the tests assert;
  green badge text darkened to pass contrast.
