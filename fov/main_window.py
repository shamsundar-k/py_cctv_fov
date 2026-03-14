from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTabWidget, QPushButton, QDialog,
)
from PySide6.QtCore import Qt, QTimer  # Qt still used for PointingHandCursor
from PySide6.QtGui import QColor, QPalette

from . import theme as _theme
from .theme import TH
from .constants import CAMERA_MODEL
from .geometry import compute_geometry
from .dialogs import CameraParamsDialog
from .gl_view import GLView
from .views2d import Views2D
from .control_panel import ControlPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCTV FOV Visualiser — 3D + 2D DORI Analysis")
        self.resize(1600, 900)

        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(40)
        self._debounce.timeout.connect(self._refresh)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # Left column: theme button on top + control panel below
        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self._theme_btn = QPushButton("🌙  Dark Mode")
        self._theme_btn.setFixedHeight(30)
        self._theme_btn.setCursor(Qt.PointingHandCursor)
        self._theme_btn.clicked.connect(self._toggle_theme)
        self._theme_btn.setStyleSheet(self._theme_btn_style())
        left_layout.addWidget(self._theme_btn)

        self._ctrl = ControlPanel(
            on_change=lambda: self._debounce.start(),
            on_cam_params=self._open_cam_params,
        )
        left_layout.addWidget(self._ctrl)
        root.addWidget(left_col)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(self._tab_style())
        self._gl  = GLView()
        self._v2d = Views2D()
        self._tabs.addTab(self._gl,  "3D View")
        self._tabs.addTab(self._v2d, "2D View")
        root.addWidget(self._tabs, 1)

        self._apply_palette()
        self._refresh()

    def _tab_style(self):
        return f"""
            QTabWidget::pane {{
                border:1px solid {TH('border')}; border-radius:4px;
                background:{TH('bg2')};
            }}
            QTabBar::tab {{
                background:{TH('panel')}; color:{TH('text')};
                border:1px solid {TH('border')}; border-bottom:none;
                border-radius:4px 4px 0 0;
                padding:6px 24px; font-size:10px; font-weight:bold;
            }}
            QTabBar::tab:selected {{
                background:{TH('accent')}; color:#ffffff;
            }}
            QTabBar::tab:hover:!selected {{
                background:{TH('bg')}; color:{TH('text')};
            }}
        """

    def _theme_btn_style(self):
        return (f"QPushButton{{background:{TH('accent')};color:#ffffff;"
                f"border:none;border-radius:4px;padding:4px 12px;"
                f"font-size:10px;font-weight:bold;}}"
                f"QPushButton:hover{{background:{TH('accent2')};}}")

    def _toggle_theme(self):
        _theme.DARK_MODE = not _theme.DARK_MODE
        self._theme_btn.setText("☀  Light Mode" if _theme.DARK_MODE else "🌙  Dark Mode")
        self._apply_palette()
        self._theme_btn.setStyleSheet(self._theme_btn_style())
        self._ctrl._rebuild_styles()
        self._tabs.setStyleSheet(self._tab_style())
        self._v2d.update()

    def _apply_palette(self):
        app = QApplication.instance()
        pal = QPalette()
        pal.setColor(QPalette.Window,          QColor(TH("bg")))
        pal.setColor(QPalette.WindowText,      QColor(TH("text")))
        pal.setColor(QPalette.Base,            QColor(TH("bg2")))
        pal.setColor(QPalette.AlternateBase,   QColor(TH("panel")))
        pal.setColor(QPalette.Text,            QColor(TH("text")))
        pal.setColor(QPalette.Button,          QColor(TH("panel")))
        pal.setColor(QPalette.ButtonText,      QColor(TH("text")))
        pal.setColor(QPalette.Highlight,       QColor(TH("accent")))
        pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.Mid,             QColor(TH("border")))
        pal.setColor(QPalette.Dark,            QColor(TH("border")))
        pal.setColor(QPalette.Light,           QColor(TH("bg2")))
        app.setPalette(pal)
        self.update()

    def _open_cam_params(self):
        dlg = CameraParamsDialog(CAMERA_MODEL, parent=self)
        if dlg.exec() == QDialog.Accepted:
            CAMERA_MODEL.update(dlg.get_model())
            self._ctrl.refresh_model_label()
            self._ctrl.refresh_focal_slider()
            self._debounce.start()

    def _refresh(self):
        pr = self._ctrl.get_params()
        geo, warn = compute_geometry(
            pr["f"], pr["H"], pr["tgt_d"], pr["tgt_h"], CAMERA_MODEL)
        self._ctrl.update_stats(geo, warn)
        if geo:
            self._gl.set_geometry(geo, pr["bearing"])
            self._v2d.set_geometry(geo)
