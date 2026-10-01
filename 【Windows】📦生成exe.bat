@echo off
rem Jobs EnglishWordBook: prepare a project-local venv and build. No system packages are changed.
setlocal
chcp 65001 >nul
echo Jobs EnglishWordBook - build
echo Project-local .venv only. Missing dependencies: Enter to install; any character to cancel.
echo Output: dist with timestamp. Log: %%TEMP%%\JobsEnglishWordBook-build.log
echo Press any key to continue, or Ctrl+C to cancel.
echo Output: dist\YYYY.MM.DD HH-mm-ss\ using local build time, shared by all artifacts.
echo Build clears old dist. On success, reveal output and launch the packaged app.
pause >nul
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 -c "import sys,venv; assert sys.version_info >= (3,11)" >nul 2>nul
if errorlevel 1 goto use_python
py -3 "%~dp0JobsEnglishWordBook\scriptsootstrap.py" build
set "RESULT=%ERRORLEVEL%"
goto finish
:use_python
python -c "import sys,venv; assert sys.version_info >= (3,11)" >nul 2>nul
if errorlevel 1 goto missing
python "%~dp0JobsEnglishWordBook\scriptsootstrap.py" build
set "RESULT=%ERRORLEVEL%"
goto finish
:missing
echo Install Python 3.11 or newer from https://www.python.org/downloads/
set "RESULT=1"
:finish
echo Exit code: %RESULT%
exit /b %RESULT%
