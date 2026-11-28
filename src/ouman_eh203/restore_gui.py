from PySide6.QtWidgets import (QDialog,QVBoxLayout,QPushButton,QLabel,QFileDialog,
    QTableWidget,QTableWidgetItem,QAbstractItemView,QMessageBox)
from .backup import load
from .restore_preview import preview
from .metadata import PARAMETERS

class RestoreDialog(QDialog):
    def __init__(self, source, lang, parent=None):
        super().__init__(parent)
        self.source = source
        self.lang = lang
        self.setWindowTitle(self.tr2("Palautussuunnitelma","Restore preview"))
        self.resize(850,600)
        layout = QVBoxLayout(self)
        self.choose = QPushButton(self.tr2("Valitse kohdelaitteen varmuuskopio","Choose target backup"))
        self.choose.clicked.connect(self.select)
        layout.addWidget(self.choose)
        self.status = QLabel(self.tr2("Vain suunnittelu – ei kirjoituksia.","Preview only – no writes."))
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

    def select(self):
        path,_ = QFileDialog.getOpenFileName(self,self.choose.text(),"","JSON (*.json)")
        if path:
            self.open_target(path)

    def open_target(self,path):
        self.table.setRowCount(0)
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
            self.tr2("Palautusmoottorin ulkopuoliset ID:t: ","IDs outside restore engine: ")+str(report["excluded_ids"])))
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
        return True
