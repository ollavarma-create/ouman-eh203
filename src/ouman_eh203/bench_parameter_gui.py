"""Modal, exclusively owned physical bench editor."""
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QThread, Signal, QStandardPaths
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QInputDialog, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QMessageBox, QHBoxLayout)
from .backup import acquire, verify_file, known_fields
from .bench_parameter import DRAFT_KEYS, DRAFT_MAP, draft_preview, execute_draft
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
                result = execute_draft(self.port, self.snapshot, self.approved,
                    self.path, self.journal, confirmation='BENCH', progress=self.progress.emit)
                self.outcome.emit(result, str(self.journal))
        except Exception as exc:
            self.outcome.emit(None, str(exc) + (' | ' + str(self.journal) if self.journal else ''))


class BenchParameterDialog(QDialog):
    def __init__(self, port, lang, parent=None):
        super().__init__(parent)
        self.port, self.lang = port, lang
        self.worker = self.snapshot = None
        self.original = {}
        self.values = {}
        self.approved = None
        self.directory = Path(QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation)) / 'bench-edits'
        self.setWindowTitle(self.t('Testilaitteen asetukset', 'Bench controller settings'))
        self.resize(880, 480)
        layout = QVBoxLayout(self)
        warning = QLabel(self.t('Kokeellinen: vain eristetty EH-203 2.15, kuormat irrotettu. Kynä muuttaa vain paikallista luonnosta.',
                                'Experimental: isolated EH-203 2.15 only, loads disconnected. Pencil edits only the local draft.'))
        warning.setWordWrap(True)
        layout.addWidget(warning)
        self.read_button = QPushButton(self.t('Lue testilaite', 'Read bench controller'))
        self.read_button.clicked.connect(self.capture)
        layout.addWidget(self.read_button)
        self.table = QTableWidget(len(DRAFT_KEYS), 5)
        self.table.setHorizontalHeaderLabels(self.t(
            ['Parametri', 'Nykyinen', 'Luonnos', 'Testialue', 'Muokkaa'],
            ['Parameter', 'Current', 'Draft', 'Bench range', 'Edit']))
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)
        self.validation = QLabel()
        self.validation.setWordWrap(True)
        layout.addWidget(self.validation)
        buttons = QHBoxLayout()
        self.discard_button = QPushButton(self.t('Hylkää muutokset', 'Discard changes'))
        self.discard_button.clicked.connect(self.discard)
        buttons.addWidget(self.discard_button)
        self.apply_button = QPushButton(self.t('Esikatsele ja kirjoita', 'Preview and write'))
        self.apply_button.clicked.connect(self.commit)
        buttons.addWidget(self.apply_button)
        layout.addLayout(buttons)
        self.status = QLabel(self.t('Lue ensin laitteen asetukset.', 'Read controller settings first.'))
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.close_button = QPushButton(self.t('Sulje', 'Close'))
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button)
        self.pencils = {}
        for row, key in enumerate(DRAFT_KEYS):
            self.table.setItem(row, 0, QTableWidgetItem(PARAMETERS[key]['label'][lang]))
            factor, unit = DRAFT_MAP[key][-2:]
            lo, hi = PARAMETERS[key]['manual_range']
            blo, bhi = [Decimal(x)*Decimal(factor) for x in BOUNDS[key]]
            bounds = f'{max(lo,blo)}…{min(hi,bhi)} {unit}'
            self.table.setItem(row, 3, QTableWidgetItem(bounds))
            pencil = QPushButton('✎')
            pencil.setAccessibleName(self.t('Muokkaa ', 'Edit ') + PARAMETERS[key]['label'][lang])
            pencil.setToolTip(pencil.accessibleName())
            pencil.clicked.connect(lambda checked=False, k=key: self.edit(k))
            self.table.setCellWidget(row, 4, pencil)
            self.pencils[key] = pencil
        self.refresh()

    def t(self, fi, en):
        return fi if self.lang == 'fi' else en

    def dirty(self):
        return self.values != self.original

    def confirm_discard(self):
        return not self.dirty() or QMessageBox.question(self, self.windowTitle(),
            self.t('Hylätäänkö kirjoittamattomat muutokset?', 'Discard unwritten changes?'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def controls(self):
        idle = self.worker is None
        self.read_button.setEnabled(idle)
        self.close_button.setEnabled(idle)
        for pencil in self.pencils.values():
            pencil.setEnabled(idle and self.snapshot is not None)
        self.discard_button.setEnabled(idle and self.dirty())
        self.apply_button.setEnabled(idle and self.approved is not None and bool(self.approved.steps))

    def refresh(self):
        self.approved = None
        for row, key in enumerate(DRAFT_KEYS):
            unit = DRAFT_MAP[key][-1]
            old = self.original.get(key)
            new = self.values.get(key)
            for column, value in ((1, old), (2, new)):
                item = QTableWidgetItem('—' if value is None else f'{value} {unit}')
                if column == 2 and new != old:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.table.setItem(row, column, item)
        if self.snapshot is None:
            self.validation.clear()
        else:
            try:
                self.approved = draft_preview(self.snapshot, self.values)
                self.validation.setText(self.t('Tarkistusehdot täyttyvät', 'Validation passed') +
                    f' · {len(self.approved.changes)} ' + self.t('muutosta', 'changes') +
                    f' · {len(self.approved.steps)} ' + self.t('lohkokirjoitusta', 'block writes'))
            except (ValueError, ArithmeticError, OverflowError) as exc:
                self.validation.setText(self.t('Tarkista luonnos: ', 'Check draft: ') + str(exc))
        self.controls()

    def edit(self, key):
        if self.worker is not None or self.snapshot is None:
            return
        meta = PARAMETERS[key]
        factor, unit = DRAFT_MAP[key][-2:]
        low, high = meta['manual_range']
        value, ok = QInputDialog.getText(self, self.windowTitle(),
            f"{meta['label'][self.lang]} ({unit})\n" +
            self.t('Ohjekirjan alue', 'Manual range') + f': {low}…{high}\n' +
            self.t('Askel', 'Step') + f': {factor}',
            text=str(self.values[key]))
        if not ok:
            return
        try:
            number = Decimal(value.strip().replace(',', '.'))
            if not number.is_finite():
                raise ValueError('Non-finite value')
        except (ValueError, ArithmeticError) as exc:
            self.status.setText(str(exc))
            return
        self.values[key] = number
        self.refresh()

    def discard(self):
        if self.worker is None:
            self.values = dict(self.original)
            self.refresh()

    def set_snapshot(self, snapshot):
        self.snapshot = snapshot
        self.original = {} if snapshot is None else {
            key: Decimal(known_fields(snapshot)['fields'][key]['value']) for key in DRAFT_KEYS}
        self.values = dict(self.original)
        self.refresh()

    def capture(self):
        if self.worker is not None or not self.confirm_discard():
            return
        self.set_snapshot(None)
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
        self.set_snapshot(result)
        self.status.setText((self.t('Luettu: ', 'Read: ') if result is not None else
                             self.t('Luku epäonnistui: ', 'Read failed: ')) + detail)

    def commit(self):
        if self.worker is not None or self.approved is None or not self.approved.steps:
            return
        approved = self.approved
        lines = [f"{PARAMETERS[k]['label'][self.lang]}: {old} → {new} {DRAFT_MAP[k][-1]}"
                 for k, old, new in approved.changes]
        confirmation, ok = QInputDialog.getText(self, self.windowTitle(),
            '\n'.join(lines) + '\n' +
            f"ID: {', '.join(str(s[0]) for s in approved.steps)} | EH-203 2.15 | {approved.identity.hex()}\n" +
            self.t('Kuormat irrotettu? Vahvista kirjoittamalla BENCH.',
                   'Loads disconnected? Type BENCH to confirm.'))
        if not ok or confirmation != 'BENCH':
            return
        snapshot = self.snapshot
        self.set_snapshot(None)
        token = uuid4().hex
        self.start(BenchWorker(self.port, self.directory/(token+'-before.json'), self,
                   snapshot, approved, self.directory/(token+'-journal.json')), self.write_done)

    def write_done(self, result, detail):
        self.set_snapshot(result)
        message = self.t('Takaisinluku varmennettu. Pysyvyys vaatii uudelleenkäynnistyksen. ',
                         'Readback verified. Persistence requires restart verification. ') if result else self.t(
            'Keskeytetty; lue nykytila ja tarkista journalointi (varmennettu / epävarma / aloittamaton) ennen uutta kirjoitusta. ',
            'Interrupted; read current state and inspect journal (verified / uncertain / not started) before another write. ')
        if result is None:
            # Show per-step outcome directly, when the durable journal is available.
            from .backup import load
            try:
                journal = load(self.worker.journal)
                message += '\n' + '\n'.join(
                    f"ID {e['id']}: " + {'verified': self.t('Varmennettu','Verified'),
                    'write_outcome_unknown': self.t('Epävarma','Uncertain'),
                    'not_started': self.t('Aloittamaton','Not started')}.get(e['status'],e['status'])
                    for e in journal['entries']) + '\n'
            except (OSError, ValueError, KeyError, TypeError):
                pass
        self.status.setText(message + detail)

    def finished_worker(self):
        self.worker.deleteLater()
        self.worker = None
        self.controls()

    def reject(self):
        if self.worker is None and self.confirm_discard():
            super().reject()

    def closeEvent(self, event):
        if self.worker is not None or not self.confirm_discard():
            event.ignore()
        else:
            event.accept()
