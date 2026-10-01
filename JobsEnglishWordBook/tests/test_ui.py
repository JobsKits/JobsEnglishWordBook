"""离屏验证真实界面导航和点击发音的文本，避免测试时播放声音。"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtTest import QTest
from jobs_english_wordbook.app import Window


class FakeSpeech(QObject):
    message = Signal(str)
    voices = []

    def __init__(self):
        super().__init__()
        self.spoken = []

    def say(self, text):
        self.spoken.append(text)

    def stop(self):
        pass

    def set_voice(self, index):
        pass

    def set_rate(self, rate):
        pass


def test_navigation_search_and_click_to_speak():
    app = QApplication.instance() or QApplication([])
    speech = FakeSpeech()
    window = Window(speech=speech)
    window.show()
    window.choose_level("cet4")
    QTest.mouseClick(window.level_buttons["junior"], Qt.MouseButton.LeftButton)
    assert window.level_id == "junior"
    assert window.heading.text() == "初中"
    QTest.mouseClick(window.level_buttons["junior"], Qt.MouseButton.LeftButton)
    assert window.level_buttons["junior"].isChecked()
    window.search.setText("book")
    QTest.qWait(500)
    app.processEvents()
    book = next(w for w in window.visible_words if w["word"].lower() == "book")
    word_button = next(b for b in window.findChildren(QPushButton, "word") if b.text().lower() == "book" and b.isVisible())
    QTest.mouseClick(word_button, Qt.MouseButton.LeftButton)
    assert speech.spoken[-1].lower() == "book"
    window.open_detail(book["id"], 0)
    assert window.stack.currentIndex() == 1
    title = window.findChild(QPushButton, "titleWord")
    title.click()
    assert speech.spoken[-1].lower() == "book"
    assert window.example_buttons
    window.example_buttons[0].linkActivated.emit("speak")
    assert speech.spoken[-1] == book["examples"][0]["en"]
    window.go_back()
    assert window.search.text() == "book"
    assert window.stack.currentIndex() == 0
    window.choose_level("ielts7")
    assert not window.search.text()
    window.choose_letter("Z")
    assert all(w["initial"] == "Z" for w in window.visible_words)
    window.search.setText("no-such-word-972314")
    QTest.qWait(500)
    app.processEvents()
    assert not window.visible_words
    assert not window.next.isEnabled()
    assert not window.previous.isEnabled()
    window.close()
    app.processEvents()


def test_title_and_theme_switching(tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QLabel
    import jobs_english_wordbook.app as ui

    app = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "theme.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr(ui, "QSettings", lambda *args: settings)
    window = Window(speech=FakeSpeech())
    window.show()
    app.processEvents()
    for width, height in [(920, 640), (1220, 850), (1600, 1000)]:
        window.resize(width, height)
        app.processEvents()
        assert window.brand.width() >= window.brand.sizeHint().width()
        assert window.theme_button.isVisible()
    window.open_detail(window.visible_words[0]["id"], 0)
    window.theme_actions["dark"].trigger()
    app.processEvents()
    assert window.theme_dark
    assert window.stack.currentIndex() == 1
    assert window.palette().color(QPalette.ColorRole.Text).lightness() > 150
    assert settings.value("appearance/theme") == "dark"
    links = [item for item in window.findChildren(QLabel) if item.property("themeHtml")]
    assert links
    assert all("#305d44" not in item.text() and "#344a3b" not in item.text() for item in links)
    window.theme_actions["light"].trigger()
    assert not window.theme_dark
    assert window.palette().color(QPalette.ColorRole.Text).lightness() < 100
    window.theme_actions["system"].trigger()
    window.system_theme_changed(Qt.ColorScheme.Dark)
    assert window.theme_dark
    window.system_theme_changed(Qt.ColorScheme.Light)
    assert not window.theme_dark
    assert settings.value("appearance/theme") == "system"
    window.close()
    restored = Window(speech=FakeSpeech())
    assert restored.theme_mode == "system"
    restored.close()
    app.processEvents()
