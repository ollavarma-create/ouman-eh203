from pathlib import Path
from uuid import uuid4
from decimal import Decimal
from PySide6.QtCore import QThread, Signal, QStandardPaths
from PySide6.QtWidgets import QDialog,QVBoxLayout,QComboBox,QLabel,QLineEdit,QPushButton,QMessageBox
from .parameter_edit import KEYS,MAP,current,proposal,apply
from .metadata import PARAMETERS
from .validation import BOUNDS

class EditWorker(QThread):
    outcome = Signal(bool,str)
    def __init__(self,sim,key,value,approved,parent):
        super().__init__(parent)
        self.args = sim,key,value,approved
    def run(self):
        try:
            directory = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))/'edit-safety'
            token = uuid4().hex
            journal = directory/(token+'-journal.json')
            apply(*self.args,directory/(token+'-before.json'),journal)
            self.outcome.emit(True,str(journal))
        except Exception as exc:
            self.outcome.emit(False,str(exc))

class ParameterDialog(QDialog):
    def __init__(self,sim,lang,help_callback,parent=None):
        super().__init__(parent)
        self.sim,self.lang,self.help_callback = sim,lang,help_callback
        self.worker = None
        self.setWindowTitle(self.t('Simulaattorin asetukset','Simulator settings'))
        self.resize(620,350)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.t('Vain simulaattori – ei fyysisen laitteen kirjoituksia.','Simulator only – no physical writes.')))
        self.choice = QComboBox()
        for key in KEYS:
            self.choice.addItem(key.split('_')[0].upper()+' · '+PARAMETERS[key]['label'][lang],key)
        layout.addWidget(self.choice)
        self.info = QLabel()
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        self.value = QLineEdit()
        layout.addWidget(self.value)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.manual = QPushButton(self.t('Käsikirja','Manual'))
        self.manual.clicked.connect(self.open_help)
        layout.addWidget(self.manual)
        self.save = QPushButton(self.t('Esikatsele ja hyväksy','Preview and approve'))
        self.save.clicked.connect(self.commit)
        layout.addWidget(self.save)
        self.close_button = QPushButton(self.t('Sulje','Close'))
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button)
        self.choice.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def t(self,fi,en):
        return fi if self.lang=='fi' else en

    def refresh(self,*_):
        key = self.choice.currentData()
        meta = PARAMETERS[key]
        old = current(self.sim,key)
        factor,unit = MAP[key][-2:]
        limits = meta['manual_range']
        bounds = BOUNDS.get(key)
        tested = '0 → 5' if key=='dhw_boost' else '—' if bounds is None else '…'.join(str(Decimal(v)*Decimal(factor)) for v in bounds)
        self.info.setText(self.t('Nykyinen','Current')+f': {old} {unit}\n'+self.t('Dokumentoitu oletus','Documented default')+f": {meta['factory_default']} {unit}\n"+self.t('Dokumentoitu alue','Documented range')+f': {limits[0]}…{limits[1]} {unit}\n'+self.t('Kokeellinen kirjoitusraja (ei kirjoituslupa)','Experimental write bounds (not authorization)')+f': {tested} {unit}\n'+self.t('Askel','Step')+f': {factor} {unit}')
        self.value.setText(str(old))
        self.status.clear()

    def open_help(self):
        page = PARAMETERS[self.choice.currentData()]['manual_page'][self.lang]
        if page is not None:
            self.help_callback(page)

    def commit(self):
        if self.worker is not None:
            return
        key = self.choice.currentData()
        value = self.value.text().strip().replace(',','.')
        try:
            approved = proposal(self.sim,key,value)
        except (ValueError,ArithmeticError,OverflowError) as exc:
            self.status.setText(self.t('Virhe: ','Error: ')+str(exc))
            return
        if approved[1]==approved[2]:
            self.status.setText(self.t('Ei muutoksia','No changes'))
            return
        if QMessageBox.question(self,self.windowTitle(),f'{self.choice.currentText()}: {current(self.sim,key)} → {value} {MAP[key][-1]}\n'+self.t('Muuta vain simulaattoria?','Change simulator only?'))!=QMessageBox.StandardButton.Yes:
            return
        self.worker = EditWorker(self.sim,key,value,approved,self)
        for w in (self.choice,self.value,self.save,self.close_button):
            w.setEnabled(False)
        self.worker.outcome.connect(self.result)
        self.worker.finished.connect(self.finished_worker)
        self.worker.start()

    def result(self,ok,detail):
        if ok:
            self.refresh()
        self.status.setText(self.t('Takaisinluku varmennettu: ','Readback verified: ')+detail if ok else self.t('Virhe; tarkista simulaattorin tila: ','Error; inspect simulator state: ')+detail)

    def finished_worker(self):
        self.worker.deleteLater()
        self.worker = None
        for w in (self.choice,self.value,self.save,self.close_button):
            w.setEnabled(True)

    def reject(self):
        if self.worker is None:
            super().reject()

    def closeEvent(self,event):
        if self.worker is not None:
            event.ignore()
        else:
            super().closeEvent(event)
