"""ngspice adapter for the Lab 04 CE voltage-divider simulator.

The module owns netlist construction, process execution, result parsing and
run artifacts.  Values crossing this boundary are SI (V, ohm, Hz, s); the
HTTP layer is responsible for converting form units.
"""

from dataclasses import dataclass
from decimal import Decimal
import math
import os
from pathlib import Path
import shutil


class SpiceError(Exception):
    """A structured failure from the ngspice integration."""

    def __init__(self, kind, message, run_id=None, artifacts=None):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.run_id = run_id
        self.artifacts = artifacts


@dataclass(frozen=True)
class SpiceRequest:
    analysis: str
    vcc_V: float
    r1_ohm: float
    r2_ohm: float
    rc_ohm: float
    re_ohm: float
    beta: float
    vbe_V: float
    vin_amp_V: float
    vin_freq_Hz: float
    ac_start_Hz: float
    ac_stop_Hz: float
    ac_ppd: int
    tran_stop_s: float
    tran_step_s: float
    rl_ohm: float


def _num(value):
    """Render a finite SI number without scientific notation in a netlist."""
    return format(Decimal(str(value)), "f")


def find_ngspice():
    env = os.environ.get("NGSPICE_BIN")
    if env:
        return env
    for name in ("ngspice_con", "ngspice_con.exe", "ngspice"):
        found = shutil.which(name)
        if found:
            return found
    raise SpiceError(
        "not_found",
        "ไม่พบ ngspice_con ใน PATH หรือตัวแปร NGSPICE_BIN — ต้องใช้ ngspice_con.exe (ไม่ใช่ ngspice.exe แบบ GUI)",
    )


def find_model(beta):
    """Return ``(model_card, source)`` for the BJT model to simulate."""
    configured = os.environ.get("SPICE_MODEL_PATH")
    project = Path("models") / "instructor.model"
    path = Path(configured) if configured else project
    source = "env" if configured else "project"
    if path.is_file():
        card = path.read_text(encoding="utf-8").strip()
        if card:
            return card, source
        raise SpiceError("model_error", f"ไฟล์ BJT model ว่าง: {path}")
    if configured:
        raise SpiceError("model_error", f"ไม่พบไฟล์ BJT model ที่ SPICE_MODEL_PATH ชี้ไปยัง: {path}")
    card = f".model QNPN NPN (BF={beta:g} IS=1e-15 VAF=100)"
    return card, "provisional"


def _csv_columns(path, expected):
    """Read `wrdata` output: each vector is preceded by its own scale column."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise SpiceError("parse_error", f"อ่านไฟล์ผลไม่ได้: {path} ({exc})") from exc
    rows = []
    for line in lines:
        if not line.strip():
            continue
        try:
            values = [float(part) for part in line.split()]
        except ValueError as exc:
            raise SpiceError("parse_error", f"ข้อมูลไม่ใช่ตัวเลขใน {path}: {line!r}") from exc
        if len(values) != expected:
            raise SpiceError(
                "parse_error",
                f"รูปแบบ {path} ไม่ตรง: คาด {expected} คอลัมน์ ได้ {len(values)}",
            )
        rows.append(values)
    if not rows:
        raise SpiceError("parse_error", f"ไฟล์ผลว่าง: {path}")
    return rows


def parse_op_csv(path):
    row = _csv_columns(Path(path), 12)[-1]
    values = row[1::2]
    return {
        "vb_V": values[0],
        "ve_V": values[1],
        "vc_V": values[2],
        "vce_V": values[3],
        "ic_mA": values[4] * 1e3,
        "ib_uA": values[5] * 1e6,
        "ie_mA": (values[4] + values[5]) * 1e3,
    }


def parse_ac_csv(path):
    points = []
    for row in _csv_columns(Path(path), 4):
        freq, mag, _scale, phase_rad = row
        points.append(
            {
                "freq_Hz": freq,
                "gain_db": 20 * math.log10(max(mag, 1e-12)),
                "phase_deg": math.degrees(phase_rad),
            }
        )
    return points


def parse_tran_csv(path):
    return [
        {
            "time_ms": row[0] * 1e3,
            "vin_V": row[1],
            "vout_V": row[3],
        }
        for row in _csv_columns(Path(path), 4)
    ]


_ANALYSIS_BLOCKS = {
    "dc": "op\nwrdata op.csv v(4) v(6) v(5) v(5)-v(6) @q1[ic] @q1[ib]",
    "ac": "ac dec {ppd} {start} {stop}\nwrdata ac.csv vm(7) vp(7)",
    "tran": "tran {step} {stop}\nwrdata tran.csv v(2) v(7)",
}


def build_netlist(request):
    if request.analysis not in _ANALYSIS_BLOCKS:
        raise SpiceError(
            "validation_error",
            f"analysis ต้องเป็น dc, ac หรือ tran เท่านั้น (ได้ {request.analysis!r})",
        )
    model_card, _source = find_model(request.beta)
    if request.analysis == "ac":
        analysis = _ANALYSIS_BLOCKS["ac"].format(
            ppd=request.ac_ppd,
            start=_num(request.ac_start_Hz),
            stop=_num(request.ac_stop_Hz),
        )
    elif request.analysis == "tran":
        analysis = _ANALYSIS_BLOCKS["tran"].format(
            step=_num(request.tran_step_s),
            stop=_num(request.tran_stop_s),
        )
    else:
        analysis = _ANALYSIS_BLOCKS["dc"]

    lines = [
        "* Lab 04 CE Voltage Divider Bias",
        f"VCC 1 0 {_num(request.vcc_V)}",
        (
            f"VIN 2 0 DC 0 AC 1 "
            f"SIN(0 {_num(request.vin_amp_V)} {_num(request.vin_freq_Hz)})"
        ),
        "CIN 2 4 10u",
        f"R1 1 4 {_num(request.r1_ohm)}",
        f"R2 4 0 {_num(request.r2_ohm)}",
        f"RC 1 5 {_num(request.rc_ohm)}",
        f"RE 6 0 {_num(request.re_ohm)}",
        "Q1 5 4 6 QNPN",
        "COUT 5 7 10u",
        f"RL 7 0 {_num(request.rl_ohm)}",
        model_card,
        "",
        ".control",
        analysis,
        ".endc",
        ".end",
        "",
    ]
    return "\n".join(lines)
