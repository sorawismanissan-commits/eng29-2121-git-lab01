"""Server-rendered SVG charts for simulation results.

No JavaScript is involved: the Flask view builds these strings from parsed
ngspice output and injects them into the template as trusted markup.  All
user-derived text is HTML-escaped before it reaches the SVG.
"""

from html import escape
import math


def _fmt(value):
    if abs(value) >= 1000 or (0 < abs(value) < 0.01):
        return f"{value:.2g}"
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.3g}".rstrip("0").rstrip(".")


def _safe_color(color):
    text = str(color or "#0c8e83")
    return text if text.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in text[1:]) else "#0c8e83"


def line_chart(series, x_label, y_label, *, log_x=False, width=720, height=320):
    """Return an SVG string, or a placeholder paragraph when there is no data.

    ``series`` items are ``{"name": str, "color": str, "points": [(x, y), ...]}``.
    With ``log_x=True``, positive x values use ``log10`` while non-positive ones
    are pinned just below the smallest positive decade so the chart never fails.
    """
    usable = [item for item in series if item.get("points")]
    if not usable:
        return '<p class="plot-empty">ไม่มีข้อมูลสำหรับกราฟนี้</p>'

    left, right, top, bottom = 64, 20, 20, 76
    plot_w, plot_h = width - left - right, height - top - bottom

    raw_x = [float(x) for item in usable for x, _y in item["points"]]
    raw_y = [float(y) for item in usable for _x, y in item["points"]]
    if log_x:
        positive = [math.log10(x) for x in raw_x if x > 0]
        floor = min(positive) - 0.5 if positive else 0.0
        tx = [math.log10(x) if x > 0 else floor for x in raw_x]
    else:
        tx = raw_x
    ty = raw_y

    xmin, xmax = min(tx), max(tx)
    ymin, ymax = min(ty), max(ty)
    if xmax == xmin:
        xmin, xmax = xmin - 0.5, xmax + 0.5
    if ymax == ymin:
        ymin, ymax = ymin - 1, ymax + 1
    ypad = (ymax - ymin) * 0.05
    ymin, ymax = ymin - ypad, ymax + ypad

    def px(value):
        return left + (value - xmin) / (xmax - xmin) * plot_w

    def py(value):
        return top + plot_h - (value - ymin) / (ymax - ymin) * plot_h

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="auto" '
        'role="img" xmlns="http://www.w3.org/2000/svg" class="sim-plot">',
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" '
        'fill="#fbfcfe" stroke="#dde3ec"/>',
    ]

    for i in range(5):
        frac = i / 4
        gx = left + frac * plot_w
        gy = top + plot_h - frac * plot_h
        xv = xmin + frac * (xmax - xmin)
        yv = ymin + frac * (ymax - ymin)
        parts.append(f'<line x1="{gx:.2f}" y1="{top}" x2="{gx:.2f}" y2="{top + plot_h}" stroke="#e7ebf1"/>')
        parts.append(f'<line x1="{left}" y1="{gy:.2f}" x2="{left + plot_w}" y2="{gy:.2f}" stroke="#e7ebf1"/>')
        parts.append(
            f'<text x="{gx:.2f}" y="{top + plot_h + 18}" text-anchor="middle" '
            f'class="plot-tick">{escape(_fmt(10 ** xv if log_x else xv))}</text>'
        )
        parts.append(
            f'<text x="{left - 8}" y="{gy + 4:.2f}" text-anchor="end" '
            f'class="plot-tick">{escape(_fmt(yv))}</text>'
        )

    parts.append(
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#8a94a6"/>'
    )
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#8a94a6"/>')

    for item in usable:
        color = _safe_color(item.get("color"))
        name = escape(str(item.get("name", "")))
        coords = " ".join(f"{px(tx[i]):.2f},{py(ty[i]):.2f}" for i in range(len(item["points"])))
        parts.append(
            f'<g><title>{name}</title><polyline points="{coords}" fill="none" '
            f'stroke="{color}" stroke-width="2.2" stroke-linejoin="round"/></g>'
        )

    legend_y = height - 10
    legend_x = left
    for item in usable:
        color = _safe_color(item.get("color"))
        name = escape(str(item.get("name", "")))
        parts.append(
            f'<line x1="{legend_x}" y1="{legend_y - 4}" x2="{legend_x + 18}" y2="{legend_y - 4}" '
            f'stroke="{color}" stroke-width="2.2"/>'
        )
        parts.append(f'<text x="{legend_x + 23}" y="{legend_y}" class="plot-legend">{name}</text>')
        legend_x += 30 + 9 * len(name)

    parts.append(
        f'<text x="{left + plot_w / 2:.2f}" y="{height - 34}" text-anchor="middle" '
        f'class="plot-axis-label">{escape(str(x_label))}</text>'
    )
    parts.append(
        f'<text transform="translate(16,{top + plot_h / 2:.2f}) rotate(-90)" text-anchor="middle" '
        f'class="plot-axis-label">{escape(str(y_label))}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)
