#!/bin/zsh
# 脚本自述：准备工程独立 Python 环境并run；仅修改当前工程和 dist。
# 首先展示说明并等待回车；缺失依赖需要另行选择安装；Ctrl+C 取消。
# shell: zsh
# 展示运行范围并等待确认，确认前不写入文件。
# 仅渲染自述：标题红色加粗，编号正文蓝色常规字重；非彩色终端输出纯文本。
jobs_intro_style() {
  local intro_color=0
  if [ -t 1 ] && [ -n "${TERM:-}" ] && [ "${TERM:-}" != dumb ] &&
     [ -z "${NO_COLOR+x}" ] && [ "${PLAIN_OUTPUT:-0}" != 1 ] &&
     [ "${IS_SOURCETREE_RUNTIME:-0}" != 1 ]; then
    intro_color=1
  fi
  /usr/bin/awk -v color="$intro_color" -v role="${1:-body}" '
    BEGIN { esc = sprintf("%c", 27) }
    {
      gsub(esc "\\[[0-9;]*m", "")
      gsub(/\\(033|e|x1[bB])\[[0-9;]*m/, "")
      if (!color || $0 ~ /^[[:space:]]*$/) { print; next }
      numbered = ($0 ~ /^[[:space:]➤ℹ🔹✔⚠]*([0-9]+[、.)）]|[0-9]+️⃣|[-•])/)
      heading = ($0 ~ /^[[:space:]]*#{1,6}[[:space:]]/ || $0 ~ /[：:][[:space:]]*$/ || $0 ~ /^[[:space:]]*[=━─-]{3}/)
      title = (!numbered && (role == "title" || heading))
      if (role == "auto" && !seen && !numbered) title = 1
      if ($0 !~ /^[[:space:]]*[=━─-]+[[:space:]]*$/) seen = 1
      printf "%s%s%s\n", esc (title ? "[1;31m" : "[0;34m"), $0, esc "[0m"
    }
  '
}
show_script_intro_and_wait() {
    print -r -- "Jobs EnglishWordBook · run" | jobs_intro_style body
    print -r -- "仅使用工程内 .venv；缺失依赖时回车联网安装，任意字符取消，不升级系统环境。" | jobs_intro_style body
    print -r -- "构建产物：当前目录 dist/时间戳；日志：系统临时目录 JobsEnglishWordBook-run.log。" | jobs_intro_style body
    print -r -- "按回车继续，Ctrl+C 取消。" | jobs_intro_style body
    [[ -t 0 ]] || { print -u2 -- "请在终端中运行以完成确认。"; exit 1; }
    read -r reply
}
# 确认后设置路径和日志。
initialize() {
    setopt NO_NOMATCH PIPE_FAIL
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" && pwd)"
    LOG_FILE="${TMPDIR:-/tmp/}JobsEnglishWordBook-run.log"
    : > "$LOG_FILE"
}
# 验证 Python 与标准库完整性。
check_environment() {
    command -v python3 >/dev/null || { print -u2 -- "请安装 Python 3.11+：https://www.python.org/downloads/"; exit 1; }
    python3 -c 'import sys, venv, pathlib; assert sys.version_info >= (3,11)' || exit 1
}
# 执行业务并保留日志和退出码。
run_business() {
    python3 "$SCRIPT_DIR/JobsEnglishWordBook/scripts/bootstrap.py" run 2>&1 | tee -a "$LOG_FILE"
    local result=$?
    if (( result != 0 )); then
        print -u2 -- "执行失败，日志：$LOG_FILE"
    else
        print -r -- "执行完成，日志：$LOG_FILE"
    fi
    read -r 'reply?按回车关闭：'
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
