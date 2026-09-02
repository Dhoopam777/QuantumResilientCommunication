@echo off
REM Build script for QuantumResilientCommunication Launcher
REM Compiles launcher.py into a standalone EXE using PyInstaller

echo ============================================
echo Building QuantumResilientCommunication Launcher
echo ============================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [BUILD] PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo [BUILD] ERROR: Failed to install PyInstaller.
        exit /b 1
    )
)

REM Build the EXE
echo [BUILD] Compiling launcher.py to EXE...
python -m PyInstaller ^
    --onefile ^
    --console ^
    --name "QuantumResilientCommunication" ^
    --clean ^
    --noconfirm ^
    launcher.py

if errorlevel 1 (
    echo [BUILD] ERROR: PyInstaller build failed.
    exit /b 1
)

echo.
echo [BUILD] Build successful!
echo [BUILD] EXE location: dist\QuantumResilientCommunication.exe
echo.

REM Copy EXE to launcher directory
copy /Y "dist\QuantumResilientCommunication.exe" "QuantumResilientCommunication.exe" >nul
if errorlevel 1 (
    echo [BUILD] WARNING: Could not copy EXE to launcher directory.
) else (
    echo [BUILD] EXE copied to launcher directory.
)

echo.
echo [BUILD] Done!
pause