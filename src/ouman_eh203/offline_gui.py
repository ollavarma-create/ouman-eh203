"""Read-only inspection of verified captures."""
from .backup import load, known_fields
from .metadata import PARAMETERS
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,
    QLineEdit,QFileDialog,QTableWidget,QTableWidgetItem,QAbstractItemView,QTabWidget,QHeaderView)

class OfflinePage(QWidget):
    def __init__(self, help_callback):
        super().__init__()
        self.snapshot = None
        self.fields = {}
        self.path = ""
        self.lang = "en"
        self.help_callback = help_callback
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.open_button = QPushButton()
        self.open_button.clicked.connect(self.choose)
        self.search = QLineEdit()
        self.search.textChanged.connect(self.filter)
        self.help = QPushButton()
        self.help.clicked.connect(self.open_help)
        for w in (self.open_button,self.search,self.help):
            bar.addWidget(w)
        layout.addLayout(bar)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.table = QTableWidget()
        self.raw = QTableWidget()
        for table in (self.table,self.raw):
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setStretchLastSection(True)
            self.tabs.addTab(table,"")
        self.table.itemSelectionChanged.connect(self.help_state)
        self.tabs.currentChanged.connect(self.help_state)
        self.translate("en")

    def tr2(self,fi,en):
        return fi if self.lang == "fi" else en

    def choose(self):
        path,_ = QFileDialog.getOpenFileName(self,self.tr2("Avaa varmuuskopio","Open backup"),"","JSON (*.json)")
        if path:
            self.open_path(path)

    def open_path(self,path):
        self.snapshot = None
        self.fields = {}
        self.path = ""
        try:
            snapshot = load(path)
            fields = known_fields(snapshot)["fields"]
        except (OSError,ValueError,KeyError,TypeError,AttributeError,IndexError) as exc:
            self.populate()
            self.status.setText(self.tr2("Varmuuskopiota ei hyväksytty: ","Backup rejected: ")+str(exc))
            return False
        self.snapshot,self.fields,self.path = snapshot,fields,str(path)
        self.populate()
        return True

    def translate(self,lang):
        self.lang = lang
        self.open_button.setText(self.tr2("Avaa varmuuskopio","Open backup"))
        self.search.setPlaceholderText(self.tr2("Hae parametreja","Search parameters"))
        self.help.setText(self.tr2("Käsikirja","Manual"))
        self.tabs.setTabText(0,self.tr2("Tunnetut asetukset","Known settings"))
        self.tabs.setTabText(1,self.tr2("Raakadata","Raw data"))
        self.populate()

    def populate(self):
        headers = self.tr2(["Ryhmä","Parametri","Arvo","Yksikkö","Dokumentoitu oletus","Avain"],["Group","Parameter","Value","Unit","Documented default","Key"])
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.fields))
        for row,(key,field) in enumerate(sorted(self.fields.items())):
            meta = PARAMETERS[key]
            group = {"l1":"L1","l2":"L2","dhw":self.tr2("LV","DHW"),"r1":"R1","r2":"R2"}.get(key.split("_")[0],self.tr2("Muut","Other"))
            label = meta["label"].get(self.lang) or key
            default = meta.get("factory_default")
            values = (group,label,field["value"],field["unit"],"—" if default is None else default,key)
            for col,value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(key+" | "+str(meta.get("documentation_status","")))
                self.table.setItem(row,col,item)
        records = self.snapshot["records"] if self.snapshot else {}
        self.raw.setColumnCount(4)
        self.raw.setHorizontalHeaderLabels(["ID",self.tr2("Tila","Status"),self.tr2("Data (hex)","Data (hex)"),"RX (hex)"])
        self.raw.setRowCount(len(records))
        for row,pid in enumerate(sorted(records,key=int)):
            rec = records[pid]
            for col,value in enumerate((pid,rec["status"],rec["data"] or "—",rec["rx"])):
                self.raw.setItem(row,col,QTableWidgetItem(str(value)))
        self.status.setText(self.tr2("Ei avattua varmuuskopiota","No backup loaded") if not self.snapshot else
            self.tr2("Varmennettu offline-kaappaus","Verified offline capture")+" · EH-203 / 2.15 · "+str(self.snapshot.get("created_at",""))+" · "+self.path)
        self.filter()
        self.help_state()

    def filter(self,*_):
        query = self.search.text().casefold()
        for table in (self.table,self.raw):
            for row in range(table.rowCount()):
                table.setRowHidden(row,not any(query in table.item(row,col).text().casefold() for col in range(table.columnCount()) if table.item(row,col)))

    def selected_page(self):
        row = self.table.currentRow()
        if self.tabs.currentIndex()!=0 or row<0 or self.table.isRowHidden(row):
            return None
        item = self.table.item(row,5)
        return PARAMETERS[item.text()]["manual_page"].get(self.lang) if item else None

    def help_state(self,*_):
        self.help.setEnabled(self.selected_page() is not None)

    def open_help(self):
        page = self.selected_page()
        if page is not None:
            self.help_callback(page)
