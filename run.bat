@echo off
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set INPUT_DIR=%SCRIPT_DIR%input
set OUTPUT_DIR=%SCRIPT_DIR%output
set PYTHONPATH=%SCRIPT_DIR%
set PYTHON=python
set GM=%PYTHON% -m gaussian_maker.cli

:: Pre-compute tool dirs using immediate expansion (no delayed expansion issues)
set FFMPEG_DIR=%SCRIPT_DIR%.ffmpeg
set COLMAP_DIR=%SCRIPT_DIR%.colmap
set COLMAP_EXE=%SCRIPT_DIR%.colmap\colmap.exe

echo ============================================
echo  Gaussian Maker
echo ============================================
echo  Input folder:  %INPUT_DIR%
echo  Output folder: %OUTPUT_DIR%
echo ============================================
echo.

%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)

echo ============================================
echo  Step 1/6: Upgrading pip
echo ============================================
%PYTHON% -m pip install --upgrade pip --quiet

echo ============================================
echo  Step 2/6: Installing binary packages
echo ============================================
%PYTHON% -m pip install fpsample --prefer-binary --quiet
if errorlevel 1 (
    echo [ERROR] Could not install fpsample.
    echo Install Visual Studio C++ Build Tools:
    echo   https://visualstudio.microsoft.com/visual-cpp-build-tools/
    pause & exit /b 1
)
echo [OK] Binary packages ready.

echo ============================================
echo  Step 3/6: Installing PyTorch with CUDA
echo ============================================
echo Trying CUDA 12.4...
%PYTHON% -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 --force-reinstall --quiet
%PYTHON% -c "import torch; exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
if errorlevel 1 (
    echo Trying CUDA 11.8...
    %PYTHON% -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118 --force-reinstall --quiet
    %PYTHON% -c "import torch; exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] GPU not detected - will use CPU. Update NVIDIA drivers if you have a GPU.
    ) else (
        for /f "tokens=*" %%g in ('%PYTHON% -c "import torch; print(torch.cuda.get_device_name(0))"') do echo [OK] GPU: %%g
    )
) else (
    for /f "tokens=*" %%g in ('%PYTHON% -c "import torch; print(torch.cuda.get_device_name(0))"') do echo [OK] GPU: %%g
)

echo ============================================
echo  Step 4/6: Installing Python packages
echo ============================================
%PYTHON% -m pip install imageio-ffmpeg -r "%SCRIPT_DIR%requirements.txt" --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your internet connection.
    pause & exit /b 1
)
echo [OK] Python packages ready.

echo ============================================
echo  Step 5/6: Setting up FFmpeg
echo ============================================
if not exist "%FFMPEG_DIR%" mkdir "%FFMPEG_DIR%"
for /f "tokens=*" %%i in ('%PYTHON% -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"') do (
    copy /y "%%i" "%FFMPEG_DIR%\ffmpeg.exe" >nul
)
set PATH=%FFMPEG_DIR%;%PATH%
echo [OK] FFmpeg ready.

echo ============================================
echo  Step 6/6: Setting up COLMAP
echo ============================================
where colmap >nul 2>&1
if not errorlevel 1 (
    echo [OK] COLMAP already on PATH.
    goto colmap_done
)

if exist "%COLMAP_EXE%" (
    echo [OK] Using cached COLMAP.
    goto colmap_found
)

echo Downloading COLMAP 3.10 for Windows (~300 MB)...
if not exist "%COLMAP_DIR%" mkdir "%COLMAP_DIR%"
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/colmap/colmap/releases/download/3.10/colmap-x86_64-windows-cuda.zip' -OutFile '%TEMP%\colmap.zip'"
if errorlevel 1 (
    echo [ERROR] Failed to download COLMAP. Check internet connection.
    pause & exit /b 1
)
echo Extracting...
powershell -NoProfile -Command "Expand-Archive -Path '%TEMP%\colmap.zip' -DestinationPath '%COLMAP_DIR%' -Force"
del /q "%TEMP%\colmap.zip" >nul 2>&1

:: COLMAP zip extracts colmap.exe to root of the archive = %COLMAP_DIR%\colmap.exe
:: If it's nested in a subfolder, move it up
if not exist "%COLMAP_EXE%" (
    for /f "tokens=*" %%f in ('dir /b /s "%COLMAP_DIR%\colmap.exe" 2^>nul') do (
        copy /y "%%f" "%COLMAP_EXE%" >nul 2>&1
        goto colmap_found
    )
    echo [ERROR] colmap.exe not found after extraction.
    pause & exit /b 1
)

:colmap_found
set PATH=%COLMAP_DIR%;%PATH%
echo [OK] COLMAP ready.

:colmap_done
echo.
echo [OK] All dependencies ready. Starting pipeline...
echo.

:: Check for video files
set VIDEO_COUNT=0
for %%F in ("%INPUT_DIR%\*.mp4" "%INPUT_DIR%\*.MOV" "%INPUT_DIR%\*.mov" "%INPUT_DIR%\*.avi" "%INPUT_DIR%\*.mkv" "%INPUT_DIR%\*.webm") do (
    if exist "%%F" set /a VIDEO_COUNT+=1
)

if %VIDEO_COUNT%==0 (
    echo No video files found in input folder.
    echo Drop your videos into: %INPUT_DIR%
    echo.
    pause & exit /b 1
)

echo Found %VIDEO_COUNT% video file(s). Processing...
echo.

for %%F in ("%INPUT_DIR%\*.mp4" "%INPUT_DIR%\*.MOV" "%INPUT_DIR%\*.mov" "%INPUT_DIR%\*.avi" "%INPUT_DIR%\*.mkv" "%INPUT_DIR%\*.webm") do (
    if exist "%%F" (
        set VIDEO_NAME=%%~nF
        echo ------------------------------------------
        echo Processing: %%~nxF
        echo ------------------------------------------
        %GM% run "%%F" --output "%OUTPUT_DIR%\!VIDEO_NAME!" --trainer nerfstudio --fps 2 --format ply --format splat
        if errorlevel 1 (
            echo.
            echo [ERROR] Failed to process %%~nxF
            echo.
        ) else (
            echo.
            echo [DONE] Output saved to: %OUTPUT_DIR%\!VIDEO_NAME!
            echo.
        )
    )
)

echo ============================================
echo  All done! Check: %OUTPUT_DIR%
echo ============================================
echo.
pause
