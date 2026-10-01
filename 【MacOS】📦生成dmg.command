#!/bin/zsh
# 脚本自述：准备工程独立 Python 环境并build；仅修改当前工程和 dist。
# 首先展示说明并等待回车；缺失依赖需要另行选择安装；Ctrl+C 取消。
# shell: zsh
# 展示运行范围并等待确认，确认前不写入文件。
show_script_intro_and_wait() {
    print -r -- "Jobs EnglishWordBook · build"
    print -r -- "仅使用工程内 .venv；缺失依赖时回车联网安装，任意字符取消，不升级系统环境。"
    print -r -- "构建产物：当前目录 dist/YYYY.MM.DD HH-mm-ss；日志：系统临时目录 JobsEnglishWordBook-build.log。"
    print -r -- "按回车继续，Ctrl+C 取消。"
    [[ -t 0 ]] || { print -u2 -- "请在终端中运行以完成确认。"; exit 1; }
    print '构建产物按本机年月日时分秒保存到 dist/YYYY.MM.DD HH-mm-ss/（例如 2020.06.04 12-23-21），同次构建共用一个时间目录。'
    print '打包前清理旧 dist；成功后在第一层更新产物快捷方式、打开目录并启动本机软件。'
    read -r reply
}
# 确认后设置路径和日志。
initialize() {
    setopt NO_NOMATCH PIPE_FAIL
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" && pwd)"
    LOG_FILE="${TMPDIR:-/tmp/}JobsEnglishWordBook-build.log"
    : > "$LOG_FILE"
}
# 验证 Python 与标准库完整性。
check_environment() {
    command -v python3 >/dev/null || { print -u2 -- "请安装 Python 3.11+：https://www.python.org/downloads/"; exit 1; }
    python3 -c 'import sys, venv, pathlib; assert sys.version_info >= (3,11)' || exit 1
}
# 执行业务并保留日志和退出码。
run_business() {
    python3 "$SCRIPT_DIR/JobsEnglishWordBook/scripts/bootstrap.py" build 2>&1 | tee -a "$LOG_FILE"
    local result=$?
    if (( result != 0 )); then
        print -u2 -- "执行失败，日志：$LOG_FILE"
    else
        print -r -- "执行完成，日志：$LOG_FILE"
    fi
    exit "$result"
}
# 编排自述、环境检查与执行。
main() {
    show_script_intro_and_wait # 先确认用途与影响范围。
    initialize # 初始化当前脚本路径与日志。
    check_environment # 确认 Python 和标准库健康。
    run_business # 执行启动或本机打包。
}
main "$@"
