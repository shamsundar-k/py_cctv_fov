from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QSlider, QFrame, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .theme import TH
from .constants import CAMERA_MODEL, DORI_THRESHOLDS, DORI_HEX
from .geometry import fov_from_sensor


class ControlPanel(QWidget):
    def __init__(self, on_change, on_cam_params):
        super().__init__()
        self._cb            = on_change
        self._on_cam_params = on_cam_params
        self._sliders       = {}
        self._vl            = {}
        self._stats         = {}
        self._warn_lbl      = None
        self._model_lbl     = None
        self._build()

    def _build(self):
        self.setFixedWidth(295)
        ll = QVBoxLayout(self)
        ll.setContentsMargins(6, 6, 6, 6)
        ll.setSpacing(6)

        # ── Camera model box ─────────────────────────────────────────────
        mb = QGroupBox("Camera Model"); mb.setStyleSheet(self._gs())
        mbl = QVBoxLayout(mb); mbl.setSpacing(4)
        self._model_lbl = QLabel(self._model_text())
        self._model_lbl.setWordWrap(True)
        mbl.addWidget(self._model_lbl)

        cam_btn = QPushButton("⚙  Camera Parameters…")
        cam_btn.setStyleSheet(self._btn_style())
        cam_btn.clicked.connect(self._on_cam_params)
        mbl.addWidget(cam_btn)
        ll.addWidget(mb)

        # ── Sliders ───────────────────────────────────────────────────────
        sb = QGroupBox("Installation Parameters"); sb.setStyleSheet(self._gs())
        sg = QGridLayout(sb); sg.setVerticalSpacing(3)

        params = [
            ("focal",   "Focal Length",
             int(CAMERA_MODEL["f_min"]*10), int(CAMERA_MODEL["f_max"]*10),
             60,  "mm", 10),
            ("height",  "Install Height",  10, 150,  40, "m",  10),
            ("tgt_d",   "Target Distance",  5, 1500, 300, "m",  10),
            ("tgt_h",   "Target Height",    0,   30,  18, "m",  10),
            ("bearing", "Bearing",          0,  359,   0, "°",   1),
        ]
        for row, (key, label, lo, hi, default, unit, div) in enumerate(params):
            lbl = QLabel(label); lbl.setFont(QFont("Arial", 9, QFont.Bold))
            sg.addWidget(lbl, row*2, 0, 1, 2)
            sl = QSlider(Qt.Horizontal)
            sl.setMinimum(lo); sl.setMaximum(hi); sl.setValue(default)
            vl = QLabel(f"{default/div:.1f} {unit}")
            vl.setFixedWidth(58); vl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
            vl.setFont(QFont("Courier", 9))
            sl.valueChanged.connect(
                lambda v, vl=vl, u=unit, d=div: (
                    vl.setText(f"{v/d:.1f} {u}"), self._cb()))
            sg.addWidget(sl, row*2+1, 0); sg.addWidget(vl, row*2+1, 1)
            self._sliders[key] = sl; self._vl[key] = vl
        ll.addWidget(sb)

        # ── Results ───────────────────────────────────────────────────────
        stb = QGroupBox("Results"); stb.setStyleSheet(self._gs())
        stg = QGridLayout(stb); stg.setVerticalSpacing(2)
        rows = [
            ("H_angle", "H-FOV"), ("V_angle", "V-FOV"), ("tilt", "Tilt (calc)"),
            ("D_near",  "D_near"), ("D_far",  "D_far"), ("render_far", "Render far"),
            ("W_near",  "W_near"), ("W_far",  "W_far"), ("area",       "Coverage"),
            ("sep", None),
            ("d_ident", "Identification"), ("d_recog", "Recognition"),
            ("d_obs",   "Observation"),    ("d_det",   "Detection"),
        ]
        dm = {"d_ident": "Identification", "d_recog": "Recognition",
              "d_obs":   "Observation",    "d_det":   "Detection"}
        for r, (key, label) in enumerate(rows):
            if label is None:
                sep = QFrame(); sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet(f"color:{TH('sep')};")
                stg.addWidget(sep, r, 0, 1, 2); continue
            lbl = QLabel(label+":"); lbl.setFont(QFont("Arial", 8))
            val = QLabel("—"); val.setFont(QFont("Courier", 9, QFont.Bold))
            val.setAlignment(Qt.AlignRight)
            if key in dm:
                val.setStyleSheet(f"color:{DORI_HEX[dm[key]]};font-weight:bold;")
            stg.addWidget(lbl, r, 0); stg.addWidget(val, r, 1)
            self._stats[key] = val
        ll.addWidget(stb)

        # ── DORI legend ───────────────────────────────────────────────────
        from PySide6.QtWidgets import QHBoxLayout
        lgb = QGroupBox("DORI Legend"); lgb.setStyleSheet(self._gs())
        lgl = QVBoxLayout(lgb); lgl.setSpacing(3)
        for level, ppm in DORI_THRESHOLDS.items():
            rw = QWidget(); rl = QHBoxLayout(rw); rl.setContentsMargins(0, 0, 0, 0)
            sw = QLabel("  "); sw.setFixedSize(16, 12)
            sw.setStyleSheet(f"background:{DORI_HEX[level]};border-radius:2px;")
            rl.addWidget(sw); rl.addWidget(QLabel(f"{level}  ≥{ppm} PPM"))
            rl.addStretch(); lgl.addWidget(rw)
        ll.addWidget(lgb)

        hint = QLabel("3D: L-drag rotate · R-drag zoom\nM-drag pan · Scroll zoom")
        hint.setStyleSheet(f"color:{TH('text2')};font-size:8px;")
        ll.addWidget(hint)

        self._warn_lbl = QLabel("")
        self._warn_lbl.setStyleSheet(f"color:{TH('warn')};font-size:8px;font-weight:bold;")
        self._warn_lbl.setWordWrap(True)
        ll.addWidget(self._warn_lbl)
        ll.addStretch()

    def refresh_model_label(self):
        if self._model_lbl:
            self._model_lbl.setText(self._model_text())

    def _rebuild_styles(self):
        """Re-apply all QSS after a theme change."""
        gs = self._gs()
        for child in self.findChildren(QGroupBox):
            child.setStyleSheet(gs)
        for child in self.findChildren(QPushButton):
            child.setStyleSheet(self._btn_style())
        self._warn_lbl.setStyleSheet(
            f"color:{TH('warn')};font-size:8px;font-weight:bold;")
        self.update()

    def refresh_focal_slider(self):
        sl = self._sliders["focal"]
        sl.setMinimum(int(CAMERA_MODEL["f_min"]*10))
        sl.setMaximum(int(CAMERA_MODEL["f_max"]*10))
        sl.setValue(max(sl.minimum(), min(sl.maximum(), sl.value())))

    def _model_text(self):
        m  = CAMERA_MODEL
        sw = m.get("sensor_width", 0.0)
        if sw == 0.0:
            fov_txt = (f"H-FOV: {m['H_max']:.1f}°–{m['H_min']:.1f}°  "
                       f"V-FOV: {m['V_max']:.1f}°–{m['V_min']:.1f}°<br>"
                       f"<i>Mode: datasheet angles</i>")
        else:
            fmt    = m.get("sensor_format", "")
            ar     = m.get("aspect_name", "")
            sh     = sw / m.get("aspect_ratio", 16/9)
            H_fmin = fov_from_sensor(m["f_min"], sw)
            H_fmax = fov_from_sensor(m["f_max"], sw)
            V_fmin = fov_from_sensor(m["f_min"], sh)
            V_fmax = fov_from_sensor(m["f_max"], sh)
            fov_txt = (f"Sensor: {fmt}  ({sw:.3f}×{sh:.3f} mm)  {ar}<br>"
                       f"H-FOV: {H_fmin:.1f}°–{H_fmax:.1f}°  "
                       f"V-FOV: {V_fmin:.1f}°–{V_fmax:.1f}°<br>"
                       f"<i>Mode: sensor physics</i>")
        return (f"<b>{m['name']}</b><br>"
                f"f: {m['f_min']}–{m['f_max']} mm  |  R: {m['R_H']} px<br>"
                f"{fov_txt}")

    def get_params(self):
        s = self._sliders
        return {
            "f":       s["focal"].value()   / 10,
            "H":       s["height"].value()  / 10,
            "tgt_d":   s["tgt_d"].value()   / 10,
            "tgt_h":   s["tgt_h"].value()   / 10,
            "bearing": s["bearing"].value(),
        }

    def update_stats(self, geo, warn):
        self._warn_lbl.setText(warn)
        if not geo:
            for v in self._stats.values(): v.setText("—")
            return
        d = geo["dori"]
        self._stats["H_angle"].setText(   f"{geo['H_angle']:.1f}°")
        self._stats["V_angle"].setText(   f"{geo['V_angle']:.1f}°")
        self._stats["tilt"].setText(      f"{geo['tilt']:.1f}°")
        self._stats["D_near"].setText(    f"{geo['D_near']:.2f} m")
        self._stats["D_far"].setText(     f"{geo['D_far']:.2f} m")
        self._stats["render_far"].setText(f"{geo['render_far']:.2f} m")
        self._stats["W_near"].setText(    f"{geo['W_near']:.2f} m")
        self._stats["W_far"].setText(     f"{geo['W_render']:.2f} m")
        self._stats["area"].setText(      f"{geo['area']:.1f} m²")
        km = {"d_ident": "Identification", "d_recog": "Recognition",
              "d_obs":   "Observation",    "d_det":   "Detection"}
        for sk, lv in km.items():
            info = d[lv]; sfx = "" if info["within_render"] else " ⚠"
            self._stats[sk].setText(f"{info['D_effective']:.1f} m{sfx}")

    def _gs(self):
        return f"""
        QGroupBox {{
            color:{TH('text')}; font-weight:bold; font-size:10px;
            border:1px solid {TH('border')}; border-radius:5px;
            margin-top:8px; padding-top:6px;
            background:{TH('bg2')};
        }}
        QGroupBox::title {{
            subcontrol-origin:margin; left:8px; padding:0 4px;
            background:{TH('bg2')};
        }}
        QLabel {{ color:{TH('text2')}; font-size:9px; }}
        QSlider::groove:horizontal {{
            height:4px; background:{TH('border')}; border-radius:2px;
        }}
        QSlider::handle:horizontal {{
            background:{TH('accent')}; width:14px; height:14px;
            margin:-5px 0; border-radius:7px;
        }}
        QSlider::sub-page:horizontal {{
            background:{TH('accent2')}; border-radius:2px;
        }}
        """

    def _btn_style(self):
        return f"""
        QPushButton {{
            background:{TH('accent')}; color:#ffffff;
            border:none; border-radius:4px;
            padding:5px 10px; font-size:9px; font-weight:bold;
        }}
        QPushButton:hover {{ background:{TH('accent2')}; }}
        QPushButton:pressed {{ background:{TH('accent')}; }}
        """
