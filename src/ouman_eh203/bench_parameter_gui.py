"""Modal, exclusively owned physical bench editor."""
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QThread, Signal, QStandardPaths
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QInputDialog)
from .backup import acquire, verify_file, known_fields
from .bench_parameter import KEYS, MAP, preview, execute_bench
from .metadata import PARAMETERS
from .validation import BOUNDS
from .transport import open_serial


class BenchWorker(QThread):
    outcome = Signal(object, str)
    progress = Signal(int, int)

    def __init__(self, port, path, parent, snapshot=None, approved=None, journal=None):
        super().__init__(parent)
        self.port, self.path = port, path
        self.snapshot, self.approved, self.journal = snapshot, approved, journal

    def run(self):
        try:
            if self.approved is None:
                with open_serial(self.port) as ser:
                    result = acquire(ser, self.path, 0.05, quick=True, progress=self.progress.emit)
                verify_file(result)
                self.outcome.emit(result, str(self.path))
            else:
                result = execute_bench(self.port, self.snapshot, self.approved,
                    self.path, self.journal, confirmation='BENCH', progress=self.progress.emit)
                self.outcome.emit(result, str(self.journal))
        except Exception as exc:
            self.outcome.emit(None, str(exc) + (' | ' + str(self.journal) if self.journal else ''))


class BenchParameterDialog(QDialog):
    def __init__(self, port, lang, parent=None):
        super().__init__(parent)
        self.port, self.lang = port, lang
        self.worker = self.snapshot = None
        self.directory = Path(QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation)) / 'bench-edits'
        self.setWindowTitle(self.t('Testilaitteen asetukset', 'Bench controller settings'))
        self.resize(650, 400)
        layout = QVBoxLayout(self)
        warning = QLabel(self.t('Kokeellinen: vain eristetty EH-203 2.15, kuormat irrotettu.',
                                'Experimental: isolated EH-203 2.15 only, loads disconnected.'))
        warning.setWordWrap(True)
        layout.addWidget(warning)
        self.read_button = QPushButton(self.t('Lue testilaite', 'Read bench controller'))
        self.read_button.clicked.connect(self.capture)
        layout.addWidget(self.read_button)
        self.choice = QComboBox()
        for key in KEYS:
            self.choice.addItem(PARAMETERS[key]['label'][lang], key)
        layout.addWidget(self.choice)
        self.info = QLabel()
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        self.value = QLineEdit()
        layout.addWidget(self.value)
        self.apply_button = QPushButton(self.t('Esikatsele ja kirjoita', 'Preview and write'))
        self.apply_button.clicked.connect(self.commit)
        layout.addWidget(self.apply_button)
        self.status = QLabel(self.t('Lue ensin laitteen asetukset.', 'Read controller settings first.'))
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.close_button = QPushButton(self.t('Sulje', 'Close'))
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button)
        self.choice.currentIndexChanged.connect(self.refresh)
        self.controls()

    def t(self, fi, en):
        return fi if self.lang == 'fi' else en

    def controls(self):
        idle = self.worker is None
        self.read_button.setEnabled(idle)
        self.close_button.setEnabled(idle)
        for widget in (self.choice, self.value, self.apply_button):
            widget.setEnabled(idle and self.snapshot is not None)

    def refresh(self, *_):
        if self.snapshot is None:
            self.info.clear()
            self.value.clear()
            return
        key = self.choice.currentData()
        old = known_fields(self.snapshot)['fields'][key]['value']
        factor, unit = MAP[key][-2:]
        low, high = PARAMETERS[key]['manual_range']
        lo, hi = [Decimal(x)*Decimal(factor) for x in BOUNDS[key]]
        self.info.setText(self.t('Nykyinen', 'Current') + f': {old} {unit}\n' +
            self.t('Ohjekirjan alue', 'Manual range') + f': {low}…{high} {unit}\n' +
            self.t('Testialue', 'Bench range') + f': {lo}…{hi} {unit}\n' +
            self.t('Askel', 'Step') + f': {factor} {unit}')
        self.value.setText(old)

    def capture(self):
        if self.worker is not None:
            return
        self.snapshot = None
        self.refresh()
        self.start(BenchWorker(self.port, self.directory/(uuid4().hex+'-preview.json'), self),
                   self.capture_done)

    def start(self, worker, callback):
        self.worker = worker
        self.controls()
        worker.progress.connect(self.show_progress)
        worker.outcome.connect(callback)
        worker.finished.connect(self.finished_worker)
        worker.start()

    def show_progress(self, count, total):
        self.status.setText(f'{count}/{total}')

    def capture_done(self, result, detail):
        self.snapshot = result
        self.refresh()
        self.status.setText((self.t('Luettu: ', 'Read: ') if result is not None else
                             self.t('Luku epäonnistui: ', 'Read failed: ')) + detail)

    def commit(self):
        if self.worker is not None or self.snapshot is None:
            return
        try:
            approved = preview(self.snapshot, self.choice.currentData(),
                               self.value.text().strip().replace(',', '.'))
        except (ValueError, ArithmeticError, OverflowError) as exc:
            self.status.setText(str(exc))
            return
        if approved.before == approved.after:
            self.status.setText(self.t('Ei muutoksia', 'No changes'))
            return
        unit = MAP[approved.key][-1]
        confirmation, ok = QInputDialog.getText(self, self.windowTitle(),
            f'{self.choice.currentText()}: {approved.old} → {approved.value} {unit}\n'
            f'ID: {approved.pid} | EH-203 2.15 | {approved.identity.hex()}\n' +
            self.t('Kuormat irrotettu? Vahvista kirjoittamalla BENCH.',
                   'Loads disconnected? Type BENCH to confirm.'))
        if not ok or confirmation != 'BENCH':
            return
        snapshot, self.snapshot = self.snapshot, None
        token = uuid4().hex
        self.start(BenchWorker(self.port, self.directory/(token+'-before.json'), self,
                   snapshot, approved, self.directory/(token+'-journal.json')), self.write_done)

    def write_done(self, result, detail):
        self.refresh()
        self.status.setText((self.t('Takaisinluku varmennettu. Pysyvyys vaatii uudelleenkäynnistyksen. ',
            'Readback verified. Persistence requires restart verification. ') if result else
            self.t('Keskeytetty; tarkista nykytila ja journalointi ennen uutta kirjoitusta. ',
                   'Interrupted; inspect state and journal before another write. ')) + detail)

    def finished_worker(self):
        self.worker.deleteLater()
        self.worker = None
        self.controls()

    def reject(self):
        if self.worker is None:
            super().reject()

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
        else:
            super().closeEvent(event)
