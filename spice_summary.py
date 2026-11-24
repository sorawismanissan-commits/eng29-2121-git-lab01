"""Pure summary values for the engineering-results dashboard column.

The helper never runs a simulation and never recomputes circuit physics.  It
only reorganises values that ``app.py`` already received from ``dc_bias`` and
from the parsed ngspice CSV files, so the template can stay presentation-only.
"""

from math import atan2, cos, degrees, hypot, isfinite, log10, sin


_DC_ROWS = (
    ("VB", "vb_V", "V"),
    ("VE", "ve_V", "V"),
    ("VC", "vc_V", "V"),
    ("VCE", "vce_V", "V"),
    ("IC", "ic_mA", "mA"),
    ("IB", "ib_uA", "µA"),
    ("IE", "ie_mA", "mA"),
)


def _points(raw):
    """Accept either the parser's list or the ``{"points": [...]}`` wrapper."""
    if isinstance(raw, dict):
        raw = raw.get("points")
    return [p for p in (raw or []) if isinstance(p, dict)]


def _number(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) else None


def _dc_rows(spice_dc, analytical):
    rows = []
    for label, key, unit in _DC_ROWS:
        spice_value = _number((spice_dc or {}).get(key))
        analytical_value = _number((analytical or {}).get(key))
        delta = None
        if spice_value is not None and analytical_value is not None:
            delta = round(spice_value - analytical_value, 4)
            if delta == 0:
                delta = 0.0
        rows.append({
            "label": label,
            "analytical": analytical_value,
            "spice": spice_value,
            "delta": delta,
            "unit": unit,
        })
    return {"rows": rows}


def _ac_summary(raw, source_freq_Hz):
    points = []
    for point in _points(raw):
        freq = _number(point.get("freq_Hz"))
        gain = _number(point.get("gain_db"))
        phase = _number(point.get("phase_deg"))
        if freq is not None and gain is not None:
            points.append({"freq_Hz": freq, "gain_db": gain, "phase_deg": phase})
    if not points:
        return None

    points.sort(key=lambda p: p["freq_Hz"])
    source = _number(source_freq_Hz)
    if source is None or source <= 0:
        at = min(points, key=lambda p: p["freq_Hz"])
    else:
        at = min(points, key=lambda p: abs(log10(p["freq_Hz"] / source)))

    reference = max(p["gain_db"] for p in points)
    threshold = reference - 3.0
    below = [p for p in points if p["gain_db"] <= threshold]
    low = below[0]["freq_Hz"] if below else None
    high = below[-1]["freq_Hz"] if below else None
    sweep_low = points[0]["freq_Hz"]
    sweep_high = points[-1]["freq_Hz"]

    if low is not None and high is not None:
        status = f"-3 dB points within sweep ({low:g} Hz and {high:g} Hz)"
    elif low is not None:
        status = f"-3 dB edge at {low:g} Hz; upper edge outside sweep"
    else:
        status = (
            f"No -3 dB point within sweep — outside sweep "
            f"({sweep_low:g} Hz to {sweep_high:g} Hz)"
        )

    return {
        "at_freq_Hz": at["freq_Hz"],
        "gain_db": at["gain_db"],
        "phase_deg": at["phase_deg"],
        "reference_gain_db": reference,
        "threshold_db": threshold,
        "cutoff_low_Hz": low,
        "cutoff_high_Hz": high,
        "cutoff_status": status,
        "sweep_low_Hz": sweep_low,
        "sweep_high_Hz": sweep_high,
        "point_count": len(points),
    }


def _phasor(points, freq_hz):
    """Least-squares fit of ``y = a*cos(wt) + b*sin(wt)``.

    The phase is returned in the sine convention, so an inverted output is
    near +/-180 degrees relative to the input.
    """
    omega = 2 * 3.141592653589793 * (freq_hz or 0.0)
    if omega <= 0:
        return 0.0, 0.0

    scc = sss = scs = syc = sysum = 0.0
    for point in points:
        value = _number(point.get("vout_V") if point.get("_series") == "out" else point.get("vin_V"))
        if value is None:
            continue
        angle = omega * (_number(point.get("time_ms")) or 0.0) / 1000.0
        c, s = cos(angle), sin(angle)
        scc += c * c
        sss += s * s
        scs += c * s
        if point.get("_series") == "out":
            syc += value * c
            sysum += value * s
        else:
            syc += value * c
            sysum += value * s

    det = scc * sss - scs * scs
    if abs(det) < 1e-12:
        return 0.0, 0.0
    a = (syc * sss - sysum * scs) / det
    b = (sysum * scc - syc * scs) / det
    return hypot(a, b), degrees(atan2(a, b))


def _wrap_degrees(value):
    while value <= -180.0:
        value += 360.0
    while value > 180.0:
        value -= 360.0
    return value


def _tran_summary(raw, source_freq_Hz):
    points = []
    for point in _points(raw):
        time_ms = _number(point.get("time_ms"))
        vin = _number(point.get("vin_V"))
        vout = _number(point.get("vout_V"))
        if time_ms is not None and vin is not None and vout is not None:
            points.append({"time_ms": time_ms, "vin_V": vin, "vout_V": vout})
    if not points:
        return None

    points.sort(key=lambda p: p["time_ms"])
    span_ms = points[-1]["time_ms"] - points[0]["time_ms"]
    source = _number(source_freq_Hz)
    window_ms = 3000.0 / source if source and source > 0 else span_ms
    start_ms = points[-1]["time_ms"] - window_ms
    window = [p for p in points if p["time_ms"] >= start_ms] or points

    vin_peak = max(abs(p["vin_V"]) for p in window)
    vout_peak = max(abs(p["vout_V"]) for p in window)
    gain = vout_peak / vin_peak if vin_peak > 0 else None

    vin_points = [{"time_ms": p["time_ms"], "vin_V": p["vin_V"], "_series": "in"} for p in window]
    vout_points = [{"time_ms": p["time_ms"], "vout_V": p["vout_V"], "_series": "out"} for p in window]
    _vin_amp, vin_phase = _phasor(vin_points, source)
    _vout_amp, vout_phase = _phasor(vout_points, source)
    phase_diff = _wrap_degrees(vout_phase - vin_phase)
    inversion = 150.0 <= abs(phase_diff) <= 210.0

    return {
        "vin_peak_V": vin_peak,
        "vout_peak_V": vout_peak,
        "vin_peak_mV": vin_peak * 1000.0,
        "vout_peak_mV": vout_peak * 1000.0,
        "gain": gain,
        "vin_phase_deg": vin_phase,
        "vout_phase_deg": vout_phase,
        "phase_diff_deg": phase_diff,
        "inversion": inversion,
        "window_start_ms": window[0]["time_ms"],
        "window_end_ms": window[-1]["time_ms"],
        "sample_count": len(window),
    }


def build_summary(spice, result, source_freq_Hz):
    """Return display-ready DC/AC/transient summaries plus engine provenance."""
    spice = spice or {}
    dc = _dc_rows(spice.get("dc"), result) if spice.get("dc") else None
    ac = _ac_summary(spice.get("ac"), source_freq_Hz)
    tran = _tran_summary(spice.get("tran"), source_freq_Hz)

    engine = None
    if any(spice.get(key) is not None for key in (
        "engine", "engine_version", "status", "run_id", "model", "model_source"
    )):
        engine = {
            "name": spice.get("engine"),
            "status": spice.get("status"),
            "version": spice.get("engine_version"),
            "run_id": spice.get("run_id"),
            "model": spice.get("model"),
            "model_source": spice.get("model_source"),
            "duration_ms": spice.get("duration_ms"),
            "artifacts": spice.get("artifacts"),
        }

    return {"dc": dc, "ac": ac, "tran": tran, "engine": engine}
