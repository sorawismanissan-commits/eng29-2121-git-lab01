import math

from flask import Flask, jsonify, render_template, request

from dc_bias import (
    calculate_divider_bias,
    calculate_emitter_bias,
    calculate_fixed_bias,
)

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


def _render(mode, values, result=None, error=None, status_code=200):
    return (
        render_template(
            "index.html",
            mode=mode,
            mode_label=MODE_LABELS[mode],
            mode_labels=MODE_LABELS,
            values=values,
            result=result,
            error=error,
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
