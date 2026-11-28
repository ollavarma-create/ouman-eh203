"""Desktop foundation. Only canonical identity reads are exposed."""
import sys
from serial.tools.list_ports import comports
from pathlib import PurePath, Path
from .offline_gui import OfflinePage
from threading import Event
from .backup import acquire, verify_file
from .monitoring import OperationManager
from .dashboard import Dashboard
from .curve_gui import CurvePage
from PySide6.QtCore import QSettings, QThread, Signal
from PySide6.QtWidgets import (QApplication, QWidget, QMainWindow, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit, QTabWidget, QFileDialog, QProgressDialog)
from .protocol import request, classify
from .transport import open_serial, exchange
from .simulator import SimulatedSerial

STRINGS = {
    "en": ("Monitoring", "Configuration", "Probe connection", "Not connected",
           "Simulator", "Serial port", "Identity response (hex)", "Read-only foundation; configuration tools are planned."),
    "fi": ("Käytönvalvonta", "Asetusten hallinta", "Testaa yhteys", "Ei yhteyttä",
           "Simulaattori", "Sarjaportti", "Tunnistevastaus (hex)", "Vain luku; asetustyökalut ovat suunnitteilla."),
}

def probe(port, simulated):
    # Synthetic identity bytes, not a claim about real firmware.
    ser = SimulatedSerial({1: b"DEMO"}) if simulated else open_serial(port)
    try:
        status, data, error = classify(exchange(ser, request(1)), 1)
        if status != "accepted" or not data:
            raise ValueError(error or status)
        return data.hex(" ")
    finally:
        if not simulated:
            ser.close()

class ProbeWorker(QThread):
    outcome = Signal(bool, str)
    def __init__(self, port, simulated, parent=None):
        super().__init__(parent)
        self.port, self.simulated = port, simulated
    def run(self):
        try:
            self.outcome.emit(True, probe(self.port, self.simulated))
        except Exception as exc:
            self.outcome.emit(False, str(exc))

class MonitorWorker(QThread):
    identity = Signal(str)
    sample = Signal(object, object, str)
    failed = Signal(str)
    def __init__(self, port, simulated, parent=None):
        super().__init__(parent)
        self.manager = OperationManager(port, simulated)
    def run(self):
        try:
            self.manager.run(self.identity.emit, self.sample.emit)
        except Exception as exc:
            self.failed.emit(str(exc))

class BackupWorker(QThread):
    progress = Signal(int, int)
    outcome = Signal(str, str)

    def __init__(self, port, path, parent=None):
        super().__init__(parent)
        self.port, self.path = port, path
        self.cancel = Event()

    def run(self):
        try:
            ser = open_serial(self.port)
            try:
                result = acquire(ser, self.path, 0.05, progress=self.progress.emit,
                                 cancelled=self.cancel.is_set)
            finally:
                ser.close()
            if not result['complete']:
                self.outcome.emit("partial", self.path)
                return
            verify_file(result)
            self.outcome.emit("verified", self.path)
        except Exception as exc:
            self.outcome.emit("error", str(exc))


class Window(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings("EH203Manager", "Desktop")
        self.worker = None
        self.backup_worker = None
        self.setWindowTitle("Ouman EH-203 Manager")
        self.resize(1050, 640)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        bar = QHBoxLayout()
        layout.addLayout(bar)
        self.language = QComboBox()
        self.language.addItems(["en", "fi"])
        self.language.setCurrentText(self.settings.value("language", "en"))
        self.mode = QComboBox()
        self.mode.addItems(["Simulator", "Serial port"])
        self.port = QLineEdit(self.settings.value("port", "/dev/ttyUSB0"))
        self.port.setEnabled(False)
        self.port.setMinimumWidth(140)
        self.connect_button = QPushButton()
        self.session = None
        self.closing = False
        self.scan_button = QPushButton("↻")
        self.scan_button.clicked.connect(self.scan_ports)
        self.port_choices = QComboBox()
        self.port_choices.setMinimumContentsLength(12)
        self.port_choices.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.port_choices.activated.connect(self.select_port)
        self.port.textChanged.connect(self.sync_port_choice)
        self.live_button = QPushButton()
        self.live_button.clicked.connect(self.toggle_monitor)
        for widget in (self.language, self.mode, self.port, self.connect_button):
            bar.addWidget(widget)
        self.manual_button = QPushButton('⚙')
        self.manual_button.clicked.connect(self.open_manual_settings)
        bar.addWidget(self.manual_button)
        bar.addWidget(self.port_choices)
        bar.addWidget(self.scan_button)
        bar.addWidget(self.live_button)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.monitor = Dashboard(settings=self.settings)
        self.tabs.addTab(self.monitor, '')
        self.config = QLabel()
        self.config.setWordWrap(True)
        for label in (self.config,):
            page = QWidget()
            box = QVBoxLayout(page)
            box.addWidget(label)
            self.backup_button = QPushButton()
            self.backup_button.clicked.connect(self.start_backup)
            box.addWidget(self.backup_button)
            self.backup_result = None
            self.backup_status = QLabel()
            self.backup_status.setWordWrap(True)
            box.addWidget(self.backup_status)
            self.offline = OfflinePage(self.monitor.open_help)
            box.addWidget(self.offline, 1)
            self.tabs.addTab(page, "")
        self.curves = CurvePage(self.monitor.open_help)
        self.tabs.addTab(self.curves, '')
        self.language.currentTextChanged.connect(self.translate)
        self.mode.currentIndexChanged.connect(self.reset_status)
        self.port.textChanged.connect(self.reset_status)
        self.connect_button.clicked.connect(self.start_probe)
        self.translate()
        self.reset_status()
        self.scan_ports()

    def backup_enabled(self):
        self.backup_button.setEnabled(self.mode.currentIndex() == 1 and
            self.session is None and self.worker is None and self.backup_worker is None)

    def start_backup(self):
        if not self.backup_button.isEnabled():
            return
        fi = self.language.currentText() == "fi"
        path, _ = QFileDialog.getSaveFileName(self, "Varmuuskopio" if fi else "Backup",
                                              "eh203-backup.json", "JSON (*.json)", options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:
            return
        if Path(path).exists():
            self.backup_outcome('exists', path)
            return
        self.backup_worker = BackupWorker(self.port.text().strip(), path, self)
        self.backup_dialog = QProgressDialog("Luetaan 256 parametria" if fi else "Reading 256 parameters",
                                            "Keskeytä" if fi else "Cancel", 0, 256, self)
        self.backup_dialog.setAutoClose(False)
        self.backup_dialog.setAutoReset(False)
        self.backup_dialog.canceled.connect(self.backup_worker.cancel.set)
        self.backup_worker.progress.connect(self.backup_progress)
        self.backup_worker.outcome.connect(self.backup_outcome)
        self.backup_worker.finished.connect(self.backup_finished)
        for widget in (self.connect_button, self.mode, self.port, self.language,
                       self.scan_button, self.port_choices, self.live_button):
            widget.setEnabled(False)
        self.backup_enabled()
        self.backup_dialog.show()
        self.backup_worker.start()

    def backup_progress(self, count, total):
        if not self.backup_worker.cancel.is_set():
            self.backup_dialog.setValue(count)

    def backup_outcome(self, state, detail):
        self.backup_result = (state, detail)
        self.translate_backup_status()

    def translate_backup_status(self):
        if self.backup_result is None:
            return
        state, detail = self.backup_result
        fi = self.language.currentText() == "fi"
        labels = {"exists": ("Tiedosto on jo olemassa; valitse uusi nimi", "File already exists; choose a new name"),
                  "verified": ("Raakakaappaus varmennettu", "Raw capture verified"),
                  "partial": ("Keskeneräinen kaappaus", "Incomplete capture"),
                  "error": ("Virhe; mahdollinen osittainen tiedosto", "Error; partial file may exist")}
        self.backup_status.setText(labels[state][0 if fi else 1] + ": " + detail)

    def backup_finished(self):
        self.backup_dialog.hide()
        self.backup_dialog.deleteLater()
        self.backup_worker.deleteLater()
        self.backup_worker = None
        for widget in (self.connect_button, self.mode, self.port, self.language,
                       self.scan_button, self.port_choices, self.live_button):
            widget.setEnabled(True)
        self.backup_enabled()

    def select_port(self, index):
        port = self.port_choices.itemData(index)
        if port:
            self.port.setText(port)

    def sync_port_choice(self, *_):
        self.port_choices.setCurrentIndex(self.port_choices.findData(self.port.text().strip()))

    def scan_ports(self):
        self.port_choices.clear()
        ports = list(comports())
        selected = self.port.text().strip()
        for item in sorted(ports, key=lambda p: (p.vid is None and not PurePath(p.device).name.startswith(("ttyUSB", "ttyACM")), p.device)):
            if (PurePath(item.device).name.startswith("ttyS") and
                    item.description in ("n/a", "", None) and item.device != selected):
                continue
            self.port_choices.addItem(f"{item.device} — {item.description}", item.device)
        if selected and self.port_choices.findData(selected) < 0:
            self.port_choices.addItem(selected, selected)
        self.sync_port_choice()

    def toggle_monitor(self):
        if self.session is not None:
            self.session.manager.stop()
            self.live_button.setEnabled(False)
            return
        if self.worker is not None:
            return
        simulated = self.mode.currentIndex() == 0
        port = self.port.text().strip()
        if not simulated and not port:
            return
        self.settings.setValue("port", port)
        self.monitor.begin()
        self.curves.begin()
        self.status.setToolTip('')
        self.session = MonitorWorker(port, simulated, self)
        self.session.identity.connect(self.monitor_identity)
        self.session.sample.connect(self.monitor_sample)
        self.session.failed.connect(self.monitor_error)
        self.session.finished.connect(self.monitor_finished)
        for widget in (self.connect_button, self.mode, self.port, self.language,
                       self.scan_button, self.port_choices):
            widget.setEnabled(False)
        self.live_button.setText("Katkaise" if self.language.currentText() == "fi" else "Disconnect")
        self.status.setText("…")
        self.backup_enabled()
        self.session.start()

    def monitor_identity(self, detail):
        prefix = ("Simulaattori" if self.language.currentText() == "fi" else "Simulator") if self.mode.currentIndex() == 0 else f"RS-232 · {self.port.text().strip()}"
        self.status.setToolTip(detail)
        self.status.setText(f"{prefix} · " + ("Yhteys muodostettu" if self.language.currentText() == "fi" else "Connected"))

    def monitor_sample(self, pid, value, stamp):
        self.monitor.update_sample(pid, value, stamp)
        self.curves.update_sample(pid, value, stamp)

    def monitor_error(self, detail):
        self.status.setText(("Virhe: " if self.language.currentText() == "fi" else "Error: ") + detail)

    def monitor_finished(self):
        self.session.deleteLater()
        self.session = None
        for widget in (self.connect_button, self.mode, self.language, self.scan_button,
                       self.port_choices, self.live_button):
            widget.setEnabled(True)
        self.port.setEnabled(self.mode.currentIndex() == 1)
        fi = self.language.currentText() == "fi"
        self.live_button.setText("Yhdistä" if fi else "Connect")
        self.monitor.end()
        self.curves.end()
        self.backup_enabled()
        if self.closing:
            self.close()
        if not self.status.text().startswith(("Virhe:", "Error:")):
            self.status.setText("Ei yhteyttä" if fi else "Disconnected")

    def open_manual_settings(self):
        from .manual_gui import ManualSettings
        ManualSettings(self.settings, self.language.currentText(), self).exec()

    def translate(self):
        lang = self.language.currentText()
        self.settings.setValue("language", lang)
        s = STRINGS[lang]
        self.tabs.setTabText(0, s[0])
        self.tabs.setTabText(1, s[1])
        self.connect_button.setText(s[2])
        self.live_button.setText('Yhdistä' if lang == 'fi' else 'Connect')
        self.manual_button.setToolTip('Dokumentaatio' if lang == 'fi' else 'Documentation')
        self.mode.setItemText(0, s[4])
        self.mode.setItemText(1, s[5])
        self.monitor.translate(lang)
        self.curves.translate(lang)
        self.tabs.setTabText(2, 'Lämmityskäyrät' if lang == 'fi' else 'Heating curves')
        self.config.setText('Katkaise käytönvalvontayhteys ennen varmuuskopiointia. Raakakaappaus ei takaa kaikkien asetusten palautettavuutta.' if lang == 'fi' else 'Disconnect monitoring before backup. Raw capture does not guarantee restoration of every setting.')
        self.offline.translate(lang)
        self.translate_backup_status()
        self.backup_button.setText('Ota varmuuskopio' if lang == 'fi' else 'Create backup')
        self.backup_enabled()
        if self.worker is None:
            self.status.setText(s[3])

    def reset_status(self, *_):
        self.backup_enabled()
        self.port.setEnabled(self.mode.currentIndex() == 1 and self.worker is None)
        self.status.setToolTip('')
        self.status.setText(STRINGS[self.language.currentText()][3])

    def start_probe(self):
        if self.worker is not None or self.session is not None:
            return
        simulated = self.mode.currentIndex() == 0
        port = self.port.text().strip()
        if not simulated and not port:
            return
        self.settings.setValue("port", port)
        self.worker = ProbeWorker(port, simulated, self)
        self.worker.outcome.connect(self.show_outcome)
        self.worker.finished.connect(self.finish_probe)
        for widget in (self.connect_button, self.mode, self.port, self.language):
            widget.setEnabled(False)
        self.status.setText("…" )
        self.live_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.port_choices.setEnabled(False)
        self.backup_enabled()
        self.worker.start()

    def show_outcome(self, ok, detail):
        fi = self.language.currentText() == "fi"
        prefix = ("Simulaattori" if fi else "Simulator") if self.mode.currentIndex() == 0 else "RS-232"
        label = ("Testi onnistui" if fi else "Probe succeeded") if ok else ("Virhe" if fi else "Error")
        self.status.setText(f"{prefix}: {label}: {detail}")

    def finish_probe(self):
        self.worker.deleteLater()
        self.worker = None
        self.backup_enabled()
        self.live_button.setEnabled(True)
        self.scan_button.setEnabled(True)
        self.port_choices.setEnabled(True)
        for widget in (self.connect_button, self.mode, self.language):
            widget.setEnabled(True)
        self.port.setEnabled(self.mode.currentIndex() == 1)

    def closeEvent(self, event):
        if self.backup_worker is not None:
            self.backup_worker.cancel.set()
            event.ignore()
            return
        if self.session is not None:
            self.closing = True
            self.session.manager.stop()
            event.ignore()
            return
        if self.worker is not None:
            event.ignore()
        else:
            super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
