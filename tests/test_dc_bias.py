import unittest

from dc_bias import (
    calculate_divider_bias,
    calculate_emitter_bias,
    calculate_fixed_bias,
)

KEYS = {
    "status",
    "region",
    "message",
    "ib_uA",
    "ic_mA",
    "ie_mA",
    "vb_V",
    "ve_V",
    "vc_V",
    "vce_V",
}


class BiasTests(unittest.TestCase):
    def test_divider_keeps_lab2_baseline(self):
        r = calculate_divider_bias(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0)
        self.assertEqual(set(r), KEYS)
        self.assertEqual(r["status"], "Success")
        self.assertEqual(r["region"], "Active")
        self.assertAlmostEqual(r["ib_uA"], 12.2985, places=3)
        self.assertAlmostEqual(r["ic_mA"], 1.2298, places=3)
        self.assertAlmostEqual(r["ie_mA"], 1.2421, places=3)
        self.assertAlmostEqual(r["vb_V"], 1.9422, places=3)
        self.assertAlmostEqual(r["ve_V"], 1.2421, places=3)
        self.assertAlmostEqual(r["vc_V"], 9.2943, places=3)
        self.assertAlmostEqual(r["vce_V"], 8.0522, places=3)

    def test_fixed_bias(self):
        r = calculate_fixed_bias(12.0, 1_000_000.0, 2_200.0, 100.0)
        self.assertEqual(set(r), KEYS)
        self.assertEqual(r["status"], "Success")
        self.assertEqual(r["region"], "Active")
        self.assertAlmostEqual(r["ib_uA"], 11.3, places=3)
        self.assertAlmostEqual(r["ic_mA"], 1.13, places=3)
        self.assertAlmostEqual(r["ie_mA"], 1.1413, places=3)
        self.assertEqual(r["ve_V"], 0.0)
        self.assertAlmostEqual(r["vb_V"], 0.7, places=3)
        self.assertAlmostEqual(r["vc_V"], 9.514, places=3)
        self.assertAlmostEqual(r["vce_V"], 9.514, places=3)

    def test_emitter_bias(self):
        r = calculate_emitter_bias(12.0, 1_000_000.0, 1_000.0, 2_200.0, 100.0)
        self.assertEqual(set(r), KEYS)
        self.assertEqual(r["status"], "Success")
        self.assertEqual(r["region"], "Active")
        self.assertAlmostEqual(r["ib_uA"], 10.2634, places=3)
        self.assertAlmostEqual(r["ic_mA"], 1.0263, places=3)
        self.assertAlmostEqual(r["ie_mA"], 1.0366, places=3)
        self.assertAlmostEqual(r["vb_V"], 1.7366, places=3)
        self.assertAlmostEqual(r["ve_V"], 1.0366, places=3)
        self.assertAlmostEqual(r["vc_V"], 9.7421, places=3)
        self.assertAlmostEqual(r["vce_V"], 8.7055, places=3)

    def test_cutoff_has_no_negative_current(self):
        r = calculate_divider_bias(
            12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, vbe=2.5
        )
        self.assertEqual(r["status"], "Success")
        self.assertEqual(r["region"], "Cutoff")
        self.assertEqual((r["ib_uA"], r["ic_mA"], r["ie_mA"]), (0, 0, 0))
        self.assertAlmostEqual(r["vce_V"], 12.0, places=3)
        self.assertIn("Cutoff", r["message"])

    def test_saturation_keeps_ie_equal_to_ic_plus_ib(self):
        r = calculate_divider_bias(
            12.0, 100_000.0, 22_000.0, 10_000.0, 100.0, 100.0
        )
        self.assertEqual(r["status"], "Success")
        self.assertEqual(r["region"], "Saturation")
        self.assertAlmostEqual(r["ic_mA"], 1.1678, places=3)
        self.assertAlmostEqual(r["ie_mA"], 1.2198, places=3)
        self.assertAlmostEqual(
            r["ie_mA"], r["ic_mA"] + r["ib_uA"] / 1000.0, places=3
        )
        self.assertIn("Saturation", r["message"])

    def test_saturation_voltages_satisfy_kvl(self):
        vcc, rc, re = 12.0, 10_000.0, 100.0
        r = calculate_divider_bias(vcc, 100_000.0, 22_000.0, rc, re, 100.0)
        self.assertAlmostEqual(r["vce_V"], 0.2, places=4)
        self.assertAlmostEqual(r["ve_V"], r["ie_mA"] / 1000.0 * re, places=3)
        self.assertAlmostEqual(r["vc_V"], r["ve_V"] + r["vce_V"], places=3)
        self.assertAlmostEqual(r["vb_V"], r["ve_V"] + 0.7, places=3)
        self.assertAlmostEqual(
            r["ic_mA"] / 1000.0 * rc + r["vce_V"] + r["ve_V"], vcc, places=3
        )

    def test_fixed_bias_saturates_when_rc_is_large(self):
        r = calculate_fixed_bias(12.0, 1_000_000.0, 100_000.0, 100.0)
        self.assertEqual(r["region"], "Saturation")
        self.assertAlmostEqual(r["ic_mA"], 0.118, places=3)
        self.assertAlmostEqual(r["ie_mA"], 0.1293, places=3)
        self.assertAlmostEqual(
            r["ie_mA"], r["ic_mA"] + r["ib_uA"] / 1000.0, places=3
        )
        self.assertEqual(r["ve_V"], 0.0)
        self.assertAlmostEqual(r["vce_V"], 0.2, places=4)
        self.assertAlmostEqual(r["vc_V"], 0.2, places=4)
        self.assertAlmostEqual(r["vb_V"], 0.7, places=4)
        self.assertIn("Saturation", r["message"])

    def test_saturation_message_reports_computed_vce_not_clamped_value(self):
        r = calculate_divider_bias(
            12.0, 100_000.0, 22_000.0, 10_000.0, 100.0, 100.0
        )
        self.assertIn("VCE -40.56 V < 0.20 V", r["message"])

    def test_active_message_reports_vce(self):
        r = calculate_fixed_bias(12.0, 1_000_000.0, 2_200.0, 100.0)
        self.assertIn("VCE", r["message"])
        self.assertIn("active", r["message"])


if __name__ == "__main__":
    unittest.main()
