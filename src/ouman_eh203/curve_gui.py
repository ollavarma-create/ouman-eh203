"""Read-only native Qt curve visualization."""
from datetime import datetime, timezone
from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox

class CurvePlot(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 240)
        self.curve = None
        self.outdoor = self.supply = self.target = None
        self.fi = False

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        p.setPen(ink)
        if self.curve is None:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Ei käyrätietoa" if self.fi else "No curve data")
            return
        points = self.curve.active
        values = [y for x,y in points] + [v for v in (self.supply,self.target) if v is not None]
        lo = min(0, min(values))
        hi = max(60, max(values)+10)
        xmin = min(-20, self.outdoor if self.outdoor is not None else -20)
        xmax = max(20, self.outdoor if self.outdoor is not None else 20)
        left, top, w, h = 45, 28, self.width()-65, self.height()-70
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
        if self.outdoor is not None:
            p.setPen(QPen(ink,1,Qt.PenStyle.DashLine))
            p.drawLine(pos(self.outdoor,lo),pos(self.outdoor,hi))
            for value,color in ((self.supply,"#d94b42"),(self.target,"#4389dc")):
                if value is not None:
                    p.setPen(QPen(QColor(color),3))
                    p.drawEllipse(pos(self.outdoor,value),5,5)

class CurvePage(QWidget):
    def __init__(self, help_callback):
        super().__init__()
        self.samples = {}
        self.connected = False
        self.fi = False
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        layout.addLayout(row)
        self.panels = []
        for circuit in (1,2):
            group = QGroupBox(f"L{circuit}")
            box = QVBoxLayout(group)
            status, details, plot = QLabel(), QLabel(), CurvePlot()
            details.setWordWrap(True)
            box.addWidget(status)
            box.addWidget(plot)
            box.addWidget(details)
            row.addWidget(group)
            self.panels.append((status,details,plot))
        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.help = QPushButton()
        self.help.clicked.connect(lambda: help_callback(4))
        layout.addWidget(self.help)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.translate("en")

    def translate(self, lang):
        self.fi = lang == "fi"
        self.help.setText("Käsikirja" if self.fi else "Manual")
        self.note.setText("Vain luku. Vihreä: käyrä, punainen: mitattu menovesi, sininen: laskennallinen tavoite. X-päätepisteet ja 3-pistekäyrän X-arvot perustuvat käsikirjaan." if self.fi else "Read only. Green: curve, red: measured supply, blue: calculated target. Endpoint X and three-point X values follow the manual.")
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
        for i,(status,details,plot) in enumerate(self.panels):
            curve = fresh(65+i)
            plot.fi = self.fi
            plot.curve = curve
            plot.outdoor = fresh(18)
            plot.supply = fresh(20 if i==0 else 26)
            plot.target = fresh("l1_target") if i==0 else None
            if curve is None:
                status.setText("Ei ajantasaista käyrää" if self.fi else "No current curve")
                details.clear()
            else:
                n = len(curve.active)
                status.setText(f"{n}-pistekäyrä" if self.fi else f"{n}-point curve")
                details.setText("  ·  ".join(f"{x} → {y} °C" for x,y in curve.active))
            plot.update()
