@echo off
setlocal EnableDelayedExpansion

:: ============================================================================
:: NextGenPoliceDepartment - Automated Windows Setup, Build & Packaging Script
:: Target Hardware Profile: AMD Radeon RX 580 2048SP | Ryzen 5 3600X | 16 GB RAM
:: Engine Target: Multi Theft Auto: San Andreas (MTA:SA) 1.6+ (DirectX 9)
:: ============================================================================

cd /d "%~dp0"
if not exist "build" mkdir "build"
if not exist "dist" mkdir "dist"
set "LOGFILE=%~dp0build\setup_and_build.log"

echo ============================================================================ > "%LOGFILE%"
echo [NGPD] NextGenPoliceDepartment Setup ^& Build Started at %DATE% %TIME% >> "%LOGFILE%"
echo ============================================================================ >> "%LOGFILE%"

echo.
echo ============================================================================
echo   NextGenPoliceDepartment - Photorealistic Golden-Hour ^& 4K Upscaler Build
echo   Target Profile: AMD Radeon RX 580 2048SP / Ryzen 5 3600X / 16 GB RAM
echo ============================================================================
echo.

:: Parse CLI flags (--rebuild, --install, --install-deps)
set "DO_REBUILD=0"
set "DO_INSTALL=0"
set "DO_DEPS=0"
for %%A in (%*) do (
    if /I "%%~A"=="--rebuild" set "DO_REBUILD=1"
    if /I "%%~A"=="--install" set "DO_INSTALL=1"
    if /I "%%~A"=="--install-deps" set "DO_DEPS=1"
)

:: 1. Detect Python 3
echo [1/6] Checking Python 3 environment...
set "PYTHON_CMD="
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=py -3"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python 3 was not found in PATH. Please install Python 3.10+ from https://www.python.org/
    echo [ERROR] Python 3 missing >> "%LOGFILE%"
    exit /b 1
)
echo       Found Python command: %PYTHON_CMD%
echo [INFO] Python command: %PYTHON_CMD% >> "%LOGFILE%"

:: 2. Check / install Python dependencies
echo [2/6] Verifying required Python packages (numpy, Pillow, scipy, lupa)...
if "%DO_DEPS%"=="1" (
    %PYTHON_CMD% -m pip install --upgrade numpy Pillow scipy lupa >> "%LOGFILE%" 2>&1
)
%PYTHON_CMD% -c "import numpy, PIL, scipy, lupa; print('       Python dependencies OK')" 2>>"%LOGFILE%"
if %ERRORLEVEL% NEQ 0 (
    echo       Installing missing Python packages via pip...
    %PYTHON_CMD% -m pip install numpy Pillow scipy lupa >> "%LOGFILE%" 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install Python dependencies. See "%LOGFILE%".
        exit /b 1
    )
)

:: 3. Optional C++ DX9 Spatial Upscaler DLL compilation (MinGW g++ or MSVC cl)
echo [3/6] Checking optional C++ compiler for standalone DX9 4K Upscaler DLL...
where g++ >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo       Compiling source\dx9_upscaler_dll\ngpd_dx9_upscaler.dll with g++...
    g++ -O3 -std=c++17 -shared "source\dx9_upscaler_dll\ngpd_dx9_upscaler.cpp" -o "dist\ngpd_dx9_upscaler.dll" >> "%LOGFILE%" 2>&1
) else (
    where cl >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo       Compiling source\dx9_upscaler_dll\ngpd_dx9_upscaler.dll with MSVC cl.exe...
        cl /O2 /LD /EHsc "source\dx9_upscaler_dll\ngpd_dx9_upscaler.cpp" /Fe:"dist\ngpd_dx9_upscaler.dll" >> "%LOGFILE%" 2>&1
    ) else (
        echo       No C++ compiler in PATH (skipping standalone DLL; MTA uses HLSL upscale_easu.fx + upscale_rcas.fx).
    )
)

:: 4. Optional full asset rebuild (--rebuild)
if "%DO_REBUILD%"=="1" (
    echo [4/6] Rebuilding PBR TXD/DDS textures and 3D botanical vegetation models...
    %PYTHON_CMD% "tools\rebuild_textures.py" >> "%LOGFILE%" 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Texture synthesis failed. See "%LOGFILE%".
        exit /b 1
    )
    %PYTHON_CMD% "tools\rebuild_models.py" >> "%LOGFILE%" 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] 3D Model / vegetation rebuild failed. See "%LOGFILE%".
        exit /b 1
    )
) else (
    echo [4/6] Using pre-built PBR textures (textures\) and 3D models (models\ ^& collisions\).
    echo       (Pass --rebuild to regenerate all textures and 3D models from source.)
)

:: 5. Run Automated Asset, Shader & Lua Runtime Validation Suite
echo [5/6] Running automated QA ^& validation suite (tests\run_all_tests.py)...
%PYTHON_CMD% "tests\run_all_tests.py" >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Validation suite reported failures! Check "%LOGFILE%" and "tests\test_report.json".
    type "%LOGFILE%"
    exit /b 1
)
echo       All 8 automated validation suites PASSED (0 FAILED).

:: 6. Package ready-to-install MTA:SA resource archive
echo [6/6] Packaging dist\NextGenPoliceDepartment.zip...
%PYTHON_CMD% "tools\package_release.py" >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Resource packaging failed! See "%LOGFILE%".
    exit /b 1
)
echo       Packaged: "%~dp0dist\NextGenPoliceDepartment.zip"

:: Auto-detect MTA:SA 1.6 Server resources folder
set "MTA_RES_DIR="
if not "%MTA_SERVER_DIR%"=="" (
    if exist "%MTA_SERVER_DIR%\mods\deathmatch\resources" set "MTA_RES_DIR=%MTA_SERVER_DIR%\mods\deathmatch\resources"
)
if "%MTA_RES_DIR%"=="" (
    if exist "C:\Program Files (x86)\MTA San Andreas 1.6\server\mods\deathmatch\resources" (
        set "MTA_RES_DIR=C:\Program Files (x86)\MTA San Andreas 1.6\server\mods\deathmatch\resources"
    ) else if exist "C:\Program Files\MTA San Andreas 1.6\server\mods\deathmatch\resources" (
        set "MTA_RES_DIR=C:\Program Files\MTA San Andreas 1.6\server\mods\deathmatch\resources"
    )
)

if not "%MTA_RES_DIR%"=="" (
    echo       Detected MTA:SA resources directory: "%MTA_RES_DIR%"
    if "%DO_INSTALL%"=="1" (
        echo       Installing NextGenPoliceDepartment.zip into "%MTA_RES_DIR%"...
        copy /Y "dist\NextGenPoliceDepartment.zip" "%MTA_RES_DIR%\NextGenPoliceDepartment.zip" >> "%LOGFILE%" 2>&1
        echo       Installed successfully! Run "refresh" and "start NextGenPoliceDepartment" in MTA Server console.
    ) else (
        echo       Tip: Run "setup_and_build.bat --install" to copy directly into "%MTA_RES_DIR%".
    )
) else (
    echo       Copy "dist\NextGenPoliceDepartment.zip" to your MTA Server "mods\deathmatch\resources\" folder.
)

echo.
echo ============================================================================
echo   BUILD ^& VALIDATION SUCCEEDED!
echo   Deliverable ZIP : dist\NextGenPoliceDepartment.zip
echo   Build Log       : build\setup_and_build.log
echo   Test Report     : tests\test_report.json
echo ============================================================================
exit /b 0
