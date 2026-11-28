from datetime import datetime, timezone
from pathlib import Path
from PySide6.QtCore import QTimer, QStandardPaths, QSettings
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QGroupBox, QLabel, QPushButton, QMessageBox
from .manuals import ManualManager
from .monitoring import ACTIVE_KEYS
from .manual_gui import ManualViewer

# Only verified measurement channels are enabled. Other rows are placeholders.
FIELDS = (
    (18, 0, "Ulkolämpötila", "Outdoor temperature", 8),
    (20, 1, "Menovesi", "Supply water", 8),
    (21, 1, "Huonelämpötila", "Room temperature", 8),
    ("l1_target", 1, "Laskennallinen tavoite", "Calculated target", 10),
    ("l1_valve", 1, "Venttiiliohjaus", "Valve command", 9),
    ("l2_supply", 2, "Menovesi", "Supply water", 8),
    ("l2_room", 2, "Huonelämpötila", "Room temperature", 8),
    ("l2_target", 2, "Laskennallinen tavoite", "Calculated target", 10),
    ("l2_valve", 2, "Venttiiliohjaus", "Valve command", 9),
    ("dhw_temp", 3, "Lämpötila", "Temperature", 8),
    ("dhw_target", 3, "Asetusarvo", "Setpoint", 7),
    ("dhw_valve", 3, "Venttiiliohjaus", "Valve command", 9),
    ("l1_mode", 1, "Ohjaustapa", "Operating mode", 12),
    ("l2_mode", 2, "Ohjaustapa", "Operating mode", 12),
    ("dhw_mode", 3, "Ohjaustapa", "Operating mode", 12),
    ("r1", 4, "R1 ohjaus", "R1 command", 26),
    ("r2", 4, "R2 ohjaus", "R2 command", 27),
    ("alarm", 4, "Hälytystila", "Alarm state", 18),
)

def reading_state(sample, connected, now):
    if sample is None:
        return "waiting"
    value, stamp = sample
    if not connected or (now - datetime.fromisoformat(stamp)).total_seconds() > 10:
        return "stale"
    return "missing" if value is None else "live"

class Dashboard(QWidget):
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings("EH203Manager", "Desktop")
        self.lang = "en"
        self.samples = {}
        self.connected = False
        self.groups, self.rows = [], {}
        layout = QVBoxLayout(self)
        grid = QGridLayout()
        layout.addLayout(grid)
        for i, pos in enumerate(((0,0,1,2),(1,0,1,1),(1,1,1,1),(2,0,1,2),(3,0,1,2))):
            group = QGroupBox()
            self.groups.append(group)
            grid.addWidget(group, *pos)
            group.setLayout(QGridLayout())
        for key, group, fi, en, page in FIELDS:
            box = self.groups[group].layout()
            row = box.rowCount()
            name, value, state = QLabel(), QLabel("—"), QLabel()
            font = value.font()
            font.setPointSize(font.pointSize() + 5)
            font.setBold(True)
            value.setFont(font)
            help_button = QPushButton("?")
            help_button.setFixedWidth(30)
            help_button.clicked.connect(lambda checked=False, p=page: self.open_help(p))
            box.addWidget(name, row, 0)
            box.addWidget(value, row, 1)
            box.addWidget(state, row, 2)
            box.addWidget(help_button, row, 3)
            self.rows[key] = (name, value, state, help_button)
        self.updated = QLabel()
        layout.addWidget(self.updated)
        layout.addStretch()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.translate("en")

    def tr2(self, fi, en):
        return fi if self.lang == "fi" else en

    def translate(self, lang):
        self.lang = lang
        for group, titles in zip(self.groups, (("Yleiset", "General"), ("L1 – Lämmityspiiri", "L1 – Heating circuit"), ("L2 – Lämmityspiiri", "L2 – Heating circuit"), ("LV – Käyttövesi", "DHW"), ("Releet ja hälytykset", "Relays and alarms"))):
            group.setTitle(self.tr2(*titles))
        for key, _, fi, en, page in FIELDS:
            name, value, state, button = self.rows[key]
            name.setText(self.tr2(fi, en))
            tip = self.tr2(f"Käsikirja, s. {page} (painos varmentamatta)", f"Manual, p. {page} (edition unverified)")
            name.setToolTip(tip)
            button.setToolTip(tip)
        self.refresh()

    def begin(self):
        self.samples.clear()
        self.connected = True
        self.refresh()

    def update_sample(self, pid, value, stamp):
        self.samples[pid] = (value, stamp)
        self.refresh()

    def end(self):
        self.connected = False
        self.refresh()

    def refresh(self):
        now = datetime.now(timezone.utc)
        for key, (_, value, state, _) in self.rows.items():
            sample = self.samples.get(key)
            status = reading_state(sample, self.connected, now) if key in ACTIVE_KEYS else "pending"
            val = sample[0] if sample else None
            value.setText(self.format_value(key, val))
            labels = {"pending": ("Ei toteutettu", "Not implemented"), "waiting": ("Odottaa", "Waiting") if self.connected else ("Ei yhteyttä", "Disconnected"),
                      "stale": ("Vanhentunut", "Stale"), "missing": ("Anturi puuttuu", "Sensor missing"), "live": ("Ajantasainen", "Current")}
            state.setText(self.tr2(*labels[status]))
        stamps = [datetime.fromisoformat(s[1]) for s in self.samples.values()]
        stamp = max(stamps).astimezone().strftime("%H:%M:%S") if stamps else "—"
        self.updated.setText(self.tr2("Viimeisin vastaanotto: ", "Last received: ") + stamp)

    def format_value(self, key, val):
        if val is None:
            return "—"
        if key in ("r1", "r2"):
            return self.tr2("Päällä", "On") if val else self.tr2("Pois", "Off")
        if isinstance(key, str) and key.endswith("_mode"):
            modes = {0: ("Automaatti", "Automatic"), 1: ("Jatkuva päivä", "Continuous day"),
                     2: ("Jatkuva yö", "Continuous night"), 3: ("Seis", "Shutdown"),
                     4: ("Mekaaninen käsiajo", "Mechanical manual"), 5: ("Sähköinen käsiajo", "Electrical manual")}
            if key == "dhw_mode" and val not in (0, 4, 5):
                return self.tr2(f"Tuntematon ({val})", f"Unknown ({val})")
            return self.tr2(*modes.get(val, (f"Tuntematon ({val})", f"Unknown ({val})")))
        if key == "dhw_valve":
            return f"{val} %"
        return f"{val:.2f} °C"

    def open_help(self, page):
        directory = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)) / "ouman-eh203" / "manuals"
        path = ManualManager(directory).path(self.lang)
        if not path.exists():
            QMessageBox.information(self, "PDF", self.tr2("Lataa käsikirja ensin dokumentaatioasetuksista.", "Download the manual in documentation settings first."))
            return
        try:
            _, digest = ManualManager.inspect(path)
            key = f"manual/accepted/{self.lang}"
            if self.settings.value(key, "") != digest:
                if QMessageBox.question(self, "PDF", self.tr2(
                    "Painosta ei ole varmennettu. Hyväksytäänkö tämä käsikirja ohjesivujen avaamiseen?",
                    "Edition not verified. Accept this manual for opening suggested pages?")) != QMessageBox.StandardButton.Yes:
                    return
                self.settings.setValue(key, digest)
            ManualViewer(path, page, self).exec()
        except Exception as exc:
            QMessageBox.warning(self, "PDF", str(exc))
