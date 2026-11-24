import math
import unittest

from spice_summary import build_summary


class SummaryTests(unittest.TestCase):
    def test_build_summary_handles_empty_spice(self):
        s = build_summary({}, None, 1000.0)
        self.assertEqual(s, {"dc": None, "ac": None, "tran": None, "engine": None})

    def test_dc_summary_pairs_analytical_and_spice(self):
        spice = {"dc": {"vb_V": 1.9576, "ve_V": 1.2395, "vc_V": 9.2984,
                        "vce_V": 8.0589, "ic_mA": 1.2288, "ib_uA": 11.4476,
                        "ie_mA": 1.2402}}
        result = {"vb_V": 1.9422, "ve_V": 1.2422, "vc_V": 9.2943,
                  "vce_V": 8.0522, "ic_mA": 1.2299, "ib_uA": 12.2986,
                  "ie_mA": 1.2422}
        dc = build_summary(spice, result, 1000.0)["dc"]
        self.assertEqual(dc["rows"][0], {"label": "VB", "analytical": 1.9422,
                                         "spice": 1.9576, "delta": 0.0154,
                                         "unit": "V"})
        self.assertEqual(dc["rows"][4]["label"], "IC")

    def test_ac_summary_reports_no_cutoff_in_sweep(self):
        points = [{"freq_Hz": 10, "gain_db": 4.7, "phase_deg": -179},
                  {"freq_Hz": 1000, "gain_db": 4.85, "phase_deg": -180},
                  {"freq_Hz": 1000000, "gain_db": 4.84, "phase_deg": -180}]
        ac = build_summary({"ac": points}, None, 1000.0)["ac"]
        self.assertEqual(ac["at_freq_Hz"], 1000)
        self.assertEqual(ac["gain_db"], 4.85)
        self.assertEqual(ac["phase_deg"], -180)
        self.assertIsNone(ac["cutoff_low_Hz"])
        self.assertIsNone(ac["cutoff_high_Hz"])
        self.assertIn("outside sweep", ac["cutoff_status"])

    def test_ac_summary_reports_upper_edge_only(self):
        points = [{"freq_Hz": 10, "gain_db": 4.85, "phase_deg": -180},
                  {"freq_Hz": 1000, "gain_db": 4.85, "phase_deg": -180},
                  {"freq_Hz": 10000, "gain_db": 1.85, "phase_deg": -180},
                  {"freq_Hz": 100000, "gain_db": -3.15, "phase_deg": -180}]
        ac = build_summary({"ac": points}, None, 1000.0)["ac"]
        self.assertIsNone(ac["cutoff_low_Hz"])
        self.assertEqual(ac["cutoff_high_Hz"], 10000)
        self.assertIn("lower edge outside sweep", ac["cutoff_status"])

    def test_ac_summary_reports_lower_edge_only(self):
        points = [{"freq_Hz": 10, "gain_db": -3.15, "phase_deg": -180},
                  {"freq_Hz": 100, "gain_db": 1.85, "phase_deg": -180},
                  {"freq_Hz": 1000, "gain_db": 4.85, "phase_deg": -180},
                  {"freq_Hz": 100000, "gain_db": 4.85, "phase_deg": -180}]
        ac = build_summary({"ac": points}, None, 1000.0)["ac"]
        self.assertEqual(ac["cutoff_low_Hz"], 100)
        self.assertIsNone(ac["cutoff_high_Hz"])
        self.assertIn("upper edge outside sweep", ac["cutoff_status"])

    @staticmethod
    def _sine_points(vin_phase_deg, vout_phase_deg):
        points = []
        for i in range(30):
            time_ms = i * 0.1
            angle = 2 * math.pi * 1000 * (time_ms / 1000)
            points.append({
                "time_ms": time_ms,
                "vin_V": 0.01 * math.sin(angle + math.radians(vin_phase_deg)),
                "vout_V": 0.0175 * math.sin(angle + math.radians(vout_phase_deg)),
            })
        return points

    def test_tran_summary_detects_inversion_with_wraparound(self):
        points = [{"time_ms": i * 0.1,
                   "vin_V": 0.01 * math.sin(2 * math.pi * 1000 * (i * 0.0001)),
                   "vout_V": -0.0175 * math.sin(2 * math.pi * 1000 * (i * 0.0001))}
                  for i in range(30)]
        tran = build_summary({"tran": points}, None, 1000.0)["tran"]
        self.assertLess(abs(tran["gain"] - 1.75), 0.1)
        self.assertTrue(tran["inversion"])
        self.assertLess(abs(abs(tran["phase_diff_deg"]) - 180), 10)

    def test_tran_summary_wraps_phase_across_plus_minus_180(self):
        tran = build_summary(
            {"tran": self._sine_points(179, -1)}, None, 1000.0
        )["tran"]
        self.assertTrue(tran["inversion"])
        self.assertLess(abs(abs(tran["phase_diff_deg"]) - 180), 10)

    def test_tran_summary_treats_both_phases_near_180_as_in_phase(self):
        tran = build_summary(
            {"tran": self._sine_points(179.94, -179.94)}, None, 1000.0
        )["tran"]
        self.assertFalse(tran["inversion"])
        self.assertLess(abs(tran["phase_diff_deg"]), 5)


if __name__ == "__main__":
    unittest.main()
