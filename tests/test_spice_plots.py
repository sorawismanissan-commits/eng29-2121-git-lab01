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
