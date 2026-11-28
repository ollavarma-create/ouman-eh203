from PySide6.QtCore import QThread, Signal, QStandardPaths
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QSpinBox)
from pathlib import Path
from .manuals import ManualManager, DEFAULT_URLS, acquire, validate_url

class AcquireWorker(QThread):
    result = Signal(object, str)
    def __init__(self, source, remote, parent):
        super().__init__(parent)
        self.source, self.remote = source, remote
    def run(self):
        try:
            self.result.emit(acquire(self.source, self.remote), "")
        except Exception as exc:
            self.result.emit(None, str(exc))

class ManualViewer(QDialog):
    def __init__(self, path, page=1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EH-203 PDF")
        self.resize(900, 750)
        self.doc = QPdfDocument(self)
        if self.doc.load(str(path)) != QPdfDocument.Error.None_:
            raise ValueError("Invalid PDF")
        layout = QVBoxLayout(self)
        self.view = QPdfView(self)
        self.view.setDocument(self.doc)
        self.view.setZoomMode(QPdfView.ZoomMode.FitInView)
        self.pages = QSpinBox()
        self.pages.setRange(1, self.doc.pageCount())
        layout.addWidget(self.pages)
        layout.addWidget(self.view)
        self.pages.valueChanged.connect(self.jump)
        self.pages.setValue(max(1, min(page, self.doc.pageCount())))
        self.jump(self.pages.value())
    def jump(self, page):
        from PySide6.QtCore import QPointF
        self.view.pageNavigator().jump(page - 1, QPointF(), self.view.zoomFactor())

class ManualSettings(QDialog):
    def __init__(self, settings, lang, parent=None, directory=None):
        super().__init__(parent)
        self.settings, self.fi = settings, lang == "fi"
        self.worker = None
        self.manager = ManualManager(directory or Path(QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.GenericDataLocation)) / "ouman-eh203" / "manuals")
        self.setWindowTitle(self.tr2("Dokumentaatio", "Documentation"))
        self.resize(720, 340)
        layout = QVBoxLayout(self)
        self.controls = []
        self.urls, self.labels = {}, {}
        for code in ("fi", "en"):
            layout.addWidget(QLabel("Suomi" if code == "fi" else "English"))
            field = QLineEdit(settings.value("manual/url/" + code, DEFAULT_URLS[code]))
            self.urls[code] = field
            layout.addWidget(field)
            self.controls.append(field)
            row = QHBoxLayout()
            for title, action in (
                (self.tr2("Lataa", "Download"), lambda c=code: self.download(c)),
                (self.tr2("Tuo PDF", "Import PDF"), lambda c=code: self.import_pdf(c)),
                (self.tr2("Avaa", "Open"), lambda c=code: self.open_pdf(c))):
                button = QPushButton(title)
                button.clicked.connect(lambda checked=False, a=action: a())
                row.addWidget(button)
                self.controls.append(button)
            layout.addLayout(row)
            label = QLabel()
            label.setWordWrap(True)
            self.labels[code] = label
            layout.addWidget(label)
            self.refresh(code)
        self.status = QLabel(self.tr2("PDF-tiedostoja ei jaella sovelluksen mukana.",
                                     "Manufacturer PDFs are not distributed with the application."))
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        save = QPushButton(self.tr2("Tallenna ja sulje", "Save and close"))
        save.clicked.connect(self.save)
        layout.addWidget(save)
        self.controls.append(save)

    def tr2(self, fi, en):
        return fi if self.fi else en

    def refresh(self, code):
        try:
            pages, digest = self.manager.inspect(self.manager.path(code))
            self.labels[code].setText(f"{pages} PDF | SHA-256: {digest}\n" +
                self.tr2("Painosta ei ole varmennettu.", "Edition not verified."))
        except FileNotFoundError:
            self.labels[code].setText(self.tr2("Ei paikallista PDF-tiedostoa.", "No local PDF."))
        except Exception as exc:
            self.labels[code].setText(str(exc))

    def download(self, code):
        try:
            url = validate_url(self.urls[code].text().strip())
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        self.start(code, url, True)

    def import_pdf(self, code):
        path, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
        if path:
            self.start(code, path, False)

    def start(self, code, source, remote):
        if self.worker is not None:
            return
        self.active_code = code
        self.worker = AcquireWorker(source, remote, self)
        self.worker.result.connect(self.received)
        self.worker.finished.connect(self._on_acquire_finished)
        for widget in self.controls:
            widget.setEnabled(False)
        self.status.setText(self.tr2("Luetaan PDF-tiedostoa…", "Reading PDF…"))
        self.worker.start()

    def received(self, data, error):
        try:
            if error:
                raise ValueError(error)
            self.manager.install(self.active_code, data)
            self.refresh(self.active_code)
            self.status.setText(self.tr2("Tallennettu.", "Saved."))
        except Exception as exc:
            self.status.setText(str(exc))

    def _on_acquire_finished(self):
        self.worker.deleteLater()
        self.worker = None
        for widget in self.controls:
            widget.setEnabled(True)

    def open_pdf(self, code):
        try:
            viewer = ManualViewer(self.manager.path(code), parent=self)
            viewer.exec()
        except Exception as exc:
            self.status.setText(str(exc))

    def save(self):
        try:
            urls = {code: validate_url(field.text().strip()) for code, field in self.urls.items()}
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        for code, url in urls.items():
            self.settings.setValue("manual/url/" + code, url)
        self.accept()

    def reject(self):
        if self.worker is None:
            super().reject()

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
        else:
            super().closeEvent(event)
