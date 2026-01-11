@echo off
chcp 65001 >nul
echo === 实验室打印系统启动 ===
cd /d "%~dp0.."
call venv\Scripts\activate.bat
python run.py
pause

