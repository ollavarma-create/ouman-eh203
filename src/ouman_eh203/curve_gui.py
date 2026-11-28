"""Read-only native Qt curve visualization."""
from datetime import datetime, timezone
from math import floor, ceil
from PySide6.QtCore import Qt, QPointF, QTimer, Signal
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QToolTip, QSizePolicy, QDialog, QSpinBox, QGridLayout, QDialogButtonBox

from .curves import HeatingCurve

class CurvePlot(QWidget):
    moved = Signal(int, int, int)
    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 240)
        self.curve = None
        self.bounds = (0, 60)
        self.hits = []
        self.draft = None
        self.drag = None
        self.edit_hits = []
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.outdoor = self.supply = self.target = None
        self.fi = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.draft is not None:
            for i, point in enumerate(self.edit_hits):
                if (point-event.position()).manhattanLength() <= 14:
                    self.drag = i
                    return

    def mouseReleaseEvent(self, event):
        self.drag = None

    def mouseMoveEvent(self, event):
        if self.drag is not None and self.draft is not None:
            left, top, w, h, xmin, xmax, lo, hi = self.geometry_scale
            x = round(xmin+(event.position().x()-left)*(xmax-xmin)/w)
            y = round(hi-(event.position().y()-top)*(hi-lo)/h)
            self.moved.emit(self.drag,x,y)
            return
        for point, label in self.hits:
            if (point - event.position()).manhattanLength() <= 12:
                QToolTip.showText(event.globalPosition().toPoint(), label, self)
                return
        QToolTip.hideText()

    def paintEvent(self, event):
        self.hits = []
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        p.setPen(ink)
        if self.curve is None:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Ei käyrätietoa" if self.fi else "No curve data")
            return
        points = self.curve.active
        lo, hi = self.bounds
        xmin = min(-20, self.outdoor if self.outdoor is not None else -20)
        xmax = max(20, self.outdoor if self.outdoor is not None else 20)
        left, top, w, h = 45, 28, self.width()-65, self.height()-70
        self.geometry_scale = (left,top,w,h,xmin,xmax,lo,hi)
        def pos(x,y):
            return QPointF(left+(x-xmin)*w/(xmax-xmin), top+(hi-y)*h/(hi-lo))
        for y in range(int(lo), int(hi)+1, 10):
            a,c = pos(xmin,y),pos(xmax,y)
            p.setPen(QPen(ink, 1, Qt.PenStyle.DotLine))
            p.drawLine(a,c)
            p.setPen(ink)
            p.drawText(QPointF(5,a.y()+4),str(y))
        for x in (-20,-10,0,10,20):
            a,c = pos(x,lo),pos(x,hi)
            p.setPen(QPen(ink,1,Qt.PenStyle.DotLine))
            p.drawLine(a,c)
            p.setPen(ink)
            p.drawText(QPointF(a.x()-10,a.y()+17),str(x))
        p.drawText(5,16,"Menovesi °C" if self.fi else "Supply °C")
        p.drawText(left,self.height()-5,"Ulkolämpötila °C" if self.fi else "Outdoor °C")
        p.setPen(QPen(QColor("#26965b"),2))
        for a,c in zip(points,points[1:]):
            p.drawLine(pos(*a),pos(*c))
        for x,y in points:
            p.drawEllipse(pos(x,y),4,4)
            self.hits.append((pos(x,y), f'{x} °C → {y} °C'))
        self.edit_hits = []
        if self.draft is not None:
            p.setPen(QPen(QColor('#d97706'),2,Qt.PenStyle.DashLine))
            for a,c in zip(self.draft.active,self.draft.active[1:]):
                p.drawLine(pos(*a),pos(*c))
            for x,y in self.draft.active:
                point = pos(x,y)
                self.edit_hits.append(point)
                p.drawEllipse(point,6,6)
        if self.outdoor is not None:
            p.setPen(QPen(ink,1,Qt.PenStyle.DashLine))
            p.drawLine(pos(self.outdoor,lo),pos(self.outdoor,hi))
            for value,color in ((self.supply,"#d94b42"),(self.target,"#4389dc")):
                if value is not None:
                    p.setPen(QPen(QColor(color),3))
                    p.drawEllipse(pos(self.outdoor,value),5,5)
                    self.hits.append((pos(self.outdoor,value), f'{value:.1f} °C'))

class CurveEditor(QDialog):
    """Local draft only; no transport or write operations."""
    def __init__(self, curve, outdoor, fi, parent=None):
        super().__init__(parent)
        self.original, self.fi = curve, fi
        self.setWindowTitle("Säätökäyrän luonnos" if fi else "Heating curve draft")
        self.resize(650, 550)
        layout = QVBoxLayout(self)
        self.plot = CurvePlot()
        self.plot.fi, self.plot.curve, self.plot.outdoor = fi, curve, outdoor
        self.plot.bounds = (0, max(80, 10*ceil(max(y for x,y in curve.active)/10)))
        layout.addWidget(self.plot,1)
        grid = QGridLayout()
        layout.addLayout(grid)
        self.fields = []
        for i,(x,y) in enumerate(curve.active):
            a,b = QSpinBox(),QSpinBox()
            a.setRange(-20,20)
            b.setRange(min(15,y),max(70,y))
            a.setValue(x)
            b.setValue(y)
            a.setEnabled(curve.mode == 0 and i not in (0,len(curve.active)-1))
            grid.addWidget(QLabel(str(i+1)),i,0)
            grid.addWidget(a,i,1)
            grid.addWidget(b,i,2)
            self.fields.append((a,b))
            a.valueChanged.connect(self.refresh)
            b.valueChanged.connect(self.refresh)
        self.info = QLabel()
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        reset = QPushButton("Palauta alkuperäinen" if fi else "Reset draft")
        reset.clicked.connect(self.reset)
        layout.addWidget(reset)
        close = QPushButton("Sulje luonnos" if fi else "Close draft")
        close.clicked.connect(self.reject)
        layout.addWidget(close)
        self.plot.moved.connect(self.move_point)
        self.refresh()

    def reset(self):
        for (a,b),(x,y) in zip(self.fields,self.original.active):
            a.setValue(x)
            b.setValue(y)

    def move_point(self,i,x,y):
        a,b = self.fields[i]
        if a.isEnabled():
            a.setValue(max(self.fields[i-1][0].value()+1,min(self.fields[i+1][0].value()-1,x)))
        b.setValue(max(15,min(70,y)))

    def refresh(self,*_):
        points = tuple((a.value(),b.value()) for a,b in self.fields)
        valid = all(a[0]<b[0] and a[1]>=b[1] for a,b in zip(points,points[1:])) and all(15<=y<=70 for x,y in points)
        stored = list(self.original.stored)
        for i,point in zip((0,2,4) if self.original.mode==1 else range(5),points):
            stored[i] = point
        self.plot.draft = HeatingCurve(self.original.mode,tuple(stored))
        estimate = None
        if valid and self.plot.outdoor is not None:
            for (x,y),(z,w) in zip(points,points[1:]):
                if x<=self.plot.outdoor<=z:
                    estimate = y+(w-y)*(self.plot.outdoor-x)/(z-x)
                    break
        msg = ("Luonnos – ei kirjoituksia. Vihreä: alkuperäinen; oranssi: luonnos." if self.fi else "Draft only – no writes. Green: original; orange: draft.") if valid else ("Käyrä ei täytä testirajoja." if self.fi else "Curve outside test bounds.")
        if estimate is not None:
            msg += (" Arvio: " if self.fi else " Estimate: ")+f"{estimate:.1f} °C"
        self.info.setText(msg)
        self.plot.update()

class CurvePage(QWidget):
    def __init__(self, help_callback):
        super().__init__()
        self.samples = {}
        self.connected = False
        self.fi = False
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        layout.addLayout(row, 1)
        self.panels = []
        self.edit_buttons = []
        for circuit in (1,2):
            group = QGroupBox(f"L{circuit}")
            box = QVBoxLayout(group)
            status, details, plot = QLabel(), QLabel(), CurvePlot()
            details.setWordWrap(True)
            box.addWidget(status)
            box.addWidget(plot, 1)
            box.addWidget(details)
            edit = QPushButton()
            edit.clicked.connect(lambda checked=False, p=plot: self.edit_curve(p))
            box.addWidget(edit)
            self.edit_buttons.append(edit)
            row.addWidget(group)
            self.panels.append((status,details,plot))
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.legend = QLabel()
        layout.addWidget(self.legend)
        layout.addWidget(self.note)
        self.help = QPushButton()
        self.help.clicked.connect(lambda: help_callback(4))
        layout.addWidget(self.help, 0, Qt.AlignmentFlag.AlignRight)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.translate("en")

    def edit_curve(self, plot):
        if plot.curve is not None:
            dialog = CurveEditor(plot.curve,plot.outdoor,self.fi,self)
            dialog.exec()
            dialog.deleteLater()

    def translate(self, lang):
        self.fi = lang == "fi"
        for button in self.edit_buttons:
            button.setText('Muokkaa luonnosta' if self.fi else 'Edit draft')
        self.help.setText("Käsikirja" if self.fi else "Manual")
        self.legend.setText('<span style="color:#26965b">●</span> ' + ("Säätökäyrä" if self.fi else "Heating curve") + ' &nbsp; <span style="color:#d94b42">●</span> ' + ("Mitattu menovesi" if self.fi else "Measured supply") + ' &nbsp; <span style="color:#4389dc">●</span> ' + ("Laskennallinen tavoite" if self.fi else "Calculated target"))
        self.note.setText("Vain luku. X-päätepisteet ja 3-pistekäyrän X-arvot perustuvat käsikirjaan." if self.fi else "Read only. Endpoint X and three-point X values follow the manual.")
        self.refresh()

    def begin(self):
        self.samples.clear()
        self.connected = True
        self.refresh()

    def end(self):
        self.connected = False
        self.refresh()

    def update_sample(self,key,value,stamp):
        self.samples[key] = (value,stamp)
        self.refresh()

    def refresh(self):
        now = datetime.now(timezone.utc)
        def fresh(key):
            item = self.samples.get(key)
            return item[0] if self.connected and item and (now-datetime.fromisoformat(item[1])).total_seconds() <= 10 else None
        values = [0, 50]
        for key in (65, 66):
            curve = fresh(key)
            if curve is not None:
                values.extend(y for x,y in curve.active)
        values.extend(v for v in (fresh(20), fresh(26), fresh("l1_target")) if v is not None)
        bounds = (10*floor(min(values)/10), 10*ceil((max(values)+5)/10))
        for i,(status,details,plot) in enumerate(self.panels):
            plot.bounds = bounds
            curve = fresh(65+i)
            plot.fi = self.fi
            plot.curve = curve
            self.edit_buttons[i].setEnabled(curve is not None)
            plot.outdoor = fresh(18)
            plot.supply = fresh(20 if i==0 else 26)
            plot.target = fresh("l1_target") if i==0 else None
            if curve is None:
                status.setText("Ei ajantasaista käyrää" if self.fi else "No current curve")
                details.clear()
            else:
                n = len(curve.active)
                status.setText(f"{n}-pistekäyrä" if self.fi else f"{n}-point curve")
                def fmt(value):
                    return "—" if value is None else f"{value:.1f} °C"
                names = ("Ulko", "Menovesi", "Tavoite", "Käyrän arvio") if self.fi else ("Outdoor", "Supply", "Target", "Curve estimate")
                estimate = None
                if plot.outdoor is not None:
                    for (a,y), (b,z) in zip(curve.active, curve.active[1:]):
                        if a <= plot.outdoor <= b:
                            estimate = y + (z-y)*(plot.outdoor-a)/(b-a)
                            break
                details.setText("  ·  ".join(f"{x} → {y} °C" for x,y in curve.active) + "\n" + "  ·  ".join(f"{name}: {fmt(value)}" for name,value in zip(names,(plot.outdoor,plot.supply,plot.target,estimate))))
            plot.update()
