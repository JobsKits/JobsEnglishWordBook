"""Jobs EnglishWordBook 原生桌面界面。"""
import html
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QSettings, QStandardPaths, QTimer
from PySide6.QtGui import QColor, QFont, QKeySequence, QPalette, QShortcut, QAction, QActionGroup
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QLineEdit, QScrollArea, QFrame, QStackedWidget,
    QComboBox, QSlider, QMessageBox, QMenu, QSizePolicy, QDialog, QTextBrowser, QLayout,
)
from .catalog import Catalog
from .speech import Speech

STYLE = """
QWidget { color: #283b36; font-size: 14px; }
QMainWindow, QDialog, QWidget#content { background: #f6f7f3; }
QWidget#sidebar { background: #e8eee6; border-right: 1px solid #d6dfd4; }
QLabel#brand { font-size: 24px; font-weight: 700; }
QLabel#eyebrow { color: #718177; font-size: 11px; letter-spacing: 2px; }
QLabel#heading { font-size: 29px; font-weight: 700; }
QLabel#muted { color: #6c7a73; }
QLabel#notice { color: #64734d; background: #edf1df; padding: 12px; border-radius: 8px; }
QPushButton { background: #ffffff; border: 1px solid #dbe2d8; border-radius: 7px; padding: 8px 12px; }
QPushButton:hover { background: #edf2e8; border-color: #8caa8a; }
QPushButton:focus { border: 2px solid #698263; }
QPushButton:checked { background: #355744; color: white; border-color: #355744; }
QPushButton:disabled { color: #abb4a7; background: #f1f3ed; }
QPushButton#level { text-align: left; padding: 10px 14px; background: transparent; border: none; }
QPushButton#level:checked { background: #355744; color: white; }
QPushButton#word { text-align: left; border: none; background: transparent; padding: 0; font-size: 23px; font-weight: 650; color: #305d44; }
QPushButton#titleWord { text-align: left; border: none; background: transparent; padding: 0; font-size: 38px; font-weight: 700; color: #305d44; }
QPushButton#word:hover, QPushButton#titleWord:hover { color: #639144; }
QLineEdit, QComboBox { background: white; border: 1px solid #d5ded3; border-radius: 7px; padding: 9px; }
QFrame#card { background: white; border: 1px solid #dde4da; border-radius: 10px; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QStatusBar { background: #e8eee6; color: #586c5e; }
QTextBrowser, QComboBox QAbstractItemView, QMenu { background: white; color: #283b36; }
QMenu::item:selected { background: #355744; color: white; }
QToolTip { background: #fff; color: #283b36; border: 1px solid #d5ded3; }
"""


DARK_COLORS = {
    "#283b36": "#e1ebe5", "#f6f7f3": "#1c2521", "#e8eee6": "#25332b",
    "#d6dfd4": "#46574a", "#718177": "#a8baac", "#6c7a73": "#afc0b5",
    "#64734d": "#d0dbaa", "#edf1df": "#35412b", "#ffffff": "#29372f",
    "#dbe2d8": "#4a5d4f", "#edf2e8": "#374b3d", "#8caa8a": "#a0bf99",
    "#698263": "#9fbc94", "#355744": "#3b674e", "#abb4a7": "#809285",
    "#f1f3ed": "#263129", "#305d44": "#9bd5ac", "#639144": "#c2e9a2",
    "#d5ded3": "#4a5d4f", "#dde4da": "#46574a", "#586c5e": "#b0c5b5",
    "#fff": "#29372f", "#344a3b": "#d2e4d6", "#88977c": "#a9bd98",
}


def themed_text(text, dark):
    return re.sub(r"#[0-9a-fA-F]{6}|#fff\b",
                  lambda match: DARK_COLORS.get(match.group(), match.group()) if dark else match.group(), text)


def label(text, name=None, wrap=False):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, name=None):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if name:
        widget.setObjectName(name)
    widget.clicked.connect(callback)
    return widget


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


def scroll_container():
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(0, 0, 12, 0)
    layout.setSpacing(12)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
    scroll.setWidget(body)
    return scroll, layout


class Window(QMainWindow):
    PAGE_SIZE = 35

    def __init__(self, catalog=None, speech=None):
        super().__init__()
        self.catalog = catalog or Catalog()
        self.settings = QSettings("Jobs", "JobsEnglishWordBook")
        self.speech = speech or Speech(self)
        self.speech.message.connect(self.statusBar().showMessage)
        self.levels = self.catalog.levels()
        self.level_id = self.levels[0]["id"]
        self.letter = ""
        self.page = 0
        self.detail_word = None
        self.setWindowTitle("Jobs EnglishWordBook · 分级英语词典")
        self.resize(1220, 850)
        self.setMinimumSize(920, 640)
        self.theme_mode = self.settings.value("appearance/theme", "system")
        self.theme_dark = False
        self._changing_theme = False
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self.make_sidebar())
        self.stack = QStackedWidget()
        self.stack.setObjectName("content")
        root_layout.addWidget(self.stack, 1)
        self.stack.addWidget(self.make_list())
        self.stack.addWidget(self.make_detail())
        self.setCentralWidget(root)
        QApplication.instance().styleHints().colorSchemeChanged.connect(self.system_theme_changed)
        self.set_theme(self.theme_mode)
        QShortcut(QKeySequence("Escape"), self, activated=self.go_back)
        QShortcut(QKeySequence.StandardKey.Find, self, activated=self.focus_search)
        chosen = self.settings.value("level", self.level_id)
        self.choose_level(chosen if chosen in self.level_buttons else self.level_id)
        self.statusBar().showMessage("点击单词朗读 · 点击释义查看例句 · 词库可离线使用")

    def make_sidebar(self):
        side = QWidget()
        side.setObjectName("sidebar")
        layout = QVBoxLayout(side)
        layout.setContentsMargins(18, 28, 18, 18)
        layout.setSpacing(7)
        layout.addWidget(label("JOBS / LANGUAGE", "eyebrow"))
        self.brand = label("EnglishWordBook", "brand")
        layout.addWidget(self.brand)
        # 根据实际字体度量预留标题空间，避免系统缩放后裁切。
        self.brand.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.brand.ensurePolished()
        side.setFixedWidth(max(232, self.brand.sizeHint().width() + 36))
        layout.addWidget(label("把单词放回句子里。", "muted"))
        self.theme_button = button("主题", self.show_theme_menu)
        self.theme_button.setAccessibleName("切换主题：白天、黑夜、跟随系统")
        self.theme_menu = QMenu(self.theme_button)
        self.theme_group = QActionGroup(self)
        self.theme_actions = {}
        for title, mode in [("白天", "light"), ("黑夜", "dark"), ("跟随系统", "system")]:
            action = QAction(title, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, value=mode: self.set_theme(value))
            self.theme_group.addAction(action)
            self.theme_menu.addAction(action)
            self.theme_actions[mode] = action
        layout.addWidget(self.theme_button)
        layout.addSpacing(7)
        layout.addWidget(label("选择学习难度", "eyebrow"))
        level_scroll, level_layout = scroll_container()
        level_layout.setContentsMargins(0, 0, 0, 0)
        level_layout.setSpacing(3)
        self.level_buttons = {}
        for level in self.levels:
            b = button(level["name"], lambda: None, "level")
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.toggled.connect(lambda checked, key=level["id"]: self.choose_level(key) if checked else None)
            level_layout.addWidget(b)
            self.level_buttons[level["id"]] = b
        level_layout.addStretch()
        layout.addWidget(level_scroll, 1)
        layout.addWidget(label("英语发音", "eyebrow"))
        self.voice_combo = QComboBox()
        for voice in self.speech.voices:
            self.voice_combo.addItem(f"{voice.name()} · {voice.locale().name()}")
        if self.speech.voices:
            current = self.speech.engine.voice()
            self.voice_combo.setCurrentIndex(next((i for i, v in enumerate(self.speech.voices) if v == current), 0))
        else:
            self.voice_combo.addItem("系统未安装英语语音")
            self.voice_combo.setEnabled(False)
        self.voice_combo.currentIndexChanged.connect(self.speech.set_voice)
        layout.addWidget(self.voice_combo)
        layout.addWidget(label("语速  慢 ← → 快", "muted"))
        rate = QSlider(Qt.Orientation.Horizontal)
        rate.setRange(-70, 50)
        rate.setValue(-15)
        rate.valueChanged.connect(self.speech.set_rate)
        layout.addWidget(rate)
        layout.addWidget(button("停止朗读", self.speech.stop))
        layout.addWidget(button("词库与分级说明", self.show_sources))
        return side

    def show_theme_menu(self):
        self.theme_menu.popup(self.theme_button.mapToGlobal(self.theme_button.rect().bottomLeft()))

    def set_theme(self, mode):
        self.theme_mode = mode if mode in self.theme_actions else "system"
        self.settings.setValue("appearance/theme", self.theme_mode)
        hints = QApplication.instance().styleHints()
        self._changing_theme = True
        try:
            if self.theme_mode == "system":
                hints.unsetColorScheme()
            else:
                hints.setColorScheme(Qt.ColorScheme.Dark if self.theme_mode == "dark" else Qt.ColorScheme.Light)
        finally:
            self._changing_theme = False
        self.theme_actions[self.theme_mode].setChecked(True)
        self.theme_button.setText("主题 · " + self.theme_actions[self.theme_mode].text())
        self.system_theme_changed(hints.colorScheme())

    def system_theme_changed(self, scheme):
        if self._changing_theme:
            return
        self.theme_dark = self.theme_mode == "dark" or (self.theme_mode == "system" and scheme == Qt.ColorScheme.Dark)
        palette = QPalette()
        for role, color in {
            QPalette.ColorRole.Window: "#f6f7f3", QPalette.ColorRole.WindowText: "#283b36",
            QPalette.ColorRole.Base: "#ffffff", QPalette.ColorRole.Text: "#283b36",
            QPalette.ColorRole.Button: "#ffffff", QPalette.ColorRole.ButtonText: "#283b36",
            QPalette.ColorRole.Highlight: "#355744", QPalette.ColorRole.HighlightedText: "#ffffff",
            QPalette.ColorRole.PlaceholderText: "#6c7a73", QPalette.ColorRole.Link: "#305d44",
            QPalette.ColorRole.ToolTipBase: "#ffffff", QPalette.ColorRole.ToolTipText: "#283b36",
        }.items():
            palette.setColor(role, QColor(themed_text(color, self.theme_dark) if role != QPalette.ColorRole.HighlightedText else color))
        self.setPalette(palette)
        self.setStyleSheet(themed_text(STYLE.replace("background: white", "background: #ffffff"), self.theme_dark))
        for widget in self.findChildren(QLabel):
            source = widget.property("themeHtml")
            if source:
                widget.setText(themed_text(source, self.theme_dark))

    def set_link_text(self, widget, text):
        widget.setProperty("themeHtml", text)
        widget.setText(themed_text(text, self.theme_dark))

    def make_list(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 26, 18)
        layout.setSpacing(14)
        layout.addWidget(label("YOUR WORDS, IN CONTEXT", "eyebrow"))
        self.heading = label("", "heading")
        layout.addWidget(self.heading)
        self.summary = label("", "muted")
        layout.addWidget(self.summary)
        self.notice = label("", "notice", True)
        layout.addWidget(self.notice)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索当前难度中的单词或中文释义…")
        self.search.setClearButtonEnabled(True)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(180)
        self.search_timer.timeout.connect(self.search_changed)
        self.search.textChanged.connect(lambda: self.search_timer.start())
        layout.addWidget(self.search)
        letters = QHBoxLayout()
        letters.setSpacing(3)
        self.letter_buttons = {}
        for letter in ["", *"ABCDEFGHIJKLMNOPQRSTUVWXYZ", "#"]:
            b = button(letter or "全部", lambda: None)
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.toggled.connect(lambda checked, value=letter: self.choose_letter(value) if checked else None)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.setMinimumWidth(0)
            b.setStyleSheet("padding: 7px 0; font-size: 12px;")
            self.letter_buttons[letter] = b
            letters.addWidget(b)
        layout.addLayout(letters)
        layout.addWidget(label("单词 / 点击发音                         全部已收录释义 / 点击查看用法", "muted"))
        self.list_scroll, self.cards = scroll_container()
        layout.addWidget(self.list_scroll, 1)
        footer = QHBoxLayout()
        self.page_label = label("", "muted")
        footer.addWidget(self.page_label, 1)
        self.previous = button("上一页", lambda: self.change_page(-1))
        self.next = button("下一页", lambda: self.change_page(1))
        footer.addWidget(self.previous)
        footer.addWidget(self.next)
        layout.addLayout(footer)
        return page

    def make_detail(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 26, 18)
        back = button("← 返回单词列表  /  Esc", self.go_back)
        layout.addWidget(back, alignment=Qt.AlignmentFlag.AlignLeft)
        self.detail_scroll, self.detail_layout = scroll_container()
        layout.addWidget(self.detail_scroll, 1)
        return page

    def choose_level(self, key):
        self.speech.stop()
        self.level_id, self.letter, self.page = key, "", 0
        self.settings.setValue("level", key)
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.search_timer.stop()
        self.stack.setCurrentIndex(0)
        for k, b in self.level_buttons.items():
            b.blockSignals(True)
            b.setChecked(k == key)
            b.blockSignals(False)
        level = next(l for l in self.levels if l["id"] == key)
        self.heading.setText(level["name"])
        self.notice.setText(level["description"])
        self.refresh()

    def choose_letter(self, value):
        self.letter, self.page = value, 0
        self.refresh()

    def search_changed(self):
        self.letter, self.page = "", 0
        self.refresh()

    def change_page(self, delta):
        self.page += delta
        self.refresh()

    def refresh(self):
        counts = self.catalog.initials(self.level_id, self.search.text())
        for key, b in self.letter_buttons.items():
            b.blockSignals(True)
            b.setChecked(key == self.letter)
            b.blockSignals(False)
            b.setEnabled(not key or counts.get(key, 0) > 0 or key == self.letter)
            b.setToolTip(f"{key or '全部'}：{counts.get(key, 0) if key else sum(counts.values()):,} 个词条")
        total = self.catalog.count(self.level_id, self.letter, self.search.text())
        all_count = self.catalog.count(self.level_id)
        self.page = min(max(0, self.page), max(0, (total - 1) // self.PAGE_SIZE))
        self.summary.setText(f"{all_count:,} 个收录词条  ·  A–Z 字母分区  ·  本地词库")
        clear_layout(self.cards)
        self.visible_words = self.catalog.words(self.level_id, self.letter, self.search.text(), self.page * self.PAGE_SIZE, self.PAGE_SIZE)
        for word in self.visible_words:
            self.cards.addWidget(self.word_card(word))
        if not total:
            self.cards.addWidget(label("没有匹配的词条。请尝试其他拼写或清空搜索。", "muted", True))
        self.cards.addStretch()
        pages = max(1, (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page_label.setText(f"{self.letter or '全部字母'}  ·  {total:,} 个结果  ·  第 {self.page + 1} / {pages} 页")
        self.previous.setEnabled(self.page > 0)
        self.next.setEnabled((self.page + 1) * self.PAGE_SIZE < total)
        self.list_scroll.verticalScrollBar().setValue(0)

    def word_card(self, word):
        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        row = QHBoxLayout(card)
        row.setContentsMargins(20, 18, 20, 18)
        row.setSpacing(25)
        left = QVBoxLayout()
        left.setSpacing(6)
        speak = button(word["word"], lambda: self.speech.say(word["word"]), "word")
        speak.setToolTip("点击朗读 " + word["word"])
        left.addWidget(speak, alignment=Qt.AlignmentFlag.AlignLeft)
        left.addWidget(label(word["phonetic"] or "英语点读", "muted", True))
        left.addStretch()
        left_widget = QWidget()
        left_widget.setFixedWidth(210)
        left_widget.setLayout(left)
        row.addWidget(left_widget, 0, Qt.AlignmentFlag.AlignTop)
        right = QVBoxLayout()
        right.setSpacing(8)
        for i, sense in enumerate(word["senses"]):
            entry = QLabel()
            entry.setWordWrap(True)
            entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            entry.setTextFormat(Qt.TextFormat.RichText)
            entry.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.LinksAccessibleByKeyboard)
            self.set_link_text(entry, f'<a style="color:#344a3b;text-decoration:none" href="{i}"><span style="color:#88977c">{i+1:02d} · {html.escape(sense["pos"])}</span>  {html.escape(sense["meaning"])}  →</a>')
            entry.linkActivated.connect(lambda target, wid=word["id"]: self.open_detail(wid, int(target)))
            entry.setAccessibleName(f'{sense["pos"]} {sense["meaning"]}，查看例句')
            right.addWidget(entry)
        right.addStretch()
        row.addLayout(right, 1)
        return card

    def open_detail(self, word_id, sense_index):
        word = self.catalog.word(word_id)
        self.detail_word = word
        sense = word["senses"][sense_index]
        clear_layout(self.detail_layout)
        self.detail_layout.addWidget(label("WORD / MEANING / CONTEXT", "eyebrow"))
        self.detail_layout.addWidget(button(word["word"], lambda: self.speech.say(word["word"]), "titleWord"))
        self.detail_layout.addWidget(label((word["phonetic"] or "") + "  ·  点击标题发音", "muted"))
        self.detail_layout.addWidget(label(f'{sense["pos"]}  {sense["meaning"]}', "heading", True))
        if sense.get("english"):
            self.detail_layout.addWidget(label(sense["english"], "muted", True))
        self.detail_layout.addWidget(label("例句与短语 · 点击英文朗读", "brand"))
        self.detail_layout.addWidget(label("以下为该词的参考用法。原始词库未提供逐义对应关系，例句不一定对应当前所选释义。", "notice", True))
        self.example_buttons = []
        for index, example in enumerate(word["examples"]):
            self.detail_layout.addWidget(self.example_card(example, index + 1))
        if not word["examples"]:
            self.detail_layout.addWidget(label("当前词库尚未收录该词例句。可先学习下方短语；缺失内容不以自动拼接句子代替。", "muted", True))
        if word["phrases"]:
            self.detail_layout.addWidget(label("常用短语", "brand"))
            for index, phrase in enumerate(word["phrases"]):
                self.detail_layout.addWidget(self.example_card(phrase, index + 1))
        self.detail_layout.addWidget(label("词条来源：" + "、".join(word["sources"]), "muted", True))
        self.detail_layout.addStretch()
        self.detail_scroll.verticalScrollBar().setValue(0)
        self.stack.setCurrentIndex(1)

    def example_card(self, example, number):
        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        sentence = QLabel()
        sentence.setWordWrap(True)
        sentence.setTextFormat(Qt.TextFormat.RichText)
        self.set_link_text(sentence, f'<a href="speak" style="color:#305d44;text-decoration:none;font-size:18px">{number:02d} &nbsp; {html.escape(example["en"])}</a>')
        sentence.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.LinksAccessibleByKeyboard)
        sentence.linkActivated.connect(lambda _: self.speech.say(example["en"]))
        sentence.setAccessibleName(example["en"] + "，点击朗读")
        self.example_buttons.append(sentence)
        layout.addWidget(sentence)
        if example.get("zh"):
            layout.addWidget(label(example["zh"], "muted", True))
        return card

    def go_back(self):
        self.stack.setCurrentIndex(0)

    def focus_search(self):
        self.go_back()
        self.search.setFocus()
        self.search.selectAll()

    def show_sources(self):
        report = self.catalog.report()
        dialog = QDialog(self)
        dialog.setWindowTitle("词库来源与覆盖范围")
        dialog.resize(720, 580)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        rows = "".join(f'<tr><td>{html.escape(x["name"])}</td><td>{x["count"]:,}</td></tr>' for x in report["levels"])
        browser.setHtml(f'''<h2>真实收录，透明分级</h2><p>全库 {report["words"]:,} 个词条，{report["examples"]:,} 条去重例句。缺例句词条 {report["words_without_examples"]:,} 个。</p>
        <p>初中、高中、CET4、CET6、专八采用公开备考词书合集，较高学段包含较低学段基础词。完整覆盖本软件所列来源，不代表官方最新大纲的全部词汇或词典的所有义项。</p>
        <p>雅思 1～7 分为本软件学习目标档位：基础词与雅思词合并后按词频排序，累计收录。它不是官方分数词表，也不代表掌握这些词即可取得对应分数。</p>
        <table cellpadding="7"><tr><th>级别</th><th>词条数</th></tr>{rows}</table>
        <p>所有原始中文释义保留并按词性、分号分义；例句与短语保留原文，不伪造逐义映射。</p>
        <p><a href="https://github.com/kajweb/dict">备考词书来源：kajweb/dict</a> · <a href="https://github.com/rspeer/wordfreq">词频排序：wordfreq 3.1.1</a> · <a href="https://ielts.org/take-a-test/your-results/ielts-scoring-in-detail">IELTS 官方评分说明</a></p>
        <p>备考词书来源未提供清晰的再分发许可；当前作为个人学习资料。公开发行前应替换为已授权数据。系统语音由本机提供。</p>''')
        layout.addWidget(browser)
        layout.addWidget(button("关闭", dialog.accept))
        dialog.exec()

    def closeEvent(self, event):
        self.speech.stop()
        self.catalog.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JobsEnglishWordBook")
    app.setOrganizationName("Jobs")
    app.setStyle("Fusion")
    font = QFont("PingFang SC" if sys.platform == "darwin" else "Microsoft YaHei", 11)
    app.setFont(font)
    log_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(log_dir / "app.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")])
    def handle_error(kind, value, tb):
        logging.error("未处理异常", exc_info=(kind, value, tb))
        QMessageBox.critical(None, "运行异常", f"{value}\n日志：{log_dir}")
    sys.excepthook = handle_error
    try:
        window = Window()
    except Exception as exc:
        logging.exception("启动失败")
        QMessageBox.critical(None, "启动失败", str(exc))
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
