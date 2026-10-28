"""Bilingual parameter ranges and problem-led adjustment previews."""
from copy import deepcopy
from PySide6 import QtCore as C, QtWidgets as W
from .detection_guidance import (PARAMETERS, PARAMETER_BY_KEY, ISSUES, ISSUE_BY_KEY,
    DEFAULT_DETECTION, LEGACY_DETECTION, RULE_VERSION, recommend, match_issues,
    validate_settings, range_text, calibrated_value, format_value)


def text_label(text=''):
    label = W.QLabel(text)
    label.setWordWrap(True)
    return label


class ParameterTable(W.QTableWidget):
    def __init__(self, *args):
        super().__init__(*args)
        self.row_sizing = C.QTimer(self)
        self.row_sizing.setSingleShot(True)
        self.row_sizing.timeout.connect(self.resizeRowsToContents)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Measure after the stretched column reaches its final width.
        self.row_sizing.start(0)

    def showEvent(self, event):
        super().showEvent(event)
        self.row_sizing.start(0)


class DetectionPanel(W.QTabWidget):
    def __init__(self, context_provider, parent=None):
        super().__init__(parent)
        self.context_provider = context_provider
        self.params = {}
        self.proposal = None
        self.last_applied = None
        self.previous_settings = None
        self._changing = False
        self.height_sizing = C.QTimer(self)
        self.height_sizing.setSingleShot(True)
        self.height_sizing.timeout.connect(self.update_minimum_height)
        self.setMinimumHeight(430)
        self.build_helper()
        self.build_parameters()
        for widget in self.params.values():
            widget.valueChanged.connect(self.settings_changed)
        self.refresh_context()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.height_sizing.start(0)

    def update_minimum_height(self):
        # QTabWidget does not propagate each page's wrapped-text height to the
        # outer scroll area. Reserve it explicitly to prevent overlapping rows.
        width = max(100, self.width() - 4)
        height = max(self.widget(i).layout().totalHeightForWidth(width)
                     for i in range(self.count()))
        self.setMinimumHeight(max(430, height + self.tabBar().height() + 6))

    def settings(self):
        return {key: widget.value() for key, widget in self.params.items()}

    def build_helper(self):
        page = W.QWidget()
        layout = W.QVBoxLayout(page)
        layout.addWidget(text_label('What needs improvement? / どの点を改善したいですか？'))
        self.issue = W.QComboBox()
        self.fill_issues([issue.key for issue in ISSUES])
        self.issue.currentIndexChanged.connect(self.preview)
        layout.addWidget(self.issue)
        search = W.QHBoxLayout()
        self.description = W.QLineEdit()
        self.description.setMaxLength(400)
        self.description.setPlaceholderText('Describe the issue (English / 日本語): too many events, 隣接信号が一つ…')
        self.description.returnPressed.connect(self.search_issues)
        search.addWidget(self.description, 1)
        find = W.QPushButton('Find issue / 問題を探す')
        find.clicked.connect(self.search_issues)
        search.addWidget(find)
        layout.addLayout(search)
        self.match_note = text_label('Choose a problem or search locally by keywords. / 問題を選ぶか、キーワードで検索します。')
        self.match_note.setObjectName('muted')
        layout.addWidget(self.match_note)
        self.advice = text_label('Preview a small adjustment, apply it, then rerun and compare the same signals. / 小さな変更を確認して適用し、再検出して同じ信号を比較してください。')
        layout.addWidget(self.advice)
        self.preview_table = W.QTableWidget(0, 3)
        self.preview_table.setHorizontalHeaderLabels(['Parameter / 項目', 'Current / 現在', 'Suggested / 推奨'])
        self.preview_table.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.verticalHeader().hide()
        self.preview_table.horizontalHeader().setSectionResizeMode(W.QHeaderView.ResizeMode.Stretch)
        self.preview_table.setFixedHeight(100)
        layout.addWidget(self.preview_table)
        self.effect = text_label()
        layout.addWidget(self.effect)
        self.limitation = text_label('Suggestions are starting points, not validated ATP settings. Final event counts can change through both detection and splitting. / 提案は開始点であり、検証済みのATP設定ではありません。最終イベント数は検出と分割の両方で変わります。')
        self.limitation.setObjectName('muted')
        layout.addWidget(self.limitation)
        row = W.QHBoxLayout()
        refresh = W.QPushButton('Preview / 変更を確認')
        refresh.clicked.connect(self.preview)
        row.addWidget(refresh)
        self.apply_btn = W.QPushButton('Apply suggestion / 提案を適用')
        self.apply_btn.setObjectName('primary')
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.apply_proposal)
        row.addWidget(self.apply_btn)
        self.undo_btn = W.QPushButton('Undo adjustment / 調整を戻す')
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.undo)
        row.addWidget(self.undo_btn)
        row.addStretch()
        layout.addLayout(row)
        layout.addStretch()
        self.addTab(page, 'Adjustment helper / 調整ガイド')

    def build_parameters(self):
        page = W.QWidget()
        layout = W.QVBoxLayout(page)
        layout.addWidget(text_label('Allowed ranges are application limits, not recommended biological ranges. Select a row for details. / 許容範囲はアプリの制限です。生物学的な推奨範囲ではありません。行を選ぶと詳細を表示します。'))
        self.parameter_table = ParameterTable(len(PARAMETERS), 4)
        table = self.parameter_table
        table.setHorizontalHeaderLabels(['Parameter / 項目', 'Value / 値', 'Allowed / 許容範囲', 'Effect of changes / 変更の影響'])
        table.verticalHeader().hide()
        table.verticalHeader().setMinimumSectionSize(64)
        table.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(W.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(W.QAbstractItemView.SelectionMode.SingleSelection)
        table.setWordWrap(True)
        table.setColumnWidth(0, 210)
        table.setColumnWidth(1, 95)
        table.setColumnWidth(2, 160)
        for col in range(3):
            table.horizontalHeader().setSectionResizeMode(col, W.QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(3, W.QHeaderView.ResizeMode.Stretch)
        for row, spec in enumerate(PARAMETERS):
            if spec.decimals:
                widget = W.QDoubleSpinBox()
                widget.setDecimals(spec.decimals)
            else:
                widget = W.QSpinBox()
            widget.setRange(spec.low, spec.high)
            widget.setSingleStep(spec.step)
            widget.setValue(DEFAULT_DETECTION[spec.key])
            widget.setKeyboardTracking(False)
            widget.setFixedHeight(36)
            widget.setAccessibleName(spec.title)
            widget.setToolTip(spec.caution)
            self.params[spec.key] = widget
            table.setItem(row, 0, W.QTableWidgetItem(spec.title))
            holder = W.QWidget()
            cell = W.QVBoxLayout(holder)
            cell.setContentsMargins(3, 3, 3, 3)
            cell.addWidget(widget, 0, C.Qt.AlignmentFlag.AlignVCenter)
            table.setCellWidget(row, 1, holder)
            table.setItem(row, 2, W.QTableWidgetItem())
            table.setItem(row, 3, W.QTableWidgetItem('↑ ' + spec.higher + '\n↓ ' + spec.lower))
            for col in (0, 2, 3):
                table.item(row, col).setToolTip(spec.caution)
            table.setRowHeight(row, 80)
        table.itemSelectionChanged.connect(self.show_parameter_detail)
        layout.addWidget(table, 1)
        self.parameter_detail = text_label('Select a parameter to see its units and cautions. / パラメーターを選ぶと単位と注意点を表示します。')
        self.parameter_detail.setObjectName('muted')
        layout.addWidget(self.parameter_detail)
        self.validation_message = text_label()
        layout.addWidget(self.validation_message)
        row = W.QHBoxLayout()
        strict = W.QPushButton('Strict defaults / 厳しめの初期値')
        strict.clicked.connect(lambda: self.apply_preset(DEFAULT_DETECTION, 'strict_defaults'))
        earlier = W.QPushButton('Earlier defaults / 以前の初期値')
        earlier.clicked.connect(lambda: self.apply_preset(LEGACY_DETECTION, 'earlier_defaults'))
        self.previous_btn = W.QPushButton('Use last run / 前回の設定')
        self.previous_btn.clicked.connect(self.load_previous)
        for widget in (strict, earlier, self.previous_btn):
            row.addWidget(widget)
        row.addStretch()
        layout.addLayout(row)
        self.addTab(page, 'Parameters & ranges / 値と範囲')

    def fill_issues(self, keys):
        self.issue.blockSignals(True)
        self.issue.clear()
        self.issue.addItem('Choose an issue / 問題を選択', None)
        for key in keys:
            self.issue.addItem(ISSUE_BY_KEY[key].title, key)
        self.issue.blockSignals(False)

    def search_issues(self):
        value = self.description.text().strip()
        matches = match_issues(value)
        self.fill_issues(matches or [issue.key for issue in ISSUES])
        self.clear_proposal()
        self.advice.setText('Choose an issue to preview a recommendation. / 問題を選ぶと提案を表示します。')
        if len(matches) == 1:
            self.match_note.setText('Matched issue shown below. Confirm it before applying. / 対応候補を表示しました。内容を確認してから適用してください。')
            self.issue.setCurrentIndex(1)
        elif matches:
            self.match_note.setText('Several issues match. Choose the intended one above. / 複数の候補があります。上の一覧から選択してください。')
        else:
            self.match_note.setText('No unique match. Choose an issue from the full list above. / 対応が不明です。上の全一覧から問題を選んでください。')

    def clear_proposal(self):
        self.proposal = None
        self.apply_btn.setEnabled(False)
        self.preview_table.setRowCount(0)
        self.effect.clear()
        self.height_sizing.start(0)

    def preview(self, *args):
        self.clear_proposal()
        key = self.issue.currentData()
        if not key:
            self.advice.setText('Choose an issue to preview a recommendation. / 問題を選ぶと提案を表示します。')
            return
        try:
            proposal = recommend(key, self.settings(), self.context_provider())
        except ValueError as error:
            self.advice.setText(str(error))
            return
        self.proposal = proposal
        self.advice.setText(proposal['advice'])
        for row, change in enumerate(proposal['changes']):
            self.preview_table.insertRow(row)
            for col, value in enumerate((PARAMETER_BY_KEY[change['key']].title,
                                         format_value(change['before']), format_value(change['after']))):
                self.preview_table.setItem(row, col, W.QTableWidgetItem(value))
            self.preview_table.setRowHeight(row, 44)
            self.effect.setText(change['effect'] + '\n' + change['caution'])
        self.apply_btn.setEnabled(bool(proposal['changes']))

    def set_values(self, values):
        self._changing = True
        try:
            for key, value in values.items():
                if key in self.params:
                    self.params[key].setValue(value)
        finally:
            self._changing = False

    def apply_proposal(self):
        proposal = self.proposal
        if not proposal or self.settings() != proposal['before']:
            self.clear_proposal()
            return
        # Recheck recording-dependent bounds immediately before changing values.
        try:
            validate_settings(proposal['after'], self.context_provider())
        except ValueError as error:
            self.advice.setText(str(error))
            self.clear_proposal()
            return
        self.set_values(proposal['after'])
        self.last_applied = deepcopy(proposal)
        self.proposal = None
        self.apply_btn.setEnabled(False)
        self.advice.setText('Applied to the next run. Select Run AQuA2 and compare the result. / 次の検出に適用しました。Run AQuA2で再検出して比較してください。')
        self.refresh_context()

    def apply_preset(self, values, name):
        try:
            values = validate_settings(values, self.context_provider())
        except ValueError as error:
            self.validation_message.setText(str(error))
            return
        before = self.settings()
        self.set_values(values)
        self.last_applied = {'rule_version': RULE_VERSION, 'issue': name,
                             'before': before, 'after': self.settings(), 'changes': []}
        self.clear_proposal()
        self.advice.setText('Preset loaded. Check the ranges before the next run. / 設定を読み込みました。次の検出前に範囲を確認してください。')
        self.refresh_context()

    def load_previous(self):
        if self.previous_settings:
            self.apply_preset({**DEFAULT_DETECTION, **self.previous_settings}, 'previous_run')

    def undo(self):
        if not self.last_applied or self.settings() != self.last_applied['after']:
            return
        self.set_values(self.last_applied['before'])
        self.last_applied = None
        self.clear_proposal()
        self.advice.setText('Restored the values before the adjustment. / 調整前の値に戻しました。')
        self.refresh_context()

    def settings_changed(self):
        if self._changing:
            return
        if self.proposal:
            self.clear_proposal()
            self.advice.setText('Values changed. Preview again before applying. / 値が変更されました。提案を再表示してください。')
        self.refresh_context()

    def refresh_context(self, previous=None, reset=False):
        if reset:
            self.clear_proposal()
            self.last_applied = None
            self.previous_settings = previous
            self.advice.setText('Choose an issue to preview a recommendation. / 問題を選ぶと提案を表示します。')
        self.previous_btn.setEnabled(bool(self.previous_settings))
        values, context = self.settings(), self.context_provider()
        for row, spec in enumerate(PARAMETERS):
            text = range_text(spec.key, context, values)
            converted = calibrated_value(spec.key, values[spec.key], context)
            self.parameter_table.item(row, 2).setText(text + ('\n' + converted if converted else ''))
        try:
            validate_settings(values, context)
            self.validation_message.setText('Values are within the allowed ranges. / 値は許容範囲内です。')
        except ValueError as error:
            self.validation_message.setText(str(error))
        self.undo_btn.setEnabled(bool(self.last_applied and values == self.last_applied['after']))
        self.show_parameter_detail()
        self.parameter_table.resizeRowsToContents()
        self.height_sizing.start(0)

    def show_parameter_detail(self):
        row = self.parameter_table.currentRow()
        if row >= 0:
            spec = PARAMETERS[row]
            self.parameter_detail.setText(spec.caution)

    def guidance_for_run(self):
        if self.last_applied and self.settings() == self.last_applied['after']:
            return deepcopy(self.last_applied)
        return None
