"""为启动、打包准备工程独立虚拟环境；只补齐缺失依赖。"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]


def source_environment():
    """随工程定位源码，不依赖迁移前的 editable 安装路径。"""
    environment = os.environ.copy()
    paths = [str(ROOT / "src")]
    if environment.get("PYTHONPATH"):
        paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    return environment


def call(args):
    log_path = Path(tempfile.gettempdir()) / f"JobsEnglishWordBook-{ACTION}.log"
    with log_path.open("a", encoding="utf-8") as log:
        log.write("执行：" + repr(args) + "\n")
        with subprocess.Popen(args, cwd=ROOT, env=source_environment(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1) as process:
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
            result = process.wait()
    if result:
        raise SystemExit(f"执行失败 ({result})，日志：{log_path}")


def confirm_required_install(message):
    """缺失必需依赖时回车安装，任何非空输入取消整个流程。"""
    try:
        answer = input(message + "：直接回车安装，输入任意字符后回车取消：")
    except EOFError:
        raise SystemExit("没有交互输入，已取消依赖安装。")
    if answer != "":
        raise SystemExit("已取消依赖安装，停止当前流程。")


def main():
    global ACTION
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "build"])
    args = parser.parse_args()
    ACTION = args.action
    if sys.version_info < (3, 11):
        raise SystemExit("请安装 Python 3.11 或更高版本。")
    env = ROOT / ".venv"
    python = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(env)
    probe = subprocess.run([str(python), "-c", "import sys, pip; assert sys.version_info >= (3,11)"], capture_output=True)
    if probe.returncode:
        raise SystemExit("工程 .venv 已损坏，请将它改名备份后重新运行。未修改系统 Python。")
    modules = ["PySide6.QtWidgets", "jobs_english_wordbook"] + (["PyInstaller"] if args.action == "build" else [])
    test = subprocess.run([str(python), "-c", ";".join(f"import {m}" for m in modules)], cwd=ROOT, env=source_environment(), capture_output=True, text=True)
    if test.returncode:
        print("依赖检测失败：\n" + test.stderr.strip(), flush=True)
        confirm_required_install("需要联网补齐工程依赖")
        package = str(ROOT) + ("[build]" if args.action == "build" else "")
        call([str(python), "-m", "pip", "install", "-e", package])
        call([str(python), "-c", ";".join(f"import {m}" for m in modules)])
    if args.action == "build":
        call([str(python), str(ROOT / "scripts/build.py")])
    else:
        call([str(python), "-m", "jobs_english_wordbook.app"])


if __name__ == "__main__":
    main()
