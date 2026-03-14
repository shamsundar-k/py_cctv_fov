import math

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QPolygonF

from . import theme as _theme
from .theme import TH
from .constants import DORI_HEX


class Views2D(QWidget):
    def __init__(self):
        super().__init__()
        self.geo = None
        self.setMinimumSize(500, 600)

    def set_geometry(self, geo):
        self.geo = geo
        self.update()

    def _draw_label(self, p, x, y, text, text_col, font_size=8, bold=True):
        """Text with solid background pill for maximum legibility."""
        f = QFont("Arial", font_size, QFont.Bold if bold else QFont.Normal)
        p.setFont(f)
        fm  = p.fontMetrics()
        br  = fm.boundingRect(text)
        pad = 3
        rx  = int(x) - pad
        ry  = int(y) - br.height() - pad + 2
        rw  = br.width() + pad*2 + 2
        rh  = br.height() + pad*2
        bg  = QColor(TH("canvas_bg2")); bg.setAlpha(220)
        p.setBrush(QBrush(bg))
        p.setPen(QPen(QColor(text_col), 0.8))
        p.drawRoundedRect(rx, ry, rw, rh, 3, 3)
        p.setPen(QColor(text_col))
        p.drawText(int(x), int(y), text)

    def paintEvent(self, e):
        if not self.geo: return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(TH("canvas_bg")))
        W = self.width(); H = self.height(); half = H // 2
        self._draw_top_view (p, 0, 0,    W, half)
        self._draw_divider  (p, W, half)
        self._draw_side_view(p, 0, half, W, H - half)
        p.end()

    def _draw_divider(self, p, W, y):
        p.setPen(QPen(QColor(TH("divider")), 2))
        p.drawLine(0, y, W, y)

    def _margins(self): return 52, 30, 18, 36

    # ── SIDE VIEW ─────────────────────────────────────────────────────────────
    def _draw_side_view(self, p, ox, oy, W, H):
        geo = self.geo
        ml, mt, mr, mb = self._margins()
        pw = W-ml-mr; ph = H-mt-mb
        if pw <= 0 or ph <= 0: return

        cam_h = geo["H"];        tgt_d  = geo["target_dist"]
        tgt_h = geo["target_h"]; D_near = geo["D_near"]
        D_far = geo["D_far"];    rf     = geo["render_far"]
        tilt  = geo["tilt"];     half_v = geo["half_v"]
        dori  = geo["dori"]

        max_d = max(rf*1.15, tgt_d*1.1)
        max_h = cam_h * 1.35

        def wx(d): return ox+ml + d/max_d*pw
        def wy(h): return oy+mt+ph - h/max_h*ph

        # Plot background
        p.fillRect(int(ox+ml), int(oy+mt), int(pw), int(ph), QColor(TH("canvas_bg2")))

        # Grid
        p.setPen(QPen(QColor(TH("grid")), 0.8))
        h_step = max(1, int(max_h/5))
        step   = max(1, int(max_d/8))
        d = 0
        while d <= max_d:
            p.drawLine(int(wx(d)), int(oy+mt), int(wx(d)), int(oy+mt+ph)); d += step
        hv = 0
        while hv <= max_h:
            p.drawLine(int(ox+ml), int(wy(hv)), int(ox+ml+pw), int(wy(hv))); hv += h_step

        # Ground line
        p.setPen(QPen(QColor(TH("ground")), 1.5))
        p.drawLine(int(wx(0)), int(wy(0)), int(wx(max_d)), int(wy(0)))

        # DORI zone polygons
        zone_order = [
            ("Detection",      dori["Observation"]["D_effective"],    dori["Detection"]["D_effective"]),
            ("Observation",    dori["Recognition"]["D_effective"],    dori["Observation"]["D_effective"]),
            ("Recognition",    dori["Identification"]["D_effective"], dori["Recognition"]["D_effective"]),
            ("Identification", D_near,                                dori["Identification"]["D_effective"]),
        ]
        def top_ray(d): return cam_h - d*math.tan(math.radians(tilt)-half_v)
        def bot_ray(d): return max(cam_h - d*math.tan(math.radians(tilt)+half_v), 0)

        for level, di, do in zone_order:
            di2 = max(di, D_near); do2 = min(do, rf)
            if do2 <= di2+0.01: continue
            col = QColor(DORI_HEX[level])
            col.setAlpha(130 if not _theme.DARK_MODE else 110)
            pts = [QPointF(wx(di2), wy(max(top_ray(di2), 0))),
                   QPointF(wx(do2), wy(max(top_ray(do2), 0))),
                   QPointF(wx(do2), wy(bot_ray(do2))),
                   QPointF(wx(di2), wy(bot_ray(di2)))]
            p.setBrush(QBrush(col)); p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF(pts))
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(DORI_HEX[level]), 1.5))
            p.drawPolygon(QPolygonF(pts))

        # Region beyond Detection threshold (below any DORI level)
        d_det = dori["Detection"]["D_effective"]
        if rf > d_det + 0.01:
            bc = QColor("#505878"); bc.setAlpha(55)
            pts = [QPointF(wx(d_det), wy(max(top_ray(d_det), 0))),
                   QPointF(wx(rf),    wy(max(top_ray(rf),    0))),
                   QPointF(wx(rf),    wy(bot_ray(rf))),
                   QPointF(wx(d_det), wy(bot_ray(d_det)))]
            p.setBrush(QBrush(bc)); p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF(pts))
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor("#6a7a8a"), 1.0, Qt.DashLine))
            p.drawPolygon(QPolygonF(pts))
            mx = wx((d_det + rf) / 2)
            self._draw_label(p, mx-14, wy(max(top_ray((d_det+rf)/2), 0))+14,
                             "< Det.", "#8899aa", 7, bold=False)

        # FOV rays
        # Top ray: camera → render_far at the projected height
        # Bottom ray: camera → D_near (where it hits the ground), then along ground to rf
        cam_px = wx(0); cam_py = wy(cam_h)
        p.setPen(QPen(QColor(TH("fov_ray")), 2.0))
        p.drawLine(int(cam_px), int(cam_py), int(wx(rf)), int(wy(max(top_ray(rf), 0))))
        p.drawLine(int(cam_px), int(cam_py), int(wx(D_near)), int(wy(0)))
        p.drawLine(int(wx(D_near)), int(wy(0)), int(wx(rf)), int(wy(0)))

        # Near-field dashed
        p.setPen(QPen(QColor(TH("fov_near")), 1, Qt.DashLine))
        p.drawLine(int(wx(D_near)), int(wy(0)), int(wx(D_near)), int(wy(cam_h)))

        # Target distance dashed
        p.setPen(QPen(QColor(TH("tgt_dist")), 1.5, Qt.DashLine))
        p.drawLine(int(wx(tgt_d)), int(wy(0)), int(wx(tgt_d)), int(oy+mt))

        # Target height bar
        p.setPen(QPen(QColor(TH("tgt_h")), 2.5))
        p.drawLine(int(wx(tgt_d)), int(wy(0)), int(wx(tgt_d)), int(wy(tgt_h)))
        p.drawLine(int(wx(tgt_d))-6, int(wy(tgt_h)), int(wx(tgt_d))+6, int(wy(tgt_h)))

        # Camera body + pole
        p.setPen(QPen(QColor(TH("cam_pole")), 2))
        p.drawLine(int(cam_px), int(wy(0)), int(cam_px), int(cam_py))
        p.setBrush(QBrush(QColor(TH("cam_body"))))
        p.setPen(QPen(QColor(TH("cam_body")), 1))
        p.drawRect(int(cam_px)-5, int(cam_py)-4, 12, 8)

        # DORI boundary ticks + labels
        p.setFont(QFont("Arial", 7, QFont.Bold))
        for level, info in dori.items():
            de = info["D_effective"]
            if de < D_near+0.1: continue
            p.setPen(QPen(QColor(DORI_HEX[level]), 2))
            p.drawLine(int(wx(de)), int(wy(0)), int(wx(de)), int(wy(0))+6)
            self._draw_label(p, wx(de)-14, wy(0)+22, f"{de:.1f}m", DORI_HEX[level], 7)

        # Target labels
        self._draw_label(p, wx(tgt_d)+3, wy(0)+22, f"Tgt {tgt_d:.0f}m", TH("tgt_dist"), 7)
        self._draw_label(p, wx(tgt_d)+5, wy(tgt_h)-2, f"Tgt H {tgt_h:.1f}m", TH("tgt_h"), 7)

        # Axis tick values
        p.setFont(QFont("Arial", 7)); p.setPen(QColor(TH("tick")))
        d = 0
        while d <= max_d:
            p.drawLine(int(wx(d)), int(wy(0)), int(wx(d)), int(wy(0))+3)
            p.drawText(int(wx(d))-8, int(wy(0))+12, f"{d:.0f}"); d += step
        hv = 0
        while hv <= max_h:
            p.drawLine(int(ox+ml)-3, int(wy(hv)), int(ox+ml), int(wy(hv)))
            p.drawText(ox+2, int(wy(hv))+4, f"{hv:.0f}"); hv += h_step

        # Axis labels
        p.setFont(QFont("Arial", 8, QFont.Bold)); p.setPen(QColor(TH("axis_lbl")))
        p.drawText(ox+ml+pw//2-20, oy+mt+ph+28, "Distance (m)")
        p.save(); p.translate(ox+12, oy+mt+ph//2); p.rotate(-90)
        p.drawText(-20, 0, "Height (m)"); p.restore()

        # Plot border
        p.setBrush(Qt.NoBrush); p.setPen(QPen(QColor(TH("border")), 1))
        p.drawRect(int(ox+ml), int(oy+mt), int(pw), int(ph))

        # Title
        p.setFont(QFont("Arial", 9, QFont.Bold)); p.setPen(QColor(TH("title")))
        p.drawText(ox+ml, oy+20,
            f"Side View  —  tilt={geo['tilt']:.1f}°  "
            f"D_near={D_near:.1f}m  D_far={D_far:.1f}m")

    # ── TOP VIEW ──────────────────────────────────────────────────────────────
    def _draw_top_view(self, p, ox, oy, W, H):
        geo = self.geo
        ml, mt, mr, mb = self._margins()
        pw = W-ml-mr; ph = H-mt-mb
        if pw <= 0 or ph <= 0: return

        D_near = geo["D_near"]; rf    = geo["render_far"]
        D_far  = geo["D_far"];  tgt_d = geo["target_dist"]
        hh     = geo["half_h"]; dori  = geo["dori"]

        max_d = max(rf*1.15, tgt_d*1.1)
        max_w = max_d * math.tan(hh) * 1.3

        def w2p(d, lat):
            return (ox+ml + d/max_d*pw,
                    oy+mt+ph//2 - lat/max_w*(ph//2))

        # Plot background
        p.fillRect(int(ox+ml), int(oy+mt), int(pw), int(ph), QColor(TH("canvas_bg2")))

        # Grid
        p.setPen(QPen(QColor(TH("grid")), 0.8))
        step = max(1, int(max_d/8)); d = 0
        while d <= max_d:
            x, _ = w2p(d, 0); p.drawLine(int(x), oy+mt, int(x), oy+mt+ph); d += step
        lat_step = max(1, int(max_w/4)); lat = -int(max_w)
        while lat <= max_w:
            _, y = w2p(0, lat); p.drawLine(ox+ml, int(y), ox+ml+pw, int(y)); lat += lat_step

        # Camera axis dotted line
        cam_px, cam_py = w2p(0, 0); far_cx, far_cy = w2p(rf, 0)
        p.setPen(QPen(QColor(TH("fov_near")), 1, Qt.DotLine))
        p.drawLine(int(cam_px), int(cam_py), int(far_cx), int(far_cy))

        # DORI zones
        zone_order = [
            ("Detection",      dori["Observation"]["D_effective"],    dori["Detection"]["D_effective"]),
            ("Observation",    dori["Recognition"]["D_effective"],    dori["Observation"]["D_effective"]),
            ("Recognition",    dori["Identification"]["D_effective"], dori["Recognition"]["D_effective"]),
            ("Identification", D_near,                                dori["Identification"]["D_effective"]),
        ]
        for level, di, do in zone_order:
            di2 = max(di, D_near); do2 = min(do, rf)
            if do2 <= di2+0.01: continue
            th = math.tan(hh); col = QColor(DORI_HEX[level])
            col.setAlpha(130 if not _theme.DARK_MODE else 120)
            p1x, p1y = w2p(di2, -di2*th); p2x, p2y = w2p(di2,  di2*th)
            p3x, p3y = w2p(do2,  do2*th); p4x, p4y = w2p(do2, -do2*th)
            poly = QPolygonF([QPointF(p1x, p1y), QPointF(p2x, p2y),
                              QPointF(p3x, p3y), QPointF(p4x, p4y)])
            p.setBrush(QBrush(col)); p.setPen(Qt.NoPen); p.drawPolygon(poly)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(DORI_HEX[level]), 1.5)); p.drawPolygon(poly)

        # Region beyond Detection threshold (below any DORI level)
        th = math.tan(hh)
        d_det = dori["Detection"]["D_effective"]
        if rf > d_det + 0.01:
            bc = QColor("#505878"); bc.setAlpha(55)
            p1x, p1y = w2p(d_det, -d_det*th); p2x, p2y = w2p(d_det,  d_det*th)
            p3x, p3y = w2p(rf,     rf*th);     p4x, p4y = w2p(rf,    -rf*th)
            poly = QPolygonF([QPointF(p1x, p1y), QPointF(p2x, p2y),
                              QPointF(p3x, p3y), QPointF(p4x, p4y)])
            p.setBrush(QBrush(bc)); p.setPen(Qt.NoPen); p.drawPolygon(poly)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor("#6a7a8a"), 1.0, Qt.DashLine)); p.drawPolygon(poly)
            mx, my = w2p((d_det + rf) / 2, 0)
            self._draw_label(p, mx-14, my-5, "< Det.", "#8899aa", 7, bold=False)

        # FOV boundary lines
        th = math.tan(hh)
        fl_x, fl_y = w2p(rf, -rf*th); fr_x, fr_y = w2p(rf,  rf*th)
        nl_x, nl_y = w2p(D_near, -D_near*th); nr_x, nr_y = w2p(D_near,  D_near*th)
        p.setPen(QPen(QColor(TH("fov_ray")), 2.0))
        p.drawLine(int(cam_px), int(cam_py), int(fl_x), int(fl_y))
        p.drawLine(int(cam_px), int(cam_py), int(fr_x), int(fr_y))
        p.drawLine(int(nl_x), int(nl_y), int(nr_x), int(nr_y))
        p.drawLine(int(fl_x), int(fl_y), int(fr_x), int(fr_y))

        # Target distance dashed
        tl_x, tl_y = w2p(tgt_d, -tgt_d*th*1.1); tr_x, tr_y = w2p(tgt_d, tgt_d*th*1.1)
        p.setPen(QPen(QColor(TH("tgt_dist")), 1.8, Qt.DashLine))
        p.drawLine(int(tl_x), int(tl_y), int(tr_x), int(tr_y))

        # DORI boundary lines + labels
        p.setFont(QFont("Arial", 7, QFont.Bold))
        for level, info in dori.items():
            de = info["D_effective"]
            if de < D_near+0.1: continue
            lx, ly = w2p(de, -de*th); rx, ry = w2p(de, de*th)
            p.setPen(QPen(QColor(DORI_HEX[level]), 2.0))
            p.drawLine(int(lx), int(ly), int(rx), int(ry))
            mx, my = w2p(de, 0)
            self._draw_label(p, mx-14, my-5, f"{de:.1f}m", DORI_HEX[level], 7)

        # Target distance label
        tx, ty = w2p(tgt_d, 0)
        self._draw_label(p, tx+3, ty-6, f"Tgt {tgt_d:.0f}m", TH("tgt_dist"), 7)

        # Camera dot
        p.setBrush(QBrush(QColor(TH("cam_body"))))
        p.setPen(QPen(QColor(TH("cam_body")), 1))
        p.drawEllipse(int(cam_px)-5, int(cam_py)-5, 10, 10)

        # Axis tick values
        p.setFont(QFont("Arial", 7)); p.setPen(QColor(TH("tick")))
        step = max(1, int(max_d/8)); d = 0
        while d <= max_d:
            x, _ = w2p(d, 0); _, py_b = w2p(0, -max_w)
            p.drawLine(int(x), int(py_b), int(x), int(py_b)+3)
            p.drawText(int(x)-8, int(py_b)+13, f"{d:.0f}"); d += step
        lat_step = max(1, int(max_w/4)); lat = -int(max_w)
        while lat <= max_w:
            _, y = w2p(0, lat)
            p.drawLine(ox+ml-3, int(y), ox+ml, int(y))
            p.drawText(ox+ml-28, int(y)+4, f"{lat:.0f}"); lat += lat_step

        # Axis labels
        p.setFont(QFont("Arial", 8, QFont.Bold)); p.setPen(QColor(TH("axis_lbl")))
        p.drawText(ox+ml+pw//2-20, oy+mt+ph+28, "Distance (m)")
        p.save(); p.translate(ox+12, oy+mt+ph//2); p.rotate(-90)
        p.drawText(-25, 0, "Lateral (m)"); p.restore()

        # Plot border
        p.setBrush(Qt.NoBrush); p.setPen(QPen(QColor(TH("border")), 1))
        p.drawRect(int(ox+ml), int(oy+mt), int(pw), int(ph))

        # Title
        p.setFont(QFont("Arial", 9, QFont.Bold)); p.setPen(QColor(TH("title")))
        p.drawText(ox+ml, oy+20,
            f"Top View  —  H-FOV={geo['H_angle']:.1f}°  "
            f"W_near={geo['W_near']:.1f}m  W_far={geo['W_render']:.1f}m")
