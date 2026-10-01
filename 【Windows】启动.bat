@echo off
rem Jobs EnglishWordBook: prepare a project-local venv and run. No system packages are changed.
setlocal
chcp 65001 >nul
echo Jobs EnglishWordBook - run
echo Project-local .venv only. Missing dependencies: Enter to install; any character to cancel.
echo Output: dist with timestamp. Log: %%TEMP%%\JobsEnglishWordBook-run.log
echo Press any key to continue, or Ctrl+C to cancel.
pause >nul
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 -c "import sys,venv; assert sys.version_info >= (3,11)" >nul 2>nul
if errorlevel 1 goto use_python
py -3 "%~dp0JobsEnglishWordBook\scriptsootstrap.py" run
set "RESULT=%ERRORLEVEL%"
goto finish
:use_python
python -c "import sys,venv; assert sys.version_info >= (3,11)" >nul 2>nul
if errorlevel 1 goto missing
python "%~dp0JobsEnglishWordBook\scriptsootstrap.py" run
set "RESULT=%ERRORLEVEL%"
goto finish
:missing
echo Install Python 3.11 or newer from https://www.python.org/downloads/
set "RESULT=1"
:finish
echo Exit code: %RESULT%
pause
exit /b %RESULT%
