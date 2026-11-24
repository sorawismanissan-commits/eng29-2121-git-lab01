import unittest
from unittest.mock import patch

from app import app, parse_spice_request
from spice_engine import SpiceError
from spice_plots import line_chart

FORM = {
    "mode": "divider",
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1.0",
    "beta": "100",
    "vbe": "0.70",
}

FIXED_FORM = {
    "mode": "fixed",
    "vcc": "12",
    "rb": "1000",
    "rc": "2.2",
    "beta": "100",
    "vbe": "0.70",
}


class GetFormTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_default_shows_divider_fields(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn('name="r1"', body)
        self.assertIn('name="r2"', body)
        self.assertIn('name="re"', body)
        self.assertNotIn('name="rb"', body)

    def test_get_fixed_shows_only_rb(self):
        res = self.client.get("/?mode=fixed")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn('name="rb"', body)
        self.assertNotIn('name="r1"', body)
        self.assertNotIn('name="r2"', body)
        self.assertNotIn('name="re"', body)

    def test_get_emitter_shows_rb_and_re(self):
        body = self.client.get("/?mode=emitter").get_data(as_text=True)
        self.assertIn('name="rb"', body)
        self.assertIn('name="re"', body)
        self.assertNotIn('name="r1"', body)

    def test_unknown_mode_is_an_error(self):
        res = self.client.get("/?mode=hbridge")
        self.assertEqual(res.status_code, 400)
        self.assertIn("โหมดไม่ถูกต้อง", res.get_data(as_text=True))


class CalculateFormTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_post_calculate_renders_result(self):
        res = self.client.post("/calculate", data=FORM)
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("1.23", body)
        self.assertIn("Voltage Divider", body)

    def test_post_fixed_renders_fixed_result(self):
        res = self.client.post("/calculate", data=FIXED_FORM)
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("Fixed Bias", body)
        self.assertIn("9.51", body)

    def test_post_invalid_beta_has_no_stale_result(self):
        res = self.client.post("/calculate", data={**FORM, "beta": "0"})
        self.assertEqual(res.status_code, 400)
        body = res.get_data(as_text=True)
        self.assertIn("β ต้องมากกว่า 0", body)
        # The acceptance log quotes reference values from the lab sheet, so
        # check the result cells themselves rather than the whole page.
        for field in ("vb", "ve", "vc", "vce", "ib", "ic", "ie"):
            self.assertIn(f'id="res-{field}">—</td>', body)

    def test_ignores_fields_the_mode_does_not_use(self):
        res = self.client.post(
            "/calculate", data={**FIXED_FORM, "r1": "abc", "re": "-99"}
        )
        self.assertEqual(res.status_code, 200)

    def test_post_unknown_mode_is_an_error(self):
        res = self.client.post("/calculate", data={**FORM, "mode": "hbridge"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("โหมดไม่ถูกต้อง", res.get_data(as_text=True))

    def test_post_missing_rc_is_an_error(self):
        payload = dict(FORM)
        payload.pop("rc")
        res = self.client.post("/calculate", data=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("ไม่พบค่า RC", res.get_data(as_text=True))


class JsonApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_json_api_matches_form_result(self):
        res = self.client.post("/api/calculate", json=FORM)
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body["status"], "Success")
        self.assertEqual(body["region"], "Active")
        self.assertAlmostEqual(body["ic_mA"], 1.2298, places=3)

    def test_json_rejects_non_object_body(self):
        res = self.client.post("/api/calculate", data="", content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["message"], "ข้อมูลต้องเป็น JSON object")

    def test_json_rejects_unknown_mode(self):
        res = self.client.post("/api/calculate", json={**FORM, "mode": "hbridge"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.get_json(), {"status": "Error", "message": "โหมดไม่ถูกต้อง"}
        )

    def test_json_rejects_non_numeric_field(self):
        res = self.client.post("/api/calculate", json={**FORM, "beta": "abc"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["message"], "ค่า β ต้องเป็นตัวเลข")

    def test_json_rejects_zero_resistance(self):
        res = self.client.post("/api/calculate", json={**FORM, "rc": 0})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["message"], "RC ต้องมากกว่า 0")

    def test_json_rejects_negative_vbe(self):
        res = self.client.post("/api/calculate", json={**FORM, "vbe": -0.1})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["message"], "VBE ต้องไม่ติดลบ")


SPICE_FORM = {
    **FORM,
    "analysis": "dc",
    "vin_amp_mv": "10",
    "vin_freq_hz": "1000",
    "ac_start_hz": "10",
    "ac_stop_hz": "1000000",
    "ac_ppd": "10",
    "tran_stop_ms": "5",
    "tran_step_us": "10",
    "rl_kohm": "10",
}


FAKE_DC = {
    "status": "Success",
    "analysis": "dc",
    "run_id": "20261124-160000-abcdef12",
    "engine": "ngspice",
    "engine_version": "ngspice-47",
    "model": "QNPN NPN (BF=100 IS=1e-15 VAF=100)",
    "model_source": "provisional",
    "duration_ms": 80,
    "warnings": [],
    "netlist": "* test",
    "artifacts": {"directory": "instance/spice_runs/20261124-160000-abcdef12"},
    "dc": {"vb_V": 1.9576, "ve_V": 1.2395, "vc_V": 9.2984,
           "vce_V": 8.0589, "ib_uA": 11.4476, "ic_mA": 1.2288, "ie_mA": 1.2402},
}


class SpiceValidationTests(unittest.TestCase):
    def test_converts_form_units_to_si(self):
        req = parse_spice_request(SPICE_FORM)
        self.assertEqual(req.analysis, "dc")
        self.assertAlmostEqual(req.vin_amp_V, 0.010)
        self.assertAlmostEqual(req.vin_freq_Hz, 1000.0)
        self.assertAlmostEqual(req.ac_start_Hz, 10.0)
        self.assertAlmostEqual(req.ac_stop_Hz, 1_000_000.0)
        self.assertEqual(req.ac_ppd, 10)
        self.assertAlmostEqual(req.tran_stop_s, 0.005)
        self.assertAlmostEqual(req.tran_step_s, 0.00001)
        self.assertAlmostEqual(req.rl_ohm, 10_000.0)
        self.assertAlmostEqual(req.r1_ohm, 100_000.0)
        self.assertAlmostEqual(req.vcc_V, 12.0)

    def test_rejects_unknown_analysis(self):
        with self.assertRaises(ValueError):
            parse_spice_request({**SPICE_FORM, "analysis": "all"})

    def test_rejects_zero_frequency(self):
        with self.assertRaises(ValueError):
            parse_spice_request({**SPICE_FORM, "vin_freq_hz": "0"})

    def test_rejects_bad_ac_range_and_ppd(self):
        with self.assertRaises(ValueError):
            parse_spice_request({**SPICE_FORM, "ac_stop_hz": "10"})
        with self.assertRaises(ValueError):
            parse_spice_request({**SPICE_FORM, "ac_ppd": "101"})

    def test_rejects_bad_transient_range(self):
        with self.assertRaises(ValueError):
            parse_spice_request({**SPICE_FORM, "tran_step_us": "5000"})


class SpiceRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_dc_calls_engine_and_keeps_analytical(self):
        with patch("app.run_ngspice", return_value=FAKE_DC) as engine:
            res = self.client.post("/spice", data=SPICE_FORM)
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("1.23", body)
        self.assertEqual(engine.call_count, 1)
        self.assertEqual(engine.call_args.args[0].analysis, "dc")

    def test_rejects_non_divider_mode(self):
        res = self.client.post("/spice", data={**SPICE_FORM, "mode": "fixed"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Voltage Divider", res.get_data(as_text=True))

    def test_rejects_unknown_analysis(self):
        res = self.client.post("/spice", data={**SPICE_FORM, "analysis": "all"})
        self.assertEqual(res.status_code, 400)

    def test_bad_spice_setting_keeps_analytical_result(self):
        res = self.client.post("/spice", data={**SPICE_FORM, "vin_freq_hz": "0"})
        self.assertEqual(res.status_code, 400)
        body = res.get_data(as_text=True)
        self.assertIn("1.23", body)
        self.assertNotIn('class="sim-plot"', body)

    def test_engine_error_returns_502(self):
        error = SpiceError("not_found", "ไม่พบ ngspice", run_id="run-1", artifacts={})
        with patch("app.run_ngspice", side_effect=error):
            res = self.client.post("/spice", data=SPICE_FORM)
        self.assertEqual(res.status_code, 502)
        self.assertIn("1.23", res.get_data(as_text=True))

    def test_timeout_returns_504(self):
        error = SpiceError("timeout", "หมดเวลา", run_id="run-2", artifacts={})
        with patch("app.run_ngspice", side_effect=error):
            res = self.client.post("/spice", data=SPICE_FORM)
        self.assertEqual(res.status_code, 504)

    def test_api_spice_returns_analytical_and_spice(self):
        with patch("app.run_ngspice", return_value=FAKE_DC):
            res = self.client.post("/api/spice", json=SPICE_FORM)
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertEqual(payload["status"], "Success")
        self.assertAlmostEqual(payload["analytical"]["ic_mA"], 1.2298, places=3)
        self.assertEqual(payload["spice"]["run_id"], FAKE_DC["run_id"])

    def test_api_spice_engine_error_carries_run_id(self):
        error = SpiceError("not_found", "ไม่พบ ngspice", run_id="run-json-1", artifacts={})
        with patch("app.run_ngspice", side_effect=error):
            res = self.client.post("/api/spice", json=SPICE_FORM)
        self.assertEqual(res.status_code, 502)
        body = res.get_json()
        self.assertEqual(body["status"], "Error")
        self.assertEqual(body["kind"], "not_found")
        self.assertEqual(body["run_id"], "run-json-1")

    def test_api_spice_rejects_unknown_analysis(self):
        res = self.client.post("/api/spice", json={**SPICE_FORM, "analysis": "all"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["status"], "Error")


def fake_result(analysis):
    if analysis == "ac":
        points = [
            {"freq_Hz": 10, "gain_db": -6.0, "phase_deg": -150.0},
            {"freq_Hz": 1000, "gain_db": 4.85, "phase_deg": -179.86},
        ]
        return {
            **FAKE_DC,
            "analysis": "ac", "dc": None, "tran": None,
            "ac": {"points": points, "gain_db_mid": 4.85, "phase_deg_mid": -179.86},
            "plots": {
                "magnitude": line_chart(
                    [{"name": "Gain", "color": "#0c8e83",
                      "points": [(p["freq_Hz"], p["gain_db"]) for p in points]}],
                    "Frequency (Hz)", "Gain (dB)", log_x=True,
                ),
                "phase": line_chart(
                    [{"name": "Phase", "color": "#c77a35",
                      "points": [(p["freq_Hz"], p["phase_deg"]) for p in points]}],
                    "Frequency (Hz)", "Phase (°)", log_x=True,
                ),
            },
        }
    if analysis == "tran":
        points = [
            {"time_ms": 0.0, "vin_V": 0.0, "vout_V": 0.0},
            {"time_ms": 0.1, "vin_V": 0.00628, "vout_V": -0.0109},
        ]
        return {
            **FAKE_DC,
            "analysis": "tran", "dc": None, "ac": None,
            "tran": points,
            "plots": {
                "waveform": line_chart(
                    [
                        {"name": "Vin", "color": "#8a94a6",
                         "points": [(p["time_ms"], p["vin_V"]) for p in points]},
                        {"name": "Vout", "color": "#c77a35",
                         "points": [(p["time_ms"], p["vout_V"]) for p in points]},
                    ],
                    "Time (ms)", "Voltage (V)",
                )
            },
        }
    return FAKE_DC


class SpiceTemplateTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_page_title_is_lab_04(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("<title>Lab 04: BJT CE Amplifier Simulator</title>", body)
        self.assertIn("<h1>Lab 04: BJT CE Amplifier Simulator</h1>", body)

    def test_divider_shows_spice_controls(self):
        body = self.client.get("/?mode=divider").get_data(as_text=True)
        self.assertIn('name="analysis"', body)
        for value in ("dc", "ac", "tran"):
            self.assertIn(f'value="{value}"', body)
        self.assertIn('name="vin_amp_mv"', body)
        self.assertIn("Run Simulation", body)

    def test_fixed_hides_spice_controls(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertNotIn('name="analysis"', body)
        self.assertNotIn("Run Simulation", body)

    def test_not_run_shows_status(self):
        body = self.client.get("/?mode=divider").get_data(as_text=True)
        self.assertIn("spice-status-card", body)
        self.assertIn("Not run", body)

    def test_dc_result_shows_provenance_and_table(self):
        with patch("app.run_ngspice", return_value=FAKE_DC):
            res = self.client.post("/spice", data=SPICE_FORM)
        body = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("spice-dc-table", body)
        self.assertIn(FAKE_DC["run_id"], body)
        self.assertIn("provisional model", body)
        self.assertIn("Analytical", body)
        self.assertIn("Cross-check", body)
        self.assertIn("instance/spice_runs/", body)

    def test_ac_result_contains_svg_and_units(self):
        with patch("app.run_ngspice", return_value=fake_result("ac")):
            res = self.client.post("/spice", data={**SPICE_FORM, "analysis": "ac"})
        body = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('class="sim-plot"', body)
        self.assertIn("spice-ac-plot", body)
        self.assertIn("dB", body)
        self.assertIn("Frequency", body)

    def test_tran_result_contains_svg(self):
        with patch("app.run_ngspice", return_value=fake_result("tran")):
            res = self.client.post("/spice", data={**SPICE_FORM, "analysis": "tran"})
        body = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("spice-tran-plot", body)
        self.assertIn('class="sim-plot"', body)
        self.assertIn("Time (ms)", body)

    def test_engine_error_hides_stale_plots(self):
        error = SpiceError("not_found", "ไม่พบ ngspice", run_id="run-stale", artifacts={})
        with patch("app.run_ngspice", side_effect=error):
            res = self.client.post("/spice", data={**SPICE_FORM, "analysis": "ac"})
        body = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 502)
        self.assertIn("run-stale", body)
        self.assertNotIn('class="sim-plot"', body)
        self.assertIn("1.23", body)


if __name__ == "__main__":
    unittest.main()
