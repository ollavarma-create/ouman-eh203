"""Desktop foundation. Only canonical identity reads are exposed."""
import sys
from PySide6.QtCore import QSettings, QThread, Signal
from PySide6.QtWidgets import (QApplication, QWidget, QMainWindow, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit, QTabWidget)
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

class Window(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings("EH203Manager", "Desktop")
        self.worker = None
        self.setWindowTitle("Ouman EH-203 Manager")
        self.resize(820, 480)
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
        self.connect_button = QPushButton()
        for widget in (self.language, self.mode, self.port, self.connect_button):
            bar.addWidget(widget)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.monitor = QLabel()
        self.monitor.setWordWrap(True)
        self.config = QLabel()
        self.config.setWordWrap(True)
        for label in (self.monitor, self.config):
            page = QWidget()
            box = QVBoxLayout(page)
            box.addWidget(label)
            box.addStretch()
            self.tabs.addTab(page, "")
        self.language.currentTextChanged.connect(self.translate)
        self.mode.currentIndexChanged.connect(self.reset_status)
        self.port.textChanged.connect(self.reset_status)
        self.connect_button.clicked.connect(self.start_probe)
        self.translate()
        self.reset_status()

    def translate(self):
        lang = self.language.currentText()
        self.settings.setValue("language", lang)
        s = STRINGS[lang]
        self.tabs.setTabText(0, s[0])
        self.tabs.setTabText(1, s[1])
        self.connect_button.setText(s[2])
        self.mode.setItemText(0, s[4])
        self.mode.setItemText(1, s[5])
        self.monitor.setText(s[6])
        self.config.setText(s[7])
        if self.worker is None:
            self.status.setText(s[3])

    def reset_status(self, *_):
        self.port.setEnabled(self.mode.currentIndex() == 1 and self.worker is None)
        self.status.setText(STRINGS[self.language.currentText()][3])

    def start_probe(self):
        if self.worker is not None:
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
        self.worker.start()

    def show_outcome(self, ok, detail):
        fi = self.language.currentText() == "fi"
        prefix = ("Simulaattori" if fi else "Simulator") if self.mode.currentIndex() == 0 else "RS-232"
        label = ("Testi onnistui" if fi else "Probe succeeded") if ok else ("Virhe" if fi else "Error")
        self.status.setText(f"{prefix}: {label}: {detail}")

    def finish_probe(self):
        self.worker.deleteLater()
        self.worker = None
        for widget in (self.connect_button, self.mode, self.language):
            widget.setEnabled(True)
        self.port.setEnabled(self.mode.currentIndex() == 1)

    def closeEvent(self, event):
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
