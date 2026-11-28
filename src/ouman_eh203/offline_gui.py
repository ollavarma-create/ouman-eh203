"""Read-only inspection of verified captures."""
from .backup import load, known_fields, compare
from .metadata import PARAMETERS
from PySide6.QtWidgets import (QCheckBox,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,
    QLineEdit,QFileDialog,QTableWidget,QTableWidgetItem,QAbstractItemView,QTabWidget,QHeaderView)

class OfflinePage(QWidget):
    def __init__(self, help_callback):
        super().__init__()
        self.snapshot = None
        self.fields = {}
        self.path = ""
        self.second = None
        self.second_path = ""
        self.report = None
        self.lang = "en"
        self.help_callback = help_callback
        self.restore_callback = None
        self.editable_callback = None
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.open_button = QPushButton()
        self.open_button.clicked.connect(self.choose)
        self.search = QLineEdit()
        self.search.textChanged.connect(self.filter)
        self.help = QPushButton()
        self.help.clicked.connect(self.open_help)
        self.compare_button = QPushButton()
        self.compare_button.clicked.connect(self.choose_comparison)
        self.only_changes = QCheckBox()
        self.only_changes.setChecked(True)
        self.only_changes.toggled.connect(self.filter)
        self.restore_button = QPushButton()
        self.restore_button.clicked.connect(self.open_restore)
        for w in (self.open_button,self.compare_button,self.restore_button,self.search,self.help):
            bar.addWidget(w)
        layout.addLayout(bar)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.comparison_status = QLabel()
        self.comparison_status.setWordWrap(True)
        layout.addWidget(self.comparison_status)
        layout.addWidget(self.only_changes)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.table = QTableWidget()
        self.raw = QTableWidget()
        self.diff = QTableWidget()
        self.raw_diff = QTableWidget()
        for table in (self.table,self.raw,self.diff,self.raw_diff):
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setStretchLastSection(True)
            self.tabs.addTab(table,"")
        self.table.itemSelectionChanged.connect(self.help_state)
        self.diff.itemSelectionChanged.connect(self.help_state)
        self.tabs.currentChanged.connect(self.help_state)
        self.translate("en")

    def tr2(self,fi,en):
        return fi if self.lang == "fi" else en

    def choose(self):
        path,_ = QFileDialog.getOpenFileName(self,self.tr2("Avaa varmuuskopio","Open backup"),"","JSON (*.json)")
        if path:
            self.open_path(path)

    def open_path(self,path):
        self.second = self.report = None
        self.second_path = ''
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

    def open_restore(self):
        if self.restore_callback is not None:
            self.restore_callback()

    def choose_comparison(self):
        path,_ = QFileDialog.getOpenFileName(self,self.tr2("Valitse toinen varmuuskopio","Choose second backup"),"","JSON (*.json)")
        if path:
            self.compare_path(path)

    def compare_path(self,path):
        self.second = self.report = None
        self.second_path = ""
        try:
            if self.snapshot is None:
                raise ValueError("No baseline")
            second = load(path)
            report = compare(self.snapshot,second)
            fields = known_fields(second)["fields"]
        except (OSError,ValueError,KeyError,TypeError,AttributeError,IndexError) as exc:
            self.populate_comparison()
            self.comparison_status.setText(self.tr2("Vertailu hylätty: ","Comparison rejected: ")+str(exc))
            return False
        self.second,self.report,self.second_path = fields,report,str(path)
        self.populate_comparison()
        self.tabs.setCurrentIndex(2)
        return True

    def populate_comparison(self):
        self.compare_button.setEnabled(self.snapshot is not None)
        self.restore_button.setEnabled(True)
        self.only_changes.setEnabled(self.report is not None)
        self.diff.setColumnCount(6)
        self.diff.setHorizontalHeaderLabels(self.tr2(["Parametri","Ensimmäinen","Toinen","Yksikkö","Tila","Avain"],["Parameter","First","Second","Unit","Status","Key"]))
        self.raw_diff.setColumnCount(5)
        self.raw_diff.setHorizontalHeaderLabels(self.tr2(["ID","Ensimmäinen tila","Toinen tila","Muuttuneet tavusiirtymät","Luokitus"],["ID","First status","Second status","Changed byte offsets","Category"]))
        self.diff.setRowCount(0)
        self.raw_diff.setRowCount(0)
        self.comparison_status.clear()
        if self.report is not None:
            changes = self.report["known_field_changes"]
            self.diff.setRowCount(len(self.fields))
            for row,(key,field) in enumerate(sorted(self.fields.items())):
                changed = key in changes
                values = (PARAMETERS[key]["label"].get(self.lang) or key,field["value"],self.second[key]["value"],field["unit"],self.tr2("Muuttunut","Changed") if changed else self.tr2("Sama","Same"),key)
                for col,value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if changed:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    self.diff.setItem(row,col,item)
            raw = self.report["raw_payload_differences"]
            self.raw_diff.setRowCount(len(raw))
            for row,(pid,entry) in enumerate(sorted(raw.items(),key=lambda pair:int(pair[0]))):
                offsets = entry["changed_data_offsets"]
                category = self.tr2("Mahdollinen aikaleima","Timestamp candidate") if entry["category"] == "timestamp_candidate" else self.tr2("Tuntematon / tarkistettava","Unknown / review required")
                for col,value in enumerate((pid,entry["before_status"],entry["after_status"],"—" if offsets is None else ", ".join(map(str,offsets)),category)):
                    self.raw_diff.setItem(row,col,QTableWidgetItem(str(value)))
            self.comparison_status.setText(self.tr2("Toinen: ","Second: ")+self.second_path+" · "+self.tr2("Muuttuneet asetukset: ","Changed settings: ")+str(len(changes))+"/"+str(len(self.fields))+" · "+self.tr2("Raakalohkojen erot: ","Raw block differences: ")+str(len(raw))+"\n"+self.tr2("Tunnettujen asetusten yhtäläisyys ei takaa koko konfiguraation yhtäläisyyttä.","Known settings equality does not prove complete configuration equality."))
        self.filter()
        self.help_state()

    def translate(self,lang):
        self.lang = lang
        self.open_button.setText(self.tr2("Avaa varmuuskopio","Open backup"))
        self.search.setPlaceholderText(self.tr2("Hae parametreja","Search parameters"))
        self.help.setText(self.tr2("Käsikirja","Manual"))
        self.tabs.setTabText(0,self.tr2("Tunnetut asetukset","Known settings"))
        self.tabs.setTabText(1,self.tr2("Raakadata","Raw data"))
        self.tabs.setTabText(2,self.tr2("Asetuserot","Settings comparison"))
        self.tabs.setTabText(3,self.tr2("Raakadataerot","Raw differences"))
        self.restore_button.setText(self.tr2('Palautussuunnitelma','Restore preview'))
        self.compare_button.setText(self.tr2("Vertaa varmuuskopioon","Compare backup"))
        self.only_changes.setText(self.tr2("Näytä vain muuttuneet asetukset","Show changed settings only"))
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
        self.mark_editable()
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
        self.populate_comparison()

    def mark_editable(self):
        keys = self.editable_callback() if self.editable_callback else ()
        for row in range(self.table.rowCount()):
            key = self.table.item(row,5)
            label = self.table.item(row,1)
            if key is None or label is None:
                continue
            name = PARAMETERS[key.text()]['label'].get(self.lang) or key.text()
            label.setText(('✎ ' if key.text() in keys else '') + name)
            label.setToolTip(self.tr2('Varmuuskopion arvo; kaksoisnapsauta muokataksesi simulaattorin arvoa.','Backup value; double-click to edit the simulator value.') if key.text() in keys else key.text())

    def filter(self,*_):
        query = self.search.text().casefold()
        for table in (self.table,self.raw,self.diff,self.raw_diff):
            for row in range(table.rowCount()):
                hidden = not any(query in table.item(row,col).text().casefold() for col in range(table.columnCount()) if table.item(row,col))
                if table is self.diff and self.only_changes.isChecked() and self.report is not None:
                    hidden = hidden or table.item(row,5).text() not in self.report['known_field_changes']
                table.setRowHidden(row,hidden)
        self.help_state()

    def selected_page(self):
        index = self.tabs.currentIndex()
        table = self.diff if index == 2 else self.table
        row = table.currentRow()
        if index not in (0,2) or row<0 or table.isRowHidden(row):
            return None
        item = table.item(row,5)
        return PARAMETERS[item.text()]["manual_page"].get(self.lang) if item else None

    def help_state(self,*_):
        self.help.setEnabled(self.selected_page() is not None)

    def open_help(self):
        page = self.selected_page()
        if page is not None:
            self.help_callback(page)
