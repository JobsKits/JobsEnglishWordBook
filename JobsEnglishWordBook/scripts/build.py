"""本机打包：macOS 生成 app / dmg，Windows 生成独立 exe。"""
import argparse
from datetime import datetime
import logging
from artifact_shortcuts import clear_shortcuts, publish_shortcuts
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(command):
    logging.info("执行：%s", command)
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-only", action="store_true")
    args = parser.parse_args()
    if sys.platform not in ("darwin", "win32"):
        raise SystemExit("请在 macOS 或 Windows 本机打包。")
    logging.basicConfig(level=logging.INFO)
    stamp = datetime.now().strftime("%Y.%m.%d %H-%M-%S")
    dist_root = ROOT.parent / "dist"
    if dist_root.is_symlink():
        raise SystemExit("拒绝清理符号链接 dist，请检查输出目录。")
    clear_shortcuts(ROOT.parent)
    if dist_root.exists():
        shutil.rmtree(dist_root)
    output = ROOT.parent / "dist" / stamp
    assets = ROOT / "src/jobs_english_wordbook/assets"
    if not (assets / "catalog.sqlite3").is_file():
        raise SystemExit("缺少离线词库，请先构建词库。")
    mode = "--onedir" if sys.platform == "darwin" else "--onefile"
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", mode,
               "--name", "JobsEnglishWordBook", "--paths", str(ROOT / "src"),
               "--add-data", f"{assets}:jobs_english_wordbook/assets",
               "--distpath", str(output), "--workpath", str(ROOT / "work/build" / stamp),
               "--specpath", str(ROOT / "work/spec"), str(ROOT / "scripts/launch.py")]
    if sys.platform == "darwin":
        command.extend(["--osx-bundle-identifier", "com.jobs.englishwordbook"])
    run(command)
    if sys.platform == "darwin" and not args.app_only:
        if not shutil.which("hdiutil"):
            raise SystemExit("app 已生成，但未找到 hdiutil，无法生成 dmg。")
        stage = ROOT / "work/dmg" / stamp
        stage.mkdir(parents=True)
        shutil.copytree(output / "JobsEnglishWordBook.app", stage / "JobsEnglishWordBook.app", symlinks=True)
        (stage / "Applications").symlink_to("/Applications")
        run(["hdiutil", "create", "-volname", "JobsEnglishWordBook", "-srcfolder", str(stage), "-format", "UDZO", str(output / "JobsEnglishWordBook.dmg")])
    logging.info("打包完成：%s", output)
    artifact = output / "JobsEnglishWordBook.app" if sys.platform == "darwin" else output / "JobsEnglishWordBook.exe"
    if not artifact.exists():
        raise SystemExit("构建产物不存在：" + str(artifact))
    packages = sorted(output.glob("*.dmg" if sys.platform == "darwin" else "*.zip"))
    publish_shortcuts(ROOT.parent, [artifact, *packages])
    if sys.platform == "darwin":
        subprocess.run(["open", str(output)], check=True)
        subprocess.run(["open", str(output / "JobsEnglishWordBook.app")], check=True)
    else:
        subprocess.run(["explorer.exe", str(output)], check=False)
        subprocess.Popen([str(output / "JobsEnglishWordBook.exe")], cwd=output)



if __name__ == "__main__":
    main()
