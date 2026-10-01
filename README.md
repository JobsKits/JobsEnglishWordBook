# Jobs EnglishWordBook · 分级英语词典

![Jobs出品，必属精品](https://picsum.photos/1500/400)

[toc]

---

[▶ 观看分级英语词典演示视频](./showMeNow.mp4)

https://github.com/user-attachments/assets/59530bf2-a724-4f96-ac1c-8d65800b6fb3

## 🔥 <font id=前言>前言</font>

使用 [**Python**](https://www.python.org/) 与 [**PySide6**](https://doc.qt.io/qtforpython-6/) 编写的原生桌面单词学习软件，支持 macOS 和 Windows 本机打包。词库随程序携带；浏览、搜索与系统语音点读不需要联网。

## 一、用途

- 左侧选择初中、高中、大学 CET4、大学 CET6、英语专八、雅思 1～7 分学习档。
- 按 A–Z 分区浏览。非字母开头词条归入 `#`，分区显示当前搜索条件下的真实数量。
- 每行左上角是可点读单词，右侧完整列出词库已收录释义，不截断为首义。
- 点击具体释义进入二级页面；标题是可点读单词，下方例句、短语可逐条点读。
- 支持中英文搜索、分页、英语声音选择、语速调节和停止朗读。新点读中断上一次朗读。
- `Esc` 返回列表，`⌘F / Ctrl+F` 搜索。返回保留搜索、分区、页码及滚动位置。

## 二、直接运行

Mac 可直接双击外层 `./JobsEnglishWordBook.app` 快捷入口，或打开 `./JobsEnglishWordBook.dmg`。成功构建后的成品位于 `./dist/YYYY.MM.DD HH-mm-ss/JobsEnglishWordBook.app`，双击打开；同目录的 `JobsEnglishWordBook.dmg` 可打开后将 App 拖到 Applications。成品内含 Python 与界面依赖，不需要额外安装 Python 包。

源码启动入口：

| 入口 | 平台 | 行为 |
| --- | --- | --- |
| `./【MacOS】启动.command` | macOS | 展示说明、回车确认，检查 Python 后启动 |
| `./【Windows】启动.bat` | Windows | 展示说明、按键确认，检查 Python 后启动 |
| `./【MacOS】📦生成dmg.command` | macOS | 本机生成 `.app` 和 `.dmg` |
| `./【Windows】📦生成exe.bat` | Windows | 本机生成包含运行时的单文件 `.exe` |

源码和构建要求 Python 3.11+；当前实际验证版本为 Python 3.14、PySide6 6.11.2。当前 Qt macOS 依赖要求 macOS 13+；Windows 建议 Windows 10/11 64 位。Mac 构建按本机架构生成，当前产物为 Apple Silicon arm64；Intel Mac 需在 Intel Mac 上重新构建。

入口仅准备工程内 `./JobsEnglishWordBook/.venv`，并按当前工程位置加载 `src` 源码；移动或重命名工程后，无需为了本地源码导入重新联网安装。依赖检测失败时先显示具体错误。缺少依赖时另行询问：直接回车联网安装，输入任意字符后回车取消整个流程。不会主动升级系统 Python 或 Homebrew，不执行 Git 提交或推送。

发音依赖系统英语语音。Mac 可在系统辅助功能的语音设置中配置，Windows 可在系统语言与语音设置中安装英语声音。缺少英语声音时界面会明确提示。

## 三、词库标准与覆盖范围

覆盖标准是下表列出的公开备考词书合集，不是已核验的官方最新教学大纲。高级学段累计包含低级学段基础词；相同拼写忽略大小写合并，保留各来源释义、例句和短语，义项按词性和分号拆分，逗号不强行拆分。

| 难度 | 去重后词条数 |
| --- | ---: |
| 初中 | 1,418 |
| 高中（含初中） | 3,680 |
| 大学 CET4（含高中） | 5,287 |
| 大学 CET6（含 CET4） | 7,029 |
| 英语专八（含 CET6） | 12,818 |
| 雅思 1 分学习档 | 500 |
| 雅思 2 分学习档 | 1,000 |
| 雅思 3 分学习档 | 1,800 |
| 雅思 4 分学习档 | 3,000 |
| 雅思 5 分学习档 | 4,500 |
| 雅思 6 分学习档 | 6,000 |
| 雅思 7 分学习档 | 7,559 |

**雅思学习档是软件自定义的累计词频分级，不是官方逐分词表，也不是得分保证。** 词池由初中、高中、两本雅思词书并集组成，按 wordfreq 3.1.1 的通用英语 Zipf 词频从高到低排序；同频次按字母排序。评分含听说读写能力，参见 [IELTS 官方评分说明](https://ielts.org/take-a-test/your-results/ielts-scoring-in-detail)。

全库 13,430 个词条、25,832 条去重例句。844 个词条缺少例句，其中 541 个同时缺少短语；软件显示缺失状态。原词库没有逐义例句关联，二级页明确标注“该词参考用法”，不能保证每句对应当前点击义项。当前交付未达到“每个单词的所有意义均配齐专属例句”的语料要求。

九本词书原始行数均经过完整性验证：`ChuZhongluan_2`、`GaoZhongluan_2`、`CET4_2`、`CET4_3`、`CET6_2`、`CET6_3`、`Level8_2`、`IELTS_2`、`IELTS_3`。各文件地址、SHA-256、原始记录数、分级覆盖数和缺例句数量保存于 `./JobsEnglishWordBook/src/jobs_english_wordbook/assets/coverage.json`，应用内也可点击“词库与分级说明”。

## 四、工程与开发

```text
JobsEnglishWordBook.py/
├── README.md
├── 【MacOS】启动.command
├── 【MacOS】📦生成dmg.command
├── 【Windows】启动.bat
├── 【Windows】📦生成exe.bat
├── dist/YYYY.MM.DD HH-mm-ss/                 # 成品，仅保留最新构建
└── JobsEnglishWordBook/
    ├── pyproject.toml
    ├── src/jobs_english_wordbook/
    │   ├── app.py               # 界面与导航
    │   ├── catalog.py           # SQLite 只读查询
    │   ├── speech.py            # 系统英语语音
    │   └── assets/              # 词库、覆盖报告、来源说明
    ├── scripts/
    │   ├── bootstrap.py         # 独立环境准备
    │   ├── build.py             # PyInstaller + hdiutil
    │   ├── build_catalog.py     # 词库清洗、分级和完整性检查
    │   └── launch.py
    ├── tests/
    └── work/                   # 数据源缓存与构建中间文件
```

在 `./JobsEnglishWordBook` 下执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[build,test,corpus]'
.venv/bin/python -m jobs_english_wordbook.app
.venv/bin/python -m pytest -q
.venv/bin/python scripts/build.py
```

Windows 对应解释器路径为 `.venv\Scripts\python.exe`。Windows EXE 必须在 Windows 构建，不能从 Mac 直接交叉生成。

重建词库前将九本源词书 ZIP 保存到 `./JobsEnglishWordBook/work/sources/<书名>.zip`；本项目已保留下载缓存，来源可查覆盖报告。在内层工程执行：

```bash
.venv/bin/python scripts/build_catalog.py
```

重建词库需 `corpus` 开发依赖，运行成品不需要 wordfreq。SQLite 通过临时数据库构建、校验后替换，避免失败覆盖旧词库。可选的 `--ecdict 完整CSV路径` 用于接入 [ECDICT](https://github.com/skywind3000/ECDICT) 补充词义，但会改变词表、数量和分级；当前默认交付未使用 ECDICT，切换后需要同步覆盖报告和界面说明。

## 五、日志与验证

- 启动和构建日志：系统临时目录中的 `JobsEnglishWordBook-run.log` / `JobsEnglishWordBook-build.log`。
- GUI 异常日志：Qt 平台用户应用数据目录下的 `Jobs/JobsEnglishWordBook/logs/app.log`，异常弹窗会显示本机实际路径。
- 当前测试覆盖数据库完整性、源词书保留、全部字母分区、不漏词分页、累计分级、中文与特殊字符搜索，以及二级导航和点读文本。
- macOS `.command` 已做 `zsh -n`，Python 已做编译及测试；Windows `.bat` 已静态审查，Windows 打包与发音尚未在真机执行。
- 原始语料可能包含词义重复、同形异义词合并及词书本身的错误；覆盖率报告不等于教学内容人工审校。

## 六、数据与分发边界

词书取自 [kajweb/dict](https://github.com/kajweb/dict)，原始来源标注为有道及新东方相关词书，仓库未提供清晰的再分发许可。当前作为本地个人学习资料使用，公开发行或商用前应换成具有明确授权的数据。词频来自 [wordfreq](https://github.com/rspeer/wordfreq)，数据为 CC BY-SA 4.0，代码为 Apache 2.0。程序保留来源与修改说明；第三方材料不作为 Jobs 自有内容。

PySide6 / Qt 使用其相应开源许可，分发前应保留其许可文件并满足相关条件。当前 Mac App 未作 Developer ID 签名、公证；未制作 Windows 签名安装器。脚本不会绕过 Gatekeeper、关闭安全机制或修改系统权限。

## 七、常见问题

**为什么不是每个级别都对应一个固定的官方词数？**

不同教材、备考词书的收录标准不同。本程序完整导入指定来源并累计低学段基础词，按实际去重后的数量展示。

**为什么点击一个释义后能看到其他词义的例句？**

原词库的例句关联到单词，而不是每个义项。界面明确说明这一点；逐义对应需要有授权且经过审校的语料补全。

**成品需要联网吗？**

词库与已安装的系统语音可离线使用。首次源码环境安装、重新下载源资料、安装系统英语声音需要联网。

**构建失败会覆盖已有产物吗？**

每次构建先清理旧 dist，再写入新的时间戳目录。日志保留具体失败命令；已有损坏 `.venv` 会报错，需改名备份后重建。

打包前会清理该应用工程的旧 `dist` 产物，清理失败则停止；成功后自动打开当前平台产物的磁盘位置并运行本次生成的 APP / EXE，结尾无需回车。失败时不启动软件；运行前的防误触确认保留。

必需依赖缺失时，直接回车联网安装；输入任意字符后回车取消整个流程。安装失败或复检仍不可用时停止，不继续清理旧产物或打包。健康依赖直接复用；可选升级和词库更新仍为回车跳过、任意字符执行。

第一层交付目录与平台打包脚本同层保存 `dist/`，以及最新 APP / DMG 的相对符号链接（Mac）或 EXE / 分发包的 `.lnk`（Windows）。双击快捷方式即可接触成品，真实文件保留在 `dist/`；成功构建自动更新入口，清理旧产物时移除对应旧入口。尚无成品时不生成无效快捷方式。

构建产物使用本机本地构建时间，格式为 `YYYY.MM.DD HH-mm-ss`（年月日时分秒），例如 `2020.06.04 12-23-21`。每次构建的 APP、DMG、EXE、ZIP 和配套文件统一保存到交付层 `./dist/YYYY.MM.DD HH-mm-ss/`，同次构建只取一次时间；第一层快捷方式指向本次时间目录，成功后打开该目录并启动其中的软件。旧产物沿用原有清理规则；历史产物缺少可靠构建时间时，不补写推测时间。
