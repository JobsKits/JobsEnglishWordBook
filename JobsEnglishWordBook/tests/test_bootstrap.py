"""验证迁移后的源码导入不依赖旧 editable 安装位置。"""
import importlib.util
from pathlib import Path
import subprocess
import sys


def test_source_import_from_unrelated_directory(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts/bootstrap.py"
    spec = importlib.util.spec_from_file_location("bootstrap", path)
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    project = tmp_path / "迁移后的工程"
    package = project / "src/jobs_english_wordbook"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('MARKER = "relocated"\n')
    monkeypatch.setattr(bootstrap, "ROOT", project)
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "旧路径"))
    result = subprocess.run(
        [sys.executable, "-c", 'import jobs_english_wordbook as p; assert p.MARKER == "relocated"'],
        cwd=tmp_path, env=bootstrap.source_environment(), capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
