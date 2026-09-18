@echo off
setlocal
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed --collect-all customtkinter --name FolderLauncher app.py
if errorlevel 1 exit /b 1
echo.
echo Built: dist\FolderLauncher.exe
pause
