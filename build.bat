@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   Google TTS For NVDA - Add-on Builder
echo ============================================
echo.

cd /d "%~dp0"

:: --------------- Read version from manifest.ini ---------------
set "VERSION="
for /f "tokens=1,* delims==" %%A in ('findstr /b "version" googleTtsForNvda\manifest.ini') do (
    set "VERSION=%%B"
)
:: Trim leading/trailing spaces
for /f "tokens=*" %%V in ("!VERSION!") do set "VERSION=%%V"

if "!VERSION!"=="" (
    echo [ERROR] Could not read version from manifest.ini.
    exit /b 1
)
echo Version: !VERSION!
echo.

:: --------------- Clean build artifacts ---------------
echo [1/6] Cleaning build artifacts...
for /d /r "googleTtsForNvda" %%D in (__pycache__) do (
    if exist "%%D" (
        rmdir /s /q "%%D" 2>nul
        echo       Removed %%D
    )
)
if exist "googleTtsForNvda\googleTtsForNvda.nvda-addon" (
    del /f /q "googleTtsForNvda\googleTtsForNvda.nvda-addon" 2>nul
    echo       Removed stale .nvda-addon from source tree.
)
echo       Done.
echo.

:: --------------- Python syntax check ---------------
echo [2/6] Checking Python syntax...
python -m compileall -q googleTtsForNvda
if errorlevel 1 (
    echo [ERROR] Python syntax check failed.
    exit /b 1
)
echo       Passed.
echo.

:: --------------- JavaScript syntax check ---------------
echo [3/6] Checking JavaScript syntax...
node --check googleTtsForNvda\synthDrivers\googleTtsForNvda\web\bridgeHarness.js
if errorlevel 1 (
    echo [ERROR] JavaScript syntax check failed.
    exit /b 1
)
echo       Passed.
echo.

:: --------------- Verify no .zvoice in source ---------------
echo [4/6] Verifying no .zvoice files in source tree...
set "FOUND_ZVOICE=0"
for /r "googleTtsForNvda" %%F in (*.zvoice) do (
    echo       [ERROR] Found .zvoice file: %%F
    set "FOUND_ZVOICE=1"
)
if "!FOUND_ZVOICE!"=="1" (
    echo [ERROR] Voice data files must not be in the source tree.
    exit /b 1
)
echo       Clean - no .zvoice files found.
echo.

:: --------------- Clean __pycache__ created by compileall ---------------
echo [5/6] Cleaning __pycache__ created by syntax check...
for /d /r "googleTtsForNvda" %%D in (__pycache__) do (
    if exist "%%D" rmdir /s /q "%%D" 2>nul
)
echo       Done.
echo.

:: --------------- Package the add-on ---------------
set "OUTPUT=dist\googleTtsForNvda-!VERSION!.nvda-addon"
echo [6/6] Packaging add-on to %OUTPUT% ...

if not exist "dist" mkdir dist

:: Remove old build with same version if present
if exist "!OUTPUT!" del /f /q "!OUTPUT!"

:: Use PowerShell to create a temporary ZIP archive first, as Compress-Archive requires .zip extension
set "TEMP_ZIP=dist\temp_build.zip"
if exist "!TEMP_ZIP!" del /f /q "!TEMP_ZIP!"

powershell -NoProfile -Command "Compress-Archive -Path 'googleTtsForNvda\*' -DestinationPath '!TEMP_ZIP!' -Force"
if errorlevel 1 (
    echo [ERROR] Packaging failed.
    exit /b 1
)

:: Move/Rename the temporary zip to the final destination
move /y "!TEMP_ZIP!" "!OUTPUT!" >nul
if errorlevel 1 (
    echo [ERROR] Failed to rename package to .nvda-addon.
    exit /b 1
)

:: Show file size
for %%A in ("!OUTPUT!") do (
    set "SIZE=%%~zA"
)
echo       Created: !OUTPUT!
echo       Size:    !SIZE! bytes
echo.

echo ============================================
echo   Build complete: !OUTPUT!
echo ============================================
