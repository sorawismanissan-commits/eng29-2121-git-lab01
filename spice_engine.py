"""ngspice adapter for the Lab 04 CE voltage-divider simulator.

The module owns netlist construction, process execution, result parsing and
run artifacts.  Values crossing this boundary are SI (V, ohm, Hz, s); the
HTTP layer is responsible for converting form units.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid


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
    candidates = ["ngspice_con", "ngspice_con.exe"]
    if os.name != "nt":
        candidates.append("ngspice")
    for name in candidates:
        found = shutil.which(name)
        if found:
            return found
    raise SpiceError(
        "not_found",
        "ไม่พบ ngspice_con ใน PATH หรือตัวแปร NGSPICE_BIN — ต้องใช้ ngspice_con.exe (ไม่ใช่ ngspice.exe แบบ GUI)",
    )


_VERSION_RE = re.compile(r"ngspice[- ]?(\d+(?:\.\d+)*)", re.IGNORECASE)


def detect_engine_version(log, ngspice=None, run_dir=None, timeout=15.0):
    """Read the solver version from its banner, falling back to ``-v``.

    Returns ``None`` when no version can be measured; callers must not
    substitute a hard-coded version into provenance output.
    """
    match = _VERSION_RE.search(log or "")
    if match:
        return f"ngspice-{match.group(1)}"
    if not ngspice:
        return None
    try:
        completed = subprocess.run(
            [ngspice, "-v"],
            cwd=run_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = _VERSION_RE.search(f"{completed.stdout}\n{completed.stderr}")
    return f"ngspice-{match.group(1)}" if match else None


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


_OUTPUT_FILES = {"dc": "op.csv", "ac": "ac.csv", "tran": "tran.csv"}
_FATAL_PATTERNS = (
    re.compile(r"(?im)^\s*(?:fatal\s+)?error\b"),
    re.compile(r"(?i)\bsingular matrix\b"),
    re.compile(r"(?i)\btimestep too small\b"),
    re.compile(r"(?i)\bno such vector\b"),
    re.compile(r"(?i)\bno such file\b"),
    re.compile(r"(?i)\bcan(?:'|’)t open\b"),
    re.compile(r"(?i)\bcannot open\b"),
)


def run_ngspice(request, timeout=15.0, runs_root=None):
    """Execute one ngspice analysis and persist every artifact for that run.

    Every engine failure carries ``run_id`` and ``artifacts`` so the caller can
    show provenance even when the run failed.  A run directory (with an initial
    ``meta.json``) is created before the subprocess starts; ``meta.json`` is
    always rewritten with the final status in ``finally``.
    """
    root = Path(runs_root) if runs_root is not None else Path("instance/spice_runs")
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    artifacts = {
        "run_id": run_id,
        "directory": str(run_dir),
        "netlist": "circuit.cir",
        "request": "request.json",
        "log": "ngspice.log",
        "meta": "meta.json",
        "output": _OUTPUT_FILES.get(request.analysis),
    }

    def write_meta(status, kind=None, message=None, duration_ms=0, model=None, model_source=None):
        meta = {
            "status": status,
            "kind": kind,
            "message": message,
            "analysis": request.analysis,
            "run_id": run_id,
            "duration_ms": duration_ms,
            "model": model,
            "model_source": model_source,
            "artifacts": artifacts,
        }
        (run_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    write_meta("running")

    model = None
    model_source = None
    result = None
    error = None
    status = "failed"
    kind = None
    message = None
    started = time.perf_counter()

    try:
        netlist = build_netlist(request)
        (run_dir / "circuit.cir").write_text(netlist, encoding="utf-8")
        (run_dir / "request.json").write_text(
            json.dumps(asdict(request), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        model, model_source = find_model(request.beta)
        ngspice = find_ngspice()

        completed = subprocess.run(
            [ngspice, "-b", "circuit.cir"],
            cwd=run_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        log = f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}\n"
        (run_dir / "ngspice.log").write_text(log, encoding="utf-8")

        if completed.returncode != 0:
            raise SpiceError(
                "process_error",
                f"ngspice ออกด้วยโค้ด {completed.returncode}: {completed.stderr.strip() or completed.stdout.strip()}",
            )
        for pattern in _FATAL_PATTERNS:
            if pattern.search(log):
                raise SpiceError("process_error", f"ngspice รายงานความผิดพลาดร้ายแรง ({pattern.pattern})")

        engine_version = detect_engine_version(
            log, ngspice=ngspice, run_dir=run_dir, timeout=timeout
        )
        output_name = _OUTPUT_FILES[request.analysis]
        output_path = run_dir / output_name
        if not output_path.is_file():
            raise SpiceError("missing_output", f"ngspice ไม่เขียนไฟล์ผล {output_name}")

        parsers = {
            "dc": lambda: {"dc": parse_op_csv(output_path)},
            "ac": lambda: {"ac": parse_ac_csv(output_path)},
            "tran": lambda: {"tran": parse_tran_csv(output_path)},
        }
        payload = parsers[request.analysis]()
        result = {
            "engine": "ngspice",
            "engine_version": engine_version,
            "status": "Success",
            "analysis": request.analysis,
            "run_id": run_id,
            "duration_ms": 0,
            "model": model,
            "model_source": model_source,
            "netlist": netlist,
            "warnings": [],
            "log": log,
            "artifacts": artifacts,
        }
        result.update(payload)
        status = "Success"
    except subprocess.TimeoutExpired as exc:
        kind, message = "timeout", f"ngspice หมดเวลาเกิน {timeout:g} วินาที"
        error = SpiceError(kind, message, run_id=run_id, artifacts=artifacts)
    except SpiceError as exc:
        kind, message = exc.kind, exc.message
        error = SpiceError(kind, message, run_id=run_id, artifacts=artifacts)
    except OSError as exc:
        kind, message = "process_error", f"เรียกใช้ ngspice ไม่ได้: {exc}"
        error = SpiceError(kind, message, run_id=run_id, artifacts=artifacts)
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        write_meta(status, kind, message, duration_ms, model, model_source)
        if result is not None:
            result["duration_ms"] = duration_ms

    if error is not None:
        raise error
    return result
