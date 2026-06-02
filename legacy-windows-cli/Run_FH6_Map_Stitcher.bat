@echo off
setlocal EnableExtensions EnableDelayedExpansion

title FH6 Map Stitcher

set "ROOT=%~dp0"
set "INPUT_DIR=%ROOT%input"
set "OUTPUT_DIR=%ROOT%output"
set "TOOLS_DIR=%ROOT%tools"
set "SCRIPT=%TOOLS_DIR%\fh6_map_stitcher.py"
set "VENV_DIR=%ROOT%.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "OUTPUT_FILE=%OUTPUT_DIR%\stitched_map.png"
set "COVERAGE_FILE=%OUTPUT_DIR%\coverage_map.png"

echo.
echo ============================================================
echo  FH6 Map Stitcher
echo ============================================================
echo.

if not exist "%INPUT_DIR%" mkdir "%INPUT_DIR%"
if errorlevel 1 goto mkdir_error
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
if errorlevel 1 goto mkdir_error
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"
if errorlevel 1 goto mkdir_error

if not exist "%SCRIPT%" (
    echo ERROR: Could not find:
    echo   "%SCRIPT%"
    echo.
    echo Make sure this BAT file is still next to the tools folder.
    goto end_error
)

echo Looking for Python...
set "PYTHON_CMD="

py -3 --version >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"

if not defined PYTHON_CMD (
    python --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    python3 --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python3"
)

if not defined PYTHON_CMD (
    echo.
    echo ERROR: Python was not found.
    echo Install Python 3 from https://www.python.org/downloads/windows/
    echo During install, enable "Add python.exe to PATH".
    goto end_error
)

echo Found Python: %PYTHON_CMD%
echo.

if not exist "%VENV_PY%" (
    echo Creating local virtual environment:
    echo   "%VENV_DIR%"
    call %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create the local .venv folder.
        goto end_error
    )
) else (
    echo Using existing local virtual environment.
)

echo.
echo Installing/updating required packages inside .venv...
echo   pillow
echo   numpy
echo   opencv-python
echo.
"%VENV_PY%" -m pip install --upgrade pillow numpy opencv-python
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install Python dependencies.
    goto end_error
)

set "HAS_IMAGE=0"
for %%f in ("%INPUT_DIR%\*.png") do if exist "%%~f" set "HAS_IMAGE=1"
for %%f in ("%INPUT_DIR%\*.jpg") do if exist "%%~f" set "HAS_IMAGE=1"
for %%f in ("%INPUT_DIR%\*.jpeg") do if exist "%%~f" set "HAS_IMAGE=1"
for %%f in ("%INPUT_DIR%\*.bmp") do if exist "%%~f" set "HAS_IMAGE=1"
for %%f in ("%INPUT_DIR%\*.tif") do if exist "%%~f" set "HAS_IMAGE=1"
for %%f in ("%INPUT_DIR%\*.tiff") do if exist "%%~f" set "HAS_IMAGE=1"

if "%HAS_IMAGE%"=="0" (
    echo.
    echo WARNING: No supported image files found in:
    echo   "%INPUT_DIR%"
    echo.
    echo Supported: PNG - best, JPG/JPEG, BMP, TIF/TIFF
    goto end_ok
)

echo.
set "CROP_CHOICE=Y"
set /p "CROP_CHOICE=Crop map UI from screenshots? Y/N [Y]: "
set "CROP_ARGS=--crop-top 60 --crop-bottom 55"
if /I "%CROP_CHOICE%"=="N" set "CROP_ARGS=--no-crop"

echo.
echo ============================================================
echo  Running stitcher
echo ============================================================
echo.
echo Input folder:
echo   "%INPUT_DIR%"
echo Output file:
echo   "%OUTPUT_FILE%"
echo Coverage map:
echo   "%COVERAGE_FILE%"
echo.

"%VENV_PY%" "%SCRIPT%" ^
    --input "%INPUT_DIR%" ^
    --output "%OUTPUT_FILE%" ^
    --coverage-output "%COVERAGE_FILE%" ^
    %CROP_ARGS% ^
    --mode manual ^
    --quality 3

if errorlevel 1 (
    echo.
    echo ERROR: The stitcher stopped because of an error.
    goto end_error
)

echo.
echo ============================================================
echo  Done
echo ============================================================
echo.
echo Stitched map:
echo   "%OUTPUT_FILE%"
echo Coverage map:
echo   "%COVERAGE_FILE%"
echo.
echo Orange checkerboard areas = likely gaps. Add more screenshots there and run again.
if exist "%OUTPUT_FILE%" (
    echo.
    echo Opening stitched map...
    start "" "%OUTPUT_FILE%"
)
if exist "%COVERAGE_FILE%" (
    echo Opening coverage map...
    start "" "%COVERAGE_FILE%"
)
goto end_ok

:mkdir_error
echo.
echo ERROR: Could not create input/output/tools folders.
goto end_error

:end_error
echo.
pause
exit /b 1

:end_ok
echo.
pause
exit /b 0
