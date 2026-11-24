import unittest

from spice_plots import line_chart


class PlotTests(unittest.TestCase):
    def test_returns_svg_with_axes_labels_and_polyline(self):
        svg = line_chart(
            [{"name": "Vout", "color": "#c77a35", "points": [(0, 0), (1, 2), (2, 1)]}],
            "Time (ms)",
            "Voltage (V)",
        )
        self.assertIn("<svg", svg)
        self.assertIn("Time (ms)", svg)
        self.assertIn("Voltage (V)", svg)
        self.assertIn("<polyline", svg)
        self.assertIn("Vout", svg)
        self.assertIn('aria-label="Voltage (V) versus Time (ms); series: Vout"', svg)
        self.assertNotIn('height="auto"', svg)

    def test_empty_series_has_placeholder(self):
        self.assertIn("ไม่มีข้อมูล", line_chart([], "x", "y"))

    def test_log_axis_does_not_crash_on_non_positive_values(self):
        svg = line_chart(
            [{"name": "Gain", "color": "#0c8e83", "points": [(0, -3), (10, 1), (100, 2)]}],
            "Frequency (Hz)",
            "Gain (dB)",
            log_x=True,
        )
        self.assertIn("<svg", svg)

    def test_escapes_label_text(self):
        svg = line_chart(
            [{"name": "<A&B>", "color": "#000", "points": [(0, 0), (1, 1)]}],
            "x<script>",
            "y",
        )
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)

    def test_zero_tick_is_formatted_as_zero(self):
        svg = line_chart(
            [{"name": "Vin", "color": "#000",
              "points": [(0, -0.0192), (1, 0.01922)]}],
            "Time (ms)",
            "Voltage (V)",
        )
        self.assertNotIn("1e-05", svg)
        self.assertIn(">0</text>", svg)

    def test_last_x_tick_is_right_anchored(self):
        svg = line_chart(
            [{"name": "Gain", "color": "#000",
              "points": [(10, 1), (100, 2), (1000000, 3)]}],
            "Frequency (Hz)",
            "Gain (dB)",
            log_x=True,
        )
        self.assertIn('x="672.00" y="258" text-anchor="end"', svg)
        self.assertIn("1e+06", svg)

    def test_y_axis_label_has_own_gutter(self):
        svg = line_chart(
            [{"name": "Vout", "color": "#000", "points": [(0, 0), (1, 1)]}],
            "Time (ms)",
            "Voltage (V)",
        )
        self.assertIn('transform="translate(18,', svg)
        self.assertIn('x="88"', svg)
