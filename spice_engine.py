"""ngspice adapter for the Lab 04 CE voltage-divider simulator.

The module owns netlist construction, process execution, result parsing and
run artifacts.  Values crossing this boundary are SI (V, ohm, Hz, s); the
HTTP layer is responsible for converting form units.
"""

from dataclasses import dataclass
from decimal import Decimal
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
