import math

from flask import Flask, jsonify, render_template, request

from dc_bias import (
    calculate_divider_bias,
    calculate_emitter_bias,
    calculate_fixed_bias,
)
from spice_engine import SpiceError, SpiceRequest, run_ngspice
from spice_plots import line_chart
from spice_summary import build_summary

app = Flask(__name__)

MODE_LABELS = {
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
    "divider": "Voltage Divider Bias",
}
DEFAULT_MODE = "divider"


class ValidationError(ValueError):
    """ข้อมูลจากฟอร์ม/API ไม่ถูกต้องตามเงื่อนไขของโหมดที่เลือก"""


def _number(data, field, label, scale=1.0):
    """อ่านค่าตัวเลขจาก data แล้วแปลงหน่วยด้วย scale (ค่าเริ่มต้นคือไม่แปลง)"""
    raw = data.get(field)
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        raise ValidationError(f"ไม่พบค่า {label}")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"ค่า {label} ต้องเป็นตัวเลข") from None
    if not math.isfinite(value):
        raise ValidationError(f"ค่า {label} ต้องเป็นตัวเลข")
    return value * scale


def _positive_resistance(data, field, label):
    """อ่านความต้านทานเป็น kΩ จากฟอร์ม แล้วคืนค่าเป็น Ω"""
    value = _number(data, field, label, scale=1_000.0)
    if value <= 0:
        raise ValidationError(f"{label} ต้องมากกว่า 0")
    return value


def parse_and_solve(mode, data):
    """แปลงหน่วย ตรวจเฉพาะช่องที่โหมดใช้ แล้วเลือกฟังก์ชันคำนวณด้วย if/elif"""
    mode = (mode or "").strip().lower()
    if mode not in MODE_LABELS:
        raise ValidationError("โหมดไม่ถูกต้อง")

    data = data or {}

    vcc = _number(data, "vcc", "VCC")
    if vcc <= 0:
        raise ValidationError("VCC ต้องมากกว่า 0")

    rc = _positive_resistance(data, "rc", "RC")

    beta = _number(data, "beta", "β")
    if beta <= 0:
        raise ValidationError("β ต้องมากกว่า 0")

    vbe = _number(data, "vbe", "VBE")
    if vbe < 0:
        raise ValidationError("VBE ต้องไม่ติดลบ")

    if mode == "fixed":
        rb = _positive_resistance(data, "rb", "RB")
        return calculate_fixed_bias(vcc, rb, rc, beta, vbe)

    elif mode == "emitter":
        rb = _positive_resistance(data, "rb", "RB")
        re = _positive_resistance(data, "re", "RE")
        return calculate_emitter_bias(vcc, rb, re, rc, beta, vbe)

    else:  # divider
        r1 = _positive_resistance(data, "r1", "R1")
        r2 = _positive_resistance(data, "r2", "R2")
        re = _positive_resistance(data, "re", "RE")
        return calculate_divider_bias(vcc, r1, r2, rc, re, beta, vbe)


ANALYSES = ("dc", "ac", "tran")

# Values for fields the selected analysis never sends to the netlist. They
# match the defaults already shown in the form, so a DC run needs no AC sweep
# or transient timing values.
_UNUSED_SPICE_DEFAULTS = {
    "ac_start_Hz": 10.0,
    "ac_stop_Hz": 1_000_000.0,
    "ac_ppd": 10,
    "tran_stop_s": 0.005,
    "tran_step_s": 0.00001,
}


def parse_spice_request(data):
    """Validate the SPICE-only fields and convert form units to SI."""
    data = data or {}
    analysis = str(data.get("analysis", "")).strip().lower()
    if analysis not in ANALYSES:
        raise ValidationError("Analysis Mode ต้องเป็น dc, ac หรือ tran เท่านั้น")

    vin_amp_V = _number(data, "vin_amp_mv", "Source amplitude", scale=1e-3)
    if vin_amp_V <= 0:
        raise ValidationError("Source amplitude ต้องมากกว่า 0")
    vin_freq_Hz = _number(data, "vin_freq_hz", "Source frequency")
    if vin_freq_Hz <= 0:
        raise ValidationError("Source frequency ต้องมากกว่า 0")

    if analysis == "ac":
        ac_start_Hz = _number(data, "ac_start_hz", "AC start")
        ac_stop_Hz = _number(data, "ac_stop_hz", "AC stop")
        if ac_start_Hz <= 0 or ac_stop_Hz <= ac_start_Hz:
            raise ValidationError("AC start ต้องมากกว่า 0 และน้อยกว่า AC stop")
        raw_ppd = _number(data, "ac_ppd", "AC points/decade")
        if raw_ppd != int(raw_ppd) or not 1 <= int(raw_ppd) <= 100:
            raise ValidationError("AC points/decade ต้องเป็นจำนวนเต็ม 1–100")
    else:
        ac_start_Hz = _UNUSED_SPICE_DEFAULTS["ac_start_Hz"]
        ac_stop_Hz = _UNUSED_SPICE_DEFAULTS["ac_stop_Hz"]
        raw_ppd = _UNUSED_SPICE_DEFAULTS["ac_ppd"]

    if analysis == "tran":
        tran_stop_s = _number(data, "tran_stop_ms", "Transient stop", scale=1e-3)
        tran_step_s = _number(data, "tran_step_us", "Transient max step", scale=1e-6)
        if tran_stop_s <= 0 or tran_step_s <= 0 or tran_step_s >= tran_stop_s:
            raise ValidationError("Max step ต้องมากกว่า 0 และน้อยกว่า Transient stop")
    else:
        tran_stop_s = _UNUSED_SPICE_DEFAULTS["tran_stop_s"]
        tran_step_s = _UNUSED_SPICE_DEFAULTS["tran_step_s"]

    rl_ohm = _number(data, "rl_kohm", "Load resistor", scale=1_000.0)
    if rl_ohm <= 0:
        raise ValidationError("Load resistor ต้องมากกว่า 0")
    vcc = _number(data, "vcc", "VCC")
    if vcc <= 0:
        raise ValidationError("VCC ต้องมากกว่า 0")
    rc = _positive_resistance(data, "rc", "RC")
    beta = _number(data, "beta", "β")
    if beta <= 0:
        raise ValidationError("β ต้องมากกว่า 0")
    vbe = _number(data, "vbe", "VBE")
    if vbe < 0:
        raise ValidationError("VBE ต้องไม่ติดลบ")
    r1 = _positive_resistance(data, "r1", "R1")
    r2 = _positive_resistance(data, "r2", "R2")
    re = _positive_resistance(data, "re", "RE")

    return SpiceRequest(
        analysis=analysis,
        vcc_V=vcc,
        r1_ohm=r1,
        r2_ohm=r2,
        rc_ohm=rc,
        re_ohm=re,
        beta=beta,
        vbe_V=vbe,
        vin_amp_V=vin_amp_V,
        vin_freq_Hz=vin_freq_Hz,
        ac_start_Hz=ac_start_Hz,
        ac_stop_Hz=ac_stop_Hz,
        ac_ppd=int(raw_ppd),
        tran_stop_s=tran_stop_s,
        tran_step_s=tran_step_s,
        rl_ohm=rl_ohm,
    )


def _attach_plots(spice):
    """Build server-rendered SVG strings for the selected analysis."""
    plots = {}
    if spice.get("analysis") == "ac" and spice.get("ac"):
        raw = spice["ac"]
        points = raw["points"] if isinstance(raw, dict) else raw
        plots["magnitude"] = line_chart(
            [{"name": "Gain", "color": "#0c8e83",
              "points": [(p["freq_Hz"], p["gain_db"]) for p in points]}],
            "Frequency (Hz)", "Gain (dB)", log_x=True,
        )
        plots["phase"] = line_chart(
            [{"name": "Phase", "color": "#c77a35",
              "points": [(p["freq_Hz"], p["phase_deg"]) for p in points]}],
            "Frequency (Hz)", "Phase (°)", log_x=True,
        )
    elif spice.get("analysis") == "tran" and spice.get("tran"):
        raw = spice["tran"]
        points = raw["points"] if isinstance(raw, dict) else raw
        plots["waveform"] = line_chart(
            [
                {"name": "Vin", "color": "#8a94a6",
                 "points": [(p["time_ms"], p["vin_V"]) for p in points]},
                {"name": "Vout", "color": "#c77a35",
                 "points": [(p["time_ms"], p["vout_V"]) for p in points]},
            ],
            "Time (ms)", "Voltage (V)",
        )
    spice["plots"] = plots
    return spice


def _render(
    mode, values, result=None, error=None, status_code=200,
    spice=None, spice_error=None, spice_analysis="dc", spice_values=None,
    source_freq_Hz=None,
):
    return (
        render_template(
            "index.html",
            mode=mode,
            mode_label=MODE_LABELS[mode],
            mode_labels=MODE_LABELS,
            values=values,
            result=result,
            error=error,
            spice=spice,
            spice_error=spice_error,
            spice_analysis=spice_analysis,
            spice_values=spice_values,
            spice_summary=build_summary(spice, result, source_freq_Hz or 1000.0),
        ),
        status_code,
    )


@app.route("/")
def index():
    mode = request.args.get("mode", DEFAULT_MODE)
    if mode not in MODE_LABELS:
        return _render(DEFAULT_MODE, {}, error="โหมดไม่ถูกต้อง", status_code=400)
    return _render(mode, {})


@app.post("/calculate")
def calculate_form():
    mode = request.form.get("mode", "")
    try:
        result = parse_and_solve(mode, request.form)
    except ValidationError as exc:
        return _render(
            mode if mode in MODE_LABELS else DEFAULT_MODE,
            request.form,
            error=str(exc),
            status_code=400,
        )
    return _render(mode, request.form, result=result)


@app.post("/api/calculate")
def calculate_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "Error", "message": "ข้อมูลต้องเป็น JSON object"}), 400

    try:
        result = parse_and_solve(data.get("mode", ""), data)
    except ValidationError as exc:
        return jsonify({"status": "Error", "message": str(exc)}), 400
    return jsonify(result)


@app.post("/spice")
def spice_form():
    data = request.form
    mode = str(data.get("mode", "")).strip().lower()
    analysis = str(data.get("analysis", "")).strip().lower()
    spice_analysis = analysis if analysis in ANALYSES else "dc"
    if mode != "divider":
        return _render(
            mode if mode in MODE_LABELS else DEFAULT_MODE,
            data,
            error="SPICE v1 รองรับเฉพาะ Voltage Divider Bias",
            status_code=400,
            spice_analysis=spice_analysis,
            spice_values=data,
        )
    try:
        result = parse_and_solve("divider", data)
    except ValidationError as exc:
        return _render(
            mode, data, error=str(exc), status_code=400,
            spice_analysis=spice_analysis, spice_values=data,
        )
    try:
        spice_request = parse_spice_request(data)
    except ValidationError as exc:
        return _render(
            mode, data, result=result, spice_error=exc, status_code=400,
            spice_analysis=spice_analysis, spice_values=data,
        )
    try:
        spice = _attach_plots(run_ngspice(spice_request))
    except SpiceError as exc:
        status_code = 504 if exc.kind == "timeout" else 502
        return _render(
            mode, data, result=result, spice_error=exc, status_code=status_code,
            spice_analysis=spice_analysis, spice_values=data,
        )
    return _render(
        mode, data, result=result, spice=spice,
        spice_analysis=spice_analysis, spice_values=data,
        source_freq_Hz=spice_request.vin_freq_Hz,
    )


@app.post("/api/spice")
def spice_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "Error", "message": "ข้อมูลต้องเป็น JSON object"}), 400
    mode = str(data.get("mode", "")).strip().lower()
    if mode != "divider":
        return jsonify({"status": "Error", "message": "SPICE v1 รองรับเฉพาะ Voltage Divider Bias"}), 400
    try:
        result = parse_and_solve("divider", data)
        spice_request = parse_spice_request(data)
    except ValidationError as exc:
        return jsonify({"status": "Error", "message": str(exc)}), 400
    try:
        spice = _attach_plots(run_ngspice(spice_request))
    except SpiceError as exc:
        status_code = 504 if exc.kind == "timeout" else 502
        return jsonify({
            "status": "Error",
            "kind": exc.kind,
            "message": exc.message,
            "run_id": exc.run_id,
            "artifacts": exc.artifacts,
        }), status_code
    return jsonify({"status": "Success", "analytical": result, "spice": spice})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
