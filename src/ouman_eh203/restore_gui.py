from PySide6.QtWidgets import (QDialog,QVBoxLayout,QPushButton,QLabel,QFileDialog,
    QTableWidget,QTableWidgetItem,QAbstractItemView,QMessageBox)
from .backup import load
from .restore_preview import preview
from .metadata import PARAMETERS

class RestoreDialog(QDialog):
    def __init__(self, source, lang, parent=None):
        super().__init__(parent)
        self.source = source
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
        self.choose = QPushButton(self.tr2("Valitse kohdelaitteen varmuuskopio","Choose target backup"))
        self.choose.clicked.connect(self.select)
        self.choose.setEnabled(source is not None)
        layout.addWidget(self.choose)
        self.status.setText(self.tr2("Vain suunnittelu – ei kirjoituksia.","Preview only – no writes."))
        self.target_label = QLabel(self.tr2('Ei valittua kohdetta','No target selected'))
        self.target_label.setWordWrap(True)
        layout.addWidget(self.target_label)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.table = QTableWidget(0,5)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(self.tr2(
            ["Parametri","Kohde nyt","Palautettava","Yksikkö","Tila"],
            ["Parameter","Target now","Desired","Unit","Status"]))
        layout.addWidget(self.table)
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
        self.source_path = ""
        self.choose.setEnabled(False)
        self.table.setRowCount(0)
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
        self.status.setText(self.tr2("Valitse kohdelaitteen nykytilan varmuuskopio.","Choose a backup of the target controller's current state."))
        return True

    def select(self):
        path,_ = QFileDialog.getOpenFileName(self,self.choose.text(),"","JSON (*.json)")
        if path:
            self.open_target(path)

    def open_target(self,path):
        self.table.setRowCount(0)
        self.status.setToolTip('')
        self.target_label.setText(self.tr2('Kohde: ','Target: ')+str(path))
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
        self.status.setText(str(path)+"\n"+identity+" · "+self.tr2("Vain suunnittelu","Preview only")+"\n"+
            (self.tr2("Ei varmennettua firmwareprofiilia; kaikki kirjoitukset estetty.","No validated firmware profile; all writes blocked.") if not report["compatible"] else
            self.tr2("Suunnitellut kirjoitus-ID:t: ","Planned write IDs: ")+str(report["steps"])+"\n"+
            self.tr2("Palautusmoottorin ulkopuoliset ID:t: ","IDs outside restore engine: ")+str(len(report["excluded_ids"]))))
        self.status.setToolTip(self.tr2("Palautusmoottorin ulkopuoliset ID:t: ","IDs outside restore engine: ")+str(report["excluded_ids"]))
        if report["status"] == "blocked":
            self.status.setText(str(path)+"\n"+identity+"\n"+self.tr2("Palautus estetty – ei hyväksyttyä kirjoitussuunnitelmaa: ","Restore blocked – no approved write plan: ")+report["reason"])
        elif report["status"] == "no_changes":
            self.status.setText(str(path)+"\n"+identity+"\n"+self.tr2("Palautusmoottorin lohkot ovat samat. Ei kirjoitustarvetta; tämä ei takaa koko konfiguraation yhtäläisyyttä.","Restore engine blocks match. No writes needed; this does not prove complete configuration equality."))
        self.table.setRowCount(len(report["fields"]))
        for row,(key,before,after,unit) in enumerate(report["fields"]):
            for col,value in enumerate((PARAMETERS[key]["label"].get(self.lang) or key,before,after,unit,
                self.tr2("Muutos","Change") if before!=after else self.tr2("Sama","Same"))):
                self.table.setItem(row,col,QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        return True
