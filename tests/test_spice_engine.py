import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spice_engine import SpiceError, SpiceRequest, build_netlist, find_model, find_ngspice


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
