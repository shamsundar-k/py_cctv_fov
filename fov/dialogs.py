import copy

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QWidget, QLabel, QFrame, QDialogButtonBox,
    QDoubleSpinBox, QSpinBox, QLineEdit, QComboBox, QRadioButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .theme import TH
from .constants import (
    SENSOR_FORMAT_NAMES, SENSOR_FORMAT_WIDTHS,
    ASPECT_RATIO_NAMES, ASPECT_RATIO_VALUES,
)
from .geometry import fov_from_sensor


class CameraParamsDialog(QDialog):
    """Edit camera model — sensor-based FOV calculation (primary) with
    manual angle fallback when no sensor data is available."""

    def __init__(self, model: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Camera Parameters")
        self.setMinimumWidth(440)
        self._model = copy.deepcopy(model)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Camera Optical Parameters")
        title.setFont(QFont("Arial", 11, QFont.Bold))
        title.setStyleSheet(f"color:{TH('accent')}; padding-bottom:4px;")
        layout.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color:{TH('sep')};"); layout.addWidget(sep)

        # ── helpers ──────────────────────────────────────────────────────
        def lbl(text, italic=False):
            l = QLabel(text); l.setFont(QFont("Arial", 9))
            style = f"color:{TH('text2')};"
            if italic: style += "font-style:italic;"
            l.setStyleSheet(style); return l

        def dspin(val, lo, hi, dec=2, suffix=""):
            s = QDoubleSpinBox(); s.setRange(lo, hi); s.setDecimals(dec)
            s.setValue(val); s.setMinimumWidth(130)
            if suffix: s.setSuffix(f"  {suffix}")
            s.setStyleSheet(self._spin_style()); return s

        def ispin(val, lo, hi, suffix=""):
            s = QSpinBox(); s.setRange(lo, hi); s.setValue(val)
            s.setMinimumWidth(130)
            if suffix: s.setSuffix(f"  {suffix}")
            s.setStyleSheet(self._spin_style()); return s

        def combo(items, current=""):
            c = QComboBox(); c.addItems(items)
            if current in items: c.setCurrentText(current)
            c.setMinimumWidth(130); c.setStyleSheet(self._combo_style())
            return c

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight); form.setSpacing(8)

        # ── Model name ────────────────────────────────────────────────────
        self._name = QLineEdit(self._model["name"])
        self._name.setStyleSheet(self._spin_style())
        form.addRow(lbl("Model Name"), self._name)

        self._R_H = ispin(self._model["R_H"], 320, 7680, "px")
        form.addRow(lbl("H Resolution"), self._R_H)

        s1 = QFrame(); s1.setFrameShape(QFrame.HLine)
        s1.setStyleSheet(f"color:{TH('sep')};"); form.addRow(s1)

        # ── Focal range ───────────────────────────────────────────────────
        self._f_min = dspin(self._model["f_min"], 1.0, 200.0, 1, "mm")
        self._f_max = dspin(self._model["f_max"], 1.0, 200.0, 1, "mm")
        form.addRow(lbl("Focal Length Min"), self._f_min)
        form.addRow(lbl("Focal Length Max"), self._f_max)

        s2 = QFrame(); s2.setFrameShape(QFrame.HLine)
        s2.setStyleSheet(f"color:{TH('sep')};"); form.addRow(s2)

        # ── FOV mode selector ─────────────────────────────────────────────
        mode_w = QWidget(); mode_l = QHBoxLayout(mode_w)
        mode_l.setContentsMargins(0, 0, 0, 0)
        self._rb_sensor = QRadioButton("Sensor-based  (physics)")
        self._rb_manual = QRadioButton("Manual angles  (interpolation)")
        self._rb_sensor.setStyleSheet(f"color:{TH('text')};font-size:9px;")
        self._rb_manual.setStyleSheet(f"color:{TH('text')};font-size:9px;")
        mode_l.addWidget(self._rb_sensor); mode_l.addWidget(self._rb_manual)
        mode_l.addStretch()
        form.addRow(lbl("FOV Method"), mode_w)

        s3 = QFrame(); s3.setFrameShape(QFrame.HLine)
        s3.setStyleSheet(f"color:{TH('sep')};"); form.addRow(s3)

        # ── Sensor section ────────────────────────────────────────────────
        self._sensor_lbl1 = lbl("Sensor Format")
        self._sensor_fmt  = combo(SENSOR_FORMAT_NAMES,
                                  self._model.get("sensor_format", '1/2.8"'))
        form.addRow(self._sensor_lbl1, self._sensor_fmt)

        self._sensor_lbl2 = lbl("Sensor Width")
        self._sensor_w    = dspin(self._model.get("sensor_width", 5.37),
                                  0.1, 50.0, 3, "mm")
        form.addRow(self._sensor_lbl2, self._sensor_w)

        self._ar_lbl   = lbl("Aspect Ratio")
        self._ar_combo = combo(ASPECT_RATIO_NAMES,
                               self._model.get("aspect_name", "16:9"))
        form.addRow(self._ar_lbl, self._ar_combo)

        # Live preview of computed angles
        self._preview_lbl = QLabel("")
        self._preview_lbl.setStyleSheet(
            f"color:{TH('accent')}; font-size:9px; font-weight:bold;")
        form.addRow(lbl("Computed at f_min / f_max"), self._preview_lbl)

        s4 = QFrame(); s4.setFrameShape(QFrame.HLine)
        s4.setStyleSheet(f"color:{TH('sep')};"); form.addRow(s4)

        # ── Manual angle section ──────────────────────────────────────────
        self._man_note = lbl("H-FOV wide at f_min, narrow at f_max", italic=True)
        form.addRow(self._man_note)
        self._H_max = dspin(self._model["H_max"], 1.0, 180.0, 1, "° at f_min")
        self._H_min = dspin(self._model["H_min"], 1.0, 180.0, 1, "° at f_max")
        self._V_max = dspin(self._model["V_max"], 1.0, 180.0, 1, "° at f_min")
        self._V_min = dspin(self._model["V_min"], 1.0, 180.0, 1, "° at f_max")
        self._lH_max = lbl("H-FOV at f_min (wide)")
        self._lH_min = lbl("H-FOV at f_max (narrow)")
        self._lV_max = lbl("V-FOV at f_min (wide)")
        self._lV_min = lbl("V-FOV at f_max (narrow)")
        form.addRow(self._lH_max, self._H_max)
        form.addRow(self._lH_min, self._H_min)
        form.addRow(self._lV_max, self._V_max)
        form.addRow(self._lV_min, self._V_min)

        layout.addLayout(form)

        # ── Error label ───────────────────────────────────────────────────
        self._err = QLabel("")
        self._err.setStyleSheet(f"color:{TH('warn')}; font-size:8px;")
        self._err.setWordWrap(True); layout.addWidget(self._err)

        # ── Buttons ───────────────────────────────────────────────────────
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Apply")
        btns.button(QDialogButtonBox.Ok).setStyleSheet(self._btn_style(True))
        btns.button(QDialogButtonBox.Cancel).setStyleSheet(self._btn_style(False))
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.setStyleSheet(f"""
            QDialog {{ background:{TH('bg2')}; }}
            QLabel  {{ color:{TH('text')}; font-size:9px; }}
        """)

        # ── Wire up signals ───────────────────────────────────────────────
        use_sensor = self._model.get("sensor_width", 0) > 0
        self._rb_sensor.setChecked(use_sensor)
        self._rb_manual.setChecked(not use_sensor)

        self._sensor_fmt.currentTextChanged.connect(self._on_sensor_fmt_changed)
        self._sensor_w.valueChanged.connect(self._update_preview)
        self._ar_combo.currentTextChanged.connect(self._update_preview)
        self._f_min.valueChanged.connect(self._update_preview)
        self._f_max.valueChanged.connect(self._update_preview)
        self._rb_sensor.toggled.connect(self._on_mode_changed)

        self._on_mode_changed()
        self._update_preview()

    # ── signal handlers ──────────────────────────────────────────────────────

    def _on_sensor_fmt_changed(self, fmt):
        w = SENSOR_FORMAT_WIDTHS.get(fmt, 0.0)
        if w > 0:
            self._sensor_w.setValue(w)
            self._sensor_w.setReadOnly(True)
            self._sensor_w.setStyleSheet(
                self._spin_style() + "QDoubleSpinBox{background:#f0f0f8;}")
        else:
            self._sensor_w.setReadOnly(False)
            self._sensor_w.setStyleSheet(self._spin_style())
        self._update_preview()

    def _on_mode_changed(self):
        sensor = self._rb_sensor.isChecked()
        for w in [self._sensor_lbl1, self._sensor_fmt,
                  self._sensor_lbl2, self._sensor_w,
                  self._ar_lbl, self._ar_combo, self._preview_lbl]:
            w.setVisible(sensor)
        for w in [self._man_note, self._lH_max, self._H_max,
                  self._lH_min, self._H_min,
                  self._lV_max, self._V_max,
                  self._lV_min, self._V_min]:
            w.setVisible(not sensor)
        self._update_preview()

    def _update_preview(self):
        if not self._rb_sensor.isChecked():
            self._preview_lbl.setText("")
            return
        sw   = self._sensor_w.value()
        ar   = ASPECT_RATIO_VALUES.get(self._ar_combo.currentText(), 16/9)
        sh   = sw / ar
        fmin = self._f_min.value()
        fmax = self._f_max.value()
        if fmin <= 0 or fmax <= 0 or fmin >= fmax:
            self._preview_lbl.setText("—")
            return
        H_at_fmin = fov_from_sensor(fmin, sw)
        H_at_fmax = fov_from_sensor(fmax, sw)
        V_at_fmin = fov_from_sensor(fmin, sh)
        V_at_fmax = fov_from_sensor(fmax, sh)
        self._preview_lbl.setText(
            f"H: {H_at_fmin:.1f}° → {H_at_fmax:.1f}°   "
            f"V: {V_at_fmin:.1f}° → {V_at_fmax:.1f}°"
        )

    # ── accept / get ─────────────────────────────────────────────────────────

    def _on_accept(self):
        f_min = self._f_min.value()
        f_max = self._f_max.value()
        errors = []
        if f_min >= f_max:
            errors.append("f_min must be less than f_max.")

        if self._rb_sensor.isChecked():
            sw = self._sensor_w.value()
            if sw <= 0:
                errors.append("Sensor width must be > 0.")
            if errors:
                self._err.setText("  ".join(errors)); return
            ar_name = self._ar_combo.currentText()
            ar      = ASPECT_RATIO_VALUES.get(ar_name, 16/9)
            sh      = sw / ar
            self._model.update({
                "name"          : self._name.text().strip() or "Custom Camera",
                "f_min"         : f_min,
                "f_max"         : f_max,
                "sensor_format" : self._sensor_fmt.currentText(),
                "sensor_width"  : sw,
                "aspect_ratio"  : ar,
                "aspect_name"   : ar_name,
                "H_max"         : fov_from_sensor(f_min, sw),
                "H_min"         : fov_from_sensor(f_max, sw),
                "V_max"         : fov_from_sensor(f_min, sh),
                "V_min"         : fov_from_sensor(f_max, sh),
                "R_H"           : self._R_H.value(),
            })
        else:
            H_max = self._H_max.value(); H_min = self._H_min.value()
            V_max = self._V_max.value(); V_min = self._V_min.value()
            if H_min >= H_max:
                errors.append("H-FOV at f_max must be < H-FOV at f_min.")
            if V_min >= V_max:
                errors.append("V-FOV at f_max must be < V-FOV at f_min.")
            if errors:
                self._err.setText("  ".join(errors)); return
            self._model.update({
                "name"         : self._name.text().strip() or "Custom Camera",
                "f_min"        : f_min,
                "f_max"        : f_max,
                "sensor_format": "",
                "sensor_width" : 0.0,
                "aspect_ratio" : 16/9,
                "aspect_name"  : "16:9",
                "H_max"        : H_max, "H_min": H_min,
                "V_max"        : V_max, "V_min": V_min,
                "R_H"          : self._R_H.value(),
            })
        self.accept()

    def get_model(self):
        return self._model

    # ── styles ────────────────────────────────────────────────────────────────

    def _spin_style(self):
        return f"""
            QDoubleSpinBox, QSpinBox, QLineEdit {{
                background:{TH('bg2')}; color:{TH('text')};
                border:1px solid {TH('border')}; border-radius:4px;
                padding:3px 6px;
            }}
            QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus {{
                border:1px solid {TH('accent')};
            }}
        """

    def _combo_style(self):
        return f"""
            QComboBox {{
                background:{TH('bg2')}; color:{TH('text')};
                border:1px solid {TH('border')}; border-radius:4px;
                padding:3px 6px;
            }}
            QComboBox:focus {{ border:1px solid {TH('accent')}; }}
            QComboBox::drop-down {{ border:none; }}
            QComboBox QAbstractItemView {{
                background:{TH('bg2')}; color:{TH('text')};
                selection-background-color:{TH('accent')};
                selection-color:#ffffff;
            }}
        """

    def _btn_style(self, primary=True):
        if primary:
            return (f"QPushButton{{background:{TH('accent')};color:#fff;"
                    f"border:none;border-radius:4px;padding:5px 16px;font-weight:bold;}}"
                    f"QPushButton:hover{{background:{TH('accent2')};}}")
        return (f"QPushButton{{background:{TH('panel')};color:{TH('text')};"
                f"border:1px solid {TH('border')};border-radius:4px;padding:5px 16px;}}"
                f"QPushButton:hover{{background:{TH('bg')};}}")
