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
echo  Step 1/4: Upgrading pip
echo ============================================
%PYTHON% -m pip install --upgrade pip --quiet

echo ============================================
echo  Step 2/4: Installing binary packages
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
echo  Step 3/4: Installing PyTorch with CUDA
echo ============================================
:: Check if CUDA-enabled torch is already installed
%PYTHON% -c "import torch; assert torch.cuda.is_available(), 'no cuda'" >nul 2>&1
if errorlevel 1 (
    echo PyTorch CUDA not detected - installing CUDA 12.1 build...
    %PYTHON% -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
    if errorlevel 1 (
        echo [ERROR] Failed to install PyTorch. Check your internet connection.
        pause
        exit /b 1
    )
) else (
    echo [OK] PyTorch with CUDA already installed.
)

echo ============================================
echo  Step 4/4: Installing remaining packages
echo ============================================
:: imageio-ffmpeg bundles its own ffmpeg binary - no system install needed
%PYTHON% -m pip install imageio-ffmpeg -r "%SCRIPT_DIR%requirements.txt"
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your internet connection.
    pause
    exit /b 1
)

:: Add the imageio-ffmpeg binary directory to PATH so nerfstudio can find ffmpeg
for /f "tokens=*" %%i in ('%PYTHON% -c "import pathlib, imageio_ffmpeg; print(pathlib.Path(imageio_ffmpeg.get_ffmpeg_exe()).parent)"') do set FFMPEG_DIR=%%i
set PATH=%FFMPEG_DIR%;%PATH%
echo [OK] FFmpeg ready at: %FFMPEG_DIR%

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
