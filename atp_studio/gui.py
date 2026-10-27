from __future__ import annotations
import sys, math, traceback
from pathlib import Path
import numpy as np
from PySide6 import QtCore as C, QtGui as G, QtWidgets as W
import pyqtgraph as pg
from scipy.ndimage import binary_erosion
from .common import ROOT, Job, Cancelled, read_json
from .project import Project, inspect_oir, create_project, detect, import_mat, export_selected, DEFAULT_DETECTION, applied_settings
from .branding import APP_NAME, creator_html
from . import __version__

pg.setConfigOptions(imageAxisOrder='row-major',antialias=True,background='w',foreground='#4b5967')
STATES={'pending':'Pending / 未確認','accepted':'Keep / 採用','rejected':'Exclude / 除外','hold':'Hold / 保留'}
STYLE='''
QWidget{font-family:"Yu Gothic UI","Hiragino Sans","Segoe UI";font-size:13px;color:#253342;}
QMainWindow{background:#f3f6f8;} QFrame#card{background:white;border:1px solid #dfe7eb;border-radius:12px;}
QLabel#title{font-size:26px;font-weight:700;color:#18333a;} QLabel#subtitle{color:#687a88;font-size:13px;}
QLabel#heading{font-size:21px;font-weight:700;} QLabel#muted{color:#687a88;}
QPushButton{background:white;border:1px solid #cddadd;border-radius:7px;padding:9px 14px;}
QPushButton:hover{background:#e8f5f1;border-color:#128770;} QPushButton:disabled{color:#98a6ae;background:#f1f4f5;}
QPushButton#primary{background:#107d69;color:white;border:0;font-weight:600;padding:11px 18px;}
QPushButton#primary:hover{background:#086652;} QPushButton#nav{border:0;text-align:left;padding:17px 13px;background:transparent;color:#5e7180;}
QPushButton#nav:checked{background:#dceee8;color:#096b58;font-weight:700;}
QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox,QPlainTextEdit{background:white;border:1px solid #cedbdf;border-radius:6px;padding:7px;}
QLineEdit:disabled,QSpinBox:disabled,QDoubleSpinBox:disabled{background:#f0f3f5;color:#97a4ae;border-color:#e1e7eb;}
QGroupBox QLabel:disabled{color:#97a4ae;}
QGroupBox{background:white;border:1px solid #dfe7eb;border-radius:9px;margin-top:16px;padding:18px 12px 12px;}
QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 5px;font-weight:600;}
QHeaderView::section{background:#eef4f5;border:0;padding:8px;font-weight:600;}
QTableWidget{background:white;border:1px solid #dde6e9;gridline-color:#eef2f4;selection-background-color:#d8eee7;selection-color:#134b3e;}
QProgressBar{border:0;background:#e3ebe9;height:5px;} QProgressBar::chunk{background:#15957c;}
QSplitter::handle{background:#e3eaed;width:4px;}
'''

def label(text,name=None,wrap=True):
    w=W.QLabel(text);w.setWordWrap(wrap)
    if name:w.setObjectName(name)
    return w

def button(text,fn,primary=False):
    b=W.QPushButton(text);b.clicked.connect(fn)
    if primary:b.setObjectName('primary')
    return b

def double(value=0,minimum=0,maximum=100000,decimals=6):
    b=W.QDoubleSpinBox();b.setRange(minimum,maximum);b.setDecimals(decimals);b.setValue(value);b.setSingleStep(.1);return b

class Worker(C.QThread):
    message=C.Signal(str);succeeded=C.Signal(object);failed=C.Signal(str)
    def __init__(self,fn): super().__init__();self.fn=fn;self.job=Job(self.message.emit)
    def run(self):
        try:self.succeeded.emit(self.fn(self.job))
        except Cancelled as e:self.failed.emit(str(e))
        except Exception as e:self.failed.emit(str(e)+'\n\n'+traceback.format_exc())

class MainWindow(W.QMainWindow):
    def __init__(self,project=None):
        super().__init__();self.setWindowTitle('ATP ROA Studio · AQuA2');self.resize(1440,960);self.setMinimumSize(1100,780)
        self.project=None;self.metadata=None;self.worker=None;self.selected_id=None;self.current_data=None;self.movie=None
        self.events=[];self.voxel_cache={};self.preview_limits=(0,1);self.last_export=None
        self.timer=C.QTimer(self);self.timer.setInterval(100);self.timer.timeout.connect(self.advance_frame)
        central=W.QWidget();self.setCentralWidget(central);outer=W.QVBoxLayout(central);outer.setContentsMargins(24,20,24,12);outer.setSpacing(16)
        head=W.QHBoxLayout();brand=W.QVBoxLayout();brand.addWidget(label('ATP ROA Studio','title'));brand.addWidget(label('From OIR to reviewed ATP activity / AQuA2によるATP解析','subtitle'));head.addLayout(brand);head.addStretch()
        self.open_btn=button('Open project / プロジェクトを開く',self.open_project);head.addWidget(self.open_btn);self.folder_btn=button('Open folder / フォルダー',self.open_folder);head.addWidget(self.folder_btn)
        outer.addLayout(head);body=W.QHBoxLayout();body.setSpacing(20)
        sidebar=W.QWidget();sidebar.setFixedWidth(205);sl=W.QVBoxLayout(sidebar);sl.setContentsMargins(0,4,0,0);self.nav=[]
        self.stack=W.QStackedWidget()
        for i,text in enumerate(['01   Prepare / 準備','02   Detect / 検出','03   Review / 確認','04   Export / 出力']):
            b=W.QPushButton(text);b.setObjectName('nav');b.setCheckable(True);b.clicked.connect(lambda checked=False,n=i:self.go(n));sl.addWidget(b);self.nav.append(b)
        sl.addStretch();sl.addWidget(label('LOCAL ANALYSIS','muted'));sl.addWidget(label('Originals preserved.\n原本を保持・確認履歴を保存','muted'));sl.addSpacing(12);sl.addWidget(label('v0.1 · Research preview / 研究用','muted'))
        body.addWidget(sidebar);body.addWidget(self.stack,1);outer.addLayout(body,1)
        self.setup_prepare();self.setup_detect();self.setup_review();self.setup_export()
        self.progress=W.QProgressBar();self.progress.setRange(0,1);self.progress.setValue(0);self.progress.setTextVisible(False);outer.addWidget(self.progress)
        bottom=W.QHBoxLayout();self.status=label('Choose an OIR to begin. / OIRファイルを選択してください。','muted');bottom.addWidget(self.status,1)
        self.cancel_btn=button('Cancel / 中止',self.cancel);self.cancel_btn.setEnabled(False);bottom.addWidget(self.cancel_btn);outer.addLayout(bottom)
        self.logbox=W.QPlainTextEdit();self.logbox.setReadOnly(True);self.logbox.setMaximumHeight(90);self.logbox.setVisible(False);outer.addWidget(self.logbox)
        menu=self.menuBar().addMenu('Help / ヘルプ');action=menu.addAction('User guide / 操作ガイド');action.triggered.connect(lambda:self.open_path(ROOT/'docs/user-guide.html'))
        action=menu.addAction('Show log / ログ表示');action.triggered.connect(lambda:self.logbox.setVisible(not self.logbox.isVisible()))
        menu.addSeparator();action=menu.addAction('About / このアプリについて');action.triggered.connect(self.show_about)
        self.setStyleSheet(STYLE);self.go(0)
        if project:self.load_project(project)

    def show_about(self):
        box=W.QMessageBox(self);box.setWindowTitle('About / このアプリについて')
        box.setTextFormat(C.Qt.TextFormat.RichText)
        box.setText(f'<h2>{APP_NAME}</h2><p>Version {__version__}</p>'+creator_html()
            +'<p>Analysis engine / 解析エンジン: AQuA2-Fiji<br>OIR reader / OIR読込: Bio-Formats</p>'
            +'<p>Third-party credits and licenses / 外部ソフトウェアの著作権・ライセンス: THIRD_PARTY_NOTICES.txt</p>')
        box.setStandardButtons(W.QMessageBox.StandardButton.Ok);box.exec()

    def page(self,title,sub):
        page=W.QWidget();layout=W.QVBoxLayout(page);layout.setContentsMargins(2,0,2,0);layout.setSpacing(14)
        layout.addWidget(label(title,'heading'));layout.addWidget(label(sub,'muted'));self.stack.addWidget(page);return layout

    def setup_prepare(self):
        v=self.page('Prepare your recording / 記録を準備','Read spatial and temporal metadata from OIR, then check or edit. / OIRの時空間情報を読み込み、確認・修正します。')
        row=W.QHBoxLayout();self.source=W.QLineEdit();self.source.setReadOnly(True);self.source.setPlaceholderText('Olympus / Evident .oir')
        row.addWidget(self.source,1);row.addWidget(button('Choose OIR / OIRを選択…',self.pick_oir,True));v.addLayout(row)
        row=W.QHBoxLayout();self.series=W.QSpinBox();self.channel=W.QSpinBox();self.zplane=W.QSpinBox()
        for name,w in [('Series / シリーズ',self.series),('ATP channel / チャネル',self.channel),('Z plane / Z面',self.zplane)]:w.setRange(1,1);row.addWidget(label(name));row.addWidget(w)
        row.addStretch();row.addWidget(button('Read metadata / 再読み込み',self.reinspect));v.addLayout(row)
        self.meta_text=label('Select a file to read frames, dimensions and calibration. / ファイル選択後にフレーム数・画像サイズ・校正値を表示します。','muted');v.addWidget(self.meta_text)
        split=W.QHBoxLayout();group=W.QGroupBox('Calibration / 時空間設定 — editable');f=W.QFormLayout(group)
        self.dt=double();self.px=double();self.py=double();self.override=W.QCheckBox('Use manual interval / 時間間隔を手動指定')
        self.override.setToolTip('Use this fixed interval instead of source timestamps; original metadata is retained. / 原本の時刻情報を保持し、指定した間隔を適用します。')
        f.addRow('Interval / 時間間隔 (s/frame)',self.dt);f.addRow('Pixel X / 画素幅 (µm/pixel)',self.px);f.addRow('Pixel Y / 画素高 (µm/pixel)',self.py);f.addRow(self.override)
        self.dt.valueChanged.connect(lambda:self.override.setChecked(True) if self.metadata else None)
        f.addRow(button('Restore metadata / 原本値に戻す',self.restore_metadata));split.addWidget(group,1)
        group=W.QGroupBox('Include experiment / 実験情報を含める');self.experiment_group=group
        group.setCheckable(True);group.setChecked(True)
        group.setToolTip('Optional. Uncheck to prepare and export without these details. / 任意です。チェックを外すと、実験情報を含めずに準備・出力します。')
        f=W.QFormLayout(group);self.fields={}
        f.addRow(label('Optional — uncheck to skip. / 不要な場合はチェックを外してください。','muted'))
        for key,name in [('animal_id','Animal ID / 個体ID'),('slice_id','Slice ID / 切片ID'),('recording_id','Recording ID / 記録ID'),('condition','Condition / 条件'),('reviewer','Reviewer / 確認者')]:
            w=W.QLineEdit();self.fields[key]=w;f.addRow(name,w)
        self.drug=double(-1,-1,100000,2);self.drug.setSpecialValueText('Not specified / 未入力');f.addRow('Treatment time / 投与時刻 (s)',self.drug);split.addWidget(group,1);v.addLayout(split)
        row=W.QHBoxLayout();self.destination=W.QLineEdit(str(Path.home()/'Documents'/'ATP_ROA_Projects'));row.addWidget(label('Save to / 保存先'));row.addWidget(self.destination,1);row.addWidget(button('Browse / 参照…',self.pick_destination));v.addLayout(row)
        self.prepare_note=label('Analyze the selected channel and Z plane. Export source-resolution TIFF, MP4, PNG and a whole-field CSV. / 選択したチャネル・Z面を原解像度TIFF、MP4、PNG、視野全体のCSVに変換します。','muted');v.addWidget(self.prepare_note)
        v.addStretch();self.prepare_btn=button('Prepare files / ファイルを準備  →',self.prepare,True);v.addWidget(self.prepare_btn,alignment=C.Qt.AlignmentFlag.AlignRight)

    def setup_detect(self):
        v=self.page('Detect ATP activity / ATP活動を検出','Baseline & noise → active regions → temporal & spatial segmentation → features / 基準線・ノイズ → 活動領域 → 時間・空間分割 → 特徴量')
        self.detect_info=label('Prepare a recording first. / 先に記録を準備してください。','muted');v.addWidget(self.detect_info)
        v.addWidget(label('These are starting parameters, not validated ATP thresholds. Check representative recordings. / 初期値です。ATP用の確定閾値ではないため代表記録で調整してください。','muted'))
        group=W.QGroupBox('Detection settings / 検出設定');f=W.QFormLayout(group);self.params={}
        definitions=[('thrARScl','Activity threshold / 活動閾値 (noise SD)',True,0.1,20),('minSize','Minimum area / 最小面積 (pixels)',False,1,100000),
            ('minDur','Minimum duration / 最小持続 (frames)',False,1,10000),('sigThr','Temporal threshold / 時間分割閾値',True,.1,20),
            ('movAvgWin','Baseline smoothing / 基準線平滑化 (frames)',False,2,10000),('cut','Baseline segment / 基準線区間 (frames)',False,10,100000),
            ('regMaskGap','Edge crop / 周辺除外 (pixels)',False,0,100),('median_radius','Median radius / メディアン半径 (pixels)',False,0,5),('memory_gb','Memory limit / メモリ上限 (GB)',False,2,64)]
        for key,title,isfloat,lo,hi in definitions:
            if isfloat:b=double(DEFAULT_DETECTION[key],lo,hi,2)
            else:b=W.QSpinBox();b.setRange(lo,hi);b.setValue(DEFAULT_DETECTION[key])
            self.params[key]=b;f.addRow(title,b)
        v.addWidget(group)
        v.addWidget(label('Supports uniform 2D+t with square pixels. Global-event search, CFU and motion correction are not included. Every run preserves prior reviews. / 等間隔2D+t・正方画素に対応。全域イベント追加検出、CFU、動き補正は未対応。過去の確認履歴を保持します。','muted'))
        row=W.QHBoxLayout();row.addWidget(button('Import AQuA2 .mat / 読み込み…',self.pick_mat));row.addStretch();row.addWidget(button('Run AQuA2 / 検出開始  →',self.start_detection,True));v.addLayout(row);v.addStretch()

    def setup_review(self):
        v=self.page('Review ROAs / 位置と波形を確認','ROAs are spatiotemporal events, not individual cells. / ROAは時空間活動イベントであり、細胞単位とは限りません。')
        bar=W.QHBoxLayout();self.filter=W.QComboBox();self.filter.addItems(['All / 全て','Pending / 未確認','Keep / 採用','Exclude / 除外','Hold / 保留','Saved favorite / 以前のfavorite']);self.filter.currentIndexChanged.connect(self.populate_table)
        bar.addWidget(self.filter);self.review_count=label('No ROAs yet / ROA未検出','muted');bar.addWidget(self.review_count,1);bar.addWidget(button('Previous run / 以前の解析…',self.pick_run));v.addLayout(bar)
        split=W.QSplitter();self.table=W.QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['ROA','Review / 確認','Peak','Area µm²','★'])
        self.table.setSelectionBehavior(W.QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(W.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers);self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(W.QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.select_row);self.table.setMinimumWidth(345);split.addWidget(self.table)
        right=W.QWidget();r=W.QVBoxLayout(right);r.setContentsMargins(8,0,0,0)
        displayrow=W.QHBoxLayout();self.display_mode=W.QComboBox();self.display_mode.addItems(['Raw / 原画像','Median preview / ノイズ低減表示'])
        self.display_mode.setCurrentIndex(1);self.display_mode.currentIndexChanged.connect(lambda:self.show_frame(self.slider.value()))
        displayrow.addWidget(self.display_mode);displayrow.addWidget(label('Teal: footprint · Gold: active / 緑:領域・黄:活動','muted'));displayrow.addStretch()
        displayrow.addWidget(button('Zoom / 拡大',self.zoom_event));displayrow.addWidget(button('Fit / 全体',lambda:self.view.autoRange()));r.addLayout(displayrow)
        self.canvas=pg.GraphicsLayoutWidget();self.view=self.canvas.addViewBox(lockAspect=True,invertY=True);self.view.setMouseMode(pg.ViewBox.PanMode)
        self.image=pg.ImageItem();self.overlay=pg.ImageItem();self.view.addItem(self.image);self.view.addItem(self.overlay)
        self.canvas.scene().sigMouseClicked.connect(self.image_click);r.addWidget(self.canvas,4)
        row=W.QHBoxLayout();self.play=button('▶ Play / 再生',self.toggle_play);row.addWidget(self.play)
        self.slider=W.QSlider(C.Qt.Orientation.Horizontal);self.slider.valueChanged.connect(self.show_frame);row.addWidget(self.slider,1)
        self.frame_label=label('0.0 s','muted');row.addWidget(self.frame_label);r.addLayout(row)
        self.plot=pg.PlotWidget();self.plot.setLabel('bottom','Time',units='s');self.plot.setLabel('left','ΔF/F');self.plot.showGrid(x=True,y=True,alpha=.15);self.plot.setMinimumHeight(160)
        self.cursor=pg.InfiniteLine(angle=90,pen=pg.mkPen('#ad6e21'));r.addWidget(self.plot,2)
        self.metric_text=label('Select an ROA in the table or image. / 一覧または画像でROAを選択してください。','muted');r.addWidget(self.metric_text)
        split.addWidget(right);split.setSizes([350,700]);v.addWidget(split,1)
        note=W.QHBoxLayout();note.addWidget(label('Review note / メモ'));self.note=W.QLineEdit();self.note.setPlaceholderText('Reason, edge, noise, repeats / 除外理由・境界・ノイズなど');note.addWidget(self.note,1);v.addLayout(note)
        row=W.QHBoxLayout();row.addWidget(button('Keep / 採用 · A',lambda:self.decide('accepted'),True));row.addWidget(button('Exclude / 除外 · R',lambda:self.decide('rejected')));row.addWidget(button('Hold / 保留 · H',lambda:self.decide('hold')));row.addWidget(button('Reset / 未確認へ',lambda:self.decide('pending')))
        row.addStretch();row.addWidget(button('Save note / メモ保存',self.save_note));row.addWidget(button('Export / 出力  →',lambda:self.go(3)));v.addLayout(row)
        for key,state in [('A','accepted'),('R','rejected'),('H','hold')]:
            shortcut=G.QShortcut(G.QKeySequence(key),self);shortcut.activated.connect(lambda s=state:self.decide(s) if self.stack.currentIndex()==2 and not isinstance(W.QApplication.focusWidget(),W.QLineEdit) else None)

    def setup_export(self):
        v=self.page('Export selected ROAs / 採用ROAを出力','Only events marked Keep in this run enter the selected results. / この解析で採用したイベントのみを出力します。')
        self.export_info=label('Reviewed events will appear here. / 確認したROAを表示します。','heading');v.addWidget(self.export_info)
        self.export_warning=label('','muted');v.addWidget(self.export_warning)
        group=W.QGroupBox('Output files / 出力ファイル');g=W.QVBoxLayout(group)
        for text in ['Feature CSV / 定量値  ·  Area, Peak ΔF/F, duration, AUC, FWHM, rise, fall, decay τ',
                     'Trace CSV / 時系列  ·  Full ΔF/F and active frames',
                     'PNG / 画像  ·  ROA map and individual / combined traces',
                     'TIFF + HDF5 / マスク  ·  Per-event masks and spatiotemporal coordinates',
                     'Review & settings / 確認履歴・設定  ·  Includes excluded, held and pending events']:
            g.addWidget(label('✓  '+text))
        v.addWidget(group);self.export_movie=W.QCheckBox('Include selected-ROA overlay MP4 / 採用ROA重畳MP4も保存');self.export_movie.setChecked(True);v.addWidget(self.export_movie)
        v.addWidget(label('Unavailable measurements remain blank with qc_flags. Events are not animal n; retain animal_id and slice_id. / 測定不可は空欄とQC理由で記録します。イベント数と動物数を区別してください。','muted'))
        row=W.QHBoxLayout();row.addStretch();row.addWidget(button('Export selection / 採用結果を保存',self.start_export,True));v.addLayout(row)
        self.export_result=label('','muted');v.addWidget(self.export_result);v.addStretch()

    def go(self,index):
        self.stack.setCurrentIndex(index)
        for i,b in enumerate(self.nav): b.setChecked(i==index)
        if index!=2:self.timer.stop();self.play.setText('▶ Play / 再生') if hasattr(self,'play') else None
        if index==3:self.update_counts()

    def log(self,text):self.status.setText(text[:180]);self.logbox.appendPlainText(text)
    def run_job(self,fn,on_success):
        if self.worker and self.worker.isRunning():return
        self.timer.stop();self.stack.setEnabled(False);self.open_btn.setEnabled(False)
        for b in self.nav:b.setEnabled(False)
        self.progress.setRange(0,0);self.cancel_btn.setEnabled(True)
        self.worker=Worker(fn);self.worker.message.connect(self.log);self.worker.succeeded.connect(on_success);self.worker.failed.connect(self.failure);self.worker.finished.connect(self.job_finished);self.worker.start()
    def job_finished(self):
        self.stack.setEnabled(True);self.open_btn.setEnabled(True)
        for b in self.nav:b.setEnabled(True)
        self.progress.setRange(0,1);self.progress.setValue(1);self.cancel_btn.setEnabled(False)
    def failure(self,message):
        self.log(message);box=W.QMessageBox(self);box.setWindowTitle('Task incomplete / 処理未完了');box.setText(message.split('\n\n')[0]);box.setDetailedText(message);box.exec()
    def cancel(self):
        if self.worker:self.worker.job.cancel.set();self.status.setText('Cancelling… / 中止しています…')
    def pick_oir(self):
        path,_=W.QFileDialog.getOpenFileName(self,'Choose OIR / OIRを選択',str(Path.home()),'Olympus OIR (*.oir)')
        if path:
            self.source.setText(path);self.metadata=None
            for w in (self.series,self.channel,self.zplane):w.setValue(1)
            self.reinspect()
    def reinspect(self):
        if not self.source.text():return
        path=self.source.text();s=self.series.value()-1;c=self.channel.value()-1;z=self.zplane.value()-1
        self.run_job(lambda job:inspect_oir(path,s,c,z,job),self.on_metadata)
    def on_metadata(self,m):
        self.metadata=m
        for w,key in [(self.series,'series_count'),(self.channel,'channels'),(self.zplane,'z_planes')]:w.setMaximum(m[key])
        self.restore_metadata();n,h,w=m['shape'];self.fields['recording_id'].setText(Path(m['source_path']).stem)
        self.meta_text.setText(f'{n:,} frames  ·  {w} × {h} pixels  ·  {m["channels"]} channel(s)  ·  {m["z_planes"]} Z plane(s)  ·  {m["dtype"]}\nSource / 原本: Δt={m.get("interval_s")} s, X={m.get("pixel_x_um")} µm, Y={m.get("pixel_y_um")} µm')
        self.log('Metadata read. Check calibration and ATP channel. / 校正値とATPチャネルを確認してください。')
    def restore_metadata(self):
        if not self.metadata:return
        m=self.metadata;self.dt.blockSignals(True)
        for w,key in [(self.dt,'interval_s'),(self.px,'pixel_x_um'),(self.py,'pixel_y_um')]:w.setValue(m.get(key) or 0)
        self.dt.blockSignals(False);self.override.setChecked(not bool(m.get('interval_s')))
    def pick_destination(self):
        p=W.QFileDialog.getExistingDirectory(self,'Project folder / 保存フォルダー',self.destination.text())
        if p:self.destination.setText(p)
    def preparation_settings(self):
        settings={k:w.text().strip() for k,w in self.fields.items()}
        settings.update(include_experiment=self.experiment_group.isChecked(),interval_s=self.dt.value(),pixel_x_um=self.px.value(),pixel_y_um=self.py.value(),override_time=self.override.isChecked(),drug_s=None if self.drug.value()<0 else self.drug.value())
        return applied_settings(settings)
    def prepare(self):
        if not self.metadata:self.failure('Choose an OIR and read metadata first. / OIRを選択し情報を読み込んでください。');return
        if (self.series.value()-1,self.channel.value()-1,self.zplane.value()-1)!=(self.metadata['series'],self.metadata['channel'],self.metadata['z']):
            self.failure('Series/channel/Z changed. Read metadata again. / シリーズ・チャネル・Zを変更したため再読み込みが必要です。');return
        if min(self.dt.value(),self.px.value(),self.py.value())<=0:self.failure('Enter a positive frame interval and X/Y pixel sizes. / 時間間隔とX/Y画素サイズを入力してください。');return
        settings=self.preparation_settings()
        m=dict(self.metadata);parent=self.destination.text()
        self.run_job(lambda job:create_project(m,parent,settings,job),lambda p:(self.load_project(p),self.go(1)))
    def open_project(self):
        f,_=W.QFileDialog.getOpenFileName(self,'Open project / プロジェクトを開く',self.destination.text(),'ATP project (project.json)')
        if f:
            try:self.load_project(Path(f).parent);self.go(2 if self.events else 1)
            except Exception as e:self.failure(str(e))
    def load_project(self,path):
        p=Project(path)
        required=['movie.ome.tif','time_s.npy','preview.mp4','mean_projection.png','max_projection.png','fov_trace.csv','fov_trace.png']
        if p.manifest.get('status') not in ('prepared','review') or any(not (p.path/'raw'/name).is_file() for name in required):
            raise ValueError('This project is not fully prepared. Start file preparation again in a new project. / 準備が未完了です。新規プロジェクトで再変換してください。')
        self.project=p;self.movie=p.movie();self.times=p.times();self.preview_limits=p.manifest.get('display_limits',(0,255));self.events=p.events();self.voxel_cache={}
        from scipy.ndimage import median_filter
        sample=np.stack([median_filter(self.movie[i],size=3) for i in np.linspace(0,len(self.movie)-1,5,dtype=int)])
        low,high=np.percentile(sample,[1,99.5]);self.median_limits=(float(low),float(max(high,low+1)))
        self.source.setText(p.manifest['source']['source_path']);self.metadata=p.manifest['source'];a=p.manifest['acquisition']
        for widget,count,key in [(self.series,'series_count','series'),(self.channel,'channels','channel'),(self.zplane,'z_planes','z')]:
            widget.setMaximum(self.metadata[count]);widget.setValue(self.metadata[key]+1)
        self.meta_text.setText(f'Source / 原本: {self.metadata["shape"]} (T,Y,X) · Δt {self.metadata.get("interval_s")} s · X {self.metadata.get("pixel_x_um")} µm · Y {self.metadata.get("pixel_y_um")} µm')
        self.dt.blockSignals(True);self.dt.setValue(a['interval_s']);self.dt.blockSignals(False);self.px.setValue(a['pixel_x_um']);self.py.setValue(a['pixel_y_um']);self.override.setChecked(a.get('override_time',False))
        for key,widget in self.fields.items():widget.setText(a.get(key,''))
        self.experiment_group.setChecked(a.get('include_experiment',True))
        self.drug.setValue(a['drug_s'] if a.get('drug_s') is not None else -1)
        self.detect_info.setText(f'{a.get("recording_id",p.path.name)}\n{self.movie.shape[0]} frames · Δt {np.median(np.diff(self.times)):.6g} s · {a["pixel_x_um"]:.6g} µm/pixel\nProject / 保存先: {p.path}')
        self.slider.setRange(0,len(self.movie)-1);self.selected_id=None;self.current_data=None;self.plot.clear();self.populate_table();self.show_frame(self.slider.value());self.log('Project opened. / プロジェクトを開きました。')
    def require_project(self):
        if self.project:return True
        self.failure('Prepare or open a project first. / プロジェクトを準備するか開いてください。');return False
    def start_detection(self):
        if not self.require_project():return
        cfg={k:w.value() for k,w in self.params.items()};path=self.project.path
        self.run_job(lambda job:detect(path,cfg,job),lambda run:(self.load_project(path),self.go(2)))
    def pick_mat(self):
        if not self.require_project():return
        f,_=W.QFileDialog.getOpenFileName(self,'Choose AQuA2 MAT / MATを選択',str(Path.home()),'MATLAB v7.3 (*.mat)')
        if not f:return
        ch,ok=W.QInputDialog.getInt(self,'MAT result channel / 結果チャネル','Result channel in MAT / MAT内の結果チャネル (evt1 / evt2)',1,1,2)
        if ok:
            path=self.project.path;self.run_job(lambda job:import_mat(path,f,ch,job),lambda run:(self.load_project(path),self.go(2)))
    def pick_run(self):
        if not self.require_project():return
        runs=[p for p in (self.project.path/'runs').iterdir() if (p/'settings.json').exists() and read_json(p/'settings.json').get('status')=='complete']
        if not runs:return
        name,ok=W.QInputDialog.getItem(self,'Previous run / 以前の解析','Select a run / 解析を選択',[p.name for p in sorted(runs)],0,False)
        if ok:self.project.manifest['current_run']='runs/'+name;self.project.save();self.load_project(self.project.path)
    def populate_table(self):
        if not hasattr(self,'table'):return
        reviews=self.project.review() if self.project else {};filter_index=self.filter.currentIndex();statuses=[None,'pending','accepted','rejected','hold']
        rows=[e for e in self.events if (filter_index==0 or (filter_index==5 and e['favorite_hint']) or (0<filter_index<5 and reviews.get(str(e['event_id']),{}).get('status','pending')==statuses[filter_index]))]
        self.table.blockSignals(True);self.table.setRowCount(len(rows))
        for i,e in enumerate(rows):
            vals=[str(e['event_id']),STATES[reviews.get(str(e['event_id']),{}).get('status','pending')],f'{e["peak_dff"]:.3f}' if e['peak_dff'] is not None else '—',f'{e["area_um2"]:.1f}','★' if e['favorite_hint'] else '']
            for j,val in enumerate(vals):self.table.setItem(i,j,W.QTableWidgetItem(val))
        self.table.blockSignals(False);self.update_counts()
        if rows:self.table.selectRow(0)
        else:self.selected_id=None;self.current_data=None;self.metric_text.setText('No ROAs match this filter. / 該当するROAがありません。');self.plot.clear();self.show_frame(self.slider.value())
    def update_counts(self):
        reviews=self.project.review() if self.project else {};counts={k:sum(r.get('status')==k for r in reviews.values()) for k in STATES}
        text=f'Keep / 採用 {counts["accepted"]}  ·  Exclude / 除外 {counts["rejected"]}  ·  Hold / 保留 {counts["hold"]}  ·  Pending / 未確認 {counts["pending"]}'
        if hasattr(self,'review_count'):self.review_count.setText(text)
        if hasattr(self,'export_info'):
            self.export_info.setText(f'{counts["accepted"]} kept / 採用 / {len(self.events)} detected / 検出')
            self.export_warning.setText(text+'\nOnly kept ROAs are exported; all review states are retained. / 採用ROAのみを出力し、全確認状態を保存します。')
    def select_row(self):
        row=self.table.currentRow()
        if row<0 or not self.project:return
        item=self.table.item(row,0)
        if item is None:return
        eid=int(item.text());self.selected_id=eid;d=self.project.event_data(eid);self.current_data=d
        e=next(x for x in self.events if x['event_id']==eid);self.note.setText(self.project.review()[str(eid)].get('note',''))
        self.plot.clear();self.plot.plot(self.times,d['dff'],pen=pg.mkPen('#148d79',width=1.7))
        span=pg.LinearRegionItem([e['onset_s'],e['end_s']],movable=False,brush=(20,150,120,25),pen=None);self.plot.addItem(span)
        self.plot.addItem(self.cursor);drug=self.project.manifest['acquisition'].get('drug_s')
        if drug is not None:self.plot.addItem(pg.InfiniteLine(drug,pen=pg.mkPen('#cf8c25',style=C.Qt.PenStyle.DashLine)))
        def fmt(k):return 'N/A / 測定不可' if e[k] is None else f'{e[k]:.3g}'
        self.metric_text.setText(f'ROA {eid}  ·  Peak {fmt("peak_dff")}  ·  Area / 面積 {fmt("area_um2")} µm²  ·  FWHM {fmt("fwhm_s")} s  ·  AUC {fmt("auc_signed_dff_s")} ΔF/F·s\nQC: {e["qc_flags"] or "No flags / なし"}'+('  ·  Saved favorite / 以前のfavorite・再確認が必要' if e['favorite_hint'] else ''))
        frame=int(np.searchsorted(self.times,e['peak_time_s'] if e['peak_time_s'] is not None else e['onset_s']));self.slider.setValue(frame);self.show_frame(frame)
    def show_frame(self,index):
        if self.movie is None:return
        index=min(index,len(self.movie)-1);frame=self.movie[index];levels=self.preview_limits
        if self.display_mode.currentIndex()==1:
            from scipy.ndimage import median_filter
            frame=median_filter(frame,size=3);levels=self.median_limits
        self.image.setImage(frame,autoLevels=False,levels=levels,autoDownsample=True)
        h,w=self.movie.shape[1:];over=np.zeros((h,w,4),dtype=np.uint8)
        if self.current_data is not None:
            offset=np.asarray(read_json(self.project.run_dir()/'settings.json')['offset_yx']);v=self.current_data['voxels'];y=v[:,1]+offset[0];x=v[:,2]+offset[1]
            mask=np.zeros((h,w),bool);mask[y,x]=True;edge=mask&~binary_erosion(mask);over[edge]=[14,205,166,230]
            active=v[:,0]==index;over[y[active],x[active]]=[255,191,66,120]
        self.overlay.setImage(over,autoLevels=False);self.frame_label.setText(f'{self.times[index]:.2f} s  ·  {index+1}/{len(self.movie)}');self.cursor.setValue(self.times[index])
    def zoom_event(self):
        if self.current_data is None:return
        v=self.current_data['voxels'];dy,dx=read_json(self.project.run_dir()/'settings.json')['offset_yx']
        x0,x1=int(v[:,2].min()+dx),int(v[:,2].max()+dx);y0,y1=int(v[:,1].min()+dy),int(v[:,1].max()+dy)
        margin=max(20,max(x1-x0,y1-y0)//2);self.view.setRange(xRange=(x0-margin,x1+margin),yRange=(y0-margin,y1+margin),padding=.02)
    def image_click(self,event):
        if not self.project or event.button()!=C.Qt.MouseButton.LeftButton:return
        pt=self.view.mapSceneToView(event.scenePos());x,y=int(pt.x()),int(pt.y());frame=self.slider.value()
        if not(0<=x<self.movie.shape[2] and 0<=y<self.movie.shape[1]):return
        offset=read_json(self.project.run_dir()/'settings.json')['offset_yx'] if self.project.run_dir() else [0,0];matches=[]
        for i in range(self.table.rowCount()):
            eid=int(self.table.item(i,0).text())
            if eid not in self.voxel_cache:self.voxel_cache[eid]=self.project.event_data(eid)['voxels']
            v=self.voxel_cache[eid];spatial=(v[:,1]+offset[0]==y)&(v[:,2]+offset[1]==x)
            if np.any(spatial):matches.append((not np.any(spatial&(v[:,0]==frame)),i))
        if matches:self.table.selectRow(sorted(matches)[0][1])
    def toggle_play(self):
        if self.timer.isActive():self.timer.stop();self.play.setText('▶ Play / 再生')
        elif self.movie is not None:self.timer.start();self.play.setText('Ⅱ Pause / 停止')
    def advance_frame(self):self.slider.setValue((self.slider.value()+1)%(self.slider.maximum()+1))
    def decide(self,status):
        if self.selected_id is None:return
        row=self.table.currentRow();eid=self.selected_id;self.project.review_event(eid,status,self.note.text(),self.fields['reviewer'].text())
        self.populate_table()
        if self.filter.currentIndex()==0:
            self.table.selectRow(min(row+1,self.table.rowCount()-1))
        self.log(f'ROA {eid} → {STATES[status]} · Review saved / 確認結果を保存')
    def save_note(self):
        if self.selected_id is None:return
        state=self.project.review()[str(self.selected_id)]['status'];self.project.review_event(self.selected_id,state,self.note.text(),self.fields['reviewer'].text());self.log('Note saved / メモを保存しました。')
    def start_export(self):
        if not self.require_project():return
        path=self.project.path;movie=self.export_movie.isChecked()
        self.run_job(lambda job:export_selected(path,movie,job),self.export_done)
    def export_done(self,path):self.last_export=path;self.export_result.setText('Export complete / 保存完了\n'+path);self.log('Export complete / 出力完了。');self.open_path(Path(path)/'RESULTS.html')
    def open_path(self,path):G.QDesktopServices.openUrl(C.QUrl.fromLocalFile(str(Path(path).resolve())))
    def open_folder(self):self.open_path(self.last_export or (self.project.path if self.project else ROOT))
    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            self.cancel();self.status.setText('Wait for cancellation before closing. / 中止完了後に閉じてください。');event.ignore()
        else:event.accept()

def main():
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ATP.ROA.Studio')
    app=W.QApplication(sys.argv);app.setApplicationName(APP_NAME)
    app.setWindowIcon(G.QIcon(str(ROOT/'assets/atp-studio.ico')))
    win=MainWindow(sys.argv[1] if len(sys.argv)>1 else None);win.show();sys.exit(app.exec())

if __name__=='__main__':main()
