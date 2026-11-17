import unittest

from app import app

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


if __name__ == "__main__":
    unittest.main()
