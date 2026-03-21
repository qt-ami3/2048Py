@echo off
REM 2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
REM Do not redistribute or reuse code without accrediting and explicit permission from author.
REM Contact:
REM +1 (808) 223 4780
REM riverknuuttila2@outlook.com

setlocal

REM Get the directory of this script
set "SCRIPT_DIR=%~dp0"
set "BUILD_DIR=%SCRIPT_DIR%build"

REM Get pybind11 cmake dir from venv
for /f "delims=" %%i in ('"%SCRIPT_DIR%src\venv\Scripts\python.exe" -m pybind11 --cmakedir') do set "PYBIND11_DIR=%%i"
if "%PYBIND11_DIR%"=="" (
    echo ERROR: Could not find pybind11. Install it with: pip install pybind11
    exit /b 1
)

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
if exist "%BUILD_DIR%\CMakeCache.txt" del "%BUILD_DIR%\CMakeCache.txt"
cd /d "%BUILD_DIR%"

cmake ..\src\engine -Dpybind11_DIR="%PYBIND11_DIR%" -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 (
    echo ERROR: CMake configuration failed.
    exit /b 1
)

cmake --build . --config Release -j
if errorlevel 1 (
    echo ERROR: Build failed.
    exit /b 1
)

REM Copy the built .pyd file to src/
for %%f in (Release\game2048_engine*.pyd) do copy /Y "%%f" "%SCRIPT_DIR%src\"
if errorlevel 1 (
    echo ERROR: Failed to copy built module.
    exit /b 1
)

echo Build successful.
endlocal
