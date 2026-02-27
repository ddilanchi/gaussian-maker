@echo off
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set INPUT_DIR=%SCRIPT_DIR%input
set OUTPUT_DIR=%SCRIPT_DIR%output
set PYTHONPATH=%SCRIPT_DIR%
set PYTHON=python
set GM=%PYTHON% -m gaussian_maker.cli

echo ============================================
echo  Gaussian Maker
echo ============================================
echo  Input folder:  %INPUT_DIR%
echo  Output folder: %OUTPUT_DIR%
echo ============================================
echo.

:: Verify Python is available
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)

echo ============================================
echo  Step 1/5: Upgrading pip
echo ============================================
%PYTHON% -m pip install --upgrade pip --quiet

echo ============================================
echo  Step 2/5: Installing binary packages
echo ============================================
%PYTHON% -m pip install fpsample --prefer-binary
if errorlevel 1 (
    echo [ERROR] Could not install fpsample.
    echo Install Visual Studio C++ Build Tools from:
    echo   https://visualstudio.microsoft.com/visual-cpp-build-tools/
    pause
    exit /b 1
)

echo ============================================
echo  Step 3/5: Installing PyTorch with CUDA 12.1
echo ============================================
:: Always force-install the CUDA build to replace any CPU-only version
echo Installing PyTorch CUDA 12.1 (this may take a few minutes)...
%PYTHON% -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install PyTorch. Check your internet connection.
    pause
    exit /b 1
)
:: Confirm CUDA is now available
%PYTHON% -c "import torch; print('  GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NOT FOUND - check NVIDIA drivers')"

echo ============================================
echo  Step 4/5: Installing remaining packages
echo ============================================
%PYTHON% -m pip install imageio-ffmpeg -r "%SCRIPT_DIR%requirements.txt" --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your internet connection.
    pause
    exit /b 1
)

echo ============================================
echo  Step 5/5: Setting up FFmpeg
echo ============================================
:: imageio-ffmpeg ships a binary like "ffmpeg-win64-v7.0.2.exe"
:: Copy it as plain "ffmpeg.exe" so nerfstudio's shutil.which("ffmpeg") finds it
set FFMPEG_WRAPPER=%SCRIPT_DIR%.ffmpeg
if not exist "%FFMPEG_WRAPPER%" mkdir "%FFMPEG_WRAPPER%"

for /f "tokens=*" %%i in ('%PYTHON% -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"') do set FFMPEG_EXE=%%i
copy /y "%FFMPEG_EXE%" "%FFMPEG_WRAPPER%\ffmpeg.exe" >nul
set PATH=%FFMPEG_WRAPPER%;%PATH%
echo [OK] FFmpeg ready: %FFMPEG_WRAPPER%\ffmpeg.exe

echo.
echo [OK] All dependencies ready.
echo.

:: Check for video files in input folder
set VIDEO_COUNT=0
for %%F in ("%INPUT_DIR%\*.mp4" "%INPUT_DIR%\*.MOV" "%INPUT_DIR%\*.mov" "%INPUT_DIR%\*.avi" "%INPUT_DIR%\*.mkv" "%INPUT_DIR%\*.webm") do (
    if exist "%%F" set /a VIDEO_COUNT+=1
)

if %VIDEO_COUNT%==0 (
    echo No video files found in input folder.
    echo.
    echo Drop your video files ^(.mp4, .MOV, .avi, .mkv^) into:
    echo   %INPUT_DIR%
    echo.
    pause
    exit /b 1
)

echo Found %VIDEO_COUNT% video file(s). Processing...
echo.

:: Process each video file
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
echo  All done. Check the output folder:
echo  %OUTPUT_DIR%
echo ============================================
echo.
pause
