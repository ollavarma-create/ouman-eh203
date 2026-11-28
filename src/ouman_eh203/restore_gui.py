from PySide6.QtWidgets import (QDialog,QVBoxLayout,QPushButton,QLabel,QFileDialog,
    QTableWidget,QTableWidgetItem,QAbstractItemView,QMessageBox,QCheckBox)
from .backup import load, acquire, verify_file
from .restore import plan, execute_simulated, block_identity
from .transport import open_serial
from PySide6.QtCore import QThread, Signal, QStandardPaths
from pathlib import Path
from uuid import uuid4
from threading import Event

class RestoreWorker(QThread):
    outcome = Signal(object, str)
    progress = Signal(int, int)
    def __init__(self, port, sim, path, source=None, target=None, steps=None, parent=None):
        super().__init__(parent)
        self.port, self.sim, self.path = port, sim, path
        self.source, self.target, self.steps = source, target, steps
        self.cancel = Event()
    def run(self):
        try:
            if self.steps is not None:
                execute_simulated(self.sim, self.source, self.steps, [], target_identity=block_identity(self.target), allow_device_mismatch=True, journal_path=self.path)
                self.outcome.emit(True, str(self.path))
                return
            ser = self.sim if self.sim is not None else open_serial(self.port)
            try:
                result = acquire(ser, self.path, 0 if self.sim is not None else 0.05, progress=self.progress.emit, cancelled=self.cancel.is_set)
                verify_file(result, structural_only=True)
            finally:
                if self.sim is None:
                    ser.close()
            self.outcome.emit(result, str(self.path))
        except Exception as exc:
            self.outcome.emit(None, str(exc))
from .restore_preview import preview
from .metadata import PARAMETERS

class RestoreDialog(QDialog):
    def __init__(self, source, lang, parent=None, *, port='', sim=None):
        super().__init__(parent)
        self.source = source
        self.port, self.sim = port, sim
        self.worker = None
        self.target = None
        self.approved_steps = None
        self.directory = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'restore-safety'
        self.directory.mkdir(parents=True, exist_ok=True)
        self.source_path = ''
        self.status = QLabel()
        self.lang = lang
        self.setWindowTitle(self.tr2("Palautussuunnitelma","Restore preview"))
        self.resize(850,600)
        layout = QVBoxLayout(self)
        self.source_button = QPushButton(self.tr2('Valitse palautettava varmuuskopio (lähde)','Choose backup to restore (source)'))
        self.source_button.clicked.connect(self.select_source)
        layout.addWidget(self.source_button)
        self.source_label = QLabel(self.tr2('Ei valittua lähdettä','No source selected'))
        self.source_label.setWordWrap(True)
        layout.addWidget(self.source_label)
        self.choose = QPushButton(self.tr2("Lue kohdelaitteen nykyiset asetukset","Read current target settings"))
        self.choose.clicked.connect(self.select)
        self.choose.setEnabled(source is not None)
        layout.addWidget(self.choose)
        self.status.setText(self.tr2("Vain suunnittelu – ei kirjoituksia.","Preview only – no writes."))
        self.target_label = QLabel(self.tr2('Ei valittua kohdetta','No target selected'))
        self.target_label.setWordWrap(True)
        layout.addWidget(self.target_label)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.fields = []
        self.technical = QPushButton(self.tr2('Tekniset tiedot','Technical details'))
        self.technical.setEnabled(False)
        self.technical.clicked.connect(self.show_technical)
        self.technical_text = ''
        layout.addWidget(self.technical)
        self.only_changes = QCheckBox(self.tr2('Näytä vain muuttuvat asetukset','Show changed settings only'))
        self.only_changes.setChecked(True)
        self.only_changes.toggled.connect(self.populate_fields)
        layout.addWidget(self.only_changes)
        self.table = QTableWidget(0,5)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(self.tr2(
            ["Parametri","Kohde nyt","Palautettava","Yksikkö","Tila"],
            ["Parameter","Target now","Desired","Unit","Status"]))
        layout.addWidget(self.table)
        self.apply_button = QPushButton(self.tr2('Palauta simulaattoriin','Restore to simulator'))
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply_restore)
        layout.addWidget(self.apply_button)
        close = QPushButton(self.tr2("Sulje","Close"))
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def tr2(self,fi,en):
        return fi if self.lang == "fi" else en

    def select_source(self):
        path,_ = QFileDialog.getOpenFileName(self,self.source_button.text(),"","JSON (*.json)")
        if path:
            self.open_source(path)

    def open_source(self,path):
        from .backup import verify_file
        self.source = None
        self.target = None
        self.approved_steps = None
        self.apply_button.setEnabled(False)
        self.source_path = ""
        self.choose.setEnabled(False)
        self.clear_preview()
        self.status.setToolTip("")
        self.target_label.setText(self.tr2("Ei valittua kohdetta","No target selected"))
        self.source_label.setText(self.tr2("Ei valittua lähdettä","No source selected"))
        try:
            source = load(path)
            verify_file(source, structural_only=True)
        except (OSError,ValueError,KeyError,TypeError,AttributeError,IndexError) as exc:
            self.status.setText(self.tr2("Lähde hylätty: ","Source rejected: ")+str(exc))
            return False
        self.source,self.source_path = source,str(path)
        self.source_label.setText(self.tr2("Lähde: ","Source: ")+self.source_path)
        self.choose.setEnabled(True)
        self.status.setText(self.tr2("Lue kohdelaitteen nykyiset asetukset.","Read current target settings."))
        return True

    def select(self):
        if self.worker is not None or self.source is None:
            return
        self.apply_button.setEnabled(False)
        self.approved_steps = None
        self.clear_preview()
        path = self.directory / (uuid4().hex + "-before.json")
        self.start_worker(RestoreWorker(self.port,self.sim,path,parent=self), self.capture_done)

    def start_worker(self, worker, callback):
        self.worker = worker
        self.source_button.setEnabled(False)
        self.choose.setEnabled(False)
        self.apply_button.setEnabled(False)
        worker.outcome.connect(callback)
        worker.progress.connect(self.show_progress)
        worker.finished.connect(self.worker_done)
        worker.start()

    def show_progress(self, count, total):
        self.status.setText(f"{count}/{total}")

    def worker_done(self):
        self.worker.deleteLater()
        self.worker = None
        self.source_button.setEnabled(True)
        self.choose.setEnabled(self.source is not None)
        self.apply_button.setEnabled(self.sim is not None and bool(self.approved_steps))

    def capture_done(self, result, detail):
        if result is None:
            self.status.setText(self.tr2("Luku epäonnistui: ","Read failed: ")+detail)
            return
        self.target = result
        if self.open_target(detail) and self.sim is not None:
            report = preview(self.source,result)
            if report["status"] == "preview_only" and report["steps"]:
                self.approved_steps = plan(self.source,result,allow_device_mismatch=True)

    def apply_restore(self):
        if self.worker is not None or self.sim is None or not self.approved_steps:
            return
        if QMessageBox.question(self,self.windowTitle(),self.tr2("Palautetaanko asetukset simulaattoriin?","Restore settings to simulator?"),QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
            return
        steps,self.approved_steps = self.approved_steps,None
        self.start_worker(RestoreWorker(self.port,self.sim,self.directory/(uuid4().hex+"-journal.json"),self.source,self.target,steps,self),self.restore_done)

    def restore_done(self, result, detail):
        self.status.setText((self.tr2("Palautus varmennettu takaisinluvulla: ","Restore verified by readback: ") if result else self.tr2("Palautus keskeytyi; tarkista nykytila: ","Restore interrupted; inspect current state: "))+detail)
        self.clear_preview()

    def reject(self):
        if self.worker is None:
            super().reject()

    def closeEvent(self,event):
        if self.worker is not None:
            event.ignore()
        else:
            super().closeEvent(event)

    def open_target(self,path):
        self.clear_preview()
        self.status.setToolTip('')
        self.target_label.setText(self.tr2('Turvavarmuuskopio: ','Safety backup: ')+str(path))
        if self.source is None:
            return False
        try:
            report = preview(self.source,load(path))
        except (OSError,ValueError,KeyError,TypeError,AttributeError,IndexError) as exc:
            self.status.setText(self.tr2("Suunnitelma hylätty: ","Preview rejected: ")+str(exc))
            return False
        firmware = lambda n: f"{n//100}.{n%100:02d}"
        identity = firmware(report["source_firmware"])+" → "+firmware(report["target_firmware"])
        if report["firmware_mismatch"] or not report["compatible"]:
            warning = self.tr2(
                "Firmwareyhteensopivuutta ei ole varmennettu. Asetusten palautus voi epäonnistua. Kirjoituksia ei sallita. Jatketaanko yhteensopivuusanalyysiin?",
                "Firmware compatibility is unverified. Restoration may fail. Writes are not allowed. Continue to compatibility assessment?")
            if QMessageBox.warning(self,self.windowTitle(),identity+"\n"+warning,
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
                self.status.setText(self.tr2("Peruutettu","Cancelled"))
                return False
        if report["device_mismatch"] and report["compatible"]:
            if QMessageBox.question(self,self.windowTitle(),self.tr2(
                "Eri säädin. Jatketaanko suunnitteluun?","Different controller. Continue preview?"),
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
                self.status.setText(self.tr2("Peruutettu","Cancelled"))
                return False
        self.status.setText(identity+" · "+self.tr2("Vain suunnittelu","Preview only")+"\n"+
            (self.tr2("Ei varmennettua firmwareprofiilia; kaikki kirjoitukset estetty.","No validated firmware profile; all writes blocked.") if not report["compatible"] else
            self.tr2("Suunnitellut kirjoitusoperaatiot: ","Planned write operations: ")+str(len(report["steps"]))+"\n"+
            self.tr2("Palautusmoottorin ulkopuoliset ID:t: ","IDs outside restore engine: ")+str(len(report["excluded_ids"]))))
        self.technical_text = self.tr2("Suunnitellut kirjoitus-ID:t: ","Planned write IDs: ")+str(report["steps"])+"\n"+self.tr2("Palautusmoottorin ulkopuoliset ID:t: ","IDs outside restore engine: ")+str(report["excluded_ids"])
        self.technical.setEnabled(True)
        if report["status"] == "blocked":
            self.status.setText(identity+"\n"+self.tr2("Palautus estetty – ei hyväksyttyä kirjoitussuunnitelmaa: ","Restore blocked – no approved write plan: ")+report["reason"])
        elif report["status"] == "no_changes":
            self.status.setText(identity+"\n"+self.tr2("Palautusmoottorin lohkot ovat samat. Ei kirjoitustarvetta; tämä ei takaa koko konfiguraation yhtäläisyyttä.","Restore engine blocks match. No writes needed; this does not prove complete configuration equality."))
        self.fields = report["fields"]
        if report["compatible"]:
            count = sum(before != after for _,before,after,_ in self.fields)
            self.status.setText(self.status.text()+"\n"+self.tr2("Tunnettujen asetusten erot: ","Known setting differences: ")+str(count))
        self.populate_fields()
        return True

    def clear_preview(self):
        self.fields = []
        self.technical_text = ""
        self.technical.setEnabled(False)
        self.table.setRowCount(0)

    def show_technical(self):
        QMessageBox.information(self,self.technical.text(),self.technical_text)

    def populate_fields(self, *_):
        fields = [field for field in self.fields if not self.only_changes.isChecked() or field[1] != field[2]]
        self.table.setRowCount(len(fields))
        for row,(key,before,after,unit) in enumerate(fields):
            for col,value in enumerate((PARAMETERS[key]["label"].get(self.lang) or key,before,after,unit,
                self.tr2("Muutos","Change") if before!=after else self.tr2("Sama","Same"))):
                self.table.setItem(row,col,QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        return True
