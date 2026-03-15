import math

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QColor, QPainter
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
from OpenGL.GLU import gluPerspective, gluLookAt, gluProject

from .constants import DORI_RGBA, DORI_SOLID, DORI_HEX, BLIND_SPOT_RGBA, BLIND_SPOT_HEX, BLIND_SPOT_SOLID


class GLView(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.geo     = None
        self.bearing = 0.0
        self._rx     = 35.0
        self._rz     = -30.0
        self._zoom   = 1.0
        self._px     = 0.0
        self._py     = 0.0
        self._last   = QPoint()
        self._labels = []
        self._mv = self._pj = self._vp = None   # matrices captured in paintGL
        self.setMinimumSize(500, 480)

    def set_geometry(self, geo, bearing):
        self.geo          = geo
        self.bearing      = bearing
        geo["bearing"]    = bearing
        self.update()

    def mousePressEvent(self, e): self._last = e.position().toPoint()
    def mouseMoveEvent(self, e):
        dx = e.position().x() - self._last.x()
        dy = e.position().y() - self._last.y()
        if   e.buttons() & Qt.LeftButton:
            self._rz += dx*0.5; self._rx += dy*0.5
        elif e.buttons() & Qt.RightButton:
            self._zoom = max(0.1, min(10, self._zoom*(1+dy*0.005)))
        elif e.buttons() & Qt.MiddleButton:
            self._px += dx*0.05; self._py -= dy*0.05
        self._last = e.position().toPoint()
        self.update()

    def wheelEvent(self, e):
        self._zoom = max(0.1, min(10, self._zoom*(1+e.angleDelta().y()*0.001)))
        self.update()

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST); glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # GL_LINE_SMOOTH is NOT enabled globally: on Ubuntu/Mesa it implicitly
        # activates polygon-smooth coverage which overrides glColor4f alpha for
        # filled quads and causes all DORI zones to render as the first zone's
        # colour (green).  We enable it only locally around actual line draws.
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glClearColor(0.10, 0.10, 0.16, 1.0)

    def resizeGL(self, w, h): glViewport(0, 0, w, max(h, 1))

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(45, self.width()/max(self.height(), 1), 0.1, 2000)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()

        geo   = self.geo
        D_ref = geo["render_far"] if geo else 20.0
        cd    = D_ref * 2.5 / self._zoom
        gluLookAt(0, -cd, cd*0.8, 0, 0, 0, 0, 0, 1)
        glTranslatef(self._px, self._py, 0)
        glRotatef(self._rx, 1, 0, 0); glRotatef(self._rz, 0, 0, 1)

        if not geo: return
        self._labels = []
        b = self.bearing
        self._ground(geo)
        self._grid(geo)
        self._blind_spot_3d(geo, b)
        self._dori_zones_3d(geo, b)
        self._fov_outline_3d(geo, b)
        self._target_line(geo, b)
        self._camera_body(geo, b)
        self._north(geo)
        self._axes(geo)

        # Capture matrices here while the GL context state is still valid
        try:
            self._mv = glGetDoublev(GL_MODELVIEW_MATRIX)
            self._pj = glGetDoublev(GL_PROJECTION_MATRIX)
            self._vp = glGetIntegerv(GL_VIEWPORT)
        except Exception:
            self._mv = self._pj = self._vp = None

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _frustum_3d_corners(self, d, geo, b):
        """Return [BL, BR, TR, TL] 3D corners of the FOV cross-section at
        horizontal distance d.  BL/BR sit on the ground (z=0); TR/TL rise to
        the upper FOV boundary height at that distance."""
        tilt_rad = math.radians(geo["tilt"])
        half_v   = geo["half_v"]        # radians
        half_h   = geo["half_h"]        # radians
        H        = geo["H"]
        brad     = math.radians(b)
        cb, sb   = math.cos(brad), math.sin(brad)
        w        = d * math.tan(half_h)
        # Top ray hits z = H - d*tan(tilt - half_v); clamp to ≥ 0
        z_top    = max(0.0, H - d * math.tan(tilt_rad - half_v))
        # Lateral unit vector: left = (-cb, sb), right = (cb, -sb)
        bl = (d*sb - w*cb,  d*cb + w*sb,  0.0)
        br = (d*sb + w*cb,  d*cb - w*sb,  0.0)
        tr = (d*sb + w*cb,  d*cb - w*sb,  z_top)
        tl = (d*sb - w*cb,  d*cb + w*sb,  z_top)
        return [bl, br, tr, tl]   # 0=BL, 1=BR, 2=TR, 3=TL

    def _dashed_line3d(self, p0, p1, dash=0.4, gap=0.25):
        """Draw a dashed 3D line by emitting short GL_LINES segments."""
        dx = p1[0]-p0[0]; dy = p1[1]-p0[1]; dz = p1[2]-p0[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if dist < 0.01: return
        nx, ny, nz = dx/dist, dy/dist, dz/dist
        t = 0.0; drawing = True
        glEnable(GL_LINE_SMOOTH)
        glBegin(GL_LINES)
        while t < dist:
            seg = dash if drawing else gap
            t2  = min(t + seg, dist)
            if drawing:
                glVertex3f(p0[0]+nx*t,  p0[1]+ny*t,  p0[2]+nz*t)
                glVertex3f(p0[0]+nx*t2, p0[1]+ny*t2, p0[2]+nz*t2)
            t = t2; drawing = not drawing
        glEnd()
        glDisable(GL_LINE_SMOOTH)

    # ── Scene elements ─────────────────────────────────────────────────────────

    def _ground(self, geo):
        s = max(geo["render_far"]*2.2, 20)
        glColor4f(0.12, 0.12, 0.20, 0.7)
        glBegin(GL_QUADS)
        glVertex3f(-s, -s, 0); glVertex3f(s, -s, 0)
        glVertex3f(s,  s,  0); glVertex3f(-s, s, 0)
        glEnd()

    def _grid(self, geo):
        s    = max(geo["render_far"]*2.2, 20)
        step = max(1.0, round(s/15))
        glColor4f(0.22, 0.22, 0.38, 0.8); glLineWidth(0.5)
        glEnable(GL_LINE_SMOOTH)
        glBegin(GL_LINES)
        x = -s
        while x <= s+.01:
            glVertex3f(x, -s, .002); glVertex3f(x, s, .002); x += step
        y = -s
        while y <= s+.01:
            glVertex3f(-s, y, .002); glVertex3f(s, y, .002); y += step
        glEnd()
        glDisable(GL_LINE_SMOOTH)

    def _blind_spot_3d(self, geo, b):
        dn = geo["D_near"]
        H  = geo["H"]
        if dn <= 0.1: return

        # Ground corners at D_near
        n = self._frustum_3d_corners(dn, geo, b)   # [BL, BR, TR, TL]
        cam = (0.0, 0.0, H)
        pole_base = (0.0, 0.0, 0.0)

        r, g, bv, a = BLIND_SPOT_RGBA
        glDepthMask(GL_FALSE)

        # ── Filled Faces ──────────────────────────────────────────────────
        # Ground triangle (pole base to near edge)
        glColor4f(r, g, bv, a * 0.6)
        glBegin(GL_TRIANGLES)
        glVertex3f(*pole_base); glVertex3f(*n[0]); glVertex3f(*n[1])
        glEnd()

        # Side faces of the "dead wedge"
        glColor4f(r, g, bv, a * 0.45)
        glBegin(GL_TRIANGLES)
        # Left side: cam -> pole_base -> BL
        glVertex3f(*cam); glVertex3f(*pole_base); glVertex3f(*n[0])
        # Right side: cam -> pole_base -> BR
        glVertex3f(*cam); glVertex3f(*pole_base); glVertex3f(*n[1])
        glEnd()

        # Back face (under the near FOV face): cam -> BL -> BR
        glColor4f(r, g, bv, a * 0.55)
        glBegin(GL_TRIANGLES)
        glVertex3f(*cam); glVertex3f(*n[0]); glVertex3f(*n[1])
        glEnd()

        glDepthMask(GL_TRUE)

        # ── Outline ───────────────────────────────────────────────────────
        glColor4f(*BLIND_SPOT_SOLID); glLineWidth(2.0)
        glBegin(GL_LINE_LOOP)
        glVertex3f(*pole_base); glVertex3f(*n[0]); glVertex3f(*n[1])
        glEnd()
        glBegin(GL_LINES)
        glVertex3f(*cam); glVertex3f(*n[0])
        glVertex3f(*cam); glVertex3f(*n[1])
        glEnd()

        # Label at midpoint of blind spot
        mx = (n[0][0]+n[1][0])/4; my = (n[0][1]+n[1][1])/4
        self._labels.append((mx, my, 0.0, "Blind Spot", BLIND_SPOT_HEX))

    def _dori_zones_3d(self, geo, b):
        dn   = geo["D_near"]
        df   = geo["render_far"]
        dori = geo["dori"]

        # Render order: farthest first for correct alpha blending
        order = [
            ("Detection",
             dori["Observation"]["D_effective"],
             dori["Detection"]["D_effective"]),
            ("Observation",
             dori["Recognition"]["D_effective"],
             dori["Observation"]["D_effective"]),
            ("Recognition",
             dori["Identification"]["D_effective"],
             dori["Recognition"]["D_effective"]),
            ("Identification", dn,
             dori["Identification"]["D_effective"]),
        ]

        glDepthMask(GL_FALSE)   # don't write depth for transparent fills

        for level, di, do in order:
            di2 = max(di, dn);  do2 = min(do, df)
            if do2 <= di2 + 0.01: continue
            n = self._frustum_3d_corners(di2, geo, b)   # [BL, BR, TR, TL]
            f = self._frustum_3d_corners(do2, geo, b)
            r, g, bv, a = DORI_RGBA[level]

            # ── filled faces ──────────────────────────────────────────────────
            # Ground (bottom) face
            glColor4f(r, g, bv, a * 0.55)
            glBegin(GL_QUADS)
            glVertex3f(*n[0]); glVertex3f(*n[1])
            glVertex3f(*f[1]); glVertex3f(*f[0])
            glEnd()

            # Top face (upper FOV boundary)
            glColor4f(min(r*1.15, 1), min(g*1.15, 1), min(bv*1.15, 1), a * 0.65)
            glBegin(GL_QUADS)
            glVertex3f(*n[3]); glVertex3f(*n[2])
            glVertex3f(*f[2]); glVertex3f(*f[3])
            glEnd()

            # Near face (facing viewer — slightly more opaque to be visible)
            glColor4f(r, g, bv, a * 0.80)
            glBegin(GL_QUADS)
            glVertex3f(*n[0]); glVertex3f(*n[1])
            glVertex3f(*n[2]); glVertex3f(*n[3])
            glEnd()

            # Far face (back wall — most opaque, stands out like reference)
            glColor4f(min(r*1.2, 1), min(g*1.2, 1), min(bv*1.2, 1), a * 0.90)
            glBegin(GL_QUADS)
            glVertex3f(*f[0]); glVertex3f(*f[1])
            glVertex3f(*f[2]); glVertex3f(*f[3])
            glEnd()

            # Left side face
            glColor4f(r*0.80, g*0.80, bv*0.80, a * 0.65)
            glBegin(GL_QUADS)
            glVertex3f(*n[0]); glVertex3f(*n[3])
            glVertex3f(*f[3]); glVertex3f(*f[0])
            glEnd()

            # Right side face
            glColor4f(r*0.80, g*0.80, bv*0.80, a * 0.65)
            glBegin(GL_QUADS)
            glVertex3f(*n[1]); glVertex3f(*n[2])
            glVertex3f(*f[2]); glVertex3f(*f[1])
            glEnd()

        # ── Region beyond Detection threshold ────────────────────────────────
        d_det = dori["Detection"]["D_effective"]
        if df > d_det + 0.01:
            nd = self._frustum_3d_corners(d_det, geo, b)
            fd = self._frustum_3d_corners(df,    geo, b)
            r2, g2, b2, a2 = 0.35, 0.38, 0.52, 0.28
            glBegin(GL_QUADS)
            glColor4f(r2, g2, b2, a2*0.7)
            glVertex3f(*nd[0]); glVertex3f(*nd[1]); glVertex3f(*fd[1]); glVertex3f(*fd[0])  # bottom
            glColor4f(r2, g2, b2, a2*0.8)
            glVertex3f(*nd[3]); glVertex3f(*nd[2]); glVertex3f(*fd[2]); glVertex3f(*fd[3])  # top
            glColor4f(r2, g2, b2, a2)
            glVertex3f(*nd[0]); glVertex3f(*nd[1]); glVertex3f(*nd[2]); glVertex3f(*nd[3])  # near
            glVertex3f(*fd[0]); glVertex3f(*fd[1]); glVertex3f(*fd[2]); glVertex3f(*fd[3])  # far
            glColor4f(r2*0.8, g2*0.8, b2*0.8, a2*0.7)
            glVertex3f(*nd[0]); glVertex3f(*nd[3]); glVertex3f(*fd[3]); glVertex3f(*fd[0])  # left
            glVertex3f(*nd[1]); glVertex3f(*nd[2]); glVertex3f(*fd[2]); glVertex3f(*fd[1])  # right
            glEnd()

        glDepthMask(GL_TRUE)

        # ── DORI zone boundary lines and labels ───────────────────────────────
        glEnable(GL_LINE_SMOOTH)
        for level, info in dori.items():
            de = info["D_effective"]
            if de <= dn + .01: continue
            c  = self._frustum_3d_corners(de, geo, b)
            sr, sg, sb2, _ = DORI_SOLID[level]
            # Horizontal line at ground level
            glColor4f(sr, sg, sb2, 1.0); glLineWidth(2.2)
            glBegin(GL_LINES)
            glVertex3f(*c[0]); glVertex3f(*c[1])
            glEnd()
            # Vertical boundary marks at the two ground corners
            glLineWidth(1.5)
            glBegin(GL_LINES)
            glVertex3f(*c[0]); glVertex3f(*c[3])
            glVertex3f(*c[1]); glVertex3f(*c[2])
            glEnd()
            # Label at midpoint on the ground
            mx = (c[0][0]+c[1][0])/2; my = (c[0][1]+c[1][1])/2
            sfx = "" if info["within_render"] else "*"
            self._labels.append((mx, my, 0.0,
                f"{level[:5]}. {de:.1f}m{sfx}", DORI_HEX[level]))
        glDisable(GL_LINE_SMOOTH)

    def _fov_outline_3d(self, geo, b):
        dn  = geo["D_near"]
        df  = geo["render_far"]
        H   = geo["H"]
        cam = (0.0, 0.0, H)

        n = self._frustum_3d_corners(dn, geo, b)   # near: [BL, BR, TR, TL]
        f = self._frustum_3d_corners(df, geo, b)   # far:  [BL, BR, TR, TL]

        glEnable(GL_LINE_SMOOTH)

        # ── 4 corner rays: camera → far corners (solid cyan) ──────────────────
        glColor4f(0.0, 0.85, 0.85, 1.0); glLineWidth(1.8)
        glBegin(GL_LINES)
        glVertex3f(*cam); glVertex3f(*f[3])   # → far top-left
        glVertex3f(*cam); glVertex3f(*f[2])   # → far top-right
        glVertex3f(*cam); glVertex3f(*f[0])   # → far bottom-left
        glVertex3f(*cam); glVertex3f(*f[1])   # → far bottom-right
        glEnd()

        # ── Dashed optical axis: camera → far face centre ─────────────────────
        fc_x = (f[0][0]+f[1][0])/2; fc_y = (f[0][1]+f[1][1])/2
        fc_z = (f[2][2]+f[3][2])/2            # mid-height of far face
        far_centre = (fc_x, fc_y, fc_z)
        glColor4f(0.0, 0.85, 0.85, 0.75); glLineWidth(1.4)
        self._dashed_line3d(cam, far_centre, dash=0.45, gap=0.28)

        # ── Near face outline (white) ──────────────────────────────────────────
        glColor4f(1.0, 1.0, 1.0, 0.85); glLineWidth(1.6)
        glBegin(GL_LINE_LOOP)
        glVertex3f(*n[0]); glVertex3f(*n[1])
        glVertex3f(*n[2]); glVertex3f(*n[3])
        glEnd()

        # ── Far face outline (bright green) ───────────────────────────────────
        glColor4f(0.20, 1.00, 0.35, 1.0); glLineWidth(2.5)
        glBegin(GL_LINE_LOOP)
        glVertex3f(*f[0]); glVertex3f(*f[1])
        glVertex3f(*f[2]); glVertex3f(*f[3])
        glEnd()

        # ── Top ridge (near TL → far TL, near TR → far TR) ────────────────────
        glColor4f(0.85, 0.85, 0.85, 0.75); glLineWidth(1.3)
        glBegin(GL_LINES)
        glVertex3f(*n[3]); glVertex3f(*f[3])
        glVertex3f(*n[2]); glVertex3f(*f[2])
        glEnd()

        glDisable(GL_LINE_SMOOTH)

    def _target_line(self, geo, b):
        td = geo["target_dist"]; th = geo["target_h"]
        c  = self._frustum_3d_corners(td, geo, b)
        glEnable(GL_LINE_SMOOTH)
        # Yellow ground line at target distance
        glColor4f(1, 1, 0, 0.9); glLineWidth(2.0)
        glBegin(GL_LINES)
        glVertex3f(*c[0]); glVertex3f(*c[1])
        glEnd()
        # Cyan vertical target-height pole
        brad = math.radians(b)
        cx = td*math.sin(brad); cy = td*math.cos(brad)
        glColor4f(0, 1, 1, 1); glLineWidth(2)
        glBegin(GL_LINES)
        glVertex3f(cx, cy, 0); glVertex3f(cx, cy, th)
        glEnd()
        glDisable(GL_LINE_SMOOTH)
        self._labels.append((cx+0.2, cy, 0.0, f"Tgt H {th:.1f}m", "#00dddd"))
        self._labels.append((c[0][0], c[0][1], 0.0, f"Tgt D {td:.0f}m", "#dddd00"))

    def _camera_body(self, geo, b):
        H    = geo["H"]
        brad = math.radians(b)
        fx   = math.sin(brad); fy = math.cos(brad)

        # Mounting pole
        glEnable(GL_LINE_SMOOTH)
        glColor4f(0.55, 0.55, 0.55, 1); glLineWidth(2.5)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0); glVertex3f(0, 0, H)
        glEnd()
        glDisable(GL_LINE_SMOOTH)

        # Camera body — slightly elongated box oriented along bearing
        s = 0.20   # half-size
        lx = -math.cos(brad); ly = math.sin(brad)   # lateral direction
        fwd = (fx*s*2, fy*s*2, 0)                    # forward extent (lens side)

        # 8 corners of an elongated camera box
        def cv(sf, sl, sz):
            return (sf*fx*s*1.8 + sl*lx*s + 0,
                    sf*fy*s*1.8 + sl*ly*s + 0,
                    H + sz*s)

        corners = [cv(f, l, z) for f in (-1, 1) for l in (-1, 1) for z in (-1, 1)]
        faces = [(0,1,3,2),(4,5,7,6),(0,2,6,4),(1,3,7,5),(0,1,5,4),(2,3,7,6)]
        glColor4f(0.82, 0.82, 0.82, 1.0)
        glBegin(GL_QUADS)
        for face in faces:
            for i in face: glVertex3f(*corners[i])
        glEnd()
        glEnable(GL_LINE_SMOOTH)
        glColor4f(0.4, 0.4, 0.4, 1); glLineWidth(1.2)
        glBegin(GL_LINE_LOOP)
        for i in faces[0]:  glVertex3f(*corners[i])
        glEnd()
        glDisable(GL_LINE_SMOOTH)

        # Lens nub on the front face
        ns = 0.09
        lc = (fx*s*1.8 + 0, fy*s*1.8 + 0, H)
        glColor4f(0.20, 0.20, 0.20, 1.0)
        self._box(lc[0] + fx*ns, lc[1] + fy*ns, lc[2], ns)

        # Bearing direction indicator (teal line)
        glEnable(GL_LINE_SMOOTH)
        glColor4f(0, 0.85, 0.85, 1); glLineWidth(2)
        glBegin(GL_LINES)
        glVertex3f(0, 0, H); glVertex3f(fx*.6, fy*.6, H)
        glEnd()
        glDisable(GL_LINE_SMOOTH)

        self._labels.append((0.3, 0, 0.0, f"H={H:.1f}m", "#dddddd"))

    def _box(self, cx, cy, cz, s):
        v = [(cx+dx, cy+dy, cz+dz)
             for dx in (-s, s) for dy in (-s, s) for dz in (-s, s)]
        faces = [(0,1,3,2),(4,5,7,6),(0,2,6,4),(1,3,7,5),(0,1,5,4),(2,3,7,6)]
        glBegin(GL_QUADS)
        for f in faces:
            for i in f: glVertex3f(*v[i])
        glEnd()

    def _north(self, geo):
        d = min(geo["render_far"]*.2, 6)
        glEnable(GL_LINE_SMOOTH)
        glColor4f(0, 0.9, 0.5, 1); glLineWidth(2)
        glBegin(GL_LINES)
        glVertex3f(0, 0, .05); glVertex3f(0, d, .05)
        glEnd()
        glDisable(GL_LINE_SMOOTH)
        self._labels.append((0, d+.4, 0.0, "N", "#00ee88"))

    def _axes(self, geo):
        L = min(geo["render_far"]*.1, 3); glLineWidth(2)
        glEnable(GL_LINE_SMOOTH)
        glBegin(GL_LINES)
        glColor4f(1, 0.3, 0.3, 1); glVertex3f(0, 0, 0); glVertex3f(L, 0, 0)
        glColor4f(0.3, 1, 0.3, 1); glVertex3f(0, 0, 0); glVertex3f(0, L, 0)
        glColor4f(0.3, 0.3, 1, 1); glVertex3f(0, 0, 0); glVertex3f(0, 0, L)
        glEnd()
        glDisable(GL_LINE_SMOOTH)

    def paintEvent(self, e):
        super().paintEvent(e)
        if not self._labels: return
        if self._mv is None or self._pj is None or self._vp is None: return

        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(QFont("Arial", 9, QFont.Bold))
        fm = p.fontMetrics()
        dpr = self.devicePixelRatio()
        for (wx, wy, wz, txt, col) in self._labels:
            try: sx, sy, sz = gluProject(wx, wy, wz, self._mv, self._pj, self._vp)
            except Exception: continue
            if sz < 0 or sz > 1: continue
            px = int(sx / dpr); py = int(self.height() - sy / dpr)
            br = fm.boundingRect(txt)
            p.fillRect(px-2, py-br.height(), br.width()+6, br.height()+4,
                       QColor(0, 0, 0, 180))
            p.setPen(QColor(col)); p.drawText(px, py, txt)
        p.end()
