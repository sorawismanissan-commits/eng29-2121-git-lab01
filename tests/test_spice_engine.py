import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spice_engine import (
    SpiceError,
    SpiceRequest,
    build_netlist,
    find_model,
    find_ngspice,
    parse_ac_csv,
    parse_op_csv,
    parse_tran_csv,
    run_ngspice,
)


def ngspice_path():
    env = os.environ.get("NGSPICE_BIN")
    if env and Path(env).is_file():
        return env
    for name in ("ngspice_con", "ngspice_con.exe"):
        found = shutil.which(name)
        if found:
            return found
    known = Path(os.environ.get("LOCALAPPDATA", "")) / "ngspice" / "47" / "Spice64" / "bin" / "ngspice_con.exe"
    return str(known) if known.is_file() else None


def find_ngspice_available():
    return ngspice_path() is not None


def request(analysis="dc", **overrides):
    values = dict(
        analysis=analysis,
        vcc_V=12.0,
        r1_ohm=100_000.0,
        r2_ohm=22_000.0,
        rc_ohm=2_200.0,
        re_ohm=1_000.0,
        beta=100.0,
        vbe_V=0.70,
        vin_amp_V=0.010,
        vin_freq_Hz=1_000.0,
        ac_start_Hz=10.0,
        ac_stop_Hz=1_000_000.0,
        ac_ppd=10,
        tran_stop_s=0.005,
        tran_step_s=0.00001,
        rl_ohm=10_000.0,
    )
    values.update(overrides)
    return SpiceRequest(**values)


class NetlistTests(unittest.TestCase):
    def test_dc_builds_only_op_analysis(self):
        net = build_netlist(request("dc"))
        self.assertIn("op\nwrdata op.csv", net)
        self.assertIn("v(4) v(6) v(5) v(5)-v(6)", net)
        self.assertNotIn("ac dec", net)
        self.assertNotIn("tran 0.00001", net)

    def test_ac_builds_only_ac_analysis(self):
        net = build_netlist(request("ac"))
        self.assertIn("ac dec 10 10.0 1000000.0", net)
        self.assertIn("wrdata ac.csv vm(7) vp(7)", net)
        self.assertNotIn("op\nwrdata op.csv", net)
        self.assertNotIn("tran 0.00001", net)

    def test_tran_builds_only_transient_analysis(self):
        net = build_netlist(request("tran"))
        self.assertIn("tran 0.00001 0.005", net)
        self.assertIn("wrdata tran.csv v(2) v(7)", net)
        self.assertNotIn("ac dec", net)
        self.assertNotIn("op\nwrdata op.csv", net)

    def test_uses_si_values_and_no_form_units(self):
        net = build_netlist(request("dc"))
        self.assertIn("R1 1 4 100000.0", net)
        self.assertIn("R2 4 0 22000.0", net)
        self.assertIn("RC 1 5 2200.0", net)
        self.assertIn("RE 6 0 1000.0", net)
        self.assertIn("RL 7 0 10000.0", net)
        self.assertIn("VIN 2 0 DC 0 AC 1 SIN(0 0.01 1000.0)", net)
        self.assertNotIn("kΩ", net)

    def test_unknown_analysis_is_an_error(self):
        with self.assertRaises(SpiceError) as ctx:
            build_netlist(request("all"))
        self.assertEqual(ctx.exception.kind, "validation_error")


class DiscoveryTests(unittest.TestCase):
    def test_find_model_uses_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "instructor.model"
            model.write_text(".model QNPN NPN (BF=200 IS=1e-14 VAF=80)\n", encoding="utf-8")
            with patch.dict(os.environ, {"SPICE_MODEL_PATH": str(model)}, clear=False):
                card, source = find_model(100.0)
        self.assertEqual(source, "env")
        self.assertIn("BF=200", card)

    def test_find_model_falls_back_to_provisional(self):
        with patch.dict(os.environ, {}, clear=True):
            card, source = find_model(100.0)
        self.assertEqual(source, "provisional")
        self.assertIn("BF=100", card)
        self.assertIn("IS=1e-15", card)

    def test_find_ngspice_uses_env_override(self):
        with patch.dict(os.environ, {"NGSPICE_BIN": "C:/fake/ngspice_con.exe"}, clear=False):
            self.assertEqual(find_ngspice(), "C:/fake/ngspice_con.exe")


class ParserTests(unittest.TestCase):
    def write(self, text):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        tmp.write(text)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_parse_op_csv(self):
        path = self.write(
            "12 1.95763218 12 1.23946122 12 9.29835416 "
            "12 8.05889293 12 0.00122879744 12 0.0000114476286\n"
        )
        result = parse_op_csv(path)
        self.assertAlmostEqual(result["vb_V"], 1.9576, places=4)
        self.assertAlmostEqual(result["ve_V"], 1.2395, places=4)
        self.assertAlmostEqual(result["vc_V"], 9.2984, places=4)
        self.assertAlmostEqual(result["vce_V"], 8.0589, places=4)
        self.assertAlmostEqual(result["ic_mA"], 1.2288, places=4)
        self.assertAlmostEqual(result["ib_uA"], 11.4476, places=4)

    def test_parse_ac_csv_converts_radians_to_degrees(self):
        path = self.write("1000 1.74846117 1000 -3.13925692\n")
        points = parse_ac_csv(path)
        self.assertEqual(len(points), 1)
        self.assertAlmostEqual(points[0]["freq_Hz"], 1000.0)
        self.assertAlmostEqual(points[0]["gain_db"], 4.85, places=2)
        self.assertAlmostEqual(points[0]["phase_deg"], -179.86, places=1)

    def test_parse_tran_csv(self):
        path = self.write("0 0 0 0\n0.0001 0.00628 0.0001 -0.00153\n")
        points = parse_tran_csv(path)
        self.assertEqual(len(points), 2)
        self.assertAlmostEqual(points[1]["time_ms"], 0.1, places=4)
        self.assertAlmostEqual(points[1]["vin_V"], 0.00628, places=4)
        self.assertAlmostEqual(points[1]["vout_V"], -0.00153, places=4)

    def test_empty_csv_is_parse_error(self):
        with self.assertRaises(SpiceError) as ctx:
            parse_tran_csv(self.write(""))
        self.assertEqual(ctx.exception.kind, "parse_error")


class RunTests(unittest.TestCase):
    def test_run_dc_with_real_ngspice(self):
        if not find_ngspice_available():
            self.skipTest("ngspice_con not available in this environment")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"NGSPICE_BIN": ngspice_path()}):
                result = run_ngspice(request("dc"), runs_root=Path(tmp))
            self.assertEqual(result["status"], "Success")
            self.assertEqual(result["analysis"], "dc")
            self.assertAlmostEqual(result["dc"]["ic_mA"], 1.2288, delta=0.05)
            self.assertAlmostEqual(result["dc"]["vce_V"], 8.0589, delta=0.1)
            self.assertTrue((Path(tmp) / result["run_id"] / "meta.json").exists())
            self.assertTrue((Path(tmp) / result["run_id"] / "circuit.cir").exists())

    def test_timeout_keeps_run_dir_and_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"NGSPICE_BIN": "C:/fake/ngspice_con.exe"}):
                with patch("spice_engine.subprocess.run", side_effect=subprocess.TimeoutExpired("ngspice", 1)):
                    with self.assertRaises(SpiceError) as ctx:
                        run_ngspice(request("dc"), runs_root=Path(tmp))
            err = ctx.exception
            self.assertEqual(err.kind, "timeout")
            self.assertIsNotNone(err.run_id)
            meta = Path(tmp) / err.run_id / "meta.json"
            self.assertTrue(meta.exists())
            self.assertEqual(json.loads(meta.read_text(encoding="utf-8"))["kind"], "timeout")

    def test_process_error_is_not_success(self):
        fake = subprocess.CompletedProcess(["ngspice"], 1, "", "singular matrix")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"NGSPICE_BIN": "C:/fake/ngspice_con.exe"}):
                with patch("spice_engine.subprocess.run", return_value=fake):
                    with self.assertRaises(SpiceError) as ctx:
                        run_ngspice(request("dc"), runs_root=Path(tmp))
            self.assertEqual(ctx.exception.kind, "process_error")
