"""使用系统离线英语语音；新点读立即中断旧点读。"""
import sys
from PySide6.QtCore import QObject, Signal, QLocale
from PySide6.QtTextToSpeech import QTextToSpeech


class Speech(QObject):
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        engines = [e for e in QTextToSpeech.availableEngines() if e != "mock"]
        preferred_engine = "darwin" if sys.platform == "darwin" else "sapi"
        backend = preferred_engine if preferred_engine in engines else (engines[0] if engines else "")
        self.engine = QTextToSpeech(backend, self) if backend else QTextToSpeech(self)
        # availableVoices 仅返回当前 locale，先切英语区域再枚举。
        self.voices = []
        for locale in (self.engine.availableLocales() if engines else []):
            if locale.language() == QLocale.Language.English:
                self.engine.setLocale(locale)
                self.voices.extend(v for v in self.engine.availableVoices() if v not in self.voices)
        self.engine.errorOccurred.connect(lambda *_: self.message.emit("发音失败：" + self.engine.errorString()))
        self.engine.setRate(-0.15)
        if self.voices:
            preferred = next((v for v in self.voices if v.name() == "Samantha"), next((v for v in self.voices if v.locale().name() == "en_US"), self.voices[0]))
            self.engine.setVoice(preferred)

    def say(self, text):
        if not self.voices:
            self.message.emit("未找到英语语音。请在系统语音设置中安装英语语音后重新打开程序。")
            return False
        self.engine.stop()
        self.engine.say(text)
        self.message.emit("正在朗读：" + text)
        return True

    def stop(self):
        self.engine.stop()
        self.message.emit("已停止朗读")

    def set_voice(self, index):
        if 0 <= index < len(self.voices):
            self.engine.stop()
            self.engine.setVoice(self.voices[index])

    def set_rate(self, value):
        self.engine.setRate(value / 100)
